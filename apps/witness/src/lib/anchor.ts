import { readFileSync, existsSync } from 'node:fs'
import { ethers } from 'ethers'

export type AnchorResult = {
  disputeId: string
  verdictRoot: string
  txHash: string
  chainScanUrl: string
  blockNumber: number | null
}

export type AnchorInput = {
  disputeId: string
  verdictRoot: string
  ruling: string
  confidenceBps: number
}

const ABI_PATH = './contracts/WitnessAnchor.abi.json'

let cachedContract: ethers.Contract | null = null

function loadContract(): ethers.Contract {
  if (cachedContract) return cachedContract
  const address = process.env.WITNESS_ANCHOR_ADDRESS
  if (!address) throw new Error('WITNESS_ANCHOR_ADDRESS not set — run `npx tsx scripts/deploy-anchor.ts`')
  if (!existsSync(ABI_PATH)) throw new Error(`ABI missing at ${ABI_PATH} — run the deploy script first`)
  const provider = new ethers.JsonRpcProvider(process.env.ZG_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const abi = JSON.parse(readFileSync(ABI_PATH, 'utf8'))
  cachedContract = new ethers.Contract(address, abi, signer)
  return cachedContract
}

export function disputeIdOf(sellerId: string, buyerId: string | undefined, claim: string, ts: number): string {
  return ethers.keccak256(
    ethers.toUtf8Bytes(`${sellerId}|${buyerId ?? ''}|${claim}|${ts}`),
  )
}

export async function anchorVerdict(input: AnchorInput): Promise<AnchorResult> {
  const contract = loadContract()
  const tx = await contract.anchor(
    input.disputeId,
    input.verdictRoot,
    input.ruling,
    BigInt(input.confidenceBps),
  )
  const receipt = await tx.wait()
  return {
    disputeId: input.disputeId,
    verdictRoot: input.verdictRoot,
    txHash: tx.hash,
    chainScanUrl: `https://chainscan-galileo.0g.ai/tx/${tx.hash}`,
    blockNumber: receipt?.blockNumber ?? null,
  }
}

export function isAnchorEnabled(): boolean {
  return Boolean(process.env.WITNESS_ANCHOR_ADDRESS) && existsSync(ABI_PATH)
}

export type ChainVerdictRecord = {
  verdictRoot: string
  ruling: string
  confidenceBps: number
  ts: number
  anchoredBy: string
  contractAddress: string
} | null

export async function getVerdictFromChain(disputeId: string): Promise<ChainVerdictRecord> {
  const contract = loadContract()
  const r = await contract.getVerdict(disputeId)
  const verdictRoot = r.verdictRoot ?? r[0]
  if (!verdictRoot || verdictRoot === '0x' + '0'.repeat(64)) return null
  return {
    verdictRoot,
    ruling: r.ruling ?? r[1],
    confidenceBps: Number(r.confidenceBps ?? r[2]),
    ts: Number(r.ts ?? r[3]),
    anchoredBy: r.anchoredBy ?? r[4],
    contractAddress: process.env.WITNESS_ANCHOR_ADDRESS!,
  }
}
