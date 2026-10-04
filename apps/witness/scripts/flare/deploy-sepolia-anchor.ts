/**
 * Deploy WitnessAnchor.sol to Ethereum Sepolia.
 *
 * Why Sepolia? Flare's FDC EVMTransaction attestation type supports these
 * source chains on Coston2 testnet: testFLR, testETH (Sepolia), testSGB.
 * 0G Galileo is NOT a supported source. Redeploying the SAME WitnessAnchor
 * bytecode on Sepolia gives Flare a source to attest, without changing the
 * contract itself.
 *
 * Usage:
 *   SEPOLIA_RPC_URL=... WITNESS_DEPLOYER_PK=0x... \
 *     npx tsx scripts/flare/deploy-sepolia-anchor.ts
 */
import 'dotenv/config'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { ethers } from 'ethers'
import solc from 'solc'

const REQUIRED = ['SEPOLIA_RPC_URL', 'WITNESS_DEPLOYER_PK'] as const

function loadEnv() {
  for (const k of REQUIRED) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      process.exit(1)
    }
  }
}

function compile() {
  const source = readFileSync('./contracts/WitnessAnchor.sol', 'utf8')
  const input = {
    language: 'Solidity',
    sources: { 'WitnessAnchor.sol': { content: source } },
    settings: {
      optimizer: { enabled: true, runs: 200 },
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } },
    },
  }
  const output = JSON.parse(solc.compile(JSON.stringify(input)))
  if (output.errors) {
    let fatal = false
    for (const e of output.errors) {
      const line = `[solc] ${e.severity}: ${e.formattedMessage ?? e.message}`
      if (e.severity === 'error') {
        console.error(line)
        fatal = true
      } else {
        console.warn(line)
      }
    }
    if (fatal) process.exit(2)
  }
  const c = output.contracts['WitnessAnchor.sol']['WitnessAnchor']
  return { abi: c.abi, bytecode: '0x' + c.evm.bytecode.object }
}

async function main() {
  loadEnv()

  console.log('[deploy] compiling WitnessAnchor with solc', solc.version())
  const { abi, bytecode } = compile()

  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const addr = await signer.getAddress()
  const bal = await provider.getBalance(addr)
  const net = await provider.getNetwork()

  console.log('[deploy] network:  chainId', net.chainId.toString(), '(expected 11155111)')
  console.log('[deploy] signer:  ', addr)
  console.log('[deploy] balance: ', ethers.formatEther(bal), 'ETH')

  if (net.chainId !== 11155111n) {
    console.error('[deploy] wrong network — expected Sepolia (chainId 11155111)')
    process.exit(3)
  }
  if (bal === 0n) {
    console.error('[deploy] zero balance — drip from https://sepoliafaucet.com')
    process.exit(3)
  }

  console.log('[deploy] deploying to Ethereum Sepolia...')
  const factory = new ethers.ContractFactory(abi, bytecode, signer)
  const t0 = Date.now()
  const deployed = await factory.deploy()
  await deployed.waitForDeployment()
  const elapsed = Date.now() - t0
  const address = await deployed.getAddress()
  const txHash = deployed.deploymentTransaction()?.hash ?? '(unknown)'

  console.log(`[deploy] ✅ deployed in ${elapsed}ms`)
  console.log(`[deploy] address:   ${address}`)
  console.log(`[deploy] tx:        ${txHash}`)
  console.log(`[deploy] etherscan: https://sepolia.etherscan.io/address/${address}`)

  // Write to .env
  if (!existsSync('.env')) writeFileSync('.env', '')
  let env = readFileSync('.env', 'utf8')
  const line = `WITNESS_ANCHOR_SEPOLIA=${address}`
  if (env.match(/^WITNESS_ANCHOR_SEPOLIA=.*$/m)) {
    env = env.replace(/^WITNESS_ANCHOR_SEPOLIA=.*$/m, line)
  } else {
    env += (env.endsWith('\n') || env.length === 0 ? '' : '\n') + line + '\n'
  }
  writeFileSync('.env', env)
  console.log('[deploy] WITNESS_ANCHOR_SEPOLIA written to .env')
}

main().catch((err) => {
  console.error('[deploy] FAILED:', err?.stack ?? err?.message ?? err)
  process.exit(1)
})
