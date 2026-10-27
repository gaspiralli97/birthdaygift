// Renders a card to a standalone HTML page.
//
// Everything is inlined — no build step, no client framework, no asset server.
// The only outbound request is Google Fonts, and every face has a real fallback
// stack so the page is readable before (or without) it.

import { t } from './strings.js';
import { config } from './config.js';

/** Escapes text for use in element content or a double-quoted attribute. */
const esc = value =>
  String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const primeFactors = n => {
  const factors = [];
  let rest = n;
  for (let d = 2; d * d <= rest; d++) {
    while (rest % d === 0) {
      factors.push(d);
      rest /= d;
    }
  }
  if (rest > 1) factors.push(rest);
  return factors;
};

const groupThousands = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

const SHELL_HEAD = `<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;900&family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap">`;

const BASE_CSS = `
  :root {
    --night: #0d1526; --night-2: #16223a;
    --gold: #e9c47c; --gold-soft: #b8975a;
    --paper: #f2ede3; --muted: #9aa6bd; --flame: #ffb347;
    --display: "Big Shoulders Display", "Arial Narrow", Impact, sans-serif;
    --serif: "Instrument Serif", Georgia, "Times New Roman", serif;
    --mono: "DM Mono", ui-monospace, Menlo, monospace;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  html, body { min-height: 100%; margin: 0; }
  body {
    background: radial-gradient(120% 80% at 50% 0%, var(--night-2) 0%, var(--night) 60%) fixed, var(--night);
    color: var(--paper); font-family: var(--serif);
    padding-left: max(16px, env(safe-area-inset-left, 0px));
    padding-right: max(16px, env(safe-area-inset-right, 0px));
    padding-block: 40px 56px; overflow-x: hidden;
  }
  #sky, #confetti { position: fixed; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  #sky { z-index: 0; } #confetti { z-index: 5; }
  main {
    position: relative; z-index: 1; max-width: 620px; margin: 0 auto;
    display: flex; flex-direction: column; align-items: center; gap: 28px; text-align: center;
  }
  .eyebrow {
    font-family: var(--mono); font-size: 12px; letter-spacing: 0.22em;
    text-transform: uppercase; color: var(--gold);
  }
  .age {
    font-family: var(--display); font-weight: 900;
    font-size: clamp(120px, 38vw, 240px); line-height: 0.8; letter-spacing: -0.02em; margin: 0;
    background: linear-gradient(180deg, #fff3d6 0%, var(--gold) 55%, var(--gold-soft) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 6px 30px rgba(233, 196, 124, 0.25));
  }
  h1 {
    font-family: var(--serif); font-weight: 400; font-size: clamp(32px, 7.5vw, 50px);
    line-height: 1.05; margin: 0; text-wrap: balance;
  }
  h1 em { color: var(--gold); font-style: normal; }
  .letter {
    width: 100%; text-align: left;
    background: rgba(242, 237, 227, 0.04);
    border: 1px solid rgba(233, 196, 124, 0.22); border-radius: 6px;
    padding: 28px clamp(20px, 6vw, 40px); font-size: 21px; line-height: 1.5;
    display: flex; flex-direction: column; gap: 16px;
  }
  .letter p { margin: 0; max-width: 60ch; }
  .letter .sign { font-style: italic; color: var(--gold); text-align: right; }
  .note { font-family: var(--mono); font-size: 12px; color: var(--muted); line-height: 1.6; }
  .note a { color: var(--gold); }
`;

const CARD_CSS = `
  .candles {
    display: grid; grid-template-columns: repeat(10, 1fr); gap: 14px 10px;
    width: 100%; max-width: 420px; padding: 8px 4px 0;
  }
  .candle { position: relative; height: 54px; display: flex; justify-content: center; align-items: flex-end; }
  .candle .stick {
    width: 8px; height: 30px; border-radius: 2px;
    background: repeating-linear-gradient(135deg, var(--paper) 0 5px, var(--gold) 5px 9px);
  }
  .candle .flame {
    position: absolute; bottom: 31px; left: 50%; width: 10px; height: 18px; margin-left: -5px;
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    background: radial-gradient(circle at 50% 70%, #fff7d1 0 25%, var(--flame) 55%, rgba(255,120,40,0) 75%);
    box-shadow: 0 0 14px 4px rgba(255, 179, 71, 0.45);
    transform-origin: 50% 100%;
    animation: flicker 1.6s ease-in-out infinite alternate;
    transition: opacity .35s ease, transform .35s ease;
  }
  .candle:nth-child(3n) .flame { animation-duration: 1.2s; }
  .candle:nth-child(4n) .flame { animation-duration: 2s; animation-delay: -.6s; }
  .candle .smoke {
    position: absolute; bottom: 32px; left: 50%; width: 6px; height: 6px; margin-left: -3px;
    border-radius: 50%; background: rgba(200, 210, 230, .5); opacity: 0;
  }
  .out .flame { opacity: 0; transform: scale(.2) translateY(6px); }
  .out .smoke { animation: smoke 1.4s ease-out forwards; }
  @keyframes flicker {
    0% { transform: rotate(-3deg) scaleY(1); }
    50% { transform: rotate(2deg) scaleY(1.08); }
    100% { transform: rotate(-1deg) scaleY(.94); }
  }
  @keyframes smoke {
    0% { opacity: .7; transform: translate(0, 0) scale(1); }
    100% { opacity: 0; transform: translate(6px, -36px) scale(3); }
  }
  .blow {
    font-family: var(--mono); font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--night); background: var(--gold); border: 0; border-radius: 999px;
    padding: 15px 28px; cursor: pointer; box-shadow: 0 10px 30px rgba(233, 196, 124, .25);
    transition: transform .15s ease, box-shadow .15s ease;
  }
  .blow:hover { transform: translateY(-2px); box-shadow: 0 14px 34px rgba(233, 196, 124, .35); }
  .blow:focus-visible { outline: 2px solid var(--paper); outline-offset: 4px; }
  .hint { font-family: var(--mono); font-size: 12px; color: var(--muted); margin-top: -14px; }
  .ledger {
    width: 100%; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px;
    background: rgba(233, 196, 124, .22); border: 1px solid rgba(233, 196, 124, .22);
    border-radius: 6px; overflow: hidden;
  }
  .ledger div { background: var(--night); padding: 16px 8px; display: flex; flex-direction: column; gap: 4px; }
  .ledger b {
    font-family: var(--display); font-weight: 700; font-size: clamp(24px, 6.5vw, 34px);
    color: var(--paper); font-variant-numeric: tabular-nums; line-height: 1;
  }
  .ledger span {
    font-family: var(--mono); font-size: 11px; letter-spacing: .12em;
    text-transform: uppercase; color: var(--muted);
  }
  .math { display: flex; flex-direction: column; gap: 10px; align-items: center; }
  .math p { margin: 0; font-size: 19px; color: var(--muted); max-width: 40ch; text-wrap: balance; }
  .math .eq {
    font-family: var(--display); font-weight: 700; font-size: clamp(34px, 9vw, 52px);
    color: var(--gold); letter-spacing: .02em;
  }
  @media (max-width: 420px) { .candles { gap: 10px 6px; } .letter { font-size: 19px; } }
  @media (prefers-reduced-motion: reduce) { .candle .flame { animation: none; } }
`;

// The melody is synthesised into a WAV and played through an <audio> element.
// Web Audio is silenced by the iPhone ringer switch; an <audio> element paired
// with audioSession "playback" is not (Safari 17+).
const AUDIO_JS = `
  var G4=392,A4=440,B4=493.88,C5=523.25,D5=587.33,E5=659.25,F5=698.46,G5=783.99;
  var song=[[G4,.75],[G4,.25],[A4,1],[G4,1],[C5,1],[B4,2],
            [G4,.75],[G4,.25],[A4,1],[G4,1],[D5,1],[C5,2],
            [G4,.75],[G4,.25],[G5,1],[E5,1],[C5,1],[B4,1],[A4,2],
            [F5,.75],[F5,.25],[E5,1],[C5,1],[D5,1],[C5,2.5]];
  var BEAT=0.42, RATE=22050, songUrl=null;
  function renderSong(){
    var total=0; song.forEach(function(n){ total+=n[1]*BEAT; });
    var len=Math.ceil((total+0.3)*RATE), pcm=new Int16Array(len), pos=0;
    song.forEach(function(n){
      var d=n[1]*BEAT, count=Math.floor(d*RATE), per=RATE/n[0];
      for(var i=0;i<count;i++){
        var tt=i/RATE, ph=(i%per)/per;
        var tri=4*Math.abs(ph-0.5)-1;
        var env=Math.min(1,tt/0.02)*Math.exp(-3*tt/d);
        pcm[pos+i]=tri*env*0.5*32767;
      }
      pos+=count;
    });
    var buf=new ArrayBuffer(44+len*2), v=new DataView(buf);
    function s(o,str){ for(var i=0;i<str.length;i++) v.setUint8(o+i,str.charCodeAt(i)); }
    s(0,"RIFF"); v.setUint32(4,36+len*2,true); s(8,"WAVE"); s(12,"fmt ");
    v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
    v.setUint32(24,RATE,true); v.setUint32(28,RATE*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true);
    s(36,"data"); v.setUint32(40,len*2,true);
    new Int16Array(buf,44).set(pcm);
    return URL.createObjectURL(new Blob([buf],{type:"audio/wav"}));
  }
  var player=new Audio(); player.setAttribute("playsinline","");
  function playSong(){
    try { if (navigator.audioSession) navigator.audioSession.type="playback"; } catch(e){}
    if(!songUrl) songUrl=renderSong();
    player.src=songUrl; player.currentTime=0;
    var p=player.play(); if(p&&p.catch) p.catch(function(){});
  }
`;

const SKY_JS = `
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var sky=document.getElementById("sky"), sctx=sky.getContext("2d"), stars=[];
  function sizeSky(){
    var dpr=window.devicePixelRatio||1;
    sky.width=innerWidth*dpr; sky.height=innerHeight*dpr;
    sctx.setTransform(dpr,0,0,dpr,0,0); stars=[];
    var n=Math.round(innerWidth*innerHeight/9000);
    for(var i=0;i<n;i++) stars.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:Math.random()*1.2+.2,p:Math.random()*6.28});
  }
  function drawSky(tm){
    sctx.clearRect(0,0,innerWidth,innerHeight);
    for(var i=0;i<stars.length;i++){
      var st=stars[i], a=reduce?.6:.35+.35*Math.sin(tm/900+st.p);
      sctx.fillStyle="rgba(242,237,227,"+a+")";
      sctx.beginPath(); sctx.arc(st.x,st.y,st.r,0,6.28); sctx.fill();
    }
    if(!reduce) requestAnimationFrame(drawSky);
  }
  sizeSky(); requestAnimationFrame(drawSky);
`;

const CONFETTI_JS = `
  var conf=document.getElementById("confetti"), cctx=conf.getContext("2d"), bits=[], running=false;
  var colors=["#e9c47c","#f2ede3","#ffb347","#8fb3ff","#f28b82"];
  function sizeConf(){
    var dpr=window.devicePixelRatio||1;
    conf.width=innerWidth*dpr; conf.height=innerHeight*dpr;
    cctx.setTransform(dpr,0,0,dpr,0,0);
  }
  sizeConf();
  addEventListener("resize", function(){ sizeSky(); sizeConf(); if(reduce) drawSky(0); });
  function burst(){
    for(var i=0;i<220;i++){
      bits.push({x:innerWidth/2+(Math.random()-.5)*120,y:innerHeight*.45,
        vx:(Math.random()-.5)*14,vy:-Math.random()*15-4,
        w:Math.random()*8+4,h:Math.random()*5+3,
        r:Math.random()*6.28,vr:(Math.random()-.5)*.3,
        c:colors[(Math.random()*colors.length)|0],life:0});
    }
    if(!running){ running=true; requestAnimationFrame(stepConf); }
  }
  function stepConf(){
    cctx.clearRect(0,0,innerWidth,innerHeight);
    for(var i=bits.length-1;i>=0;i--){
      var b=bits[i];
      b.vy+=.32; b.vx*=.99; b.x+=b.vx; b.y+=b.vy; b.r+=b.vr; b.life++;
      cctx.save(); cctx.translate(b.x,b.y); cctx.rotate(b.r);
      cctx.fillStyle=b.c; cctx.fillRect(-b.w/2,-b.h/2,b.w,b.h*Math.abs(Math.cos(b.life/8)));
      cctx.restore();
      if(b.y>innerHeight+40) bits.splice(i,1);
    }
    if(bits.length) requestAnimationFrame(stepConf); else { running=false; cctx.clearRect(0,0,innerWidth,innerHeight); }
  }
`;

function page({ title, head = '', css, body, script = '', lang = 'en' }) {
  return `<!doctype html>
<html lang="${esc(lang)}">
<head>
${SHELL_HEAD}
${head}
<title>${esc(title)}</title>
<style>${BASE_CSS}${css || ''}</style>
</head>
<body>
${body}
${script ? `<script>\n(function(){\n${script}\n})();\n</script>` : ''}
</body>
</html>`;
}

/** Full card page. */
export function renderCard(card) {
  const s = t(card.lang);
  const age = card.age;
  // One candle per year, capped so a very large number cannot blow up the DOM.
  const candleCount = Math.min(Math.max(age || 1, 1), 100);
  const daysLeft = Math.max(1, Math.ceil((card.expiresAt - Date.now()) / 86400000));

  const paragraphs = (card.paragraphs || [])
    .map(p => `    <p>${esc(p)}</p>`)
    .join('\n');

  const ledger = age
    ? `  <section class="ledger" aria-label="${esc(s.eyebrow)}">
    <div><b>${age}</b><span>${esc(s.years)}</span></div>
    <div><b>${groupThousands(age * 12)}</b><span>${esc(s.months)}</span></div>
    <div><b>${groupThousands(Math.round(age * 365.2425))}</b><span>${esc(s.days)}</span></div>
  </section>`
    : '';

  const factors = age && age > 1 ? primeFactors(age) : [];
  const math =
    factors.length
      ? `  <div class="math">
    <div class="eyebrow">${esc(s.mathTitle)}</div>
    <p class="eq">${age} = ${factors.join(' × ')}</p>
    <p>${esc(factors.length === 1 ? s.primeOne : s.primeMany)}</p>
  </div>`
      : '';

  const body = `<canvas id="sky" aria-hidden="true"></canvas>
<canvas id="confetti" aria-hidden="true"></canvas>
<main>
  <div class="eyebrow">${esc(s.eyebrow)}</div>
  ${age ? `<p class="age" aria-label="${age}">${age}</p>` : ''}
  <h1>${esc(s.happy)}<br><em>${esc(card.name)}</em></h1>

  <div class="candles" id="candles" aria-label="${candleCount} ${esc(s.litLabel)}"></div>
  <button class="blow" id="blow" type="button">${esc(s.blow)}</button>
  <div class="hint" id="hint">${esc(s.hint)}</div>

  <article class="letter">
${paragraphs}
${card.from ? `    <p class="sign">${esc(s.from(card.from))}</p>` : ''}
  </article>

${ledger}
${math}

  <p class="note">${esc(s.expiresIn(daysLeft))}<br>
  <a href="${esc(config.publicUrl)}/">${esc(s.makeOne)}</a></p>
</main>`;

  const script = `${SKY_JS}${CONFETTI_JS}${AUDIO_JS}
  var COUNT=${candleCount};
  var wrap=document.getElementById("candles");
  for(var i=0;i<COUNT;i++){
    var c=document.createElement("div"); c.className="candle";
    c.innerHTML='<span class="flame"></span><span class="smoke"></span><span class="stick"></span>';
    wrap.appendChild(c);
  }
  var LIT=${JSON.stringify(`${candleCount} ${s.litLabel}`)};
  var OUT=${JSON.stringify(`${candleCount} ${s.outLabel}`)};
  var btn=document.getElementById("blow"), hint=document.getElementById("hint"), lit=true;
  btn.addEventListener("click", function(){
    var cs=wrap.children;
    if(lit){
      for(var i=0;i<cs.length;i++)(function(el,k){
        setTimeout(function(){ el.classList.add("out"); }, reduce?0:k*35);
      })(cs[i],i);
      setTimeout(burst, reduce?0:Math.min(600, COUNT*35+200));
      playSong();
      btn.textContent=${JSON.stringify(s.relight)};
      hint.textContent=${JSON.stringify(s.wished)};
      wrap.setAttribute("aria-label", OUT);
    } else {
      for(var j=0;j<cs.length;j++) cs[j].classList.remove("out");
      btn.textContent=${JSON.stringify(s.blow)};
      hint.textContent=${JSON.stringify(s.hint)};
      wrap.setAttribute("aria-label", LIT);
    }
    lit=!lit;
  });`;

  const ogTitle = `${s.happy} ${card.name}`;
  const head = `<meta property="og:title" content="${esc(ogTitle)}">
<meta property="og:description" content="${esc(s.hint)}">`;

  return page({ title: ogTitle, head, css: CARD_CSS, body, script, lang: card.lang });
}

/** Shown when an id is unknown or past its five days. */
export function renderExpired(lang = 'uz') {
  const s = t(lang);
  const body = `<canvas id="sky" aria-hidden="true"></canvas>
<main>
  <div class="eyebrow">${esc(s.eyebrow)}</div>
  <h1>${esc(s.expiredTitle)}</h1>
  <article class="letter"><p>${esc(s.expiredBody)}</p></article>
  <p class="note"><a href="${esc(config.publicUrl)}/">${esc(s.makeOne)}</a></p>
</main>`;
  return page({ title: s.expiredTitle, body, script: SKY_JS, lang });
}

export { esc, page, BASE_CSS, SKY_JS };
