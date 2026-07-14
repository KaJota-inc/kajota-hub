import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { cosineSimilarity, EMBEDDING_DIMS } from './embed.js'

export type IndexEntry = {
  cid: string
  sellerId: string
  ts: number
  embedding: number[]
  keyHex: string
  metadata: {
    kind: 'chat' | 'verdict'
    summary?: string
    participants?: string[]
    ruling?: string
    confidence?: number
    evidenceCids?: string[]
    disputeId?: string
  }
}

export type SearchHit = {
  entry: IndexEntry
  score: number
}

type IndexFile = { version: 1; entries: IndexEntry[] }

const EMPTY: IndexFile = { version: 1, entries: [] }

export class IndexStore {
  private path: string
  private cache: IndexFile

  constructor(path: string) {
    this.path = path
    if (existsSync(path)) {
      const raw = readFileSync(path, 'utf8')
      const parsed = JSON.parse(raw) as IndexFile
      if (parsed.version !== 1) throw new Error(`unsupported index version: ${parsed.version}`)
      this.cache = parsed
    } else {
      mkdirSync(dirname(path), { recursive: true })
      this.cache = { ...EMPTY, entries: [] }
      this.flush()
    }
  }

  add(entry: IndexEntry): void {
    if (entry.embedding.length !== EMBEDDING_DIMS) {
      throw new Error(`embedding dim ${entry.embedding.length} != expected ${EMBEDDING_DIMS}`)
    }
    this.cache.entries.push(entry)
    this.flush()
  }

  count(): number {
    return this.cache.entries.length
  }

  list(filter?: (e: IndexEntry) => boolean): IndexEntry[] {
    return filter ? this.cache.entries.filter(filter) : [...this.cache.entries]
  }

  topK(queryEmbedding: Float32Array, k: number, filter?: (e: IndexEntry) => boolean): SearchHit[] {
    const pool = filter ? this.cache.entries.filter(filter) : this.cache.entries
    const scored: SearchHit[] = pool.map((entry) => ({
      entry,
      score: cosineSimilarity(queryEmbedding, new Float32Array(entry.embedding)),
    }))
    scored.sort((a, b) => b.score - a.score)
    return scored.slice(0, k)
  }

  getByCid(cid: string): IndexEntry | null {
    return this.cache.entries.find((e) => e.cid === cid) ?? null
  }

  private flush(): void {
    writeFileSync(this.path, JSON.stringify(this.cache, null, 2))
  }
}
