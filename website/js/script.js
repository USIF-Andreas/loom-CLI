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

document.addEventListener('DOMContentLoaded', function() {
  runGhostAnimation();
  initGame();
});

// --- Ghost Hunter Game ---
function initGame() {
  var canvas = document.getElementById('gameCanvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var scoreEl = document.getElementById('rockCount');
  var statusEl = document.getElementById('gameStatus');
  var btn = document.getElementById('restartBtn');

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = Math.min(rect.width, 640) * 2;
    canvas.height = canvas.width * (400 / 600);
  }
  resize();
  window.addEventListener('resize', resize);

  var game = null;

  function reset() {
    game = {
      ghost: { x: canvas.width/2, y: canvas.height*0.82, size: canvas.width*0.08, speed: 3.5 },
      rocks: [],
      lasers: [],
      score: 0,
      running: true,
      gameOver: false,
      frame: 0,
      spawnRate: 50,
      blinkTimer: 0,
      happyTimer: 0,
      keys: {},
      touchTarget: null,
    };
    scoreEl.textContent = '0';
    statusEl.textContent = '\u25b6';
    btn.textContent = 'Restart';
  }

  var stars = [];
  for (var i = 0; i < 120; i++) {
    stars.push({ x: Math.random(), y: Math.random(), r: 0.5+Math.random()*1.5, p: Math.random() });
  }

  function drawStars(w, h, f) {
    for (var s of stars) {
      var a = 0.3 + 0.7 * (0.5 + 0.5*Math.sin(f*0.02 + s.p*Math.PI*2));
      ctx.fillStyle = 'rgba(200,200,255,'+a+')';
      ctx.beginPath(); ctx.arc(s.x*w, s.y*h, s.r, 0, Math.PI*2); ctx.fill();
    }
  }

  var rockColors = ['#8B7355','#A0825A','#6B5B45','#C4A265','#7A6B52','#95765A'];

  function spawnRock() {
    var size = 10 + Math.random()*18;
    var speed = 0.8 + Math.random()*1.5 + game.score*0.015;
    var pts = 6 + Math.floor(Math.random()*4);
    var shape = [];
    for (var i = 0; i < pts; i++) shape.push(0.7+Math.random()*0.3);
    game.rocks.push({
      x: 20 + Math.random()*(canvas.width-40),
      y: -size*2,
      size: size,
      speed: Math.min(speed, 5),
      color: rockColors[Math.floor(Math.random()*rockColors.length)],
      shape: shape,
      rot: Math.random()*Math.PI*2,
      rv: (Math.random()-0.5)*0.03,
    });
  }

  var shootCooldown = 0;
  function shoot() {
    if (shootCooldown > 0 || !game || !game.running) return;
    shootCooldown = 8;
    game.lasers.push({
      x: game.ghost.x,
      y: game.ghost.y - game.ghost.size * 0.6,
      speed: 8,
      w: 3,
      h: 12,
    });
  }

  var ghostFrames = [
    ['   \u2590   \u2590','  \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584',' \u2588\u2588  \u2590 \u2590  \u2588\u2588',' \u2588\u2588       \u2588\u2588','  \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580','   \u2584\u2580   \u2580\u2584'],
    ['           ','  \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584',' \u2588\u2588       \u2588\u2588',' \u2588\u2588       \u2588\u2588','  \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580','   \u2584\u2580   \u2580\u2584'],
    ['   \u25D5   \u25D5','  \u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2584',' \u2588\u2588  \u25D5 \u25D5  \u2588\u2588',' \u2588\u2588   \u2323   \u2588\u2588','  \u2580\u2588\u2588\u2588\u2588\u2588\u2588\u2580','   \u2584\u2580   \u2580\u2584'],
  ];

  function drawGhost(g) {
    ctx.save();
    var fi = game.happyTimer > 0 ? 2 : (game.blinkTimer > 0 ? 1 : 0);
    var lines = ghostFrames[fi];
    var fs = Math.round(g.size / 4);
    ctx.font = fs + 'px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    var lh = fs * 1.2;
    var startY = g.y - (lines.length * lh) / 2;

    var grd = ctx.createRadialGradient(g.x, g.y, 0, g.x, g.y, fs * 6);
    grd.addColorStop(0, 'rgba(124,58,237,0.18)');
    grd.addColorStop(1, 'rgba(124,58,237,0)');
    ctx.fillStyle = grd;
    ctx.beginPath(); ctx.arc(g.x, g.y, fs * 6, 0, Math.PI * 2); ctx.fill();

    ctx.shadowColor = 'rgba(124,58,237,0.6)';
    ctx.shadowBlur = 18;
    ctx.fillStyle = '#a78bfa';
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].trim()) ctx.fillText(lines[i], g.x, startY + i * lh);
    }
    ctx.restore();
  }

  function drawRock(r) {
    ctx.save();
    ctx.translate(r.x, r.y);
    ctx.rotate(r.rot);
    ctx.fillStyle = r.color;
    ctx.shadowColor = 'rgba(60,50,40,0.4)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    for (var i = 0; i < r.shape.length; i++) {
      var a = (i/r.shape.length)*Math.PI*2;
      var rad = r.size*r.shape[i];
      var px = Math.cos(a)*rad, py = Math.sin(a)*rad;
      if (i===0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  function collides(ghost, rock) {
    var gr = ghost.size * 0.9;
    var dx = ghost.x - rock.x, dy = ghost.y - rock.y;
    return Math.sqrt(dx*dx+dy*dy) < gr + rock.size*0.65;
  }

  function getTouchPos(e) {
    var rect = canvas.getBoundingClientRect();
    var touch = e.touches[0];
    return {
      x: (touch.clientX - rect.left) * (canvas.width / rect.width),
      y: (touch.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  function update() {
    if (!game || !game.running || game.gameOver) return;
    var g = game.ghost;
    var spd = g.speed * canvas.width/640;
    // Touch input
    if (game.touchTarget) {
      var dx = game.touchTarget.x - g.x;
      var dy = game.touchTarget.y - g.y;
      var dist = Math.sqrt(dx*dx+dy*dy);
      if (dist > 5) {
        g.x += (dx/dist) * spd * 1.8;
        g.y += (dy/dist) * spd * 1.8;
      }
    }
    // Keyboard input
    if (game.keys['ArrowLeft']||game.keys['KeyA']||game.keys['a']) g.x -= spd;
    if (game.keys['ArrowRight']||game.keys['KeyD']||game.keys['d']) g.x += spd;
    if (game.keys['ArrowUp']||game.keys['KeyW']||game.keys['w']) g.y -= spd;
    if (game.keys['ArrowDown']||game.keys['KeyS']||game.keys['s']) g.y += spd;
    g.x = Math.max(g.size, Math.min(canvas.width-g.size, g.x));
    g.y = Math.max(canvas.height*0.3, Math.min(canvas.height-g.size, g.y));

    game.frame++;
    if (game.frame % Math.max(18, Math.floor(game.spawnRate - game.score*0.4)) === 0) spawnRock();

    // Shoot
    if (shootCooldown > 0) shootCooldown--;
    if (game.keys['Space']) shoot();
    if (game.touchTarget && game.frame % 12 === 0) shoot();

    // Blink every ~3s
    if (game.blinkTimer > 0) game.blinkTimer--;
    if (Math.random()<0.005) game.blinkTimer = 8;
    if (game.happyTimer > 0) game.happyTimer--;

    // Lasers
    for (var li = game.lasers.length-1; li >= 0; li--) {
      var l = game.lasers[li];
      l.y -= l.speed;
      if (l.y < -20) { game.lasers.splice(li,1); continue; }
      var hit = false;
      for (var ri = game.rocks.length-1; ri >= 0; ri--) {
        var r = game.rocks[ri];
        if (Math.abs(l.x - r.x) < r.size*0.8 && Math.abs(l.y - r.y) < r.size*0.8) {
          game.rocks.splice(ri,1);
          game.score++;
          scoreEl.textContent = game.score;
          if (game.score > 0 && game.score % 20 === 0) game.happyTimer = 90;
          hit = true;
          break;
        }
      }
      if (hit) game.lasers.splice(li,1);
    }

    for (var i = game.rocks.length-1; i >= 0; i--) {
      var r = game.rocks[i];
      r.y += r.speed;
      r.rot += r.rv;
      if (collides(g, r)) {
        game.rocks.splice(i,1);
        game.score++;
        scoreEl.textContent = game.score;
        if (game.score > 0 && game.score % 20 === 0) game.happyTimer = 90;
        continue;
      }
      if (r.y > canvas.height + r.size*2) {
        game.gameOver = true;
        game.running = false;
        statusEl.textContent = '\u2620';
        return;
      }
    }
  }

  function render() {
    if (!game) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawStars(canvas.width, canvas.height, game.frame);
    for (var l of game.lasers) drawLaser(l);
    for (var r of game.rocks) drawRock(r);
    drawGhost(game.ghost);
    // Happy celebration
    if (game.happyTimer > 0) {
      ctx.save();
      ctx.fillStyle = 'rgba(167,139,250,'+(0.3*game.happyTimer/90)+')';
      ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = 'bold '+(canvas.width*0.065)+'px Inter,system-ui,sans-serif';
      var alpha = 0.6 + 0.4 * Math.sin(game.frame * 0.15);
      ctx.fillStyle = 'rgba(34,211,238,'+alpha+')';
      ctx.shadowColor = 'rgba(34,211,238,0.5)';
      ctx.shadowBlur = 30;
      var milestone = Math.floor(game.score / 20) * 20;
      ctx.fillText(milestone+' rocks!', canvas.width/2, canvas.height/2);
      ctx.shadowBlur = 0;
      ctx.restore();
    }
    if (game.gameOver) {
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.65)';
      ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle = '#a78bfa';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = 'bold '+(canvas.width*0.06)+'px Inter,system-ui,sans-serif';
      ctx.fillText('GAME OVER', canvas.width/2, canvas.height/2-16);
      ctx.fillStyle = '#8888b8';
      ctx.font = (canvas.width*0.03)+'px JetBrains Mono,monospace';
      ctx.fillText('Caught '+game.score+' rock'+(game.score!==1?'s':''), canvas.width/2, canvas.height/2+16);
      ctx.restore();
    }
  }

  function drawLaser(l) {
    ctx.save();
    ctx.shadowColor = 'rgba(34,211,238,0.8)';
    ctx.shadowBlur = 12;
    var grad = ctx.createLinearGradient(l.x, l.y-l.h, l.x, l.y+l.h);
    grad.addColorStop(0, 'rgba(34,211,238,0)');
    grad.addColorStop(0.5, 'rgba(34,211,238,1)');
    grad.addColorStop(1, 'rgba(34,211,238,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(l.x-l.w/2, l.y-l.h/2, l.w, l.h);
    ctx.shadowBlur = 20;
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.fillRect(l.x-1, l.y-l.h/2, 2, l.h);
    ctx.restore();
  }

  var lastTime = 0;
  function loop(now) {
    if (game) update();
    render();
    requestAnimationFrame(loop);
  }

  // Input — keyboard
  document.addEventListener('keydown', function(e) {
    if (!game) return;
    game.keys[e.code] = true;
    game.keys[e.key] = true;
    if (e.code.startsWith('Arrow')||e.code.startsWith('Key')) e.preventDefault();
  });
  document.addEventListener('keyup', function(e) {
    if (!game) return;
    game.keys[e.code] = false;
    game.keys[e.key] = false;
  });

  // Input — touch
  canvas.addEventListener('touchstart', function(e) {
    if (!game) return;
    e.preventDefault();
    game.touchTarget = getTouchPos(e);
    if (!game.running && !game.gameOver) reset();
  }, { passive: false });
  canvas.addEventListener('touchmove', function(e) {
    if (!game || !game.running) return;
    e.preventDefault();
    game.touchTarget = getTouchPos(e);
  }, { passive: false });
  canvas.addEventListener('touchend', function(e) {
    if (!game) return;
    e.preventDefault();
    game.touchTarget = null;
  }, { passive: false });

  btn.addEventListener('click', function() {
    if (!game || game.gameOver || !game.running) reset();
  });

  // Initial state: draw welcome
  game = { running: false, gameOver: false, frame: 0, blinkTimer: 0,
    ghost: { x: canvas.width/2, y: canvas.height*0.82, size: canvas.width*0.08 },
    rocks: [], lasers: [], score: 0, keys: {}, touchTarget: null, spawnRate: 50 };
  scoreEl.textContent = '0';
  statusEl.textContent = '\u25b6';
  render();
  requestAnimationFrame(loop);
}
