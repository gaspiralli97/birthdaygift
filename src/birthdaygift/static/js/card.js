/* Card page behaviour: starfield, candles, confetti and the melody.
 *
 * Everything is read from data- attributes on <main>, so this file stays
 * static and cacheable and the template carries no inline script.
 */
(() => {
  'use strict';

  const root = document.querySelector('main');
  if (!root) return;

  const config = {
    count: Number(root.dataset.candles || 0),
    light: root.dataset.light === '1',
    confetti: (root.dataset.confetti || '').split(',').filter(Boolean),
    litLabel: root.dataset.litLabel || '',
    outLabel: root.dataset.outLabel || '',
    blowLabel: root.dataset.blowLabel || '',
    relightLabel: root.dataset.relightLabel || '',
    hint: root.dataset.hint || '',
    wished: root.dataset.wished || '',
  };

  const reduceMotion =
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cssVar = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  // --- starfield ---------------------------------------------------------

  const sky = document.getElementById('sky');
  const skyCtx = sky.getContext('2d');
  let stars = [];

  const sizeSky = () => {
    const dpr = window.devicePixelRatio || 1;
    sky.width = innerWidth * dpr;
    sky.height = innerHeight * dpr;
    skyCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const total = Math.round((innerWidth * innerHeight) / 9000);
    stars = Array.from({ length: total }, () => ({
      x: Math.random() * innerWidth,
      y: Math.random() * innerHeight,
      r: Math.random() * 1.2 + 0.2,
      phase: Math.random() * Math.PI * 2,
    }));
  };

  const drawSky = (time) => {
    const hex = cssVar('--paper').replace('#', '');
    const rgb = [0, 2, 4].map((i) => parseInt(hex.substr(i, 2), 16));
    // On the cream colourway the specks are dark on light, which at full
    // strength reads as dirt rather than sky. Damp them to a paper grain.
    const scale = config.light ? 0.3 : 1;
    skyCtx.clearRect(0, 0, innerWidth, innerHeight);
    for (const star of stars) {
      const alpha =
        (reduceMotion ? 0.6 : 0.35 + 0.35 * Math.sin(time / 900 + star.phase)) * scale;
      skyCtx.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
      skyCtx.beginPath();
      skyCtx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      skyCtx.fill();
    }
    if (!reduceMotion) requestAnimationFrame(drawSky);
  };

  sizeSky();
  requestAnimationFrame(drawSky);

  // --- confetti ----------------------------------------------------------

  const confettiCanvas = document.getElementById('confetti');
  const confettiCtx = confettiCanvas.getContext('2d');
  const colors = config.confetti.length ? config.confetti : ['#f2d9a0', '#f2e5c6'];
  let bits = [];
  let running = false;

  const sizeConfetti = () => {
    const dpr = window.devicePixelRatio || 1;
    confettiCanvas.width = innerWidth * dpr;
    confettiCanvas.height = innerHeight * dpr;
    confettiCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  sizeConfetti();

  addEventListener('resize', () => {
    sizeSky();
    sizeConfetti();
    if (reduceMotion) drawSky(0);
  });

  const step = () => {
    confettiCtx.clearRect(0, 0, innerWidth, innerHeight);
    for (let i = bits.length - 1; i >= 0; i--) {
      const bit = bits[i];
      bit.vy += 0.32;
      bit.vx *= 0.99;
      bit.x += bit.vx;
      bit.y += bit.vy;
      bit.rotation += bit.spin;
      bit.life++;
      confettiCtx.save();
      confettiCtx.translate(bit.x, bit.y);
      confettiCtx.rotate(bit.rotation);
      confettiCtx.fillStyle = bit.color;
      // Scaling the height by a cosine of its age makes each piece look like
      // it is tumbling, which costs nothing next to drawing a solid.
      confettiCtx.fillRect(
        -bit.w / 2, -bit.h / 2, bit.w, bit.h * Math.abs(Math.cos(bit.life / 8)));
      confettiCtx.restore();
      if (bit.y > innerHeight + 40) bits.splice(i, 1);
    }
    if (bits.length) {
      requestAnimationFrame(step);
    } else {
      running = false;
      confettiCtx.clearRect(0, 0, innerWidth, innerHeight);
    }
  };

  const burst = () => {
    for (let i = 0; i < 220; i++) {
      bits.push({
        x: innerWidth / 2 + (Math.random() - 0.5) * 120,
        y: innerHeight * 0.45,
        vx: (Math.random() - 0.5) * 14,
        vy: -Math.random() * 15 - 4,
        w: Math.random() * 8 + 4,
        h: Math.random() * 5 + 3,
        rotation: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 0.3,
        color: colors[(Math.random() * colors.length) | 0],
        life: 0,
      });
    }
    if (!running) {
      running = true;
      requestAnimationFrame(step);
    }
  };

  // --- melody ------------------------------------------------------------

  // Synthesised to a WAV and played through an <audio> element rather than
  // Web Audio: an iPhone's ringer switch silences Web Audio outright, while an
  // <audio> element paired with audioSession "playback" keeps playing.
  const NOTES = {
    G4: 392, A4: 440, B4: 493.88, C5: 523.25,
    D5: 587.33, E5: 659.25, F5: 698.46, G5: 783.99,
  };
  const SONG = [
    ['G4', 0.75], ['G4', 0.25], ['A4', 1], ['G4', 1], ['C5', 1], ['B4', 2],
    ['G4', 0.75], ['G4', 0.25], ['A4', 1], ['G4', 1], ['D5', 1], ['C5', 2],
    ['G4', 0.75], ['G4', 0.25], ['G5', 1], ['E5', 1], ['C5', 1], ['B4', 1], ['A4', 2],
    ['F5', 0.75], ['F5', 0.25], ['E5', 1], ['C5', 1], ['D5', 1], ['C5', 2.5],
  ];
  const BEAT = 0.42;
  const RATE = 22050;

  const player = new Audio();
  player.setAttribute('playsinline', '');
  let songUrl = null;

  const renderSong = () => {
    const seconds = SONG.reduce((total, [, beats]) => total + beats * BEAT, 0);
    const length = Math.ceil((seconds + 0.3) * RATE);
    const pcm = new Int16Array(length);
    let offset = 0;

    for (const [note, beats] of SONG) {
      const duration = beats * BEAT;
      const samples = Math.floor(duration * RATE);
      const period = RATE / NOTES[note];
      for (let i = 0; i < samples; i++) {
        const t = i / RATE;
        const phase = (i % period) / period;
        const triangle = 4 * Math.abs(phase - 0.5) - 1;
        const envelope = Math.min(1, t / 0.02) * Math.exp((-3 * t) / duration);
        pcm[offset + i] = triangle * envelope * 0.5 * 32767;
      }
      offset += samples;
    }

    const buffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(buffer);
    const ascii = (at, text) => {
      for (let i = 0; i < text.length; i++) view.setUint8(at + i, text.charCodeAt(i));
    };
    ascii(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    ascii(8, 'WAVE');
    ascii(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, RATE, true);
    view.setUint32(28, RATE * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    ascii(36, 'data');
    view.setUint32(40, length * 2, true);
    new Int16Array(buffer, 44).set(pcm);

    return URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }));
  };

  const playSong = () => {
    try {
      if (navigator.audioSession) navigator.audioSession.type = 'playback';
    } catch {
      /* Safari below 17 has no audioSession; the ringer switch wins there. */
    }
    if (!songUrl) songUrl = renderSong();
    player.src = songUrl;
    player.currentTime = 0;
    player.play()?.catch(() => {});
  };

  // --- candles -----------------------------------------------------------

  const field = document.getElementById('candles');
  const button = document.getElementById('blow');
  const hint = document.getElementById('hint');
  if (!field || !button) return;

  for (let i = 0; i < config.count; i++) {
    const candle = document.createElement('div');
    candle.className = 'candle';
    candle.innerHTML =
      '<span class="flame"></span><span class="smoke"></span><span class="stick"></span>';
    field.appendChild(candle);
  }

  let lit = true;

  const syncButton = () => {
    button.textContent = lit ? config.blowLabel : config.relightLabel;
    hint.textContent = lit ? config.hint : config.wished;
    field.setAttribute('aria-label', lit ? config.litLabel : config.outLabel);
  };
  syncButton();

  button.addEventListener('click', () => {
    // Capture the target before flipping it. Reading `lit` inside the timeout
    // reads it after the flip, which snuffs the candles a click late.
    const blowingOut = lit;
    const candles = field.children;
    for (let i = 0; i < candles.length; i++) {
      const candle = candles[i];
      setTimeout(() => candle.classList.toggle('out', blowingOut), reduceMotion ? 0 : i * 35);
    }
    if (blowingOut) {
      setTimeout(burst, reduceMotion ? 0 : Math.min(600, config.count * 35 + 200));
      playSong();
    }
    lit = !lit;
    syncButton();
  });
})();
