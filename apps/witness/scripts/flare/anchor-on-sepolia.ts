/**
 * Helper: call WitnessAnchor.anchor() on Ethereum Sepolia to produce
 * a fresh VerdictAnchored event for the Flare FDC to attest.
 *
 * In production Witness anchors on 0G Galileo (see scripts/deploy-anchor.ts).
 * For the Flare Summer Signal demo we need the anchor tx on a chain FDC's
 * EVMTransaction attestation type supports (testETH = Sepolia).
 *
 * Usage:
 *   npx tsx scripts/flare/anchor-on-sepolia.ts \
 *     --dispute 0x1234... \
 *     --root    0xabcd... \
 *     --ruling  release_to_seller \
 *     --conf    8700
 *
 * Env:
 *   SEPOLIA_RPC_URL, WITNESS_DEPLOYER_PK, WITNESS_ANCHOR_SEPOLIA
 */
import 'dotenv/config'
import { readFileSync } from 'node:fs'
import { ethers } from 'ethers'

function parseArgs(): {
  disputeId: string
  root: string
  ruling: string
  confidenceBps: number
} {
  const args = process.argv.slice(2)
  const get = (flag: string): string | undefined => {
    const idx = args.indexOf(flag)
    return idx >= 0 ? args[idx + 1] : undefined
  }
  const disputeId = get('--dispute') ?? '0x' + Buffer.from(Date.now().toString()).toString('hex').padEnd(64, '0').slice(0, 64)
  const root = get('--root') ?? '0x' + 'a'.repeat(64)
  const ruling = get('--ruling') ?? 'release_to_seller'
  const conf = parseInt(get('--conf') ?? '8700', 10)
  if (isNaN(conf) || conf < 0 || conf > 10000) {
    throw new Error(`--conf must be 0..10000, got ${conf}`)
  }
  if (!/^0x[0-9a-fA-F]{64}$/.test(disputeId)) throw new Error(`--dispute must be bytes32 hex`)
  if (!/^0x[0-9a-fA-F]{64}$/.test(root)) throw new Error(`--root must be bytes32 hex`)
  return { disputeId, root, ruling, confidenceBps: conf }
}

async function main() {
  for (const k of ['SEPOLIA_RPC_URL', 'WITNESS_DEPLOYER_PK', 'WITNESS_ANCHOR_SEPOLIA']) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      process.exit(1)
    }
  }

  const { disputeId, root, ruling, confidenceBps } = parseArgs()

  const abi = JSON.parse(readFileSync('./contracts/WitnessAnchor.abi.json', 'utf8'))
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const anchor = new ethers.Contract(process.env.WITNESS_ANCHOR_SEPOLIA!, abi, signer)

  console.log('[anchor] contract:  ', await anchor.getAddress())
  console.log('[anchor] disputeId: ', disputeId)
  console.log('[anchor] root:      ', root)
  console.log('[anchor] ruling:    ', ruling)
  console.log('[anchor] confidence:', confidenceBps, 'bps')

  const tx = await anchor.anchor(disputeId, root, ruling, confidenceBps)
  const receipt = await tx.wait()
  console.log(`[anchor] ✅ mined in block ${receipt!.blockNumber}`)
  console.log(`[anchor] tx:        ${receipt!.hash}`)
  console.log(`[anchor] etherscan: https://sepolia.etherscan.io/tx/${receipt!.hash}`)
  console.log()
  console.log('Next step — attest this tx on Flare Coston2:')
  console.log(`  npx tsx scripts/flare/attest-verdict.ts ${receipt!.hash}`)
}

main().catch((err) => {
  console.error('[anchor] FAILED:', err?.stack ?? err?.message ?? err)
  process.exit(1)
})
