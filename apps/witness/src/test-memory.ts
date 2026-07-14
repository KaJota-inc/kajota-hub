import 'dotenv/config'
import { makeMemoryService, type ChatBlob } from './lib/memory.js'

const REQUIRED = ['ZG_RPC_URL', 'ZG_INDEXER_URL', 'WITNESS_DEPLOYER_PK'] as const

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

const SELLER = 'seller-amaka-fashion'
const BUYER = 'buyer-tunde'

const CHATS: ChatBlob[] = [
  {
    kind: 'chat',
    sellerId: SELLER,
    buyerId: BUYER,
    ts: Date.parse('2026-06-10T09:00:00Z'),
    topic: 'shoes-size-42-price',
    messages: [
      { role: 'buyer', text: 'Do you have these blue trainers in size 42?' },
      { role: 'seller', text: 'Yes — ₦12,000 with free Lagos delivery.' },
      { role: 'buyer', text: 'Can you do ₦10k?' },
      { role: 'seller', text: 'I can do ₦11k flat. Deal?' },
      { role: 'buyer', text: 'Agreed. Sending payment now.' },
    ],
  },
  {
    kind: 'chat',
    sellerId: SELLER,
    buyerId: BUYER,
    ts: Date.parse('2026-06-12T14:30:00Z'),
    topic: 'shipping-confirmation',
    messages: [
      { role: 'seller', text: 'Tracking number GIG-998877. Should arrive Friday.' },
      { role: 'buyer', text: 'Got it, thanks.' },
    ],
  },
  {
    kind: 'chat',
    sellerId: SELLER,
    buyerId: 'buyer-chioma',
    ts: Date.parse('2026-06-14T11:15:00Z'),
    topic: 'wedding-shoes-bulk-order',
    messages: [
      { role: 'buyer', text: 'I need 6 pairs of white satin heels for a wedding party.' },
      { role: 'seller', text: 'I have 4 in stock. Can restock in 3 days.' },
      { role: 'buyer', text: 'Perfect. What about a bulk discount?' },
      { role: 'seller', text: '10% off if you take all 6. ₦54,000 total.' },
    ],
  },
]

async function main() {
  const cfg = loadEnv()
  const svc = makeMemoryService(cfg)

  console.log(`[test] writing ${CHATS.length} chats to 0G + index...`)
  for (let i = 0; i < CHATS.length; i++) {
    const t0 = Date.now()
    const result = await svc.writeChat(CHATS[i])
    console.log(`[test] chat ${i + 1}/${CHATS.length} OK in ${Date.now() - t0}ms`)
    console.log(`         cid: ${result.cid.slice(0, 24)}...`)
    console.log(`         summary: ${result.summary}`)
  }

  const QUERIES = [
    {
      q: 'What was the agreed price for the trainers?',
      expectedTopic: 'shoes-size-42-price',
    },
    {
      q: 'When will the shoes be delivered?',
      expectedTopic: 'shipping-confirmation',
    },
    {
      q: 'How many wedding shoes did Chioma order?',
      expectedTopic: 'wedding-shoes-bulk-order',
    },
  ]

  console.log(`\n[test] running ${QUERIES.length} evidence queries...`)
  let passed = 0
  for (const { q, expectedTopic } of QUERIES) {
    const t0 = Date.now()
    const hits = await svc.queryEvidence(q, { sellerId: SELLER, k: 3 })
    const top = hits[0]
    const ok = top?.blob.topic === expectedTopic
    if (ok) passed++
    console.log(`[test] Q: "${q}"`)
    console.log(`         expected: ${expectedTopic}`)
    console.log(`         top hit:  ${top?.blob.topic} (score ${top?.score.toFixed(3)})  ${ok ? '✓' : '✗'}`)
    console.log(`         ${Date.now() - t0}ms, ${hits.length} hits`)
  }
  console.log(`\n[test] PASSED ${passed}/${QUERIES.length} queries`)
  console.log(`[test] index has ${(svc as any).store.count()} entries`)
  if (passed !== QUERIES.length) process.exit(2)
}

main().catch((err) => {
  console.error('[test] FAILED:', err)
  process.exit(1)
})
