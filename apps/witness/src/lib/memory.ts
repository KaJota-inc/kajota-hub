import { makeOgClient, type OgClient } from './og.js'
import { encrypt, decrypt, newKey, packEnvelope, unpackEnvelope } from './crypto.js'
import { embed } from './embed.js'
import { IndexStore, type IndexEntry, type SearchHit } from './index-store.js'
import type { Verdict } from './jury.js'

export type ChatMessage = {
  role: 'buyer' | 'seller' | 'agent'
  text: string
}

export type ChatBlob = {
  kind: 'chat'
  sellerId: string
  buyerId?: string
  ts: number
  topic?: string
  messages: ChatMessage[]
}

export type VerdictBlob = {
  kind: 'verdict'
  sellerId: string
  buyerId?: string
  ts: number
  dispute: {
    claim: string
  }
  verdict: Verdict
}

export type WriteResult = {
  cid: string
  txHash: string
  storageScanUrl: string
  chainScanUrl: string
  summary: string
}

export type EvidenceHit = SearchHit & {
  blob: ChatBlob
}

export type EntrySummary = {
  cid: string
  sellerId: string
  ts: number
  kind: 'chat' | 'verdict'
  summary?: string
  participants?: string[]
  ruling?: string
  confidence?: number
  evidenceCids?: string[]
  storageScanUrl: string
}

function summarize(blob: ChatBlob): string {
  const topic = blob.topic ? `[${blob.topic}] ` : ''
  const firstBuyer = blob.messages.find((m) => m.role === 'buyer')?.text ?? ''
  const head = firstBuyer.slice(0, 80)
  return `${topic}${blob.sellerId}↔${blob.buyerId ?? '?'}: ${head}${head.length === 80 ? '…' : ''}`
}

function embeddableText(blob: ChatBlob): string {
  const topicWords = blob.topic ? blob.topic.replace(/-/g, ' ') : ''
  return [
    topicWords,
    topicWords,
    topicWords,
    ...blob.messages.map((m) => `${m.role}: ${m.text}`),
  ].filter(Boolean).join('\n')
}

export class MemoryService {
  constructor(
    private og: OgClient,
    private store: IndexStore,
  ) {}

  async writeChat(blob: ChatBlob): Promise<WriteResult> {
    const plaintext = Buffer.from(JSON.stringify(blob), 'utf8')
    const key = newKey()
    const env = encrypt(plaintext, key)
    const packed = packEnvelope(env)

    const upload = await this.og.uploadBytes(packed)

    const embedding = await embed(embeddableText(blob))
    const summary = summarize(blob)

    const entry: IndexEntry = {
      cid: upload.rootHash,
      sellerId: blob.sellerId,
      ts: blob.ts,
      embedding: Array.from(embedding),
      keyHex: key.toString('hex'),
      metadata: {
        kind: 'chat',
        summary,
        participants: [blob.sellerId, ...(blob.buyerId ? [blob.buyerId] : [])],
      },
    }
    this.store.add(entry)

    return {
      cid: upload.rootHash,
      txHash: upload.txHash,
      storageScanUrl: upload.storageScanUrl,
      chainScanUrl: upload.chainScanUrl,
      summary,
    }
  }

  async queryEvidence(query: string, opts: { sellerId?: string; k?: number } = {}): Promise<EvidenceHit[]> {
    const k = opts.k ?? 3
    const queryEmbedding = await embed(query)
    const hits = this.store.topK(
      queryEmbedding,
      k,
      (e) => e.metadata.kind === 'chat' && (!opts.sellerId || e.sellerId === opts.sellerId),
    )

    const enriched: EvidenceHit[] = []
    for (const hit of hits) {
      const downloaded = await this.og.downloadBytes(hit.entry.cid)
      const env = unpackEnvelope(downloaded)
      const key = Buffer.from(hit.entry.keyHex, 'hex')
      const plaintext = decrypt(env, key)
      const blob = JSON.parse(plaintext.toString('utf8')) as ChatBlob
      enriched.push({ ...hit, blob })
    }
    return enriched
  }

  async writeVerdict(blob: VerdictBlob, disputeId?: string): Promise<WriteResult> {
    const plaintext = Buffer.from(JSON.stringify(blob), 'utf8')
    const key = newKey()
    const env = encrypt(plaintext, key)
    const packed = packEnvelope(env)
    const upload = await this.og.uploadBytes(packed)

    const summary = `[verdict:${blob.verdict.ruling}] ${blob.sellerId}↔${blob.buyerId ?? '?'}: ${blob.dispute.claim.slice(0, 60)}${blob.dispute.claim.length > 60 ? '…' : ''}`
    const embedding = await embed([
      'verdict ruling dispute',
      blob.dispute.claim,
      blob.verdict.reasoning,
    ].join('\n'))

    const entry: IndexEntry = {
      cid: upload.rootHash,
      sellerId: blob.sellerId,
      ts: blob.ts,
      embedding: Array.from(embedding),
      keyHex: key.toString('hex'),
      metadata: {
        kind: 'verdict',
        summary,
        participants: [blob.sellerId, ...(blob.buyerId ? [blob.buyerId] : [])],
        ruling: blob.verdict.ruling,
        confidence: blob.verdict.confidence,
        evidenceCids: blob.verdict.evidenceCids,
        disputeId,
      },
    }
    this.store.add(entry)

    return {
      cid: upload.rootHash,
      txHash: upload.txHash,
      storageScanUrl: upload.storageScanUrl,
      chainScanUrl: upload.chainScanUrl,
      summary,
    }
  }

  listEntries(opts: { kind?: 'chat' | 'verdict'; sellerId?: string } = {}): EntrySummary[] {
    const entries = this.store.list((e) => {
      if (opts.kind && e.metadata.kind !== opts.kind) return false
      if (opts.sellerId && e.sellerId !== opts.sellerId) return false
      return true
    })
    return entries
      .sort((a, b) => b.ts - a.ts)
      .map((e) => ({
        cid: e.cid,
        sellerId: e.sellerId,
        ts: e.ts,
        kind: e.metadata.kind,
        summary: e.metadata.summary,
        participants: e.metadata.participants,
        ruling: e.metadata.ruling,
        confidence: e.metadata.confidence,
        evidenceCids: e.metadata.evidenceCids,
        storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${e.cid}`,
      }))
  }

  async verify(cid: string): Promise<{
    local: EntrySummary | null
    storage: { exists: boolean; bytes: number | null; error?: string }
    decrypted: ChatBlob | VerdictBlob | null
    disputeId: string | null
  }> {
    const entry = this.store.list((e) => e.cid === cid)[0] ?? null
    const local: EntrySummary | null = entry
      ? {
          cid: entry.cid,
          sellerId: entry.sellerId,
          ts: entry.ts,
          kind: entry.metadata.kind,
          summary: entry.metadata.summary,
          participants: entry.metadata.participants,
          ruling: entry.metadata.ruling,
          confidence: entry.metadata.confidence,
          evidenceCids: entry.metadata.evidenceCids,
          storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${entry.cid}`,
        }
      : null

    let storage: { exists: boolean; bytes: number | null; error?: string } = { exists: false, bytes: null }
    let decrypted: ChatBlob | VerdictBlob | null = null
    try {
      const downloaded = await this.og.downloadBytes(cid)
      storage = { exists: true, bytes: downloaded.length }
      if (entry) {
        try {
          const env = unpackEnvelope(downloaded)
          const key = Buffer.from(entry.keyHex, 'hex')
          const plaintext = decrypt(env, key)
          decrypted = JSON.parse(plaintext.toString('utf8'))
        } catch (e) {
          // bytes on chain but key/format mismatch — leave decrypted as null
        }
      }
    } catch (e) {
      storage = { exists: false, bytes: null, error: e instanceof Error ? e.message : String(e) }
    }

    return {
      local,
      storage,
      decrypted,
      disputeId: entry?.metadata.disputeId ?? null,
    }
  }
}

export function makeMemoryService(opts: {
  rpcUrl: string
  indexerUrl: string
  privateKey: string
  indexPath: string
}): MemoryService {
  const og = makeOgClient({ rpcUrl: opts.rpcUrl, indexerUrl: opts.indexerUrl, privateKey: opts.privateKey })
  const store = new IndexStore(opts.indexPath)
  return new MemoryService(og, store)
}
