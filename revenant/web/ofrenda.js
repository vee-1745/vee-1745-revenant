import { spiritSVG, ghostPortrait } from './spirits.js';
import { buildBanner, startPetals } from './decor.js';

// Everything in the data block comes from git (commit messages, folder names) and from a model,
// so none of it is ever parsed as HTML: it only goes in through textContent.
const data = JSON.parse(document.getElementById('data').textContent);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
const fmtDate = (iso) =>
  new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const joinList = (items) =>
  items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;

const CANDLE =
  '<svg viewBox="0 0 46 98" aria-hidden="true">' +
  '<g class="flame"><path d="M23 2 C11 19 14 33 23 42 C32 33 35 19 23 2Z" fill="#ff9a1f"/>' +
  '<path d="M23 17 C17 27 18 35 23 40 C28 35 29 27 23 17Z" fill="#fff1b0"/></g>' +
  '<rect x="12" y="42" width="22" height="52" rx="3" fill="#f3e9d2" stroke="#1a0f2e" stroke-width="3"/>' +
  '<path d="M23 42 v-6" stroke="#1a0f2e" stroke-width="3" stroke-linecap="round"/></svg>';

const frames = [];
const touched = new Set();
let toggleBtn = null;

function fact(cls, term, value) {
  const row = el('div', cls);
  row.append(el('dt', null, term), el('dd', null, value));
  return row;
}

function buildFrame(p) {
  const card = el('li', 'frame');
  card.dataset.lit = 'false';

  const candle = el('button', 'candle');
  candle.type = 'button';
  candle.setAttribute('aria-pressed', 'false');
  candle.setAttribute('aria-label', `Light a candle for ${p.name}`);
  candle.innerHTML = CANDLE;
  candle.addEventListener('click', () => {
    touched.add(card);
    setLit(card, card.dataset.lit !== 'true');
  });

  const portrait = el('div', 'portrait');
  portrait.innerHTML = ghostPortrait(p.seed, `A sleeping ghost for ${p.name}`);

  const facts = el('dl', 'facts');
  facts.append(fact('', 'Cause of death', p.cause));
  if (p.lastWords) facts.append(fact('last', 'Last words', `“${p.lastWords}”`));
  facts.append(fact('', 'Offering', p.offering));

  const langs = p.langs.length ? ` in ${joinList(p.langs)}` : '';
  card.append(
    candle,
    portrait,
    el('h2', null, p.name),
    el('p', 'dates', `${fmtDate(p.born)} to ${fmtDate(p.died)}`),
    el('p', 'epitaph', p.epitaph),
    facts,
    el('p', 'vitals', `${plural(p.commits, 'commit')}${langs}. Quiet for ${p.quiet}.`),
  );
  return card;
}

function setLit(card, on) {
  card.dataset.lit = String(on);
  const btn = card.querySelector('.candle');
  btn.setAttribute('aria-pressed', String(on));
  btn.setAttribute('aria-label', `${on ? 'Put out' : 'Light'} the candle for ${card.querySelector('h2').textContent}`);
  syncToggle();
}

function syncToggle() {
  if (!toggleBtn) return;
  toggleBtn.textContent = frames.every((f) => f.dataset.lit === 'true') ? 'Put out the candles' : 'Light every candle';
}

// The one orchestrated moment: candles catch one after another when the page opens.
function lightInSequence() {
  if (reduced) {
    frames.forEach((f) => setLit(f, true));
    return;
  }
  const gap = Math.min(170, 2600 / Math.max(frames.length, 1));
  frames.forEach((f, i) => setTimeout(() => { if (!touched.has(f)) setLit(f, true); }, 600 + i * gap));
}

function buildElders() {
  const sec = el('section', 'elders');
  sec.setAttribute('aria-label', 'The old languages');
  sec.append(el('h2', null, 'The old ones'));
  sec.append(el('p', 'lede', 'The four languages that haunt your terminal are remembered here too. Some of them are still working.'));
  const grid = el('div', 'elder-grid');
  for (const e of data.elders) {
    const fig = el('figure', 'elder');
    fig.style.setProperty('--spirit', e.hex);
    const art = el('div', 'art');
    art.innerHTML = spiritSVG(e.name, e.display, e.hex);
    fig.append(art, el('b', null, e.short), el('span', 'born', `born ${e.born}`), el('p', null, e.death));
    grid.append(fig);
  }
  sec.append(grid);
  return sec;
}

function buildFooter() {
  const foot = el('footer', 'foot');
  const s = data.stats || {};
  if (data.demo) {
    foot.append(el('p', null, 'These projects are fictional samples. Run ghost ofrenda on your own folders to build a real one: every epitaph is then written by a local open-weight model, and nothing leaves your machine.'));
  } else if (data.model) {
    foot.append(el('p', null, `Every remembrance was written by ${data.model}, an open-weight model, on the machine that holds these repositories. Nothing was uploaded.`));
    if (s.template) {
      foot.append(el('p', null, `${plural(s.template, 'remembrance')} came from a plain template, because the model's words failed a fact check.`));
    }
  } else {
    foot.append(el('p', null, 'These remembrances were written from a plain template. No model was used.'));
  }
  foot.append(el('p', null, `Candles lit on ${fmtDate(data.generated)}.`));
  return foot;
}

function boot() {
  buildBanner(document.getElementById('banner'));
  startPetals(document.getElementById('petals'));
  const root = document.getElementById('root');
  root.textContent = '';

  const top = el('header', 'top');
  const left = el('div');
  left.append(el('h1', null, 'Ofrenda'));
  left.append(el('p', 'lede', data.projects.length
    ? 'Projects that stopped here, remembered with a candle, an epitaph and an offering.'
    : 'Nothing to remember yet.'));
  top.append(left);
  root.append(top);

  if (!data.projects.length) {
    const empty = el('p', 'empty', 'No abandoned projects were found, so every candle is still waiting. Point the scanner at a folder with older repositories, or lower the age limit: ');
    empty.append(el('code', null, 'ghost ofrenda ~/projects --months 1'));
    root.append(empty);
  } else {
    toggleBtn = el('button', null, 'Light every candle');
    toggleBtn.id = 'toggle';
    toggleBtn.type = 'button';
    toggleBtn.addEventListener('click', () => {
      const lightAll = !frames.every((f) => f.dataset.lit === 'true');
      frames.forEach((f) => { touched.add(f); setLit(f, lightAll); });
    });
    top.append(toggleBtn);

    const list = el('ul', 'frames');
    for (const p of data.projects) {
      const card = buildFrame(p);
      frames.push(card);
      list.append(card);
    }
    root.append(list);
  }
  root.append(buildElders(), buildFooter());
  if (frames.length) lightInSequence();
}

boot();
