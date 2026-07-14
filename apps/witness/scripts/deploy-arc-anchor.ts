import 'dotenv/config'
import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import solc from 'solc'
import { ethers } from 'ethers'

const REQUIRED = ['ARC_TESTNET_RPC_URL', 'WITNESS_DEPLOYER_PK'] as const

const DEFAULT_ARC_TESTNET_RPC = 'https://rpc.testnet.arc.network'
const ARC_TESTNET_CHAIN_ID = 5042002
const ARC_TESTNET_USDC = '0x3600000000000000000000000000000000000000'

function loadEnv() {
  if (!process.env.ARC_TESTNET_RPC_URL) {
    process.env.ARC_TESTNET_RPC_URL = DEFAULT_ARC_TESTNET_RPC
    console.log(`[deploy] ARC_TESTNET_RPC_URL not set; defaulting to ${DEFAULT_ARC_TESTNET_RPC}`)
  }
  if (!process.env.WITNESS_DEPLOYER_PK) {
    console.error('[deploy] Missing env var: WITNESS_DEPLOYER_PK')
    process.exit(1)
  }
}

async function main() {
  loadEnv()

  const usdc = process.env.ARC_TESTNET_USDC ?? ARC_TESTNET_USDC
  const treasury = process.env.ARC_TREASURY ?? new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!).address
  console.log(`[deploy] USDC:     ${usdc}`)
  console.log(`[deploy] treasury: ${treasury}`)

  console.log('[deploy] reading contract source...')
  const source = readFileSync('./contracts/arc/BondedWitnessAnchor.sol', 'utf8')

  console.log('[deploy] compiling with solc', solc.version())
  const input = {
    language: 'Solidity',
    sources: { 'BondedWitnessAnchor.sol': { content: source } },
    settings: {
      optimizer: { enabled: true, runs: 200 },
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } },
    },
  }
  const output = JSON.parse(solc.compile(JSON.stringify(input)))
  if (output.errors) {
    let fatal = false
    for (const e of output.errors) {
      console[e.severity === 'error' ? 'error' : 'warn'](`[solc] ${e.severity}: ${e.formattedMessage ?? e.message}`)
      if (e.severity === 'error') fatal = true
    }
    if (fatal) process.exit(2)
  }
  const compiled = output.contracts['BondedWitnessAnchor.sol']['BondedWitnessAnchor']
  const abi = compiled.abi
  const bytecode = compiled.evm.bytecode.object
  console.log('[deploy] bytecode size:', bytecode.length / 2, 'bytes')

  const provider = new ethers.JsonRpcProvider(process.env.ARC_TESTNET_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const addr = await signer.getAddress()
  const bal = await provider.getBalance(addr)
  const chainId = (await provider.getNetwork()).chainId
  console.log(`[deploy] chainId (RPC): ${chainId} (expected ${ARC_TESTNET_CHAIN_ID})`)
  console.log(`[deploy] signer:  ${addr}`)
  console.log(`[deploy] balance: ${ethers.formatEther(bal)} USDC-as-gas (18-decimal)`)

  if (bal === 0n) {
    console.error('[deploy] zero balance — drip at https://faucet.circle.com/')
    process.exit(3)
  }
  if (chainId !== BigInt(ARC_TESTNET_CHAIN_ID)) {
    console.warn(`[deploy] ⚠ RPC returned chainId ${chainId}, expected ${ARC_TESTNET_CHAIN_ID} — continuing anyway`)
  }

  console.log(`[deploy] deploying BondedWitnessAnchor to Arc Testnet (chainId ${chainId})...`)
  const factory = new ethers.ContractFactory(abi, '0x' + bytecode, signer)
  const t0 = Date.now()
  const deployed = await factory.deploy(usdc, treasury)
  await deployed.waitForDeployment()
  const elapsed = Date.now() - t0
  const address = await deployed.getAddress()
  const txHash = deployed.deploymentTransaction()?.hash ?? '(unknown)'
  console.log(`[deploy] ✅ deployed in ${elapsed}ms`)
  console.log(`[deploy] address:  ${address}`)
  console.log(`[deploy] tx:       ${txHash}`)
  console.log(`[deploy] arcscan:  https://testnet.arcscan.app/address/${address}`)

  if (!existsSync('.env')) copyFileSync('.env.example', '.env')
  let env = readFileSync('.env', 'utf8')
  if (env.match(/^ARC_BONDED_ANCHOR_ADDRESS=.*$/m)) {
    env = env.replace(/^ARC_BONDED_ANCHOR_ADDRESS=.*$/m, 'ARC_BONDED_ANCHOR_ADDRESS=' + address)
  } else {
    env += '\nARC_BONDED_ANCHOR_ADDRESS=' + address + '\n'
  }
  writeFileSync('.env', env)

  const abiPath = './contracts/arc/BondedWitnessAnchor.abi.json'
  mkdirSync(dirname(abiPath), { recursive: true })
  writeFileSync(abiPath, JSON.stringify(abi, null, 2))
  console.log('[deploy] ARC_BONDED_ANCHOR_ADDRESS written to .env')
  console.log('[deploy] ABI written to', abiPath)

  // Snapshot deployment artifact for the Circle grant application.
  const snapshot = {
    contract: 'BondedWitnessAnchor',
    address,
    txHash,
    chainId: Number(chainId),
    rpcUrl: process.env.ARC_TESTNET_RPC_URL!,
    usdc,
    treasury,
    deployer: addr,
    deployElapsedMs: elapsed,
    bytecodeSize: bytecode.length / 2,
    solcVersion: solc.version(),
    deployedAt: new Date().toISOString(),
    arcscanUrl: `https://testnet.arcscan.app/address/${address}`,
    txUrl: `https://testnet.arcscan.app/tx/${txHash}`,
  }
  const snapshotPath = './docs/deployments/arc-testnet-BondedWitnessAnchor.json'
  mkdirSync(dirname(snapshotPath), { recursive: true })
  writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2))
  console.log('[deploy] snapshot written to', snapshotPath)
}

main().catch((err) => {
  console.error('[deploy] FAILED:', err.message ?? err)
  process.exit(1)
})
