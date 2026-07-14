import { Indexer, MemData } from '@0gfoundation/0g-storage-ts-sdk'
import { ethers } from 'ethers'

export type OgConfig = {
  rpcUrl: string
  indexerUrl: string
  privateKey: string
}

export type UploadResult = {
  rootHash: string
  txHash: string
  storageScanUrl: string
  chainScanUrl: string
}

export type OgClient = {
  address: string
  uploadBytes(data: Buffer): Promise<UploadResult>
  downloadBytes(rootHash: string): Promise<Buffer>
}

export function makeOgClient(cfg: OgConfig): OgClient {
  const provider = new ethers.JsonRpcProvider(cfg.rpcUrl)
  const signer = new ethers.Wallet(cfg.privateKey, provider)
  const indexer = new Indexer(cfg.indexerUrl)

  return {
    address: signer.address,

    async uploadBytes(data: Buffer): Promise<UploadResult> {
      const memData = new MemData(data)
      const [tx, err] = await indexer.upload(memData, cfg.rpcUrl, signer)
      if (err !== null) throw new Error(`0G upload failed: ${err.message ?? err}`)
      if ('txHash' in tx) {
        return {
          rootHash: tx.rootHash,
          txHash: tx.txHash,
          storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${tx.rootHash}`,
          chainScanUrl: `https://chainscan-galileo.0g.ai/tx/${tx.txHash}`,
        }
      }
      return {
        rootHash: tx.rootHashes[0],
        txHash: tx.txHashes[0],
        storageScanUrl: `https://storagescan-galileo.0g.ai/tx/${tx.rootHashes[0]}`,
        chainScanUrl: `https://chainscan-galileo.0g.ai/tx/${tx.txHashes[0]}`,
      }
    },

    async downloadBytes(rootHash: string): Promise<Buffer> {
      const [blob, err] = await indexer.downloadToBlob(rootHash)
      if (err !== null) throw new Error(`0G download failed: ${err.message ?? err}`)
      const arr = await blob.arrayBuffer()
      return Buffer.from(arr)
    },
  }
}
