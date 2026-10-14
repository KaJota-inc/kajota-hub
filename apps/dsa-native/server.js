// dsa-native server — serves the SPA from ./public and exposes /api/sync
// (token-keyed MongoDB upsert). Lives behind Caddy's `handle_path /dsa-native/*`
// which strips the mount prefix, so this process sees requests at root.
//
// Env:
//   PORT              bound port (set by run script, default 8112)
//   MONGODB_URI       Atlas SRV URI — same cluster as the rest of the kajota apps
//   MONGODB_DB        optional override, defaults to 'dsa_native'
//
// Fail-closed: if MONGODB_URI is unset, /api/sync returns 503 (not 500) so the
// client's sync dot can show "not configured" rather than "error".

const path = require('path');
const express = require('express');
const { MongoClient } = require('mongodb');

const PORT = parseInt(process.env.PORT || '8112', 10);
const MONGODB_URI = process.env.MONGODB_URI || '';
const DB_NAME = process.env.MONGODB_DB || 'dsa_native';
const COLLECTION = 'user_state';
const MAX_BYTES = 256 * 1024; // 256 KB per state blob

const isConfigured = Boolean(MONGODB_URI);

let cachedClient = null;
let cachedDb = null;

async function getDb() {
  if (!isConfigured) throw new Error('db not configured');
  if (cachedDb) return cachedDb;
  cachedClient = new MongoClient(MONGODB_URI, {
    maxPoolSize: 5,
    serverSelectionTimeoutMS: 8000,
  });
  await cachedClient.connect();
  cachedDb = cachedClient.db(DB_NAME);
  await cachedDb.collection(COLLECTION).createIndex({ token: 1 }, { unique: true });
  return cachedDb;
}

function sanitizeToken(token) {
  if (!token || typeof token !== 'string') return null;
  const safe = token.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 64);
  return safe || null;
}

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '512kb' }));

// Permissive CORS — same origin via Caddy mount anyway, but keeps direct
// debugging + health probes trivial.
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  next();
});

app.get('/healthz', (_req, res) => {
  res.status(200).json({
    status: 'ok',
    configured: isConfigured,
    uptime: process.uptime(),
    db: DB_NAME,
  });
});

app.get('/api/sync', async (req, res) => {
  if (!isConfigured) {
    return res.status(503).json({
      error: 'db not configured',
      hint: 'Set MONGODB_URI in the Render env group for kajota-hub.',
    });
  }
  const token = sanitizeToken(String(req.query.token || ''));
  if (!token) return res.status(400).json({ error: 'token required' });
  try {
    const db = await getDb();
    const doc = await db.collection(COLLECTION).findOne({ token });
    if (!doc) return res.status(204).end();
    return res.status(200).json({ state: doc.state, fetchedAt: new Date().toISOString() });
  } catch (err) {
    console.error('[sync GET]', err.message);
    return res.status(500).json({ error: 'internal', message: err.message });
  }
});

app.post('/api/sync', async (req, res) => {
  if (!isConfigured) {
    return res.status(503).json({
      error: 'db not configured',
      hint: 'Set MONGODB_URI in the Render env group for kajota-hub.',
    });
  }
  const { token, state } = req.body || {};
  const safe = sanitizeToken(token);
  if (!safe) return res.status(400).json({ error: 'token required' });
  if (!state || typeof state !== 'object') return res.status(400).json({ error: 'state object required' });
  const encoded = JSON.stringify(state);
  if (encoded.length > MAX_BYTES) return res.status(413).json({ error: 'state too large', max: MAX_BYTES });
  try {
    const db = await getDb();
    await db.collection(COLLECTION).updateOne(
      { token: safe },
      {
        $set: { token: safe, state, updatedAt: new Date() },
        $setOnInsert: { createdAt: new Date() },
      },
      { upsert: true }
    );
    return res.status(200).json({ ok: true, bytes: encoded.length, savedAt: new Date().toISOString() });
  } catch (err) {
    console.error('[sync POST]', err.message);
    return res.status(500).json({ error: 'internal', message: err.message });
  }
});

app.delete('/api/sync', async (req, res) => {
  if (!isConfigured) {
    return res.status(503).json({ error: 'db not configured' });
  }
  const token = sanitizeToken(String(req.query.token || ''));
  if (!token) return res.status(400).json({ error: 'token required' });
  try {
    const db = await getDb();
    await db.collection(COLLECTION).deleteOne({ token });
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[sync DELETE]', err.message);
    return res.status(500).json({ error: 'internal', message: err.message });
  }
});

// Static SPA + content.json. The SPA uses relative URLs so it works both at
// the project root during local dev AND under /dsa-native/ via Caddy.
app.use(express.static(path.join(__dirname, 'public'), {
  maxAge: '5m',
  setHeaders: (res, filepath) => {
    if (filepath.endsWith('content.json')) {
      // Longer cache for the baked library; the SPA fetches it once per session.
      res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400');
    }
  },
}));

// SPA fallback for any unknown path that is not an API route.
app.use((req, res) => {
  if (req.path.startsWith('/api/')) return res.status(404).json({ error: 'not found' });
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`[dsa-native] listening on 127.0.0.1:${PORT} · db=${isConfigured ? 'configured' : 'OFF'} · dbname=${DB_NAME}`);
});
