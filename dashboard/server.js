// Crewism dashboard server. Serves the static UI and proxies /api/*
// to the bot's localhost-only API (adds the bearer token server-side,
// so the browser never holds it).
const path = require('path');
const express = require('express');

const BOT_API = `http://127.0.0.1:${process.env.DASHBOARD_PORT || '3100'}`;
const TOKEN = process.env.DASHBOARD_TOKEN || '';
const HOST = process.env.DASH_HOST || '127.0.0.1';
const PORT = Number(process.env.DASH_PORT || '3000');

const app = express();
app.use(express.json({ limit: '256kb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.use('/api', async (req, res) => {
  try {
    const url = BOT_API + req.originalUrl;
    const init = {
      method: req.method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
    };
    if (req.method !== 'GET' && req.method !== 'HEAD') init.body = JSON.stringify(req.body || {});
    const upstream = await fetch(url, init);
    const text = await upstream.text();
    res.status(upstream.status);
    res.set('Content-Type', upstream.headers.get('content-type') || 'application/json');
    res.send(text);
  } catch (e) {
    res.status(502).json({ error: 'bot api unreachable — is the bot running?' });
  }
});

app.get('/healthz', (_req, res) => res.json({ ok: true }));

app.listen(PORT, HOST, () => {
  console.log(`[dash] ui on http://${HOST}:${PORT} → bot api ${BOT_API}`);
});
