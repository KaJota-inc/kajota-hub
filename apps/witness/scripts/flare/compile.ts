import { readFileSync, existsSync } from 'node:fs'
import { resolve, dirname, join } from 'node:path'
import solc from 'solc'

/**
 * Resolve imports encountered by solc while compiling a contract that lives
 * under `contracts/flare/`. Supports:
 *   - `@flarenetwork/flare-periphery-contracts/**` from node_modules
 *   - `./Other.sol` sibling files inside `contracts/flare/`
 *   - `../elsewhere.sol` relative parent paths
 */
function importResolver(sourcePath: string): { contents?: string; error?: string } {
  const NM_PREFIXES = ['@flarenetwork/', '@openzeppelin/']

  // node_modules package imports
  for (const prefix of NM_PREFIXES) {
    if (sourcePath.startsWith(prefix)) {
      const nmPath = resolve('./node_modules', sourcePath)
      if (existsSync(nmPath)) {
        return { contents: readFileSync(nmPath, 'utf8') }
      }
      return { error: `node_modules import not found: ${sourcePath}` }
    }
  }

  // Relative imports from a flare contract's directory
  const flareDir = resolve('./contracts/flare')
  const candidate = resolve(flareDir, sourcePath)
  if (existsSync(candidate)) {
    return { contents: readFileSync(candidate, 'utf8') }
  }

  return { error: `Unresolved import: ${sourcePath}` }
}

export interface CompiledContract {
  abi: any[]
  bytecode: string
}

export function compileFlareContract(entryFile: string, contractName: string): CompiledContract {
  const entryPath = resolve('./contracts/flare', entryFile)
  if (!existsSync(entryPath)) {
    throw new Error(`Entry contract not found: ${entryPath}`)
  }

  const input = {
    language: 'Solidity',
    sources: {
      [entryFile]: { content: readFileSync(entryPath, 'utf8') },
    },
    settings: {
      viaIR: true,
      optimizer: { enabled: true, runs: 200 },
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } },
    },
  }

  const output = JSON.parse(
    solc.compile(JSON.stringify(input), { import: importResolver })
  )

  if (output.errors) {
    let fatal = false
    for (const err of output.errors) {
      const line = `[solc] ${err.severity}: ${err.formattedMessage ?? err.message}`
      if (err.severity === 'error') {
        console.error(line)
        fatal = true
      } else {
        console.warn(line)
      }
    }
    if (fatal) throw new Error('Solidity compilation failed')
  }

  const contract = output.contracts?.[entryFile]?.[contractName]
  if (!contract) {
    const available = Object.keys(output.contracts?.[entryFile] ?? {}).join(', ')
    throw new Error(
      `Contract ${contractName} not found in ${entryFile}. Available: [${available}]`
    )
  }

  return {
    abi: contract.abi,
    bytecode: '0x' + contract.evm.bytecode.object,
  }
}
