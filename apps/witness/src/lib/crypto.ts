import { randomBytes, createCipheriv, createDecipheriv } from 'node:crypto'

const ALGO = 'aes-256-gcm'
const IV_LEN = 12
const TAG_LEN = 16

export type Envelope = {
  ciphertext: Buffer
  iv: Buffer
  tag: Buffer
}

export function newKey(): Buffer {
  return randomBytes(32)
}

export function encrypt(plaintext: Buffer, key: Buffer): Envelope {
  if (key.length !== 32) throw new Error('AES-256 key must be 32 bytes')
  const iv = randomBytes(IV_LEN)
  const cipher = createCipheriv(ALGO, key, iv)
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()])
  return { ciphertext, iv, tag: cipher.getAuthTag() }
}

export function decrypt(env: Envelope, key: Buffer): Buffer {
  const decipher = createDecipheriv(ALGO, key, env.iv)
  decipher.setAuthTag(env.tag)
  return Buffer.concat([decipher.update(env.ciphertext), decipher.final()])
}

export function packEnvelope(env: Envelope): Buffer {
  return Buffer.concat([env.iv, env.tag, env.ciphertext])
}

export function unpackEnvelope(packed: Buffer): Envelope {
  if (packed.length < IV_LEN + TAG_LEN) throw new Error('envelope too short')
  return {
    iv: packed.subarray(0, IV_LEN),
    tag: packed.subarray(IV_LEN, IV_LEN + TAG_LEN),
    ciphertext: packed.subarray(IV_LEN + TAG_LEN),
  }
}
