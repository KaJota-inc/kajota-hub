import 'dotenv/config'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import Fastify from 'fastify'
import { makeMemoryService, type ChatBlob, type VerdictBlob } from './lib/memory.js'
import { deliberate } from './lib/jury.js'
import { anchorVerdict, disputeIdOf, isAnchorEnabled, getVerdictFromChain } from './lib/anchor.js'

const REQUIRED = ['ZG_RPC_URL', 'ZG_INDEXER_URL', 'WITNESS_DEPLOYER_PK', 'GROQ_API_KEY'] as const

function loadEnv() {
  for (const k of REQUIRED) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      process.exit(1)
    }
  }
  return {
    rpcUrl: process.env.ZG_RPC_URL!,
    indexerUrl: process.env.ZG_INDEXER_URL!,
    privateKey: process.env.WITNESS_DEPLOYER_PK!,
    indexPath: process.env.INDEX_PATH ?? './data/index.json',
    port: Number.parseInt(process.env.PORT ?? '4022', 10),
  }
}

type WriteChatBody = ChatBlob

type EvidenceQueryBody = {
  query: string
  sellerId?: string
  k?: number
}

type DisputeBody = {
  sellerId: string
  buyerId?: string
  claim: string
  evidenceQuery?: string
  k?: number
}

type ListQuery = {
  kind?: 'chat' | 'verdict'
  sellerId?: string
}

async function main() {
  const cfg = loadEnv()
  const svc = makeMemoryService({
    rpcUrl: cfg.rpcUrl,
    indexerUrl: cfg.indexerUrl,
    privateKey: cfg.privateKey,
    indexPath: cfg.indexPath,
  })

  const app = Fastify({
    logger: { level: 'info', transport: { target: 'pino-pretty' } },
    bodyLimit: 256 * 1024,
  })

  const __dirname = dirname(fileURLToPath(import.meta.url))
  const uiHtml = readFileSync(join(__dirname, 'ui', 'index.html'), 'utf8')
  const verifyHtml = readFileSync(join(__dirname, 'ui', 'verify.html'), 'utf8')

  app.get('/', async () => ({
    service: 'kajota-witness',
    network: '0G Galileo (chainId 16602)',
    routes: [
      'GET /', 'GET /health', 'GET /ui', 'GET /verify',
      'POST /memory', 'GET /memory',
      'POST /evidence/query',
      'POST /dispute',
      'GET /verify/:cid',
    ],
  }))

  app.get('/health', async () => ({ ok: true, ts: Date.now() }))

  app.get('/ui', async (_req, reply) => {
    reply.type('text/html').send(uiHtml)
  })

  app.get('/verify', async (_req, reply) => {
    reply.type('text/html').send(verifyHtml)
  })

  app.get<{ Params: { cid: string } }>('/verify/:cid', async (req, reply) => {
    const { cid } = req.params
    if (!/^0x[0-9a-fA-F]{64}$/.test(cid)) {
      return reply.code(400).send({ error: 'cid must be 0x-prefixed 32-byte hex' })
    }
    const result = await svc.verify(cid)
    let chain = null
    if (result.disputeId && isAnchorEnabled()) {
      try {
        const onChain = await getVerdictFromChain(result.disputeId)
        if (onChain) {
          chain = {
            ...onChain,
            chainScanUrl: `https://chainscan-galileo.0g.ai/address/${onChain.contractAddress}`,
            matchesStorageCid: onChain.verdictRoot.toLowerCase() === cid.toLowerCase(),
          }
        }
      } catch (err) {
        app.log.warn({ err }, '[verify] chain lookup failed')
      }
    }
    return reply.send({
      cid,
      storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${cid}`,
      local: result.local,
      storage: result.storage,
      decrypted: result.decrypted,
      chain,
    })
  })

  app.post<{ Body: WriteChatBody }>('/memory', async (req, reply) => {
    const blob = req.body
    if (!blob || blob.kind !== 'chat' || !blob.sellerId || !Array.isArray(blob.messages)) {
      return reply.code(400).send({ error: 'invalid chat blob' })
    }
    if (!blob.ts) blob.ts = Date.now()
    const result = await svc.writeChat(blob)
    return reply.send(result)
  })

  app.get<{ Querystring: ListQuery }>('/memory', async (req) => {
    const { kind, sellerId } = req.query
    return { entries: svc.listEntries({ kind, sellerId }) }
  })

  app.post<{ Body: EvidenceQueryBody }>('/evidence/query', async (req, reply) => {
    const { query, sellerId, k } = req.body ?? {}
    if (!query || typeof query !== 'string') {
      return reply.code(400).send({ error: 'query (string) required' })
    }
    const hits = await svc.queryEvidence(query, { sellerId, k })
    return reply.send({
      query,
      count: hits.length,
      hits: hits.map((h) => ({
        score: h.score,
        cid: h.entry.cid,
        ts: h.entry.ts,
        sellerId: h.entry.sellerId,
        summary: h.entry.metadata.summary,
        storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${h.entry.cid}`,
        blob: h.blob,
      })),
    })
  })

  app.post<{ Body: DisputeBody }>('/dispute', async (req, reply) => {
    const { sellerId, buyerId, claim, evidenceQuery, k } = req.body ?? {}
    if (!sellerId || !claim) {
      return reply.code(400).send({ error: 'sellerId and claim required' })
    }

    const t0 = Date.now()
    const evidence = await svc.queryEvidence(evidenceQuery ?? claim, { sellerId, k: k ?? 3 })
    const tEvidence = Date.now() - t0

    const t1 = Date.now()
    const verdict = await deliberate({ sellerId, buyerId, claim, evidence })
    const tJury = Date.now() - t1

    const verdictBlob: VerdictBlob = {
      kind: 'verdict',
      sellerId,
      buyerId,
      ts: verdict.ts,
      dispute: { claim },
      verdict,
    }
    const disputeId = disputeIdOf(sellerId, buyerId, claim, verdict.ts)
    const t2 = Date.now()
    const write = await svc.writeVerdict(verdictBlob, disputeId)
    const tVerdict = Date.now() - t2

    let chainAnchor: Awaited<ReturnType<typeof anchorVerdict>> | null = null
    let tAnchor = 0
    if (isAnchorEnabled()) {
      const t3 = Date.now()
      try {
        chainAnchor = await anchorVerdict({
          disputeId,
          verdictRoot: write.cid,
          ruling: verdict.ruling,
          confidenceBps: Math.round(verdict.confidence * 10000),
        })
        tAnchor = Date.now() - t3
      } catch (err) {
        app.log.warn({ err }, '[anchor] failed; verdict still saved on 0G Storage')
      }
    }

    return reply.send({
      verdict,
      evidence: evidence.map((h) => ({
        score: h.score,
        cid: h.entry.cid,
        summary: h.entry.metadata.summary,
        storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${h.entry.cid}`,
        blob: h.blob,
      })),
      onChain: {
        verdictCid: write.cid,
        verdictTxHash: write.txHash,
        verdictStorageScanUrl: write.storageScanUrl,
        verdictChainScanUrl: write.chainScanUrl,
        chainAnchor,
      },
      timings: {
        evidenceMs: tEvidence,
        juryMs: tJury,
        verdictWriteMs: tVerdict,
        anchorMs: tAnchor || undefined,
      },
    })
  })

  app.setErrorHandler((err, _req, reply) => {
    app.log.error(err)
    reply.code(500).send({ error: err instanceof Error ? err.message : String(err) })
  })

  await app.listen({ port: cfg.port, host: '0.0.0.0' })
  app.log.info(`kajota-witness listening on http://localhost:${cfg.port}`)
  app.log.info(`UI: http://localhost:${cfg.port}/ui`)
}

main().catch((err) => {
  console.error('[server] startup failed:', err)
  process.exit(1)
})
