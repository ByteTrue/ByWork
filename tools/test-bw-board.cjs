#!/usr/bin/env node
// Node checks use the shipped HTML and real CLI. Pass a Chrome binary for offline DOM checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const {spawn, spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bw-board-test-'));
const tick = String.fromCharCode(96);
const ids = {
  rich: 'implemented/security/2026-11-20-rich.md',
  live: 'proposed/feature/2026-11-20-blocked.md',
  adopted: 'implemented/feature/2026-11-20-shared.md',
  rejected: 'rejected/feature/2026-11-20-shared.md',
  linker: 'implemented/architecture/2026-11-20-links.md',
};
function note(title, status = 'implemented') {
  return '# ' + title + '\n\nStatus: ' + status + '\n\n## 问题\n\nFirst problem\nSecond problem\n\n## ' +
    (status.startsWith('implemented') ? '决策' : '提案') + '（当前范围）\n\nFirst decision\nSecond decision\n\n## 备选方案\n\n- Alternative: ALT_ONLY_MARKER\n\n## ' +
    (status.startsWith('implemented') ? '收益和代价' : '风险与代价') + '\n\nCOST_ONLY_MARKER\n';
}
const files = {
  [ids.rich]: note('Security record').replace('First decision\nSecond decision', '~~~js\nCODE_ONLY_MARKER\n~~~\n\n' + tick.repeat(4) + '\n' + tick.repeat(3) + '\n## Literal heading\n' + tick.repeat(4)) + '\n## 验证结论\n\nEVIDENCE_ONLY_MARKER\n\n## 补充说明\n\nEXTRA_ONLY_MARKER\n',
  [ids.adopted]: note('Adopted sibling'),
  [ids.rejected]: note('Rejected sibling', 'rejected — REJECT_ONLY_MARKER'),
  [ids.live]: '---\nkind: work\nstatus: blocked\ncurrent_unit: Current unit\nnext_action: NEXT_ONLY_MARKER\nmust_hold: HOLD_ONLY_MARKER\nproof_gap: GAP_ONLY_MARKER\n---\n' + note('Blocked proposal', 'proposed') + '\n## 验收标准\n\n| 行为路径 | 计划证明 | 实际证据 | 范围覆盖 | 缺口 | 结果 |\n|---|---|---|---|---|---|\n| path | probe | pending | scope | gap | 无法判定 |\n',
  [ids.linker]: note('Links') + '\n## 参考\n\n[Exact sibling](../../rejected/feature/%32%30%32%36-11-20-shared.md#decision "reason")\n[Reference sibling][peer]\n[External](https://example.invalid/source)\n[Mail](mailto:person@example.invalid)\n[Unsafe](javascript:alert(1))\n<img src=x onerror="globalThis.BODY_XSS=1">\n\n[peer]: <../../implemented/feature/2026-11-20-shared.md> "peer title"\n',
  'implemented/feature/2026-11-20-language.md': note('English note'),
  'implemented/feature/2026-11-20-language.zh.md': note('Chinese note'),
  'archived/process/old-eval/2026-11-20-attachment.md': note('Not a lifecycle note'),
  'implemented/feature/readme.md': 'Not a dated note',
};
function makeHandle(files, prefix = '') {
  return {
    kind: 'directory', name: prefix.split('/').filter(Boolean).at(-1) || 'bywork',
    async getDirectoryHandle(name) {
      const next = prefix + name + '/';
      if (!Object.keys(files).some(key => key.startsWith(next))) throw new DOMException('Missing directory', 'NotFoundError');
      return makeHandle(files, next);
    },
    async *values() {
      const children = new Set(Object.keys(files).filter(key => key.startsWith(prefix)).map(key => key.slice(prefix.length).split('/')[0]));
      for (const name of children) {
        const key = prefix + name;
        if (Object.keys(files).some(p => p.startsWith(key + '/'))) yield makeHandle(files, key + '/');
        else yield {kind: 'file', name, async getFile() {
          if (files[key] === null) throw new DOMException('Synthetic unreadable note', 'NotAllowedError');
          return {async text() { return files[key]; }};
        }};
      }
    },
  };
}
function cli(...args) {
  const proc = spawnSync('python3', [path.join(root, 'skills/bw/scripts/bw.py'), ...args, '--project', tmp], {encoding: 'utf8'});
  assert.equal(proc.status, 0, proc.stdout + proc.stderr);
}
function loadScript(html) {
  const context = vm.createContext({window: {}, document: {addEventListener() {}}, console});
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  vm.runInContext(scripts, context);
  return context;
}
const plain = value => JSON.parse(JSON.stringify(value));
async function checkParsing() {
  for (const [name, raw] of Object.entries(files)) {
    const file = path.join(tmp, 'bywork', name);
    fs.mkdirSync(path.dirname(file), {recursive: true});
    fs.writeFileSync(file, raw);
  }
  cli('board', '--bundle', 'bundle.html', '--title', '<img src=x onerror="globalThis.TITLE_XSS=7">');
  cli('board', '--init', 'live.html');
  const bundled = loadScript(fs.readFileSync(path.join(tmp, 'bundle.html'), 'utf8')).window.__INLINE_DATA__;
  const local = loadScript(fs.readFileSync(path.join(root, 'skills/bw/assets/board.html'), 'utf8'));
  const scanned = await local.scanDirectory(makeHandle(files));
  const sort = notes => plain(notes).sort((a, b) => a.id.localeCompare(b.id));
  assert.deepEqual(sort(scanned), sort(bundled), 'local and bundle data must agree');
  assert.equal(scanned.length, 7, 'keep both language files; exclude nested attachments');
  const rich = scanned.find(n => n.id === ids.rich);
  assert.equal(rich.problem, 'First problem\nSecond problem');
  assert.ok(rich.decision.includes('CODE_ONLY_MARKER') && rich.decision.includes('## Literal heading'));
  assert.ok(rich.extraSections.some(s => s.body === 'EVIDENCE_ONLY_MARKER'));
  assert.deepEqual(plain(scanned.find(n => n.id === ids.linker).outLinks).sort(), [ids.adopted, ids.rejected].sort());
  const live = scanned.find(n => n.id === ids.live);
  assert.equal(live.checkpoint.proof_gap, 'GAP_ONLY_MARKER');
  assert.equal(local.noteStatus(live), '已阻塞');
  for (const marker of ['alt_only_marker', 'cost_only_marker', 'evidence_only_marker', 'extra_only_marker', 'code_only_marker']) {
    assert.ok(local.searchableText(rich).includes(marker), marker);
  }
  assert.ok(local.searchableText(scanned.find(n => n.id === ids.rejected)).includes('reject_only_marker'));
  const markup = local.parseMarkdown(files[ids.linker], local.referenceDefinitions(files[ids.linker]));
  assert.match(markup, /href="https:\/\/example.invalid\/source"/);
  assert.match(markup, /rel="noopener noreferrer"/);
  assert.match(markup, /href="mailto:/);
  assert.ok(!markup.includes('<img') && !markup.includes('href="javascript:'));
  await assert.rejects(local.scanDirectory(makeHandle({[ids.rich]: null})), /Synthetic unreadable note/);
  await assert.rejects(local.scanDirectory({name: 'project', async getDirectoryHandle() { throw new DOMException('Denied', 'NotAllowedError'); }}), /Denied/);
  console.log('board: shared CLI/browser parser, scan boundaries, content, links and read errors passed');
}
async function checkBrowser(binary) {
  const chrome = spawn(binary, ['--headless=new', '--user-data-dir=' + path.join(tmp, 'chrome-profile'), '--remote-debugging-port=0', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync', 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
  let ws;
  const finished = new Promise(resolve => chrome.once('exit', resolve));
  try {
    const endpoint = await new Promise((resolve, reject) => {
      let output = '';
      const timer = setTimeout(() => reject(Error('Chrome DevTools startup timed out')), 10000);
      chrome.once('error', reject);
      chrome.once('exit', code => { clearTimeout(timer); reject(Error('Chrome exited ' + code)); });
      chrome.stderr.on('data', chunk => {
        output += chunk;
        const match = /DevTools listening on (ws:\/\/[^\s]+)/.exec(output);
        if (match) { clearTimeout(timer); resolve(match[1]); }
      });
    });
    ws = new WebSocket(endpoint);
    await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, {once: true}); ws.addEventListener('error', reject, {once: true}); });
    let next = 0;
    const pending = new Map(), exceptions = [];
    ws.addEventListener('message', event => {
      const data = JSON.parse(event.data);
      if (data.method === 'Runtime.exceptionThrown') exceptions.push(data.params.exceptionDetails);
      if (!data.id) return;
      const request = pending.get(data.id);
      pending.delete(data.id);
      clearTimeout(request.timer);
      if (data.error) request.reject(Error(JSON.stringify(data.error))); else request.resolve(data.result);
    });
    const call = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
      const id = ++next;
      const timer = setTimeout(() => reject(Error('CDP timed out: ' + method)), 10000);
      pending.set(id, {resolve, reject, timer});
      ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
    });
    const {targetId} = await call('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await call('Target.attachToTarget', {targetId, flatten: true});
    const c = (method, params) => call(method, params, sessionId);
    await c('Runtime.enable'); await c('Page.enable'); await c('Network.enable');
    await c('Network.emulateNetworkConditions', {offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0});
    const evaluate = async expression => {
      const result = await c('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    async function visit(file) {
      await c('Page.navigate', {url: pathToFileURL(path.join(tmp, file)).href});
      await evaluate('new Promise((resolve, reject) => { const deadline = Date.now() + 8000; function ready() { if (document.readyState === "complete" && typeof Core !== "undefined") resolve(); else if (Date.now() > deadline) reject(Error("page load timed out")); else setTimeout(ready, 20); } ready(); })');
      await evaluate('globalThis.ids = ' + JSON.stringify(ids));
    }
    await visit('bundle.html');
    const initial = await evaluate('(' + function() {
      openConsole(ids.rich);
      const rich = {problem: document.getElementById('dr-body-problem').textContent, decision: document.getElementById('dr-body-decision').textContent, extra: document.getElementById('dr-extra-sections').textContent};
      const classes = [...document.getElementById('select-class').options].map(o => o.value);
      const baseline = [...document.querySelectorAll('#matrix-chambers [data-node-id], #pillars-vault [data-node-id]')].map(el => el.dataset.nodeId);
      openConsole(ids.live);
      const blocked = {status: document.getElementById('dr-status-badge').textContent, checkpoint: document.getElementById('dr-checkpoint').textContent};
      openConsole(ids.linker);
      document.querySelector('#dr-extra-sections [data-deep-link]').click();
      const target = Core.drawerId;
      Core.altQuery = ''; renderAlternatives();
      const alternatives = [...document.querySelectorAll('.pitfall-dossier')].filter(el => !el.dataset.nodeId.startsWith('implemented/')).map(el => el.querySelector('.triumphant-verdict').textContent);
      const searches = ['ALT_ONLY_MARKER', 'COST_ONLY_MARKER', 'REJECT_ONLY_MARKER', 'EVIDENCE_ONLY_MARKER'].map(query => {
        const input = document.getElementById('global-query'); input.value = query; input.dispatchEvent(new Event('input', {bubbles: true}));
        return {query, count: document.querySelectorAll('#matrix-rows-stream [data-node-id]').length, popover: document.querySelectorAll('#search-popover .popover-item').length};
      });
      return {nodes: Core.nodes.length, rich, classes, baseline, blocked, target, alternatives, searches, titleXss: globalThis.TITLE_XSS || null, bodyXss: globalThis.BODY_XSS || null, titleImages: document.querySelectorAll('#brand-project-title img').length};
    }.toString() + ')()');
    assert.equal(initial.nodes, 7);
    assert.match(initial.rich.problem, /Second problem/);
    assert.match(initial.rich.decision, /CODE_ONLY_MARKER/);
    assert.match(initial.rich.extra, /EVIDENCE_ONLY_MARKER/);
    assert.ok(initial.classes.includes('security'));
    assert.ok(initial.baseline.includes(ids.rich) && initial.baseline.every(id => id.startsWith('implemented/')));
    assert.equal(initial.blocked.status, '已阻塞');
    assert.match(initial.blocked.checkpoint, /GAP_ONLY_MARKER/); assert.match(initial.blocked.checkpoint, /NEXT_ONLY_MARKER/);
    assert.equal(initial.target, ids.rejected);
    assert.ok(initial.alternatives.length > 0 && initial.alternatives.every(text => !text.includes('采纳决策')));
    assert.ok(initial.searches.every(result => result.count > 0 && result.popover > 0), JSON.stringify(initial.searches));
    assert.equal(initial.titleXss, null); assert.equal(initial.bodyXss, null); assert.equal(initial.titleImages, 0);
    await visit('live.html');
    await evaluate('globalThis.fixtureNotes = ' + JSON.stringify(files) + '; globalThis.makeHandle = ' + makeHandle.toString() + '; Core.dirHandle = makeHandle(fixtureNotes); triggerLiveSync()');
    await evaluate('openConsole(ids.rich); fixtureNotes[ids.rich] = fixtureNotes[ids.rich].replace("First problem", "UPDATED_AFTER_SYNC"); triggerLiveSync(true)');
    assert.match(await evaluate('document.getElementById("dr-body-problem").textContent'), /UPDATED_AFTER_SYNC/);
    await evaluate('fixtureNotes[ids.rich] = null; triggerLiveSync(true)');
    const failed = await evaluate('({count: Core.nodes.length, status: document.getElementById("beacon-status").textContent, text: document.getElementById("dr-body-problem").textContent})');
    assert.equal(failed.count, 7); assert.match(failed.status, /同步失败/); assert.match(failed.text, /UPDATED_AFTER_SYNC/);
    await evaluate('delete fixtureNotes[ids.rich]; triggerLiveSync(true)');
    assert.deepEqual(await evaluate('({id: Core.drawerId, open: document.getElementById("drawer-console").classList.contains("open"), count: Core.nodes.length})'), {id: null, open: false, count: 6});
    assert.deepEqual(exceptions, [], JSON.stringify(exceptions));
    console.log('board: offline ' + (await call('Browser.getVersion')).product + ' rendering, navigation, search, sync and failure retention passed');
    await call('Browser.close');
  } finally {
    ws?.close();
    chrome.kill('SIGTERM');
    await finished;
  }
}
(async () => {
  await checkParsing();
  if (process.argv[2]) await checkBrowser(process.argv[2]);
  fs.rmSync(tmp, {recursive: true, force: true});
})().catch(error => { console.error(error); console.error('Fixtures retained at ' + tmp); process.exitCode = 1; });
