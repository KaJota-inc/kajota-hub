import 'dotenv/config'
import { makeMemoryService } from './lib/memory.js'
import { deliberate } from './lib/jury.js'

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
  }
}

const SCENARIOS = [
  {
    label: 'Clear-cut buyer claim with no supporting evidence',
    sellerId: 'seller-amaka-fashion',
    buyerId: 'buyer-tunde',
    claim: 'I paid ₦11,000 for blue trainers size 42 but the seller never shipped them. I want a refund.',
    query: 'blue trainers size 42 price payment shipping',
    note: 'Buyer agreed ₦11k AND seller provided tracking GIG-998877. Evidence supports seller. Expect: release_to_seller.',
  },
  {
    label: 'Pricing dispute with clear chat record',
    sellerId: 'seller-amaka-fashion',
    buyerId: 'buyer-tunde',
    claim: 'The seller charged me ₦12,000 but we agreed on ₦10,000.',
    query: 'agreed price negotiation trainers',
    note: 'Chat shows they agreed ₦11k flat, not ₦10k or ₦12k. Expect: split_50_50 or escalate.',
  },
  {
    label: 'Bulk order dispute',
    sellerId: 'seller-amaka-fashion',
    buyerId: 'buyer-chioma',
    claim: 'I ordered 6 pairs of wedding heels but only received 4.',
    query: 'wedding heels order quantity bulk discount',
    note: 'Seller said only 4 in stock, restock in 3 days. If buyer was charged for 6 and only got 4 with no follow-up, leans buyer.',
  },
]

async function main() {
  const cfg = loadEnv()
  const svc = makeMemoryService(cfg)

  console.log(`[test-jury] ${SCENARIOS.length} dispute scenarios\n`)

  for (let i = 0; i < SCENARIOS.length; i++) {
    const sc = SCENARIOS[i]
    console.log('━'.repeat(70))
    console.log(`\nDISPUTE ${i + 1}/${SCENARIOS.length}: ${sc.label}`)
    console.log(`Claim: "${sc.claim}"`)
    console.log(`Expected: ${sc.note}\n`)

    const tEvidence = Date.now()
    const evidence = await svc.queryEvidence(sc.query, { sellerId: sc.sellerId, k: 3 })
    console.log(`[evidence] pulled ${evidence.length} hits in ${Date.now() - tEvidence}ms`)
    for (const e of evidence) {
      console.log(`  - ${e.entry.metadata.summary} (score ${e.score.toFixed(3)})`)
    }

    const tJury = Date.now()
    const verdict = await deliberate({
      sellerId: sc.sellerId,
      buyerId: sc.buyerId,
      claim: sc.claim,
      evidence,
    })
    console.log(`\n[jury] deliberation took ${Date.now() - tJury}ms`)
    console.log(`\n  Prosecutor (leans ${verdict.jury[0].leansToward}):`)
    console.log(`    "${verdict.jury[0].argument.slice(0, 200)}…"`)
    console.log(`\n  Defender (leans ${verdict.jury[1].leansToward}):`)
    console.log(`    "${verdict.jury[1].argument.slice(0, 200)}…"`)
    console.log(`\n  Neutral (leans ${verdict.jury[2].leansToward}):`)
    console.log(`    "${verdict.jury[2].argument.slice(0, 200)}…"`)
    console.log(`\n  ⚖️  VERDICT: ${verdict.ruling}  (confidence ${(verdict.confidence * 100).toFixed(0)}%)`)
    console.log(`     Reasoning: "${verdict.reasoning.slice(0, 250)}…"`)
    console.log(`     Evidence CIDs: ${verdict.evidenceCids.map((c) => c.slice(0, 14) + '…').join(', ')}`)
    console.log()
  }

  console.log('━'.repeat(70))
  console.log('\n[test-jury] DONE\n')
}

main().catch((err) => {
  console.error('[test-jury] FAILED:', err)
  process.exit(1)
})
