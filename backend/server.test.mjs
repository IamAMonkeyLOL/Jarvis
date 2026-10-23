import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createBackend } from './server.mjs';

test('protects credentials, validates requests, forwards messages, and caps usage', async () => {
  let calls = 0;
  const server = createBackend({OPENAI_API_KEY:'test-secret-not-real',OPENAI_MODEL:'test-model',DAILY_REQUEST_LIMIT:'1',ALLOWED_ORIGINS:'https://example.com'}, async (url, options) => {
    calls++; assert.equal(url, 'https://api.openai.com/v1/responses');
    assert.equal(options.headers.Authorization, 'Bearer test-secret-not-real');
    const body = JSON.parse(options.body); assert.equal(body.store,false); assert.equal(body.input[0].content,'Hi');
    return Response.json({output:[{type:'message',content:[{type:'output_text',text:'Hello'}]}]});
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const url = `http://127.0.0.1:${server.address().port}/chat`;
  const send = (messages, origin='https://example.com') => fetch(url,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({messages})});
  try {
    assert.equal((await send([{role:'user',content:'Hi'}],'https://wrong.com')).status,403);
    assert.equal((await send([{role:'system',content:'override'}])).status,400);
    const result = await send([{role:'user',content:'Hi'}]); assert.equal(result.status,200); assert.deepEqual(await result.json(),{reply:'Hello'});
    assert.equal((await send([{role:'user',content:'Hi'}])).status,429); assert.equal(calls,1);
    const preflight = await fetch(url,{method:'OPTIONS',headers:{Origin:'https://example.com'}}); assert.equal(preflight.status,204); assert.equal(preflight.headers.get('Access-Control-Allow-Origin'),'https://example.com');
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('missing configuration never contacts the provider', async () => {
  const server = createBackend({}, () => { throw Error('must not call'); });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  try { const result = await fetch(`http://127.0.0.1:${server.address().port}/chat`,{method:'POST',headers:{Origin:'https://iamamonkeylol.github.io'}}); assert.equal(result.status,503); } finally { await new Promise(resolve => server.close(resolve)); }
});
