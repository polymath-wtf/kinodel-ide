// Explicit paid smoke, on an owned disposable server/root. Never reads or prints credentials.
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { createServer } = require('node:net');
const { mkdtempSync, mkdirSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { resolve, join } = require('node:path');

(async () => {
  assert.ok(process.argv.includes('--live'), 'Paid smoke requires explicit --live');
  assert.ok(process.env.LIVE_ENV_FILE && process.env.PLAYWRIGHT_MODULE, 'Set LIVE_ENV_FILE and PLAYWRIGHT_MODULE explicitly');
  const root = resolve(__dirname, '..', '..'), port = Number(process.env.LIVE_CHECK_PORT || 8767), origin = `http://127.0.0.1:${port}`;
  await new Promise((resolve, reject) => { const server = createServer(); server.once('error', reject); server.listen(port, '127.0.0.1', () => server.close(resolve)); });
  const data = mkdtempSync(join(tmpdir(), 'kinodel-live-story-'));
  const folder = process.env.SCREENSHOT_DIR ? resolve(process.env.SCREENSHOT_DIR) : null;
  if (folder) mkdirSync(folder); // New evidence only, never replace an old capture.
  const evidence = [], posts = [], errors = [];
  let server, stopped, browser;
  const python = `import sys,json
from pathlib import Path
from backend.launch import load_env_file
load_env_file(Path(sys.argv[2]))
import httpx
from backend.domain import StorytellResultV1,StorytellResultV2,StoryV1,StoryV2,StoryTextInputV1,parse_json_model,validate_story_for_text_input
OriginalClient=httpx.AsyncClient
class AuditedClient(OriginalClient):
    async def send(self,*args,**kwargs):
        response=await super().send(*args,**kwargs)
        if response.request.url.path.endswith('/chat/completions'):
            try:
                value=response.json(); usage=value.get('usage',{})
                choice=value.get('choices',[{}])[0]; content=choice.get('message',{}).get('content') or ''
                validation='not_checked'
                request=json.loads(response.request.content)
                if request['response_format']['json_schema']['name']=='storytell_result':
                    try:
                        task=json.loads(request['messages'][1]['content'])
                        projection=task['context']['projection_id']
                        if projection not in ('story-text.v1','story-text.v2'):
                            raise ValueError('Unsupported Story task projection')
                        result_type,story_type=(StorytellResultV1,StoryV1) if projection=='story-text.v1' else (StorytellResultV2,StoryV2)
                        result=parse_json_model(content.encode('utf-8'),result_type)
                        if result.story is not None:
                            prior=story_type.model_validate(task['previous_story']) if task['action']=='revise' else None
                            validate_story_for_text_input(result.story,StoryTextInputV1.model_validate(task['brief']),task['shot_ids'],prior)
                        validation={'status':result.status,'shot_coverage_matches':result.story is not None,'subjects_declared':result.story is not None}
                    except ValueError as error:
                        validation=type(error).__name__
                print('OPENROUTER_EVIDENCE '+json.dumps({'http_status':response.status_code,'model':value.get('model'),'generation_id':value.get('id'),'total_tokens':usage.get('total_tokens'),'cost':usage.get('cost'),'finish_reason':choice.get('finish_reason'),'content_chars':len(content),'validation':validation}),flush=True)
            except (ValueError,AttributeError):
                print('OPENROUTER_EVIDENCE '+json.dumps({'http_status':response.status_code}),flush=True)
        return response
httpx.AsyncClient=AuditedClient
import backend.api as api
import uvicorn
api.PORT=int(sys.argv[1])
uvicorn.run(api.create_app(),host='127.0.0.1',port=api.PORT,workers=1,proxy_headers=False,access_log=False)`;
  const start = async () => {
    server = spawn(resolve(root, '.venv313/Scripts/python.exe'), ['-B', '-c', python, String(port), resolve(process.env.LIVE_ENV_FILE)], { cwd: root, env: { ...process.env, KINODEL_DATA_ROOT: data }, stdio: ['ignore', 'pipe', 'pipe'] });
    stopped = new Promise(resolve => server.once('exit', resolve));
    let listening = false, stdout = '';
    server.stderr.on('data', chunk => { listening ||= chunk.toString().includes(`Uvicorn running on ${origin} `); });
    server.stdout.on('data', chunk => {
      stdout += chunk.toString();
      const lines = stdout.split('\n'); stdout = lines.pop();
      for (const line of lines) if (line.startsWith('OPENROUTER_EVIDENCE ')) evidence.push(JSON.parse(line.slice(20)));
    });
    for (let i = 0; i < 150; i++) {
      assert.equal(server.exitCode, null, 'Owned backend exited during startup');
      if (listening) { try { if ((await fetch(`${origin}/api/session`)).ok) return; } catch {} }
      await new Promise(r => setTimeout(r, 100));
    }
    throw Error('Owned backend did not become ready');
  };
  const stop = async () => {
    if (server && server.exitCode === null) { server.kill(); await Promise.race([stopped, new Promise((_, reject) => setTimeout(() => reject(Error('Owned backend did not stop')), 5000))]); }
  };
  try {
    await start();
    const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
    const { expect } = require(join(process.env.PLAYWRIGHT_MODULE, 'test'));
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', r => { if (r.method() === 'POST') posts.push({ endpoint: new URL(r.url()).pathname, body: r.postDataJSON() }); });
    await page.goto(origin);
    await page.getByRole('button', { name: 'Новая история', exact: true }).click();
    await page.getByLabel('Идея истории', { exact: true }).fill('Напиши на русском. Любопытный лис на лесной поляне замечает старую ленту у дерева и вешает её обратно на низкую ветку. Два простых связанных действия, тихий радостный финал. Без других персонажей.');
    await page.getByLabel('Количество кадров', { exact: true }).fill('2');
    await page.getByLabel('Длительность · секунды', { exact: true }).fill('12');
    const capture = async name => { if (folder) { mkdirSync(join(folder, name)); await page.screenshot({ path: join(folder, name, 'screen-state-desktop.png') }); } };
    await capture('start');
    await page.getByRole('button', { name: 'Начать историю', exact: true }).click();
    await expect.poll(() => new URL(page.url()).searchParams.get('execution'), { timeout: 30000 }).toMatch(/^[0-9a-f-]{36}$/);
    const id = new URL(page.url()).searchParams.get('execution');
    const projection = async () => {
      const r = await page.request.get(`${origin}/api/executions/${id}/projection`);
      assert.equal(r.status(), 200, 'Projection must be readable');
      return r.json();
    };
    const wait = async predicate => {
      for (let i = 0; i < 700; i++) {
        const p = await projection();
        if (p.status === 'blocked') throw Error(`Live provider blocked: ${p.work.find(w => w.status === 'blocked')?.blocked_reason}`);
        if (predicate(p)) return p;
        await new Promise(r => setTimeout(r, 200));
      }
      throw Error('Live operation did not settle within its bounded calls');
    };
    const v1 = await wait(p => p.review);
    assert.equal(v1.graph.id, 'kinodel.live-story'); assert.equal(v1.model, 'z-ai/glm-5.3-flash');
    await expect(page.locator('.model-badge')).toContainText('OpenRouter');
    await capture('pipeline');
    await page.getByRole('button', { name: 'Chat', exact: true }).first().click();
    await expect(page.locator('.story-body')).toBeVisible();
    await capture('chat');
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Почему этот финал завершает историю?');
    await expect(page.getByRole('button', { name: 'Отправить вопрос', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    const explained = await wait(p => p.review && p.review.request_id !== v1.review.request_id);
    assert.deepEqual(explained.stories, v1.stories);
    assert.equal(explained.reviews[0].result.response.status, 'clarified');
    await stop(); await start();
    await page.reload();
    await expect(page.locator('.story-body')).toBeVisible();
    assert.deepEqual((await projection()).stories, v1.stories);
    await page.getByRole('button', { name: 'Очистить черновик', exact: true }).click();
    await page.getByRole('button', { name: 'Правка', exact: true }).click();
    await page.getByLabel('Неприменённый черновик', { exact: true }).fill('Сделай финал чуть более радостным, сохрани два кадра и всех объявленных субъектов.');
    await expect(page.getByRole('button', { name: 'Отправить правку', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Отправить правку', exact: true }).click();
    const v2 = await wait(p => p.review && p.review.binding_revision === 2);
    assert.equal(v2.stories.length, 2); assert.deepEqual(v2.stories[0].ref, v1.stories[0].ref);
    const approve = page.getByRole('button', { name: 'Утвердить Story v2', exact: true });
    await expect(approve).toBeEnabled(); await approve.click();
    const completed = await wait(p => p.status === 'completed');
    assert.equal(completed.outcome.subject_artifact_id, v2.stories.find(s => s.current).ref.artifact_id);
    await stop(); await start(); await page.reload();
    await expect(page.locator('.story-body')).toBeVisible();
    assert.deepEqual((await projection()).stories, v2.stories);
    assert.equal(posts.length, 4, 'Start, clarify, revise, approve only'); assert.deepEqual(errors, []);
    await page.getByRole('button', { name: 'Данные запуска', exact: true }).click();
    await capture('details');
    console.log(JSON.stringify({ outcome: 'PASS', live: true, graph: completed.graph, model: completed.model, story_versions: 2, browser_posts: posts.length, restart_preserved: true, provider: evidence, screenshots: folder }, null, 2));
  } catch (error) {
    console.log(JSON.stringify({ outcome: 'FAIL', live: true, provider: evidence }, null, 2));
    throw error;
  } finally {
    if (browser) await browser.close(); await stop();
    rmSync(data, { recursive: true, force: true });
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
