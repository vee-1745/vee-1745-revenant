// Four original cartoon ghosts, drawn as inline SVG so they can be animated with CSS.
// Shared body and face; each language adds its own props (visor, glasses, hat, sigil hair).

const INK = '#1a0f2e';
const BODY =
  'M40 140 C40 60 80 20 120 20 C160 20 200 60 200 140 L200 250 C200 262 190 266 182 258 ' +
  'L168 244 C160 236 150 236 142 244 L130 256 C124 262 116 262 110 256 L98 244 ' +
  'C90 236 80 236 72 244 L58 258 C50 266 40 262 40 250 Z';
const TINT = { cobol: '#ffe9a8', fortran: '#c4f4fb', lisp: '#efd2ff', perl: '#c8f8d5' };
const MONO = "'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace";

let uid = 0;

// A punch card: 3 rows of rectangular holes in a deterministic pattern.
function punchHoles() {
  let out = '';
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 9; c++) {
      if ((r * 5 + c * 3 + r * c) % 4 < 2) {
        out += `<rect x="${9 + c * 7.6}" y="${9 + r * 12}" width="4" height="7" fill="${INK}"/>`;
      }
    }
  }
  return out;
}

const ART = {
  // COBOL: an accountant's green eyeshade and a ledger-yellow bowtie.
  cobol: () => ({
    back: '',
    head:
      `<path d="M56 78 Q120 30 184 78 L178 90 Q120 50 62 90 Z" fill="#2f9e5f" stroke="${INK}" stroke-width="3.5" stroke-linejoin="round"/>` +
      `<path d="M70 80 Q120 46 170 80" fill="none" stroke="#7be0a4" stroke-width="3" stroke-linecap="round" opacity=".7"/>`,
    front:
      `<g stroke="${INK}" stroke-width="3.5" stroke-linejoin="round" fill="#ffc233">` +
      `<path d="M120 208 L92 190 Q87 208 92 226 Z"/><path d="M120 208 L148 190 Q153 208 148 226 Z"/>` +
      `<rect x="112" y="199" width="16" height="18" rx="4"/></g>`,
  }),

  // FORTRAN: round physicist glasses and a punch card clutched in front.
  fortran: () => ({
    back: '',
    head: '',
    front:
      `<g fill="rgba(190,240,250,.28)" stroke="${INK}" stroke-width="4" stroke-linecap="round">` +
      `<circle cx="92" cy="112" r="22"/><circle cx="148" cy="112" r="22"/>` +
      `<path d="M114 108 Q120 102 126 108" fill="none"/><path d="M70 106 L50 100" fill="none"/><path d="M170 106 L190 100" fill="none"/></g>` +
      `<g transform="translate(118 184) rotate(-9)"><path d="M10 0 H86 V50 H0 V10 Z" fill="#f1e4c4" stroke="${INK}" stroke-width="3.5" stroke-linejoin="round"/>` +
      `${punchHoles()}</g>`,
  }),

  // LISP: a wizard hat with a lambda, and parentheses orbiting it.
  lisp: (n, hex) => ({
    back:
      `<g font-family="${MONO}" font-weight="500" font-size="104" fill="${hex}" opacity=".9">` +
      `<text class="paren l" x="-34" y="206">(</text><text class="paren r" x="196" y="206">)</text></g>`,
    head:
      `<ellipse cx="120" cy="42" rx="66" ry="13" fill="#5b2db8" stroke="${INK}" stroke-width="3.5"/>` +
      `<path d="M76 42 Q104 -8 130 -66 Q140 -10 164 42 Z" fill="#7b3fe4" stroke="${INK}" stroke-width="3.5" stroke-linejoin="round"/>` +
      `<path d="M130 -66 Q150 -76 158 -60" fill="none" stroke="${INK}" stroke-width="3.5" stroke-linecap="round"/>` +
      `<text x="121" y="24" text-anchor="middle" font-family="${MONO}" font-weight="500" font-size="30" fill="#ffd36a">λ</text>` +
      `<circle cx="100" cy="2" r="3" fill="#ffd36a"/><circle cx="146" cy="14" r="2.5" fill="#ffd36a"/>`,
    front: '',
  }),

  // PERL: hair made of sigils, a scribbled regex on its belly, a smirk.
  perl: (n, hex) => {
    const sig = [['$', 76, 36, -35], ['@', 98, 18, -14], ['%', 122, 8, 2], ['&', 146, 18, 16], ['~', 166, 36, 34], [';', 120, 32, 0]];
    return {
      back: '',
      head: sig.map(([ch, x, y, r], i) =>
        `<g transform="translate(${x} ${y}) rotate(${r})"><g class="sigil" style="--d:${i}">` +
        `<text text-anchor="middle" font-family="${MONO}" font-weight="500" font-size="32" fill="${hex}" stroke="${INK}" stroke-width="1.6" paint-order="stroke">${ch}</text></g></g>`).join(''),
      front:
        `<text x="120" y="226" text-anchor="middle" font-family="${MONO}" font-size="12" fill="${INK}" opacity=".8">s/you/me/g;</text>` +
        `<path d="M152 166 Q160 168 163 158" fill="none" stroke="${INK}" stroke-width="3" stroke-linecap="round"/>`,
    };
  },
};

const FACE =
  `<g class="face">` +
  `<ellipse cx="66" cy="142" rx="10" ry="6" fill="#ff8fb0" opacity=".45"/><ellipse cx="174" cy="142" rx="10" ry="6" fill="#ff8fb0" opacity=".45"/>` +
  `<g class="eye"><ellipse cx="92" cy="112" rx="14" ry="17" fill="#fff" stroke="${INK}" stroke-width="3"/><circle class="pupil" cx="92" cy="115" r="7" fill="${INK}"/></g>` +
  `<g class="eye"><ellipse cx="148" cy="112" rx="14" ry="17" fill="#fff" stroke="${INK}" stroke-width="3"/><circle class="pupil" cx="148" cy="115" r="7" fill="${INK}"/></g>` +
  `<path class="brow l" d="M74 94 L108 99" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>` +
  `<path class="brow r" d="M132 99 L166 94" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>` +
  `<ellipse class="mouth" cx="120" cy="172" rx="10" ry="4" fill="#3a1b4d" stroke="${INK}" stroke-width="3"/>` +
  `</g>`;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function spiritSVG(name, label, hex) {
  const n = uid++;
  const art = (ART[name] || ART.cobol)(n, hex);
  const arm = (side, cx, rot) =>
    `<g class="arm ${side}"><ellipse cx="${cx}" cy="178" rx="17" ry="9" transform="rotate(${rot} ${cx} 178)" fill="url(#body-${n})" stroke="${INK}" stroke-width="3.5"/></g>`;
  return (
    `<svg class="spirit-svg" viewBox="0 0 240 370" role="img" aria-label="${esc(label)}, a cartoon ghost">` +
    `<defs>` +
    `<linearGradient id="body-${n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="${TINT[name] || '#f3e9d2'}"/></linearGradient>` +
    `<radialGradient id="aura-${n}"><stop offset="0" style="stop-color:var(--spirit);stop-opacity:.5"/><stop offset="1" style="stop-color:var(--spirit);stop-opacity:0"/></radialGradient>` +
    `</defs>` +
    `<ellipse class="aura" cx="120" cy="230" rx="132" ry="160" fill="url(#aura-${n})"/>` +
    `<g transform="translate(0 80)"><g class="bob"><g class="shake">` +
    art.back + arm('l', 34, 28) + arm('r', 206, -28) +
    `<path d="${BODY}" fill="url(#body-${n})" stroke="${INK}" stroke-width="4" stroke-linejoin="round"/>` +
    `<ellipse cx="82" cy="64" rx="17" ry="10" fill="#fff" opacity=".65" transform="rotate(-30 82 64)"/>` +
    FACE + art.head + art.front +
    `</g></g></g></svg>`
  );
}
