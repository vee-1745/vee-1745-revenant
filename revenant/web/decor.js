// Scenery: papel picado banner, the ofrenda altar (marigolds and candles), drifting petals.

const FLAG_COLORS = ['#e0307a', '#ff9a1f', '#19b5a5', '#8a4fff', '#f6d33b'];

const circle = (cx, cy, r) => `M${cx - r} ${cy} a${r} ${r} 0 1 0 ${2 * r} 0 a${r} ${r} 0 1 0 ${-2 * r} 0 Z`;
const diamond = (cx, cy, r) => `M${cx} ${cy - r} L${cx + r} ${cy} L${cx} ${cy + r} L${cx - r} ${cy} Z`;

// Cut-out patterns; with fill-rule evenodd the holes show the night sky through the paper.
const CUTS = [
  () => circle(40, 26, 11) + diamond(17, 42, 6) + diamond(63, 42, 6) + circle(40, 48, 4),
  () => diamond(40, 16, 7) + diamond(40, 34, 7) + diamond(40, 52, 7) + circle(16, 30, 4) + circle(64, 30, 4),
  () => circle(40, 30, 6) + circle(22, 30, 4) + circle(58, 30, 4) + circle(40, 12, 4) + circle(40, 48, 4),
];
const FLAG_EDGE = 'M0 0 H80 V62 L70 72 L60 62 L50 72 L40 62 L30 72 L20 62 L10 72 L0 62 Z';

export function buildBanner(el) {
  for (let i = 0; i < 26; i++) {
    const flag = document.createElement('div');
    flag.className = 'flag';
    flag.style.setProperty('--i', i);
    flag.innerHTML =
      `<svg viewBox="0 0 80 72" width="80" height="72" aria-hidden="true">` +
      `<path fill="${FLAG_COLORS[i % FLAG_COLORS.length]}" fill-rule="evenodd" d="${FLAG_EDGE} ${CUTS[i % CUTS.length]()}"/></svg>`;
    el.append(flag);
  }
}

// A marigold: ring of overlapping petals around a dark centre.
function marigold(cx, cy, r) {
  let petals = '';
  for (let i = 0; i < 14; i++) {
    petals += `<ellipse cx="0" cy="${-r * 0.52}" rx="${r * 0.3}" ry="${r * 0.5}" transform="rotate(${i * (360 / 14)})" fill="${i % 2 ? '#ffb83d' : '#ff9a1f'}"/>`;
  }
  return `<g transform="translate(${cx} ${cy})">${petals}<circle r="${r * 0.3}" fill="#d96a00"/></g>`;
}

function candle(x, y, s, i) {
  return (
    `<g transform="translate(${x} ${y}) scale(${s})">` +
    `<circle class="glow" style="--d:${i}" cx="0" cy="-50" r="38" fill="url(#glow)"/>` +
    `<rect x="-7" y="-36" width="14" height="36" rx="2" fill="#f3e9d2" stroke="#1a0f2e" stroke-width="2.5"/>` +
    `<path d="M-7 -30 Q-3 -22 -7 -16" fill="none" stroke="#d8c9a6" stroke-width="2"/>` +
    `<path d="M0 -36 L0 -41" stroke="#1a0f2e" stroke-width="2" stroke-linecap="round"/>` +
    `<path class="flame" style="--d:${i}" d="M0 -40 C-8 -49 -5 -60 0 -72 C5 -60 8 -49 0 -40 Z" fill="url(#flame)"/>` +
    `</g>`
  );
}

export function buildAltar(el) {
  const tiers = [
    { x: 10, y: 132, w: 580, h: 58, fill: '#3b1a5e' },
    { x: 70, y: 94, w: 460, h: 40, fill: '#4a2074' },
    { x: 150, y: 62, w: 300, h: 34, fill: '#5a2a8a' },
  ];
  const rows = [
    { y: 161, from: 38, to: 562, step: 52, r: 15 },
    { y: 114, from: 98, to: 502, step: 46, r: 12 },
    { y: 79, from: 172, to: 428, step: 42, r: 10 },
  ];
  let flowers = '';
  rows.forEach((row) => {
    for (let x = row.from; x <= row.to; x += row.step) flowers += marigold(x, row.y, row.r);
  });
  const candles = [[36, 132, 1], [564, 132, 1], [92, 94, 0.9], [508, 94, 0.9], [176, 62, 0.8], [424, 62, 0.8]]
    .map(([x, y, s], i) => candle(x, y, s, i)).join('');
  el.innerHTML =
    `<svg viewBox="0 0 600 190" preserveAspectRatio="xMidYMax meet" aria-hidden="true">` +
    `<defs>` +
    `<radialGradient id="flame" cx="50%" cy="75%" r="60%"><stop offset="0" stop-color="#fff6c8"/><stop offset=".55" stop-color="#ffc24a"/><stop offset="1" stop-color="#ff7a1a"/></radialGradient>` +
    `<radialGradient id="glow"><stop offset="0" style="stop-color:var(--spirit);stop-opacity:.55"/><stop offset="1" style="stop-color:var(--spirit);stop-opacity:0"/></radialGradient>` +
    `</defs>` +
    tiers.map((t) => `<rect x="${t.x}" y="${t.y}" width="${t.w}" height="${t.h}" rx="5" fill="${t.fill}" stroke="#ff9a1f" stroke-width="2"/>`).join('') +
    flowers + candles + `</svg>`;
}

// Marigold petals rising slowly, like something being carried upward. Skipped when motion is reduced.
export function startPetals(canvas) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const ctx = canvas.getContext('2d');
  const COLORS = ['#ff9a1f', '#ffb83d', '#f6d33b'];
  let w = 0, h = 0, raf = 0;
  const petals = Array.from({ length: 34 }, () => ({
    x: Math.random(), y: Math.random(), s: 0.6 + Math.random() * 0.9, vy: 0.00006 + Math.random() * 0.00018,
    sway: Math.random() * Math.PI * 2, rot: Math.random() * Math.PI * 2, spin: (Math.random() - 0.5) * 0.02,
    c: COLORS[(Math.random() * COLORS.length) | 0], a: 0.35 + Math.random() * 0.5,
  }));

  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    for (const p of petals) {
      p.y -= p.vy * 16; p.sway += 0.012; p.rot += p.spin;
      if (p.y < -0.05) { p.y = 1.05; p.x = Math.random(); }
      ctx.save();
      ctx.translate((p.x + Math.sin(p.sway) * 0.015) * w, p.y * h);
      ctx.rotate(p.rot);
      ctx.globalAlpha = p.a;
      ctx.fillStyle = p.c;
      ctx.beginPath();
      ctx.ellipse(0, 0, 4.5 * p.s, 8.5 * p.s, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
    raf = requestAnimationFrame(frame);
  }

  addEventListener('resize', resize);
  document.addEventListener('visibilitychange', () => {
    cancelAnimationFrame(raf);
    if (!document.hidden) raf = requestAnimationFrame(frame);
  });
  resize();
  raf = requestAnimationFrame(frame);
}
