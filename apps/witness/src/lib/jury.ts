import OpenAI from 'openai'
import type { EvidenceHit } from './memory.js'

const MODEL = 'llama-3.3-70b-versatile'
const BASE_URL = 'https://api.groq.com/openai/v1'

export type Ruling = 'refund_buyer' | 'release_to_seller' | 'split_50_50' | 'escalate_to_human'

export type JurorOutput = {
  juror: 'prosecutor' | 'defender' | 'neutral'
  argument: string
  leansToward: 'buyer' | 'seller' | 'unclear'
}

export type Verdict = {
  ruling: Ruling
  reasoning: string
  confidence: number
  evidenceCids: string[]
  jury: JurorOutput[]
  ts: number
  model: string
}

export type DisputeInput = {
  sellerId: string
  buyerId?: string
  claim: string
  evidence: EvidenceHit[]
}

function formatEvidence(evidence: EvidenceHit[]): string {
  return evidence.map((hit, i) => {
    const lines = hit.blob.messages.map((m) => `  ${m.role}: ${m.text}`).join('\n')
    const ts = new Date(hit.blob.ts).toISOString()
    return `## Evidence ${i + 1} (cid: ${hit.entry.cid.slice(0, 20)}…, ts: ${ts}, topic: ${hit.blob.topic ?? 'none'})\n${lines}`
  }).join('\n\n')
}

const PROSECUTOR_SYSTEM = `You represent the buyer in an e-commerce dispute. Build the strongest case that the seller breached their commitment, citing specific messages from the evidence. Be precise — quote exact phrases. If the evidence does not support the buyer's claim, say so honestly; do not fabricate.

Reply with JSON only:
{"argument": "<200 words max>", "leansToward": "buyer" | "seller" | "unclear"}`

const DEFENDER_SYSTEM = `You represent the seller in an e-commerce dispute. Build the strongest case that the seller fulfilled their commitment, citing specific messages from the evidence. Be precise — quote exact phrases. If the evidence does not support the seller, say so honestly; do not fabricate.

Reply with JSON only:
{"argument": "<200 words max>", "leansToward": "buyer" | "seller" | "unclear"}`

const NEUTRAL_SYSTEM = `You are a neutral analyst reviewing an e-commerce dispute. Read the evidence and the buyer's claim. State plainly: what is clearly established by the evidence, what is contested, what is missing.

Reply with JSON only:
{"argument": "<200 words max>", "leansToward": "buyer" | "seller" | "unclear"}`

const JUDGE_SYSTEM = `You are the chief judge of an AI jury for e-commerce disputes. You are given the buyer's claim, the evidence, and three jurors' outputs (prosecutor, defender, neutral analyst). Render a verdict.

Allowed rulings:
- refund_buyer: evidence clearly favors the buyer
- release_to_seller: evidence clearly favors the seller
- split_50_50: evidence is genuinely contested or both bear responsibility
- escalate_to_human: evidence is too sparse, contradictory, or off-topic for an AI to decide

Reply with JSON only:
{
  "ruling": "refund_buyer" | "release_to_seller" | "split_50_50" | "escalate_to_human",
  "reasoning": "<200 words max, cite specific evidence>",
  "confidence": <number between 0 and 1>
}`

type ChatOpts = {
  system: string
  user: string
  maxTokens?: number
  temperature?: number
}

async function chatJson(client: OpenAI, opts: ChatOpts): Promise<any> {
  const response = await client.chat.completions.create({
    model: MODEL,
    messages: [
      { role: 'system', content: opts.system },
      { role: 'user', content: opts.user },
    ],
    response_format: { type: 'json_object' },
    max_tokens: opts.maxTokens ?? 800,
    temperature: opts.temperature ?? 0.6,
  })
  const text = response.choices[0]?.message?.content ?? ''
  return parseJson(text)
}

function parseJson(text: string): any {
  const trimmed = text.trim()
  try { return JSON.parse(trimmed) } catch {}
  const match = trimmed.match(/\{[\s\S]*\}/)
  if (!match) throw new Error(`no JSON object in response: ${trimmed.slice(0, 200)}`)
  return JSON.parse(match[0])
}

function normalizeLean(v: any): 'buyer' | 'seller' | 'unclear' {
  if (v === 'buyer' || v === 'seller' || v === 'unclear') return v
  return 'unclear'
}

function normalizeRuling(v: any): Ruling {
  if (v === 'refund_buyer' || v === 'release_to_seller' || v === 'split_50_50' || v === 'escalate_to_human') return v
  return 'escalate_to_human'
}

async function callJuror(
  client: OpenAI,
  system: string,
  user: string,
  juror: JurorOutput['juror'],
): Promise<JurorOutput> {
  const parsed = await chatJson(client, { system, user, temperature: 0.6 })
  return {
    juror,
    argument: String(parsed.argument ?? '').slice(0, 1500),
    leansToward: normalizeLean(parsed.leansToward),
  }
}

export async function deliberate(input: DisputeInput): Promise<Verdict> {
  if (!process.env.GROQ_API_KEY) throw new Error('GROQ_API_KEY not set')
  const client = new OpenAI({ apiKey: process.env.GROQ_API_KEY, baseURL: BASE_URL })

  const evidenceText = formatEvidence(input.evidence)
  const baseContext = `# Dispute
- Seller: ${input.sellerId}
- Buyer: ${input.buyerId ?? '(unspecified)'}

# Buyer's claim
${input.claim}

# Evidence (decrypted from 0G Storage)
${evidenceText}
`

  const [prosecutor, defender, neutral] = await Promise.all([
    callJuror(client, PROSECUTOR_SYSTEM, baseContext, 'prosecutor'),
    callJuror(client, DEFENDER_SYSTEM, baseContext, 'defender'),
    callJuror(client, NEUTRAL_SYSTEM, baseContext, 'neutral'),
  ])

  const judgePrompt = `${baseContext}

# Juror outputs
## Prosecutor (leans: ${prosecutor.leansToward})
${prosecutor.argument}

## Defender (leans: ${defender.leansToward})
${defender.argument}

## Neutral analyst (leans: ${neutral.leansToward})
${neutral.argument}
`

  const judgeParsed = await chatJson(client, {
    system: JUDGE_SYSTEM,
    user: judgePrompt,
    temperature: 0.4,
  })

  return {
    ruling: normalizeRuling(judgeParsed.ruling),
    reasoning: String(judgeParsed.reasoning ?? '').slice(0, 1500),
    confidence: Math.max(0, Math.min(1, Number(judgeParsed.confidence ?? 0))),
    evidenceCids: input.evidence.map((e) => e.entry.cid),
    jury: [prosecutor, defender, neutral],
    ts: Date.now(),
    model: MODEL,
  }
}
