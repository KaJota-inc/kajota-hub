import 'dotenv/config'
import OpenAI from 'openai'

async function main() {
  const key = process.env.GROQ_API_KEY
  if (!key) { console.error('GROQ_API_KEY not set'); process.exit(1) }
  if (!key.startsWith('gsk_')) {
    console.error(`Key does not start with gsk_ (got: ${key.slice(0, 6)}…). Groq keys start with gsk_.`)
    process.exit(2)
  }
  console.log(`[probe] Groq key (len=${key.length})`)
  const client = new OpenAI({ apiKey: key, baseURL: 'https://api.groq.com/openai/v1' })
  const r = await client.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [{ role: 'user', content: 'Reply with the single word: pong' }],
    max_tokens: 10,
  })
  console.log('[probe] response:', (r.choices[0]?.message?.content ?? '').trim())
}

main().catch((err) => { console.error('[probe] FAILED:', err.message ?? err); process.exit(1) })
