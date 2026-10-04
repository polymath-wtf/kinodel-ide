// Lifecycle fault injection in separate Node processes: no backend, browser or files.
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { EventEmitter } = require('node:events');
const { resolve } = require('node:path');

if (process.argv[2]) {
  const scenario = process.argv[2];
  const fs = require('node:fs');
  fs.mkdtempSync = () => 'unused-regression-root';
  fs.rmSync = () => console.log('DATA_REMOVED');
  fs.mkdirSync = () => {
    console.log('CAPTURE_DIRECTORY');
    if (scenario === 'overwrite') throw new Error('EEXIST: screenshot directory already exists');
  };
  require('node:net').createServer = () => {
    const socket = new EventEmitter();
    socket.listen = () => setImmediate(() => socket.emit(scenario === 'occupied' ? 'error' : 'listening', new Error('EADDRINUSE')));
    socket.close = callback => callback();
    return socket;
  };
  require('node:child_process').spawn = (python, _args, options) => {
    const root = resolve(__dirname, '..', '..');
    assert.equal(python, resolve(root, '.venv313/Scripts/python.exe'), 'owned backend uses repository Python');
    assert.equal(options.cwd, root, 'owned backend starts at repository root');
    console.log('SPAWN');
    if (scenario === 'spawn-throw') throw new Error('spawn failed');
    const child = new EventEmitter();
    child.stderr = new EventEmitter();
    child.exitCode = scenario === 'already-exited' ? 1 : null;
    child.signalCode = null;
    child.pid = scenario === 'spawn-error' ? undefined : 12345;
    child.stdin = child.stdout = { destroy() {} };
    child.stderr.destroy = () => {};
    child.unref = () => {};
    child.kill = signal => {
      console.log(`OWNED_KILL:${signal || 'SIGTERM'}`);
      if (scenario === 'already-exited') return false;
      if (scenario === 'kill-error') { child.emit('error', new Error('kill EPERM')); return false; }
      if (scenario === 'stuck-child') return true;
      if (scenario === 'force-kill' && signal !== 'SIGKILL') return true;
      child.signalCode = signal || 'SIGTERM';
      child.emit('exit');
      child.emit('close');
      return true;
    };
    setImmediate(() => {
      if (scenario === 'spawn-error') {
        child.emit('error', new Error('spawn ENOENT'));
        child.emit('close');
      } else if (scenario === 'collision') {
        child.stderr.emit('data', Buffer.from('bind failed: address already in use'));
        child.exitCode = 1;
        child.emit('exit', 1);
        child.emit('close', 1);
      } else child.stderr.emit('data', Buffer.from('INFO: Uvicorn running on http://127.0.0.1:8766 (Press CTRL+C to quit)'));
    });
    return child;
  };
  global.fetch = async () => ({ ok: true }); // A foreign server could respond even during a bind collision.
  const chromium = { launch: async () => {
    console.log('BROWSER_LAUNCH');
    if (scenario === 'browser-error') throw new Error('browser launch failed');
    return {
      close: async () => {
        console.log('BROWSER_CLOSED');
        if (scenario === 'close-error') throw new Error('browser close failed');
        if (scenario === 'close-hang') {
          setInterval(() => {}, 1000); // Like a wedged Playwright connection, this keeps Node alive.
          await new Promise(() => {});
        }
      },
      newPage: async ({ viewport }) => {
        let selected = viewport.width < 768 ? 'Chat' : 'Pipeline', focused = 'Pipeline', authenticated = true;
        const locator = name => ({
          first() { return this; },
          click: async () => {},
          focus: async () => { focused = name; },
          getByText: child => locator(child),
          getByRole: (_role, options) => locator(options.name),
          waitFor: async () => { if (scenario === 'check-error') throw new Error('shell assertion failed'); },
          innerText: async () => name === ':focus' ? focused : selected,
          getAttribute: async attribute => attribute === 'aria-label' ? focused : attribute === 'aria-current' ? 'page' : attribute === 'data-view' ? selected.toLowerCase() : String(selected === 'Chat'),
          evaluate: async () => name === '.workspace:not([hidden])' ? { width: 100, height: 100 } : true,
        });
        return {
          on() {}, goto: async () => {}, waitForLoadState: async () => {}, close: async () => {},
          getByText: locator, getByRole: (_role, options) => locator(options.name), locator,
          evaluate: async () => [],
          keyboard: { press: async key => {
            if (key === 'Tab') focused = 'Chat';
            else if (key !== 'Escape') selected = focused;
          } },
          request: { get: async url => ({ status: () => {
            if (url.endsWith('/api/session')) { authenticated = true; return 200; }
            if (url.endsWith('/api/executions')) return authenticated ? 200 : 401;
            return url.endsWith('/api/missing') ? 404 : 200;
          } }) },
          screenshot: async () => console.log('SCREENSHOT'),
        };
      },
    };
  } };
  const Module = require('node:module');
  const load = Module._load;
  Module._load = function (name, ...args) { return name === 'mock-playwright' ? { chromium } : load.call(this, name, ...args); };
  require('./shell-check.cjs');
} else {
  for (const scenario of ['already-exited', 'occupied', 'collision', 'spawn-error', 'spawn-throw', 'browser-error', 'check-error', 'close-error', 'close-hang', 'stuck-child', 'kill-error', 'force-kill', 'success', 'capture', 'overwrite']) {
    const result = spawnSync(process.execPath, [__filename, scenario], {
      encoding: 'utf8', timeout: 9000,
      env: { ...process.env, PLAYWRIGHT_MODULE: 'mock-playwright', SHELL_CHECK_PORT: '8766',
        CAPTURE_SCREENSHOTS: ['capture', 'overwrite'].includes(scenario) ? '1' : '', SCREENSHOT_DIR: 'unused-evidence', SHELL_CHECK_BASELINE_ONLY: '1' },
    });
    assert.ifError(result.error); // Timeout is a failure, not a passing diagnostic.
    const success = ['success', 'capture', 'force-kill'].includes(scenario);
    assert.equal(result.status, success ? 0 : 1, `${scenario}: ${result.stdout}\n${result.stderr}`);
    if (!success) assert.ok(result.stderr.trim(), `${scenario}: missing failure diagnostic`);
    if (!['occupied', 'overwrite', 'stuck-child', 'kill-error'].includes(scenario)) assert.match(result.stdout, /DATA_REMOVED/, scenario);
    if (['stuck-child', 'kill-error'].includes(scenario)) {
      assert.doesNotMatch(result.stdout, /DATA_REMOVED/);
      assert.match(result.stderr, /Backend cleanup failed; data preserved/);
    }
    if (scenario === 'already-exited') assert.match(result.stderr, /Backend exited: 1/);
    if (scenario === 'occupied') assert.match(result.stderr, /Port 8766 unavailable/);
    if (scenario === 'collision') assert.match(result.stderr, /bind failed: address already in use/);
    if (scenario === 'close-hang') assert.match(result.stderr, /Browser cleanup timed out/);
    if (['occupied', 'overwrite', 'already-exited', 'spawn-error', 'collision'].includes(scenario)) assert.doesNotMatch(result.stdout, /OWNED_KILL|BROWSER_LAUNCH/, scenario);
    if (['browser-error', 'check-error', 'close-error', 'close-hang', 'stuck-child', 'success', 'capture', 'force-kill'].includes(scenario)) assert.match(result.stdout, /OWNED_KILL/, scenario);
    if (scenario === 'force-kill') assert.match(result.stdout, /OWNED_KILL:SIGKILL/);
    if (scenario === 'capture') assert.match(result.stdout, /SCREENSHOT/);
    else assert.doesNotMatch(result.stdout, /SCREENSHOT/);
    if (!['capture', 'overwrite'].includes(scenario)) assert.doesNotMatch(result.stdout, /CAPTURE_DIRECTORY/);
    console.log(`PASS: ${scenario}, exit=${result.status}, no hang`);
  }
}
