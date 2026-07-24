// --- Ghost frames ---
const G = {
  NORMAL: [
    "      \u2590   \u2590",
    "    \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "   \u2588\u2588  \u2590 \u2590  \u2588\u2588",
    "   \u2588\u2588       \u2588\u2588",
    "    \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "     \u2584\u2580   \u2580\u2584",
  ],
  BLINK: [
    "      \u2590   \u2590",
    "    \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "   \u2588\u2588       \u2588\u2588",
    "   \u2588\u2588       \u2588\u2588",
    "    \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "     \u2584\u2580   \u2580\u2584",
  ],
  WINK_L: [
    "      \u2590   \u2590",
    "    \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "   \u2588\u2588      \u2588\u2588",
    "   \u2588\u2588       \u2588\u2588",
    "    \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "     \u2584\u2580   \u2580\u2584",
  ],
  WINK_R: [
    "      \u2590   \u2590",
    "    \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "   \u2588\u2588  \u2590    \u2588\u2588",
    "   \u2588\u2588       \u2588\u2588",
    "    \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "     \u2584\u2580   \u2580\u2584",
  ],
  FLY_UP: [
    "  \u2588\u2588  \u2590   \u2590  \u2588\u2588",
    "   \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "  \u2588\u2588  \u2590 \u2590  \u2588\u2588",
    "  \u2588\u2588       \u2588\u2588",
    "   \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "    \u2584\u2580   \u2580\u2584",
  ],
  FLY_DOWN: [
    "    \u2590   \u2590",
    "  \u2588\u2588\u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2588\u2588",
    "    \u2588\u2588  \u2590 \u2590  \u2588\u2588",
    "    \u2588\u2588       \u2588\u2588",
    "  \u2588\u2588\u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580\u2588\u2588",
    "     \u2584\u2580   \u2580\u2584",
  ],
  HOVER: [
    "      \u2590   \u2590",
    "   \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584",
    "  \u2588\u2588  \u2590 \u2590  \u2588\u2588",
    "  \u2588\u2588       \u2588\u2588",
    "   \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2580",
    "     \u2580   \u2580",
  ],
};

function setGhost(frame) {
  const el = document.getElementById('ghost');
  if (el) el.textContent = frame.join('\n');
}

function ghostFly(yes) {
  const el = document.getElementById('ghost');
  if (!el) return;
  el.classList.remove('fly-up', 'fly-down');
  if (yes === false) {
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = '';
  } else if (yes) {
    el.classList.add('fly-' + yes);
  }
}

// --- Animation timeline ---
function runGhostAnimation() {
  const seq = [
    { frame: G.NORMAL, dur: 2000 },
    // Blink
    { frame: G.NORMAL, dur: 100 },
    { frame: G.BLINK, dur: 120 },
    { frame: G.NORMAL, dur: 100 },
    // Wink right
    { frame: G.NORMAL, dur: 600 },
    { frame: G.WINK_R, dur: 300 },
    { frame: G.NORMAL, dur: 500 },
    // Blink again
    { frame: G.BLINK, dur: 100 },
    { frame: G.NORMAL, dur: 100 },
    // Wink left
    { frame: G.NORMAL, dur: 800 },
    { frame: G.WINK_L, dur: 300 },
    { frame: G.NORMAL, dur: 400 },
    // Hover prep
    { frame: G.HOVER, dur: 400 },
    // Fly cycle
    { frame: G.FLY_UP, dur: 200, fly: 'up' },
    { frame: G.FLY_DOWN, dur: 200, fly: 'down' },
    { frame: G.FLY_UP, dur: 200, fly: 'up' },
    { frame: G.FLY_DOWN, dur: 200, fly: 'down' },
    { frame: G.FLY_UP, dur: 200, fly: 'up' },
    { frame: G.HOVER, dur: 300, fly: false },
    // Back to normal
    { frame: G.NORMAL, dur: 300 },
  ];

  let i = 0;
  function play() {
    if (i >= seq.length) { i = 0; }
    const s = seq[i];
    setGhost(s.frame);
    if (s.fly !== undefined) ghostFly(s.fly);
    i++;
    setTimeout(play, s.dur);
  }
  play();
}

// --- Copy command ---
function copyCmd(el) {
  const text = el.textContent.replace('copied', '').trim();
  navigator.clipboard.writeText(text).then(() => {
    const badge = el.querySelector('.copied');
    if (badge) {
      badge.classList.add('show');
      setTimeout(() => badge.classList.remove('show'), 1500);
    }
  }).catch(() => {});
}

document.addEventListener('DOMContentLoaded', runGhostAnimation);
