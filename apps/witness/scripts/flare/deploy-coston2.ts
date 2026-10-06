/**
 * Deploy FlareWitnessConsumer + FlareCosellEscrow to Flare Coston2 (chainId 114).
 *
 * Prereqs:
 *   - Ethereum Sepolia deploy already done: WITNESS_ANCHOR_SEPOLIA in .env
 *   - Coston2 RPC + funded deployer wallet: COSTON2_RPC_URL, WITNESS_DEPLOYER_PK
 *   - Coston2 faucet: https://faucet.flare.network/coston2 (0.1 C2FLR/drip)
 *
 * Usage:
 *   npx tsx scripts/flare/deploy-coston2.ts
 */
import 'dotenv/config'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { ethers } from 'ethers'
import solc from 'solc'
import { compileFlareContract } from './compile.js'

const REQUIRED = ['COSTON2_RPC_URL', 'WITNESS_DEPLOYER_PK', 'WITNESS_ANCHOR_SEPOLIA'] as const

function loadEnv() {
  for (const k of REQUIRED) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      if (k === 'WITNESS_ANCHOR_SEPOLIA') {
        console.error('  → run scripts/flare/deploy-sepolia-anchor.ts first')
      }
      process.exit(1)
    }
  }
}

function upsertEnv(key: string, value: string) {
  if (!existsSync('.env')) writeFileSync('.env', '')
  let env = readFileSync('.env', 'utf8')
  const line = `${key}=${value}`
  const re = new RegExp(`^${key}=.*$`, 'm')
  if (env.match(re)) {
    env = env.replace(re, line)
  } else {
    env += (env.endsWith('\n') || env.length === 0 ? '' : '\n') + line + '\n'
  }
  writeFileSync('.env', env)
}

async function main() {
  loadEnv()

  console.log('[deploy] compiling Flare contracts with solc', solc.version())
  const consumer = compileFlareContract('FlareWitnessConsumer.sol', 'FlareWitnessConsumer')
  const escrow = compileFlareContract('FlareCosellEscrow.sol', 'FlareCosellEscrow')
  console.log('[deploy] consumer bytecode:', consumer.bytecode.length / 2 - 1, 'bytes')
  console.log('[deploy] escrow bytecode:  ', escrow.bytecode.length / 2 - 1, 'bytes')

  const provider = new ethers.JsonRpcProvider(process.env.COSTON2_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const addr = await signer.getAddress()
  const bal = await provider.getBalance(addr)
  const net = await provider.getNetwork()

  console.log('[deploy] network: chainId', net.chainId.toString(), '(expected 114)')
  console.log('[deploy] signer: ', addr)
  console.log('[deploy] balance:', ethers.formatEther(bal), 'C2FLR')

  if (net.chainId !== 114n) {
    console.error('[deploy] wrong network — expected Coston2 (chainId 114)')
    process.exit(3)
  }
  if (bal === 0n) {
    console.error('[deploy] zero balance — drip from https://faucet.flare.network/coston2')
    process.exit(3)
  }

  const sepoliaAnchor = process.env.WITNESS_ANCHOR_SEPOLIA!
  console.log('[deploy] linking Sepolia WitnessAnchor:', sepoliaAnchor)

  const consumerFactory = new ethers.ContractFactory(consumer.abi, consumer.bytecode, signer)
  const t0 = Date.now()
  const consumerContract = await consumerFactory.deploy(sepoliaAnchor)
  await consumerContract.waitForDeployment()
  const consumerAddr = await consumerContract.getAddress()
  const consumerTx = consumerContract.deploymentTransaction()?.hash ?? '(unknown)'

  console.log(`[deploy] ✅ FlareWitnessConsumer deployed`)
  console.log(`         address:  ${consumerAddr}`)
  console.log(`         tx:       ${consumerTx}`)
  console.log(`         explorer: https://coston2-explorer.flare.network/address/${consumerAddr}`)

  const escrowFactory = new ethers.ContractFactory(escrow.abi, escrow.bytecode, signer)
  const escrowContract = await escrowFactory.deploy(consumerAddr)
  await escrowContract.waitForDeployment()
  const escrowAddr = await escrowContract.getAddress()
  const escrowTx = escrowContract.deploymentTransaction()?.hash ?? '(unknown)'
  const elapsed = Date.now() - t0

  console.log(`[deploy] ✅ FlareCosellEscrow deployed`)
  console.log(`         address:  ${escrowAddr}`)
  console.log(`         tx:       ${escrowTx}`)
  console.log(`         explorer: https://coston2-explorer.flare.network/address/${escrowAddr}`)
  console.log(`[deploy] both contracts up in ${elapsed}ms`)

  upsertEnv('FLARE_CONSUMER_COSTON2', consumerAddr)
  upsertEnv('FLARE_ESCROW_COSTON2', escrowAddr)

  writeFileSync(
    './contracts/flare/FlareWitnessConsumer.abi.json',
    JSON.stringify(consumer.abi, null, 2)
  )
  writeFileSync(
    './contracts/flare/FlareCosellEscrow.abi.json',
    JSON.stringify(escrow.abi, null, 2)
  )
  console.log('[deploy] addresses written to .env, ABIs to contracts/flare/')
}

main().catch((err) => {
  console.error('[deploy] FAILED:', err?.stack ?? err?.message ?? err)
  process.exit(1)
})
