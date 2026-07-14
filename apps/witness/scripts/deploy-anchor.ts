import 'dotenv/config'
import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import solc from 'solc'
import { ethers } from 'ethers'

const REQUIRED = ['ZG_RPC_URL', 'WITNESS_DEPLOYER_PK'] as const

function loadEnv() {
  for (const k of REQUIRED) {
    if (!process.env[k]) {
      console.error(`Missing env var: ${k}`)
      process.exit(1)
    }
  }
}

async function main() {
  loadEnv()

  console.log('[deploy] reading contract source...')
  const source = readFileSync('./contracts/WitnessAnchor.sol', 'utf8')

  console.log('[deploy] compiling with solc', solc.version())
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
      console[e.severity === 'error' ? 'error' : 'warn'](`[solc] ${e.severity}: ${e.formattedMessage ?? e.message}`)
      if (e.severity === 'error') fatal = true
    }
    if (fatal) process.exit(2)
  }
  const compiled = output.contracts['WitnessAnchor.sol']['WitnessAnchor']
  const abi = compiled.abi
  const bytecode = compiled.evm.bytecode.object
  console.log('[deploy] bytecode size:', bytecode.length / 2, 'bytes')

  const provider = new ethers.JsonRpcProvider(process.env.ZG_RPC_URL!)
  const signer = new ethers.Wallet(process.env.WITNESS_DEPLOYER_PK!, provider)
  const addr = await signer.getAddress()
  const bal = await provider.getBalance(addr)
  console.log('[deploy] signer:', addr)
  console.log('[deploy] balance:', ethers.formatEther(bal), '0G')

  if (bal === 0n) {
    console.error('[deploy] zero balance — drip at https://faucet.0g.ai')
    process.exit(3)
  }

  console.log('[deploy] deploying WitnessAnchor to 0G Galileo (chainId 16602)...')
  const factory = new ethers.ContractFactory(abi, '0x' + bytecode, signer)
  const t0 = Date.now()
  const deployed = await factory.deploy()
  await deployed.waitForDeployment()
  const elapsed = Date.now() - t0
  const address = await deployed.getAddress()
  const txHash = deployed.deploymentTransaction()?.hash ?? '(unknown)'
  console.log(`[deploy] ✅ deployed in ${elapsed}ms`)
  console.log(`[deploy] address:   ${address}`)
  console.log(`[deploy] tx:        ${txHash}`)
  console.log(`[deploy] chainscan: https://chainscan-galileo.0g.ai/address/${address}`)

  if (!existsSync('.env')) copyFileSync('.env.example', '.env')
  let env = readFileSync('.env', 'utf8')
  if (env.match(/^WITNESS_ANCHOR_ADDRESS=.*$/m)) {
    env = env.replace(/^WITNESS_ANCHOR_ADDRESS=.*$/m, 'WITNESS_ANCHOR_ADDRESS=' + address)
  } else {
    env += '\nWITNESS_ANCHOR_ADDRESS=' + address + '\n'
  }
  writeFileSync('.env', env)

  const abiPath = './contracts/WitnessAnchor.abi.json'
  mkdirSync(dirname(abiPath), { recursive: true })
  writeFileSync(abiPath, JSON.stringify(abi, null, 2))
  console.log('[deploy] WITNESS_ANCHOR_ADDRESS written to .env')
  console.log('[deploy] ABI written to', abiPath)
}

main().catch((err) => {
  console.error('[deploy] FAILED:', err.message ?? err)
  process.exit(1)
})
