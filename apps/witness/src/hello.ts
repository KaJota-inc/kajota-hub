import 'dotenv/config'
import { makeOgClient } from './lib/og.js'
import { encrypt, decrypt, newKey, packEnvelope, unpackEnvelope } from './lib/crypto.js'

const REQUIRED = ['ZG_RPC_URL', 'ZG_INDEXER_URL', 'WITNESS_DEPLOYER_PK'] as const

function loadEnv() {
  for (const k of REQUIRED) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}. Copy .env.example to .env and fill in.`)
      process.exit(1)
    }
  }
  return {
    rpcUrl: process.env.ZG_RPC_URL!,
    indexerUrl: process.env.ZG_INDEXER_URL!,
    privateKey: process.env.WITNESS_DEPLOYER_PK!,
  }
}

async function main() {
  const cfg = loadEnv()
  const og = makeOgClient(cfg)
  console.log(`[hello] signer address: ${og.address}`)

  const payload = {
    kind: 'chat',
    sellerId: 'seller-001',
    buyerId: 'buyer-042',
    ts: new Date().toISOString(),
    messages: [
      { role: 'buyer', text: 'Do you have these shoes in size 42?' },
      { role: 'seller', text: 'Yes — ₦12,000 with free Lagos delivery.' },
      { role: 'buyer', text: 'Can you do ₦10k?' },
      { role: 'seller', text: 'I can do ₦11k flat. Deal?' },
    ],
  }
  const plaintext = Buffer.from(JSON.stringify(payload, null, 2), 'utf8')
  console.log(`[hello] plaintext: ${plaintext.length} bytes`)

  const key = newKey()
  const env = encrypt(plaintext, key)
  const packed = packEnvelope(env)
  console.log(`[hello] encrypted: ${packed.length} bytes (iv=12 + tag=16 + ct=${env.ciphertext.length})`)

  console.log('[hello] uploading to 0G Galileo...')
  const t0 = Date.now()
  const result = await og.uploadBytes(packed)
  console.log(`[hello] uploaded in ${Date.now() - t0}ms`)
  console.log(`[hello]   rootHash: ${result.rootHash}`)
  console.log(`[hello]   txHash:   ${result.txHash}`)
  console.log(`[hello]   storage scan: ${result.storageScanUrl}`)
  console.log(`[hello]   chain scan:   ${result.chainScanUrl}`)

  console.log('[hello] downloading from 0G...')
  const t1 = Date.now()
  const downloaded = await og.downloadBytes(result.rootHash)
  console.log(`[hello] downloaded ${downloaded.length} bytes in ${Date.now() - t1}ms`)

  const recovered = decrypt(unpackEnvelope(downloaded), key)
  const ok = recovered.equals(plaintext)
  console.log(`[hello] round-trip equality: ${ok ? 'OK ✓' : 'MISMATCH ✗'}`)
  if (!ok) {
    console.error(`  expected ${plaintext.length} bytes, got ${recovered.length}`)
    process.exit(2)
  }

  const parsed = JSON.parse(recovered.toString('utf8'))
  console.log(`[hello] recovered chat: ${parsed.messages.length} messages between ${parsed.sellerId} and ${parsed.buyerId}`)
  console.log('[hello] DONE')
}

main().catch((err) => {
  console.error('[hello] FAILED:', err)
  process.exit(1)
})
