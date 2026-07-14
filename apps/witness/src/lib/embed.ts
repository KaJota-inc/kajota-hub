import { pipeline, env } from '@xenova/transformers'

env.cacheDir = './.cache/transformers'
env.allowRemoteModels = true

const MODEL = 'Xenova/all-MiniLM-L6-v2'
const DIMS = 384

let embedderPromise: Promise<any> | null = null

async function getEmbedder() {
  if (!embedderPromise) {
    embedderPromise = pipeline('feature-extraction', MODEL)
  }
  return embedderPromise
}

export async function embed(text: string): Promise<Float32Array> {
  const embedder = await getEmbedder()
  const output = await embedder(text, { pooling: 'mean', normalize: true })
  return new Float32Array(output.data)
}

export async function embedMany(texts: string[]): Promise<Float32Array[]> {
  const embedder = await getEmbedder()
  const out: Float32Array[] = []
  for (const t of texts) {
    const r = await embedder(t, { pooling: 'mean', normalize: true })
    out.push(new Float32Array(r.data))
  }
  return out
}

export function cosineSimilarity(a: Float32Array, b: Float32Array): number {
  if (a.length !== b.length) throw new Error(`dim mismatch: ${a.length} vs ${b.length}`)
  let dot = 0
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i]
  return dot
}

export const EMBEDDING_DIMS = DIMS
