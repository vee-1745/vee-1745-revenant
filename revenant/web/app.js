import { spiritSVG } from './spirits.js';
import { buildBanner, buildAltar, startPetals } from './decor.js';

const $ = (sel) => document.querySelector(sel);
const log = $('#log'), chips = $('#chips'), form = $('#form'), q = $('#q'), send = $('#send');
const spiritEl = $('#spirit');

const state = { spirits: [], current: null, convos: {}, models: [], busy: false, abort: null };

// One question every spirit can answer, one about Python, and one that fits the spirit.
const EXTRA = {
  cobol: 'Why do banks still need you?',
  fortran: 'Why are you still used for weather models?',
  lisp: 'What did every language steal from you?',
  perl: 'Why can nobody read your code?',
};
const chipsFor = (name) => ['Who killed you?', 'What do you make of Python?', EXTRA[name]].filter(Boolean);

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

/* ---------------------------------------------------------------- status */

function setStatus(id, text, stateName) {
  const li = $(id);
  li.textContent = text;
  li.dataset.state = stateName;
}

function renderNet() {
  const on = navigator.onLine;
  setStatus('#st-net', on ? 'Network on, not needed' : 'Network off, still haunting', on ? 'ok' : 'warn');
}

function renderModel() {
  const sp = state.current;
  if (!sp || !state.models.length) return;
  const have = state.models.includes(sp.model);
  setStatus('#st-model', have ? `${sp.model} ready` : `${sp.model} is not installed`, have ? 'ok' : 'bad');
}

async function refreshStatus() {
  try {
    const s = await getJSON('/api/status');
    state.models = s.models || [];
    setStatus('#st-ollama', s.ollama ? 'Ollama running' : 'Ollama not reachable', s.ollama ? 'ok' : 'bad');
    renderModel();
  } catch {
    setStatus('#st-ollama', 'Séance Room server not reachable', 'bad');
  }
}

/* ---------------------------------------------------------------- rendering */

function renderRich(el, text) {
  el.textContent = '';
  // Odd-numbered pieces sit between ``` fences (an unclosed fence counts, so streaming code looks right).
  text.split(/```[\w-]*\n?/).forEach((piece, i) => {
    if (i % 2) {
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = piece.replace(/\n$/, '');
      pre.append(code);
      el.append(pre);
    } else if (piece.trim()) {
      const p = document.createElement('p');
      p.textContent = piece.trim();
      el.append(p);
    }
  });
}

function spiritNode(sp, text = '') {
  const wrap = document.createElement('article');
  wrap.className = 'msg spirit';
  const who = document.createElement('div');
  who.className = 'who';
  who.textContent = sp.short;
  const body = document.createElement('div');
  body.className = 'body';
  renderRich(body, text);
  wrap.append(who, body);
  log.append(wrap);
  return { wrap, body };
}

function userNode(text) {
  const el = document.createElement('div');
  el.className = 'msg user';
  el.textContent = text;
  log.append(el);
}

function noteNode(text) {
  const el = document.createElement('div');
  el.className = 'note';
  el.textContent = text;
  log.append(el);
}

const scrollDown = () => { log.scrollTop = log.scrollHeight; };

function renderConversation() {
  const sp = state.current;
  log.textContent = '';
  spiritNode(sp, sp.greeting);
  for (const m of convoOf(sp.name)) {
    if (m.role === 'user') userNode(m.content);
    else spiritNode(sp, m.content);
  }
  renderChips();
  scrollDown();
}

function renderChips() {
  chips.textContent = '';
  if (convoOf(state.current.name).length) return;
  for (const text of chipsFor(state.current.name)) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip';
    b.textContent = text;
    b.addEventListener('click', () => ask(text));
    chips.append(b);
  }
}

const convoOf = (name) => (state.convos[name] ||= []);

/* ---------------------------------------------------------------- the spirit */

let mouthTimer = 0;
function flapMouth() {
  spiritEl.style.setProperty('--open', (1.4 + Math.random() * 1.7).toFixed(2));
  clearTimeout(mouthTimer);
  mouthTimer = setTimeout(() => spiritEl.style.setProperty('--open', '.7'), 240);
}

function setTalking(on) {
  spiritEl.classList.toggle('is-talking', on);
  if (!on) clearTimeout(mouthTimer);
}

function enrage() {
  spiritEl.classList.remove('is-angry');
  void spiritEl.offsetWidth;
  spiritEl.classList.add('is-angry');
  setTimeout(() => spiritEl.classList.remove('is-angry'), 1800);
}

function select(name, { first = false } = {}) {
  const sp = state.spirits.find((s) => s.name === name);
  if (!sp || (state.busy && sp !== state.current)) return;
  state.current = sp;
  document.documentElement.style.setProperty('--spirit', sp.hex);
  spiritEl.innerHTML = spiritSVG(sp.name, sp.display, sp.hex);
  spiritEl.classList.remove('summon');
  void spiritEl.offsetWidth;
  if (!first) spiritEl.classList.add('summon');
  document.querySelectorAll('.tomb').forEach((t) => t.setAttribute('aria-pressed', String(t.dataset.name === name)));
  renderConversation();
  renderModel();
  try { localStorage.setItem('revenant.spirit', name); } catch { /* storage may be blocked; harmless */ }
}

function renderTombs() {
  const nav = $('#tombs');
  nav.textContent = '';
  for (const sp of state.spirits) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'tomb';
    b.dataset.name = sp.name;
    b.style.setProperty('--tomb', sp.hex);
    b.setAttribute('aria-pressed', 'false');
    b.setAttribute('aria-label', `${sp.display}, born ${sp.born}`);
    const glyph = Object.assign(document.createElement('span'), { className: 'glyph', textContent: sp.glyph });
    const nm = Object.assign(document.createElement('span'), { className: 'name', textContent: sp.short });
    const yr = Object.assign(document.createElement('span'), { className: 'year', textContent: String(sp.born) });
    b.append(glyph, nm, yr);
    b.addEventListener('click', () => select(sp.name));
    nav.append(b);
  }
}

addEventListener('pointermove', (e) => {
  const r = spiritEl.getBoundingClientRect();
  const dx = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / 420));
  const dy = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height * 0.4)) / 420));
  spiritEl.style.setProperty('--px', (dx * 5).toFixed(2));
  spiritEl.style.setProperty('--py', (dy * 4).toFixed(2));
});

/* ---------------------------------------------------------------- asking */

function errorCopy(err) {
  if (err.kind === 'down') {
    return 'Ollama is not answering. Start it with `sudo systemctl start ollama` (or `ollama serve`), then ask again.';
  }
  if (/not found|pull/i.test(err.message) && err.model) {
    return `${err.model} is not installed yet. Run \`ollama pull ${err.model}\`, then ask again.`;
  }
  if (err.kind === 'server') {
    return 'The Séance Room server stopped. Restart it with `python3 ghost.py seance`, then reload this page.';
  }
  return err.message;
}

function setBusy(on) {
  state.busy = on;
  send.textContent = on ? 'Stop' : 'Ask';
  send.classList.toggle('stop', on);
  document.querySelectorAll('.chip').forEach((c) => { c.disabled = on; });
}

async function ask(text) {
  text = text.trim();
  if (!text || state.busy) return;
  const sp = state.current;
  const convo = convoOf(sp.name);
  convo.push({ role: 'user', content: text });
  q.value = '';
  chips.textContent = '';
  userNode(text);
  const { wrap, body } = spiritNode(sp);
  wrap.classList.add('streaming');
  scrollDown();

  const ctrl = new AbortController();
  state.abort = ctrl;
  setBusy(true);
  setTalking(true);
  let reply = '';
  let failure = null;
  let meta = null;

  const onFrame = (frame) => {
    const line = frame.split('\n').find((l) => l.startsWith('data: '));
    if (!line) return;
    const msg = JSON.parse(line.slice(6));
    if (msg.error) { failure = Object.assign(new Error(msg.error), { kind: msg.kind, model: msg.model }); return; }
    if (msg.done) { meta = msg; return; }
    if (msg.t) {
      reply += msg.t;
      renderRich(body, reply);
      flapMouth();
      scrollDown();
    }
  };

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spirit: sp.name, messages: convo.map(({ role, content }) => ({ role, content })) }),
      signal: ctrl.signal,
    });
    if (!res.ok || !res.body) {
      const detail = await res.json().catch(() => ({}));
      throw Object.assign(new Error(detail.error || `HTTP ${res.status}`), { kind: 'server' });
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        onFrame(buf.slice(0, i));
        buf = buf.slice(i + 2);
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') failure = e.kind ? e : Object.assign(e, { kind: 'server' });
  } finally {
    wrap.classList.remove('streaming');
    setTalking(false);
    setBusy(false);
    state.abort = null;
  }

  if (reply.trim()) {
    convo.push({ role: 'assistant', content: reply });
    if (meta) {
      const m = document.createElement('div');
      m.className = 'meta';
      const speed = meta.tps ? `, ${Math.round(meta.tps)} tokens a second` : '';
      m.textContent = `${(meta.ms / 1000).toFixed(1)}s on ${meta.model}${speed}, on this machine`;
      wrap.append(m);
    }
  } else {
    wrap.remove();
    if (!failure) convo.pop(); // stopped before anything arrived: forget the question too
  }
  if (failure) {
    noteNode(errorCopy(failure));
    enrage();
    refreshStatus();
    if (!reply.trim()) convo.pop();
  }
  renderChips();
  scrollDown();
  q.focus();
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  if (state.busy) state.abort?.abort();
  else ask(q.value);
});
q.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    form.requestSubmit();
  }
});

/* ---------------------------------------------------------------- boot */

async function boot() {
  buildBanner($('#banner'));
  buildAltar($('#altar'));
  startPetals($('#petals'));
  renderNet();
  addEventListener('online', renderNet);
  addEventListener('offline', renderNet);
  try {
    state.spirits = await getJSON('/api/spirits');
  } catch {
    noteNode('Could not load the spirits. Restart the Séance Room with `python3 ghost.py seance`.');
    return;
  }
  renderTombs();
  let saved = null;
  try { saved = localStorage.getItem('revenant.spirit'); } catch { /* ignore */ }
  select(state.spirits.some((s) => s.name === saved) ? saved : state.spirits[0].name, { first: true });
  refreshStatus();
  setInterval(refreshStatus, 15000);
}

boot();
