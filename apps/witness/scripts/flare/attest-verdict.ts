/**
 * End-to-end FDC attestation orchestrator.
 *
 * Given a Sepolia tx hash from a WitnessAnchor.anchor() call, this script:
 *   1. Asks Flare's FDC verifier to prepare + validate the request.
 *   2. Submits the request on Coston2 via FdcHub.requestAttestation (pays fee).
 *   3. Computes the FDC voting round from the block timestamp.
 *   4. Waits for round finalization (~180s buffer).
 *   5. Pulls the proof + response from the Coston2 Data Availability Layer.
 *   6. Submits the proof to FlareWitnessConsumer.submitVerdict on Coston2.
 *   7. Prints a link + status of the imported verdict.
 *
 * Usage:
 *   npx tsx scripts/flare/attest-verdict.ts <sepolia-tx-hash>
 *
 * Env:
 *   SEPOLIA_TX_HASH        (optional if passed as argv)
 *   COSTON2_RPC_URL
 *   WITNESS_DEPLOYER_PK
 *   FLARE_CONSUMER_COSTON2
 *   VERIFIER_URL_TESTNET   default https://fdc-verifiers-testnet.flare.network
 *   VERIFIER_API_KEY_TESTNET  (get from Flare — testnet keys are free)
 *   COSTON2_DA_LAYER_URL   default https://ctn2-data-availability.flare.network
 */
import 'dotenv/config'
import { readFileSync } from 'node:fs'
import { ethers } from 'ethers'

// ── FDC voting-round constants (Coston2 State Connector) ──────────────────
// Source: flare-hardhat-starter/scripts/utils/fdc.ts + Flare docs.
const FIRST_VOTING_ROUND_START_TS = 1658429955
const VOTING_EPOCH_DURATION_SECONDS = 90

const VERIFIER_URL_DEFAULT = 'https://fdc-verifiers-testnet.flare.network'
const DA_LAYER_URL_DEFAULT = 'https://ctn2-data-availability.flare.network'

// ── FdcHub is retrieved from the Flare ContractRegistry to avoid pinning ──
const FLARE_CONTRACT_REGISTRY = '0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019'
const CONTRACT_REGISTRY_ABI = [
  'function getContractAddressByName(string _name) external view returns (address)',
]
const FDC_HUB_ABI = [
  'function requestAttestation(bytes _data) external payable',
]
const FDC_REQUEST_FEE_ABI = [
  'function getRequestFee(bytes _data) external view returns (uint256)',
]

function toHex32(str: string): string {
  const hex = Buffer.from(str, 'utf8').toString('hex')
  return '0x' + hex.padEnd(64, '0')
}

async function prepareRequest(txHash: string, verifierUrl: string, apiKey: string) {
  const attestationType = toHex32('EVMTransaction')
  const sourceId = toHex32('testETH')

  const url = `${verifierUrl}/verifier/eth/EVMTransaction/prepareRequest`
  const body = {
    attestationType,
    sourceId,
    requestBody: {
      transactionHash: txHash,
      requiredConfirmations: '1',
      provideInput: true,
      listEvents: true,
      logIndices: [],
    },
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (apiKey) headers['X-API-KEY'] = apiKey

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  const json: any = await res.json()
  if (!res.ok || !json.abiEncodedRequest) {
    throw new Error(`prepareRequest failed (${res.status}): ${JSON.stringify(json)}`)
  }
  return json.abiEncodedRequest as string
}

async function submitAttestationRequest(
  abiEncodedRequest: string,
  provider: ethers.JsonRpcProvider,
  signer: ethers.Wallet
): Promise<{ roundId: number; txHash: string }> {
  const registry = new ethers.Contract(FLARE_CONTRACT_REGISTRY, CONTRACT_REGISTRY_ABI, provider)
  const fdcHubAddr: string = await registry.getContractAddressByName('FdcHub')
  const feeCfgAddr: string = await registry.getContractAddressByName('FdcRequestFeeConfigurations')
  if (fdcHubAddr === ethers.ZeroAddress) throw new Error('FdcHub not resolvable from registry')
  console.log('[fdc] FdcHub:', fdcHubAddr)
  console.log('[fdc] FeeCfg:', feeCfgAddr)

  const fee = feeCfgAddr !== ethers.ZeroAddress
    ? await new ethers.Contract(feeCfgAddr, FDC_REQUEST_FEE_ABI, provider).getRequestFee(abiEncodedRequest)
    : ethers.parseEther('0.1')
  console.log('[fdc] attestation fee:', ethers.formatEther(fee), 'C2FLR')

  const hub = new ethers.Contract(fdcHubAddr, FDC_HUB_ABI, signer)
  const tx = await hub.requestAttestation(abiEncodedRequest, { value: fee })
  const receipt = await tx.wait()
  const block = await provider.getBlock(receipt!.blockNumber)
  const roundId = Math.floor(
    (Number(block!.timestamp) - FIRST_VOTING_ROUND_START_TS) / VOTING_EPOCH_DURATION_SECONDS
  )
  return { roundId, txHash: receipt!.hash }
}

async function waitForFinalization(currentRound: number, provider: ethers.JsonRpcProvider) {
  console.log('[fdc] waiting for voting round to finalize...')
  const targetTs =
    FIRST_VOTING_ROUND_START_TS + (currentRound + 2) * VOTING_EPOCH_DURATION_SECONDS
  for (;;) {
    const block = await provider.getBlock('latest')
    const now = Number(block!.timestamp)
    if (now >= targetTs) return
    const wait = Math.min(30, Math.max(5, targetTs - now))
    process.stdout.write(`  block ts=${now}, target=${targetTs}, sleeping ${wait}s...\r`)
    await new Promise((r) => setTimeout(r, wait * 1000))
  }
}

async function retrieveDataAndProof(
  abiEncodedRequest: string,
  roundId: number,
  daLayerUrl: string
): Promise<{ proof: string[]; response_hex: string }> {
  const url = `${daLayerUrl}/api/v1/fdc/proof-by-request-round-raw`
  const body = { votingRoundId: roundId, requestBytes: abiEncodedRequest }
  for (let attempt = 1; attempt <= 10; attempt++) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const json: any = await res.json().catch(() => ({}))
    if (res.ok && json.response_hex && json.proof) return json
    console.log(`\n[fdc] attempt ${attempt}/10: DA not ready (${res.status}) — retrying in 15s`)
    await new Promise((r) => setTimeout(r, 15000))
  }
  throw new Error('DA layer never returned proof after 10 attempts')
}

async function submitProof(
  consumerAddress: string,
  merkleProof: string[],
  responseHex: string,
  signer: ethers.Wallet
): Promise<string> {
  const abiPath = './contracts/flare/FlareWitnessConsumer.abi.json'
  const abi = JSON.parse(readFileSync(abiPath, 'utf8'))
  const consumer = new ethers.Contract(consumerAddress, abi, signer)

  // The proof struct is (bytes32[] merkleProof, Response data).
  // response_hex is the ABI-encoded Response; decode it as the interface expects.
  const responseTypeAbi = [
    'tuple(bytes32 attestationType, bytes32 sourceId, uint64 votingRound, uint64 lowestUsedTimestamp, tuple(bytes32 transactionHash, uint16 requiredConfirmations, bool provideInput, bool listEvents, uint32[] logIndices) requestBody, tuple(uint64 blockNumber, uint64 timestamp, address sourceAddress, bool isDeployment, address receivingAddress, uint256 value, bytes input, uint8 status, tuple(uint32 logIndex, address emitterAddress, bytes32[] topics, bytes data, bool removed)[] events) responseBody)',
  ]
  const [decodedResponse] = ethers.AbiCoder.defaultAbiCoder().decode(responseTypeAbi, responseHex)

  const proofStruct = { merkleProof, data: decodedResponse }
  const tx = await consumer.submitVerdict(proofStruct)
  const receipt = await tx.wait()
  return receipt!.hash
}

async function main() {
  const txHashArg = process.argv[2] ?? process.env.SEPOLIA_TX_HASH
  if (!txHashArg) {
    console.error('Usage: npx tsx scripts/flare/attest-verdict.ts <sepolia-tx-hash>')
    process.exit(1)
  }
  for (const k of ['COSTON2_RPC_URL', 'WITNESS_DEPLOYER_PK', 'FLARE_CONSUMER_COSTON2']) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      process.exit(1)
    }
  }

  const verifierUrl = process.env.VERIFIER_URL_TESTNET ?? VERIFIER_URL_DEFAULT
  const daLayerUrl = process.env.COSTON2_DA_LAYER_URL ?? DA_LAYER_URL_DEFAULT
  const apiKey = process.env.VERIFIER_API_KEY_TESTNET ?? ''
  const consumerAddr = process.env.FLARE_CONSUMER_COSTON2!

  console.log('[fdc] step 1/5: prepareRequest for Sepolia tx', txHashArg)
  const abiEncodedRequest = await prepareRequest(txHashArg, verifierUrl, apiKey)
  console.log('[fdc] abiEncodedRequest (first 66 chars):', abiEncodedRequest.slice(0, 66) + '…')

  const provider = new ethers.JsonRpcProvider(process.env.COSTON2_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const bal = await provider.getBalance(signer.address)
  console.log('[fdc] signer:', signer.address, '| balance:', ethers.formatEther(bal), 'C2FLR')

  console.log('[fdc] step 2/5: submit attestation request on Coston2')
  const { roundId, txHash } = await submitAttestationRequest(abiEncodedRequest, provider, signer)
  console.log('[fdc] requestAttestation tx:', txHash)
  console.log('[fdc] voting round:', roundId)

  console.log('[fdc] step 3/5: waiting for round to finalize')
  await waitForFinalization(roundId, provider)
  console.log('\n[fdc] round finalized')

  console.log('[fdc] step 4/5: pulling proof from DA layer')
  const { proof, response_hex } = await retrieveDataAndProof(abiEncodedRequest, roundId, daLayerUrl)
  console.log('[fdc] Merkle proof:', proof.length, 'hashes')

  console.log('[fdc] step 5/5: submitting proof to FlareWitnessConsumer')
  const submitTx = await submitProof(consumerAddr, proof, response_hex, signer)
  console.log('[fdc] ✅ submitVerdict tx:', submitTx)
  console.log(`[fdc] explorer: https://coston2-explorer.flare.network/tx/${submitTx}`)
}

main().catch((err) => {
  console.error('[fdc] FAILED:', err?.stack ?? err?.message ?? err)
  process.exit(1)
})
