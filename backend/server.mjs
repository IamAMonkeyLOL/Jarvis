import http from 'node:http';
import { pathToFileURL } from 'node:url';

export function createBackend(env = process.env, request = fetch) {
  let used = 0, day = new Date().toISOString().slice(0, 10), active = 0;
  const limit = Number(env.DAILY_REQUEST_LIMIT || 100);
  if (!Number.isInteger(limit) || limit < 1) throw new Error('Invalid DAILY_REQUEST_LIMIT');
  const origins = (env.ALLOWED_ORIGINS || 'https://iamamonkeylol.github.io').split(',').map(s => s.trim());
  return http.createServer(async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Vary', 'Origin');
    const respond = (status, data) => { res.writeHead(status); res.end(JSON.stringify(data)); };
    if (req.url === '/health' && req.method === 'GET') return respond(200, {status:'ok', configured: Boolean(env.OPENAI_API_KEY && env.OPENAI_MODEL)});
    if (req.url !== '/chat') return respond(404, {error:'Not found'});
    if (!origins.includes(req.headers.origin)) return respond(403, {error:'Origin not allowed'});
    res.setHeader('Access-Control-Allow-Origin', req.headers.origin);
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }
    if (req.method !== 'POST') return respond(405, {error:'Use POST'});
    if (!env.OPENAI_API_KEY || !env.OPENAI_MODEL) return respond(503, {error:'Server API key and model must be configured'});
    if (!req.headers['content-type']?.startsWith('application/json')) return respond(415, {error:'Use application/json'});
    let input;
    try {
      const chunks = []; let size = 0;
      for await (const chunk of req) { size += chunk.length; if (size > 64000) { respond(413, {error:'Request too large'}); return; } chunks.push(chunk); }
      input = JSON.parse(Buffer.concat(chunks).toString('utf8')).messages;
      if (!Array.isArray(input) || !input.length || input.length > 40 || input.some(m => !m || !['user','assistant'].includes(m.role) || typeof m.content !== 'string' || !m.content.trim() || m.content.length > 12000) || input.at(-1).role !== 'user') throw new Error();
      input = input.map(({role,content}) => ({role,content}));
    } catch { return respond(400, {error:'Invalid messages'}); }
    const today = new Date().toISOString().slice(0,10);
    if (today !== day) { day = today; used = 0; }
    if (used >= limit || active >= 3) return respond(429, {error:'Usage limit reached. Try later.'});
    used++; active++;
    try {
      const upstream = await request('https://api.openai.com/v1/responses', {
        method:'POST', headers:{Authorization:`Bearer ${env.OPENAI_API_KEY}`, 'Content-Type':'application/json'},
        body:JSON.stringify({model:env.OPENAI_MODEL, instructions:'You are Jarvis, a thoughtful creative assistant. Help with planning, writing, and 3D project ideas. Be honest about your capabilities: you cannot access the user’s files, launch desktop software, or perform actions from this website.', input, max_output_tokens:1200, store:false}),
        signal:AbortSignal.timeout(50000)
      });
      if (!upstream.ok) return respond(upstream.status === 429 ? 429 : 502, {error:'AI provider request failed. Check server account, model, and billing.'});
      const data = await upstream.json();
      const reply = (data.output || []).filter(item => item.type === 'message').flatMap(item => item.content || []).filter(item => item.type === 'output_text').map(item => item.text).join('\n');
      if (!reply) return respond(502, {error:'AI provider returned no text'});
      respond(200, {reply});
    } catch { respond(502, {error:'AI service unavailable or timed out'}); }
    finally { active--; }
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = createBackend();
  server.requestTimeout = 65000;
  server.listen(Number(process.env.PORT || 8787), process.env.HOST || '127.0.0.1', () => console.log('Jarvis backend started. Use /health to check configuration.'));
}
