/**
 * Smoke test: compile both Flare contracts against the installed
 * @flarenetwork/flare-periphery-contracts/coston2/* imports.
 * Prints bytecode sizes; exits non-zero on any solc error.
 *
 * No RPC calls, no signers, no credentials — safe to run anywhere.
 *   npm run flare:smoke
 */
import { compileFlareContract } from './compile.js'

const targets = [
  ['FlareWitnessConsumer.sol', 'FlareWitnessConsumer'],
  ['FlareCosellEscrow.sol', 'FlareCosellEscrow'],
] as const

for (const [file, name] of targets) {
  const { abi, bytecode } = compileFlareContract(file, name)
  const size = (bytecode.length - 2) / 2
  console.log(`OK ${name} (${file}): ${size} bytes, ${abi.length} ABI entries`)
}
