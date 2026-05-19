"""
GTM Auditor — Client-side Google Tag Manager audit tool (dark theme overhaul).

Paste any URL → fetch the page → detect GTM container ID → pull the public
gtm.js script → parse tags, triggers, variables → run an AI audit via Groq.

UI: dark theme, Three.js particle hero, floating gradient orbs, glassmorphism
cards, animated counters, scroll progress bar, marquee ticker.
"""

import json
import re
from typing import Any
from urllib.parse import urlparse

import requests
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Page config + global styling
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="GTM Auditor", page_icon="🔍", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg-base: #0a0a0f;
  --bg-surface: rgba(255,255,255,0.04);
  --bg-elevated: rgba(255,255,255,0.06);
  --border: rgba(255,255,255,0.08);
  --border-strong: rgba(255,255,255,0.14);
  --text-primary: #f5f5f7;
  --text-secondary: #a0a0a8;
  --text-tertiary: #6e6e78;
  --accent-blue: #3b82f6;
  --accent-violet: #8b5cf6;
  --accent-success: #10b981;
  --accent-warn: #f59e0b;
  --accent-error: #ef4444;
  --gradient-primary: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
}

html, body, [class*="css"], .stApp, .stApp > div,
div[data-testid="stAppViewContainer"], div[data-testid="stAppViewBlockContainer"],
div[data-testid="block-container"], div[data-testid="stVerticalBlock"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  color: var(--text-primary) !important;
  background-color: var(--bg-base) !important;
}

.main, .stApp { background-color: var(--bg-base) !important; }
.block-container { padding: 1rem 2rem 4rem; max-width: 1100px; background: transparent !important; position: relative; z-index: 1; }

/* ── Floating gradient orbs in background ── */
.stApp::before {
  content: '';
  position: fixed;
  top: -20%;
  left: -10%;
  width: 60vw;
  height: 60vw;
  max-width: 800px;
  max-height: 800px;
  background: radial-gradient(circle, rgba(59,130,246,0.18) 0%, transparent 60%);
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
  animation: orb-drift-1 22s ease-in-out infinite alternate;
}
.stApp::after {
  content: '';
  position: fixed;
  bottom: -25%;
  right: -15%;
  width: 70vw;
  height: 70vw;
  max-width: 900px;
  max-height: 900px;
  background: radial-gradient(circle, rgba(139,92,246,0.16) 0%, transparent 60%);
  border-radius: 50%;
  filter: blur(90px);
  z-index: 0;
  pointer-events: none;
  animation: orb-drift-2 28s ease-in-out infinite alternate;
}
@keyframes orb-drift-1 {
  0%   { transform: translate(0,0)   scale(1); }
  100% { transform: translate(15vw,10vh) scale(1.15); }
}
@keyframes orb-drift-2 {
  0%   { transform: translate(0,0)   scale(1); }
  100% { transform: translate(-12vw,-8vh) scale(1.2); }
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: rgba(15,15,22,0.85) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
section[data-testid="stSidebar"] .stTextInput input {
  background: var(--bg-surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
}

/* ── Typography ── */
h1 { font-size: 2.4rem !important; font-weight: 700 !important; letter-spacing: -.035em !important; color: var(--text-primary) !important; }
h2 { font-size: 1.4rem !important; font-weight: 600 !important; letter-spacing: -.02em !important; color: var(--text-primary) !important; }
h3 { font-size: 1.05rem !important; font-weight: 500 !important; color: var(--text-primary) !important; }
p, span, div { color: inherit; }

/* ── Glass cards ── */
.glass-card {
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 22px 26px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  transition: transform .3s cubic-bezier(.2,.8,.2,1), border-color .3s, box-shadow .3s;
}
.glass-card:hover {
  border-color: var(--border-strong);
  transform: translateY(-3px);
  box-shadow: 0 16px 48px rgba(0,0,0,0.4);
}

.metric-card {
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 22px 20px;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: transform .3s, border-color .3s;
}
.metric-card:hover { transform: translateY(-3px); border-color: var(--border-strong); }
.metric-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: var(--gradient-primary);
  opacity: .7;
}
.metric-num { font-size: 2.2rem; font-weight: 700; letter-spacing: -.035em; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
.metric-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-tertiary); margin-top: 6px; font-weight: 600; }

/* ── Tag cards ── */
.tag-card {
  background: var(--bg-surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 10px;
  border-left: 3px solid rgba(255,255,255,0.2);
  transition: transform .25s, border-color .25s;
}
.tag-card:hover { transform: translateX(3px); border-color: var(--border-strong); }
.tag-card.pass { border-left-color: var(--accent-success); }
.tag-card.warn { border-left-color: var(--accent-warn); }
.tag-card.fail { border-left-color: var(--accent-error); }
.tag-card.info { border-left-color: var(--accent-blue); }
.tag-name { font-size: 14px; font-weight: 600; color: var(--text-primary); letter-spacing: -.01em; }
.tag-detail { font-size: 12px; color: var(--text-secondary); margin-top: 4px; font-weight: 300; line-height: 1.6; }
.tag-rec { font-size: 12px; color: var(--accent-warn); margin-top: 6px; font-style: italic; }

/* ── Badges ── */
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 980px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .03em;
  margin-left: 8px;
  border: 1px solid;
  text-transform: uppercase;
}
.badge-pass { background: rgba(16,185,129,0.12); color: var(--accent-success); border-color: rgba(16,185,129,0.25); }
.badge-warn { background: rgba(245,158,11,0.12); color: var(--accent-warn); border-color: rgba(245,158,11,0.25); }
.badge-fail { background: rgba(239,68,68,0.12); color: var(--accent-error); border-color: rgba(239,68,68,0.25); }
.badge-info { background: rgba(59,130,246,0.12); color: var(--accent-blue); border-color: rgba(59,130,246,0.25); }

/* ── Buttons ── */
.stButton > button {
  background: var(--gradient-primary) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 980px !important;
  padding: 12px 28px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  font-family: Inter, sans-serif !important;
  letter-spacing: -.01em !important;
  width: 100%;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(59,130,246,0.35);
  transition: transform .2s, box-shadow .2s;
}
.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 28px rgba(59,130,246,0.5);
}
.stButton > button::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
  transition: left .6s ease;
}
.stButton > button:hover::after { left: 100%; }

/* ── Inputs ── */
.stTextInput > div > div > input {
  background: var(--bg-surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 13px 18px !important;
  font-size: 15px !important;
  font-family: Inter, sans-serif !important;
  font-weight: 400 !important;
  transition: border-color .2s, box-shadow .2s;
}
.stTextInput > div > div > input::placeholder { color: var(--text-tertiary) !important; }
.stTextInput > div > div > input:focus {
  border-color: var(--accent-blue) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-color: var(--accent-blue) transparent transparent transparent !important; }

/* ── Site header ── */
.site-header {
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 22px 28px;
  margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.gtm-id {
  font-family: 'JetBrains Mono', monospace;
  background: rgba(59,130,246,0.12);
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  color: var(--accent-blue);
  font-weight: 600;
  border: 1px solid rgba(59,130,246,0.25);
}

/* ── GA4 banner ── */
.ga4-banner {
  background: var(--gradient-primary);
  border-radius: 18px;
  padding: 22px 26px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  box-shadow: 0 8px 32px rgba(59,130,246,0.25);
  position: relative;
  overflow: hidden;
}
.ga4-banner::before {
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%);
  border-radius: 50%;
}

/* ── Detected tools pill ── */
.detected-pill {
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 980px;
  padding: 6px 14px;
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 500;
  display: inline-block;
  margin: 3px;
  transition: transform .2s, border-color .2s;
}
.detected-pill:hover { transform: translateY(-2px); border-color: var(--accent-blue); }

/* ── Info cards on landing ── */
.info-card {
  background: var(--bg-surface);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 28px;
  transition: transform .3s, border-color .3s, box-shadow .3s;
  position: relative;
  overflow: hidden;
}
.info-card:hover {
  transform: translateY(-4px);
  border-color: var(--border-strong);
  box-shadow: 0 16px 48px rgba(0,0,0,0.4);
}
.info-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: var(--gradient-primary);
  opacity: 0; transition: opacity .3s;
}
.info-card:hover::before { opacity: 1; }
.info-card h3 { font-size: 17px !important; font-weight: 600 !important; color: var(--text-primary) !important; margin-bottom: 10px !important; letter-spacing: -.02em; }
.info-card p { font-size: 14px; color: var(--text-secondary) !important; font-weight: 300; line-height: 1.7; margin: 0; }
.info-icon {
  width: 44px; height: 44px;
  background: var(--gradient-primary);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  margin-bottom: 14px;
  box-shadow: 0 4px 16px rgba(59,130,246,0.3);
}

/* ── Marquee ticker ── */
.marquee-wrap {
  overflow: hidden;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 14px 0;
  margin: 32px 0;
  background: rgba(255,255,255,0.02);
}
.marquee-track {
  display: inline-flex;
  white-space: nowrap;
  animation: marquee 40s linear infinite;
  gap: 40px;
  padding-left: 40px;
}
.marquee-item {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  letter-spacing: .04em;
  text-transform: uppercase;
}
.marquee-dot { color: var(--accent-blue); }
@keyframes marquee {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

/* ── Parsed-container strip ── */
.parsed-strip {
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.2);
  border-radius: 12px;
  padding: 12px 18px;
  margin-bottom: 14px;
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--accent-success);
  font-weight: 500;
}

/* ── Section reveal ── */
.reveal { opacity: 0; transform: translateY(20px); transition: opacity .6s ease, transform .6s ease; }
.reveal.in-view { opacity: 1; transform: translateY(0); }

/* ── Mobile ── */
@media (max-width: 769px) {
  .stApp::before, .stApp::after { display: none; }
  h1 { font-size: 1.8rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Three.js hero component
# ─────────────────────────────────────────────────────────────────────────────

THREE_JS_HERO = """
<!DOCTYPE html>
<html>
<head>
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; font-family: 'Inter', -apple-system, sans-serif; }
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  #scene { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
  .overlay {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    text-align: center; padding: 0 20px; pointer-events: none; z-index: 2;
  }
  .pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 980px;
    padding: 7px 16px;
    font-size: 12px; font-weight: 500; color: #a0a0a8;
    margin-bottom: 24px;
    animation: fade-in 1s ease-out .3s both;
  }
  .pill-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #3b82f6;
    box-shadow: 0 0 8px #3b82f6;
    animation: pulse 2s ease-in-out infinite;
  }
  h1 {
    font-size: 3.2rem;
    font-weight: 700;
    color: #f5f5f7;
    letter-spacing: -.04em;
    line-height: 1.05;
    margin: 0 0 16px;
    animation: fade-up 1s cubic-bezier(.2,.8,.2,1) .5s both;
  }
  h1 .grad {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: grad-shift 6s ease-in-out infinite;
  }
  p {
    font-size: 16px;
    color: #a0a0a8;
    font-weight: 300;
    max-width: 540px;
    line-height: 1.6;
    margin: 0;
    animation: fade-up 1s cubic-bezier(.2,.8,.2,1) .8s both;
  }
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
  @keyframes fade-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 8px #3b82f6; }
    50% { box-shadow: 0 0 16px #3b82f6, 0 0 24px #3b82f6; }
  }
  @keyframes grad-shift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
  }
  @media (max-width: 769px) {
    h1 { font-size: 2rem; }
    p { font-size: 14px; }
  }
</style>
</head>
<body>
<canvas id="scene"></canvas>
<div class="overlay">
  <div class="pill"><div class="pill-dot"></div>GTM Auditor</div>
  <h1>Audit any website's<br><span class="grad">GTM setup instantly</span></h1>
  <p>Paste any website URL and get a full Google Tag Manager audit in seconds. No GTM access needed.</p>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function() {
  const canvas = document.getElementById('scene');
  const isMobile = window.innerWidth < 769;
  const W = () => window.innerWidth;
  const H = () => 480;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(75, W() / H(), 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setSize(W(), H());
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Particle field
  const count = isMobile ? 120 : 300;
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const palette = [[0.23, 0.51, 0.96], [0.55, 0.36, 0.96], [1, 1, 1]];
  for (let i = 0; i < count; i++) {
    positions[i*3]   = (Math.random() - 0.5) * 30;
    positions[i*3+1] = (Math.random() - 0.5) * 12;
    positions[i*3+2] = (Math.random() - 0.5) * 18;
    const c = palette[Math.floor(Math.random() * palette.length)];
    colors[i*3] = c[0]; colors[i*3+1] = c[1]; colors[i*3+2] = c[2];
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  const mat = new THREE.PointsMaterial({
    size: 0.06, vertexColors: true, transparent: true, opacity: 0.85,
    blending: THREE.AdditiveBlending, sizeAttenuation: true,
  });
  const points = new THREE.Points(geom, mat);
  scene.add(points);

  // Wireframe shapes
  const shapes = [];
  const shapeData = [
    { geo: new THREE.IcosahedronGeometry(1.6, 0), color: 0x3b82f6, x: -6 },
    { geo: new THREE.OctahedronGeometry(1.3, 0),  color: 0x8b5cf6, x:  0 },
    { geo: new THREE.TetrahedronGeometry(1.4, 0), color: 0xec4899, x:  6 },
  ];
  shapeData.forEach((s, i) => {
    const m = new THREE.MeshBasicMaterial({ color: s.color, wireframe: true, transparent: true, opacity: 0.28 });
    const mesh = new THREE.Mesh(s.geo, m);
    mesh.position.set(s.x, (i % 2 === 0 ? 1 : -1) * 1.5, -2);
    shapes.push(mesh);
    scene.add(mesh);
  });

  camera.position.z = 8;

  // Mouse reactivity
  let mx = 0, my = 0, tx = 0, ty = 0;
  if (!isMobile) {
    document.addEventListener('mousemove', (e) => {
      tx = (e.clientX / W() - 0.5) * 0.6;
      ty = (e.clientY / H() - 0.5) * 0.6;
    });
  }

  function loop() {
    requestAnimationFrame(loop);
    mx += (tx - mx) * 0.06;
    my += (ty - my) * 0.06;
    points.rotation.y += 0.0008;
    points.rotation.x = my * 0.25;
    points.position.x = mx * 0.4;
    shapes.forEach((s, i) => {
      s.rotation.x += 0.002 + i * 0.0008;
      s.rotation.y += 0.0015 + i * 0.0005;
    });
    renderer.render(scene, camera);
  }
  loop();

  window.addEventListener('resize', () => {
    camera.aspect = W() / H();
    camera.updateProjectionMatrix();
    renderer.setSize(W(), H());
  }, { passive: true });
})();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Injected FX (scroll progress bar + counter animations + reveal observer)
# ─────────────────────────────────────────────────────────────────────────────

INJECTED_FX = """
<!DOCTYPE html>
<html><head></head><body>
<script>
(function() {
  const parent = window.parent.document;
  const win = window.parent;

  // ── Scroll progress bar ──
  let bar = parent.getElementById('gtm-scroll-progress');
  if (!bar) {
    bar = parent.createElement('div');
    bar.id = 'gtm-scroll-progress';
    bar.style.cssText = `
      position: fixed; top: 0; left: 0; height: 3px; width: 0;
      background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
      z-index: 9998; transition: width .1s linear;
      box-shadow: 0 0 8px rgba(59,130,246,0.6);
    `;
    parent.body.appendChild(bar);

    win.addEventListener('scroll', () => {
      const doc = parent.documentElement;
      const max = doc.scrollHeight - win.innerHeight;
      const pct = max > 0 ? (win.scrollY / max) * 100 : 0;
      bar.style.width = pct + '%';
    }, { passive: true });
  }

  // ── Counter animations ──
  function animateCounter(el) {
    if (el.dataset.animated) return;
    el.dataset.animated = 'true';
    const target = parseInt(el.textContent, 10);
    if (isNaN(target) || target === 0) return;
    const duration = 1800;
    const start = performance.now();
    function step(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(eased * target);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ── Reveal observer (also catches counters) ──
  if (!win.__gtmFxObserver) {
    win.__gtmFxObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        if (e.target.classList.contains('metric-num')) {
          animateCounter(e.target);
        }
        if (e.target.classList.contains('reveal')) {
          e.target.classList.add('in-view');
        }
      });
    }, { threshold: 0.2 });
  }

  function scan() {
    parent.querySelectorAll('.metric-num:not([data-animated])').forEach(el => win.__gtmFxObserver.observe(el));
    parent.querySelectorAll('.reveal:not(.in-view)').forEach(el => win.__gtmFxObserver.observe(el));
  }

  scan();
  if (!win.__gtmFxMutObs) {
    win.__gtmFxMutObs = new MutationObserver(() => { scan(); });
    win.__gtmFxMutObs.observe(parent.body, { childList: true, subtree: true });
  }
})();
</script>
</body></html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Constants (audit logic — unchanged from previous version)
# ─────────────────────────────────────────────────────────────────────────────

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

GTM_TAG_TYPES = {
    "__googtag": "Google Tag (gtag.js)",
    "__ga4": "GA4 Event",
    "__gaawc": "GA4 Configuration",
    "__gaawe": "GA4 Event",
    "__ua": "Universal Analytics (DEPRECATED)",
    "__awct": "Google Ads Conversion",
    "__sp": "Google Ads Remarketing",
    "__cl": "Conversion Linker",
    "__gclidw": "Conversion Linker",
    "__fls": "Floodlight Sales",
    "__flc": "Floodlight Counter",
    "__fbpx": "Facebook Pixel",
    "__tikt": "TikTok Pixel",
    "__pntr": "Pinterest Tag",
    "__lnkd": "LinkedIn Insight Tag",
    "__bzi": "LinkedIn Insight Tag",
    "__twitter_website_tag": "Twitter / X Pixel",
    "__uet": "Microsoft / Bing UET",
    "__html": "Custom HTML",
    "__img": "Custom Image Tag",
    "__hjtc": "Hotjar Tracking",
    "__crto": "Criteo OneTag",
    "__bb": "Snap Pixel",
}

TRACKING_SIGNATURES = {
    "facebook_pixel": [r"connect\.facebook\.net", r"\bfbq\("],
    "tiktok_pixel": [r"analytics\.tiktok\.com", r"ttq\.load"],
    "pinterest_tag": [r"\bpintrk\(", r"ct\.pinterest\.com"],
    "linkedin_insight": [r"snap\.licdn\.com/li\.lms-analytics", r"_linkedin_partner_id"],
    "twitter_pixel": [r"static\.ads-twitter\.com", r"\btwq\("],
    "bing_uet": [r"bat\.bing\.com", r"\buetq\b"],
    "snap_pixel": [r"sc-static\.net/scevent", r"snaptr\("],
    "reddit_pixel": [r"redditstatic\.com.*pixel", r"rdt\("],
    "klaviyo": [r"static\.klaviyo\.com", r"klaviyo\.com/onsite"],
    "hubspot": [r"js\.hs-scripts\.com", r"js\.hs-analytics\.net"],
    "hotjar": [r"static\.hotjar\.com", r"\bhj\("],
    "clarity": [r"clarity\.ms"],
    "fullstory": [r"fullstory\.com", r"\bFS\."],
    "segment": [r"cdn\.segment\.com", r"analytics\.load"],
    "amplitude": [r"amplitude\.com/libs"],
    "mixpanel": [r"cdn\.mxpnl\.com", r"mixpanel\.init"],
    "onetrust_consent": [r"cdn\.cookielaw\.org", r"otSDKStub"],
    "cookiebot_consent": [r"consent\.cookiebot\.com"],
    "usercentrics_consent": [r"app\.usercentrics\.eu", r"app\.usercentrics\.com"],
    "shopify": [r"cdn\.shopify\.com", r"Shopify\.theme", r"shopify_pay"],
    "woocommerce": [r"wp-content/plugins/woocommerce"],
    "magento": [r"Magento_", r"/static/version\d+/frontend"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Fetching + parsing (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    return raw if parsed.netloc else ""


def fetch_page(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        st.error(f"Could not fetch page: {e}")
        return None


def fetch_gtm_script(gtm_id: str) -> str | None:
    url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        st.warning(f"Could not fetch gtm.js for {gtm_id}: {e}")
        return None


def extract_gtm_ids(html: str) -> list[str]:
    return sorted(set(re.findall(r"GTM-[A-Z0-9]{4,12}", html)))


def extract_page_signals(html: str) -> dict[str, Any]:
    detected = [
        tool for tool, patterns in TRACKING_SIGNATURES.items()
        if any(re.search(p, html, re.I) for p in patterns)
    ]
    return {
        "ga4_ids": sorted(set(re.findall(r"G-[A-Z0-9]{8,12}", html))),
        "ga_universal_ids": sorted(set(re.findall(r"UA-\d{4,10}-\d{1,4}", html))),
        "google_ads_ids": sorted(set(re.findall(r"AW-\d{8,12}", html))),
        "floodlight_ids": sorted(set(re.findall(r"DC-\d{6,10}", html))),
        "datalayer_pushes": re.findall(r"dataLayer\.push\(\{[^}]{0,300}\}\)", html)[:10],
        "gtag_calls": list(set(re.findall(r"gtag\([^)]{0,200}\)", html)))[:10],
        "consent_mode": bool(re.search(r"gtag\s*\(\s*['\"]consent['\"]", html)),
        "consent_mode_v2": bool(re.search(r"ad_user_data|ad_personalization", html)),
        "detected_tools": detected,
        "server_side_gtm": bool(re.search(r"sgtm\.|server-side.*gtm|gtm\.[a-z0-9-]+\.[a-z]{2,}\?id=GTM", html, re.I)),
        "script_count": len(re.findall(r"<script", html, re.I)),
    }


def extract_balanced_object(text: str, start_idx: int) -> str | None:
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        return None
    depth, in_string, escape = 0, False, False
    for i in range(start_idx, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return None


def parse_gtm_container(script: str | None) -> dict[str, Any] | None:
    if not script:
        return None
    m = re.search(r"(?:var|let|const)\s+data\s*=\s*", script)
    if not m:
        return None
    brace_idx = script.find("{", m.end())
    raw_obj = extract_balanced_object(script, brace_idx)
    if not raw_obj:
        return None
    try:
        data = json.loads(raw_obj)
    except json.JSONDecodeError:
        return None
    resource = data.get("resource", {}) if isinstance(data, dict) else {}
    if not resource:
        return None

    tags = []
    for t in resource.get("tags", []):
        fn = t.get("function", "")
        params = {p.get("key", ""): p.get("value", "") for p in t.get("vtp", []) if isinstance(p, dict)}
        tags.append({
            "function": fn,
            "type": GTM_TAG_TYPES.get(fn, fn.replace("__", "")),
            "name": t.get("instance_name") or t.get("function", "Unknown"),
            "paused": bool(t.get("paused", False)),
            "once_per_event": bool(t.get("once_per_event", False)),
            "params": params,
        })

    variables = []
    for v in resource.get("macros", []):
        fn = v.get("function", "")
        params = {p.get("key", ""): p.get("value", "") for p in v.get("vtp", []) if isinstance(p, dict)}
        variables.append({
            "function": fn,
            "type": fn.replace("__", ""),
            "name": v.get("instance_name") or fn,
            "params": params,
        })

    predicates = [{
        "function": p.get("function", ""),
        "arg0": p.get("arg0", ""),
        "arg1": p.get("arg1", ""),
    } for p in resource.get("predicates", [])]

    rules = resource.get("rules", [])

    return {
        "version": resource.get("version", "unknown"),
        "tags": tags,
        "variables": variables,
        "predicates": predicates,
        "rules": rules,
        "tag_count": len(tags),
        "variable_count": len(variables),
        "predicate_count": len(predicates),
        "rule_count": len(rules),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI audit
# ─────────────────────────────────────────────────────────────────────────────

def build_audit_prompt(url: str, gtm_id: str, parsed: dict[str, Any] | None, signals: dict[str, Any]) -> str:
    container_section = "Container could not be parsed."
    if parsed:
        tag_lines = [
            f"- {t['name']} | type: {t['type']}{' [PAUSED]' if t['paused'] else ''} | params: {json.dumps(t['params'])[:180]}"
            for t in parsed["tags"][:60]
        ]
        var_lines = [f"- {v['name']} | type: {v['type']}" for v in parsed["variables"][:60]]
        pred_lines = [f"- {p['function']} | arg0={p['arg0']} arg1={p['arg1']}" for p in parsed["predicates"][:40]]
        container_section = f"""
Container version: {parsed['version']}
Counts: {parsed['tag_count']} tags, {parsed['variable_count']} variables, {parsed['predicate_count']} predicates, {parsed['rule_count']} rules

TAGS:
{chr(10).join(tag_lines) or '(none)'}

VARIABLES:
{chr(10).join(var_lines) or '(none)'}

PREDICATES (trigger conditions):
{chr(10).join(pred_lines) or '(none)'}
"""

    return f"""You are a senior web analytics implementation auditor. Audit the GTM setup at {url} (Container: {gtm_id}).

GTM CONTAINER (parsed from public gtm.js):
{container_section}

PAGE SIGNALS (from rendered HTML):
- GA4 IDs detected: {signals.get('ga4_ids', [])}
- Universal Analytics IDs (DEPRECATED): {signals.get('ga_universal_ids', [])}
- Google Ads IDs: {signals.get('google_ads_ids', [])}
- Floodlight IDs: {signals.get('floodlight_ids', [])}
- Consent Mode detected: {signals.get('consent_mode', False)}
- Consent Mode v2 signals (ad_user_data / ad_personalization): {signals.get('consent_mode_v2', False)}
- Other tracking tools detected: {signals.get('detected_tools', [])}
- Server-side GTM signals: {signals.get('server_side_gtm', False)}

AUDIT PRIORITIES (apply these standards strictly):
1. Universal Analytics is DEPRECATED (sunset July 2023). Flag any UA tag, UA-XXXXX ID, or analytics.js as a HIGH priority issue.
2. Consent Mode v2 became required for EEA traffic in March 2024. If GA4 / Google Ads are present without `ad_user_data` and `ad_personalization` signals, flag as a HIGH priority issue.
3. GA4 event names must be snake_case. Flag non-compliant custom event names.
4. Conversion Linker should be present whenever Google Ads tags are present.
5. Server-side GTM is a maturity indicator — call it out if missing for ecommerce/lead-gen sites.
6. Duplicate firing: if both Shopify native tracking AND a GTM-based GA4 tag exist, flag duplicate-event risk.
7. Use the ACTUAL tag/variable names from the container above — do not invent names.

Return ONLY valid JSON, no markdown, no commentary:

{{
  "site_summary": "2 sentences about the site and how their tracking is set up",
  "health_score": 0-100,
  "tags_found": <int>,
  "triggers_found": <int>,
  "variables_found": <int>,
  "issues_count": <int>,
  "ga4": {{
    "detected": true|false,
    "measurement_id": "G-XXXXX or null",
    "via": "GTM | direct gtag | both | none",
    "ecommerce": true|false,
    "consent_mode": true|false,
    "consent_mode_v2": true|false,
    "status": "pass|warn|fail",
    "note": "specific observation"
  }},
  "tags": [
    {{"name": "<real tag name>", "type": "<readable type>", "status": "pass|warn|fail|info", "detail": "what it does", "recommendation": "specific fix or null"}}
  ],
  "triggers": [
    {{"name": "<readable trigger label>", "type": "Page View|Click|Form|Custom Event|Timer|...", "status": "pass|warn|fail|info", "detail": "what fires it", "recommendation": "specific fix or null"}}
  ],
  "top_issues": [
    {{"title": "Issue title", "priority": "high|medium|low", "detail": "what is wrong", "fix": "how to fix"}}
  ],
  "quick_wins": ["short actionable win", "..."]
}}"""


def run_audit(api_key: str, prompt: str) -> dict[str, Any] | None:
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        st.error(f"AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        st.error(f"AI audit failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────

def badge(status: str) -> str:
    mapping = {
        "pass": ("badge-pass", "Pass"),
        "warn": ("badge-warn", "Warning"),
        "fail": ("badge-fail", "Issue"),
        "info": ("badge-info", "Info"),
    }
    cls, label = mapping.get(status, ("badge-info", status.title()))
    return f'<span class="badge {cls}">{label}</span>'


def priority_badge(priority: str) -> str:
    mapping = {"high": "badge-fail", "medium": "badge-warn", "low": "badge-pass"}
    return f'<span class="badge {mapping.get(priority, "badge-info")}">{priority.title()}</span>'


def render_marquee() -> None:
    items = [
        "GA4", "Google Ads", "Floodlight", "Meta Pixel", "TikTok Pixel",
        "LinkedIn Insight", "Pinterest Tag", "Consent Mode v2", "Server-side GTM",
        "Conversion Linker", "Enhanced Conversions", "BigQuery Export", "Hotjar",
        "Clarity", "OneTrust", "Cookiebot", "Klaviyo", "HubSpot",
    ]
    seq = ""
    for it in items:
        seq += f'<span class="marquee-item">{it}</span><span class="marquee-item marquee-dot">•</span>'
    track = seq + seq  # duplicate for seamless loop
    st.markdown(
        f'<div class="marquee-wrap"><div class="marquee-track">{track}</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Sidebar ──
    with st.sidebar:
        st.markdown(
            """
        <div style="padding:8px 0 16px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px">
                <div style="width:8px;height:8px;background:#3b82f6;border-radius:50%;box-shadow:0 0 8px #3b82f6"></div>
                <span style="font-size:13px;font-weight:600;color:#f5f5f7;letter-spacing:-.01em">GTM Auditor</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        saved_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        api_key = saved_key or st.text_input(
            "Groq API Key", type="password", placeholder="gsk_...", help="Free at console.groq.com"
        )
        if saved_key:
            st.markdown(
                '<div style="font-size:11px;color:#10b981;margin-top:2px">✓ API key loaded from secrets</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:11px;color:#a0a0a8;margin-top:2px">Free key at <a href="https://console.groq.com" target="_blank" style="color:#3b82f6">console.groq.com</a></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
        <div style="background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:16px 18px">
            <div style="font-size:11px;font-weight:600;color:#f5f5f7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px">What this audits</div>
            <div style="font-size:12px;color:#a0a0a8;line-height:1.9;font-weight:300">
                GTM tags, triggers, variables<br>
                GA4 + Google Ads + Floodlight<br>
                Universal Analytics deprecation<br>
                Consent Mode v2 compliance<br>
                Server-side GTM signals<br>
                Duplicate tracking risk<br>
                Quick wins and fixes
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ── Inject scroll progress bar + counter observer (height=0, no visual) ──
    components.html(INJECTED_FX, height=0)

    # ── Three.js hero ──
    components.html(THREE_JS_HERO, height=480)

    # ── URL input ──
    col1, col2 = st.columns([4, 1])
    with col1:
        url_input = st.text_input("Website URL", placeholder="https://yourwebsite.com", label_visibility="collapsed")
    with col2:
        analyze = st.button("Audit GTM →")

    if not api_key:
        st.markdown(
            """
        <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:12px;padding:14px 18px;font-size:13px;color:#f59e0b;font-weight:400;margin-top:8px">
            ⚠ Add your free Groq API key in the sidebar to get started. Get one at <a href="https://console.groq.com" target="_blank" style="color:#3b82f6">console.groq.com</a>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    if not (analyze and url_input):
        render_marquee()
        st.markdown(
            """
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:8px">
            <div class="info-card reveal">
                <div class="info-icon">🏷️</div>
                <h3>What is GTM?</h3>
                <p>Google Tag Manager is a free tool that lets businesses add and manage tracking codes on their website without touching the source code. It controls everything from GA4 to Facebook Pixel to conversion tracking.</p>
            </div>
            <div class="info-card reveal">
                <div class="info-icon">🔍</div>
                <h3>How this tool works</h3>
                <p>Paste any website URL. The tool fetches the page source, detects the GTM container ID, pulls the public gtm.js script, parses every tag and variable, then runs an AI audit against current best practices.</p>
            </div>
            <div class="info-card reveal">
                <div class="info-icon">💡</div>
                <h3>Who is this for?</h3>
                <p>Digital marketers, analytics consultants, and agency teams who want to quickly check a client or competitor site's tracking setup without needing access to their GTM account.</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # ── Run audit ──
    url = normalize_url(url_input)
    if not url:
        st.error("Please enter a valid URL.")
        return

    with st.spinner("Fetching page source..."):
        html = fetch_page(url)
    if not html:
        return

    with st.spinner("Detecting GTM container..."):
        gtm_ids = extract_gtm_ids(html)
        signals = extract_page_signals(html)

    if not gtm_ids:
        pills = "".join(f'<div class="detected-pill">{t.replace("_", " ").title()}</div>' for t in signals["detected_tools"])
        if signals["ga4_ids"]:
            pills += f'<div class="detected-pill">GA4: {", ".join(signals["ga4_ids"])}</div>'
        if signals["ga_universal_ids"]:
            pills += f'<div class="detected-pill" style="border-color:#ef4444;color:#ef4444">UA (deprecated): {", ".join(signals["ga_universal_ids"])}</div>'

        st.markdown(
            f"""
        <div class="glass-card" style="text-align:center;margin-top:8px;padding:36px 32px">
            <div style="font-size:42px;margin-bottom:14px">🔎</div>
            <div style="font-size:22px;font-weight:600;color:#f5f5f7;margin-bottom:10px;letter-spacing:-.02em">No GTM container found</div>
            <div style="font-size:14px;color:#a0a0a8;font-weight:300;max-width:520px;margin:0 auto;line-height:1.7">
                This website does not appear to be using Google Tag Manager. Many sites manage tracking differently.
            </div>
            <div style="margin-top:18px">{pills}</div>
            <div style="margin-top:24px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:14px;padding:20px 24px;text-align:left">
                <div style="font-size:12px;font-weight:600;color:#f5f5f7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px">Common reasons GTM is not found</div>
                <div style="font-size:13px;color:#a0a0a8;font-weight:300;line-height:2.1">
                    🛍️ <strong style="color:#f5f5f7;font-weight:600">Shopify native tracking</strong> — built-in analytics replace GTM<br>
                    📦 <strong style="color:#f5f5f7;font-weight:600">Direct GA4 (gtag.js)</strong> — fires without GTM<br>
                    🔒 <strong style="color:#f5f5f7;font-weight:600">Server-side tracking</strong> — invisible in page source<br>
                    🧩 <strong style="color:#f5f5f7;font-weight:600">Custom CMS</strong> — Webflow / Wix / Squarespace native<br>
                    ⚡ <strong style="color:#f5f5f7;font-weight:600">Single Page App</strong> — GTM loads dynamically
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    gtm_id = gtm_ids[0]

    with st.spinner(f"Fetching GTM container {gtm_id}..."):
        gtm_script = fetch_gtm_script(gtm_id)
        parsed = parse_gtm_container(gtm_script)

    if parsed:
        st.markdown(
            f"""
        <div class="parsed-strip">
            <span>✓ Container parsed</span>
            <span>{parsed['tag_count']} tags</span>
            <span>{parsed['variable_count']} variables</span>
            <span>{parsed['predicate_count']} conditions</span>
            <span>{parsed['rule_count']} rules</span>
            <span>v{parsed['version']}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Container detected but could not be parsed. AI audit will use page signals only.")

    with st.spinner("Running AI audit..."):
        prompt = build_audit_prompt(url, gtm_id, parsed, signals)
        audit = run_audit(api_key, prompt)

    if not audit:
        st.error("Audit failed. Please try again.")
        return

    domain = urlparse(url).netloc

    # ── Site header ──
    st.markdown(
        f"""
    <div class="site-header reveal">
        <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap">
            <div style="width:52px;height:52px;background:var(--gradient-primary);border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:17px;color:#fff;flex-shrink:0;box-shadow:0 6px 18px rgba(59,130,246,0.35)">{domain[:2].upper()}</div>
            <div style="flex:1;min-width:200px">
                <div style="font-size:19px;font-weight:600;letter-spacing:-.02em;color:#f5f5f7">{domain}</div>
                <div style="font-size:13px;color:#a0a0a8;margin-top:3px;font-weight:300">{audit.get('site_summary', '')}</div>
            </div>
            <div style="text-align:center;flex-shrink:0">
                <div style="font-size:10px;color:#6e6e78;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px">Container</div>
                <span class="gtm-id">{gtm_id}</span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Metrics ──
    score = audit.get("health_score", 0)
    score_color = "var(--accent-success)" if score >= 70 else "var(--accent-warn)" if score >= 50 else "var(--accent-error)"
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, score, "Health Score", score_color),
        (c2, audit.get("tags_found", 0), "Tags Found", "var(--accent-blue)"),
        (c3, audit.get("triggers_found", 0), "Triggers", "var(--accent-blue)"),
        (c4, audit.get("variables_found", 0), "Variables", "var(--accent-blue)"),
        (c5, audit.get("issues_count", 0), "Issues", "var(--accent-error)"),
    ]
    for col, num, lbl, color in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card reveal"><div class="metric-num" style="color:{color}">{num}</div><div class="metric-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GA4 banner ──
    ga4 = audit.get("ga4", {})
    cm_label = "v2" if ga4.get("consent_mode_v2") else ("v1" if ga4.get("consent_mode") else "Off")
    st.markdown(
        f"""
    <div class="ga4-banner reveal">
        <div style="background:rgba(255,255,255,.18);width:44px;height:44px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:800;color:#fff;flex-shrink:0;position:relative;z-index:1">G4</div>
        <div style="flex:1;min-width:200px;position:relative;z-index:1">
            <div style="font-size:16px;font-weight:600;color:#fff;letter-spacing:-.01em">Google Analytics 4</div>
            <div style="font-size:12px;color:rgba(255,255,255,.8);margin-top:3px;font-weight:300">{ga4.get('note', '')}</div>
        </div>
        <div style="display:flex;gap:22px;text-align:center;flex-wrap:wrap;position:relative;z-index:1">
            <div><div style="font-size:10px;color:rgba(255,255,255,.65);text-transform:uppercase;letter-spacing:.06em;font-weight:600">ID</div><div style="font-size:13px;font-weight:600;color:#fff;margin-top:3px;font-family:'JetBrains Mono',monospace">{ga4.get('measurement_id') or 'None'}</div></div>
            <div><div style="font-size:10px;color:rgba(255,255,255,.65);text-transform:uppercase;letter-spacing:.06em;font-weight:600">Via</div><div style="font-size:13px;font-weight:600;color:#fff;margin-top:3px">{ga4.get('via', 'Unknown')}</div></div>
            <div><div style="font-size:10px;color:rgba(255,255,255,.65);text-transform:uppercase;letter-spacing:.06em;font-weight:600">Ecommerce</div><div style="font-size:13px;font-weight:600;color:#fff;margin-top:3px">{'Active' if ga4.get('ecommerce') else 'None'}</div></div>
            <div><div style="font-size:10px;color:rgba(255,255,255,.65);text-transform:uppercase;letter-spacing:.06em;font-weight:600">Consent</div><div style="font-size:13px;font-weight:600;color:#fff;margin-top:3px">{cm_label}</div></div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Detected tools strip ──
    if signals.get("detected_tools"):
        pills = "".join(
            f'<div class="detected-pill">{t.replace("_", " ").title()}</div>'
            for t in signals["detected_tools"]
        )
        st.markdown(
            f'<div class="glass-card reveal" style="padding:16px 22px;margin-bottom:18px"><div style="font-size:10px;font-weight:600;color:#6e6e78;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Also detected on the page</div>{pills}</div>',
            unsafe_allow_html=True,
        )

    # ── Tags + Triggers ──
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### Tags")
        for tag in audit.get("tags", []):
            rec = f'<div class="tag-rec">→ {tag["recommendation"]}</div>' if tag.get("recommendation") else ""
            st.markdown(
                f'<div class="tag-card reveal {tag.get("status","info")}">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap"><span class="tag-name">{tag["name"]}</span>{badge(tag.get("status","info"))}</div>'
                f'<div class="tag-detail">{tag.get("detail","")}</div>{rec}</div>',
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown("### Triggers")
        for t in audit.get("triggers", []):
            rec = f'<div class="tag-rec">→ {t["recommendation"]}</div>' if t.get("recommendation") else ""
            st.markdown(
                f'<div class="tag-card reveal {t.get("status","info")}">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap"><span class="tag-name">{t["name"]}</span>{badge(t.get("status","info"))}</div>'
                f'<div class="tag-detail">{t.get("detail","")}</div>{rec}</div>',
                unsafe_allow_html=True,
            )

    # ── Top issues ──
    if audit.get("top_issues"):
        st.markdown("### Top issues to fix")
        for issue in audit["top_issues"]:
            cls = "fail" if issue.get("priority") == "high" else "warn" if issue.get("priority") == "medium" else "info"
            st.markdown(
                f'<div class="tag-card reveal {cls}">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap"><span class="tag-name">{issue["title"]}</span>{priority_badge(issue.get("priority","medium"))}</div>'
                f'<div class="tag-detail">{issue.get("detail","")}</div>'
                f'<div class="tag-rec">→ {issue.get("fix","")}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Quick wins ──
    if audit.get("quick_wins"):
        st.markdown("### Quick wins")
        wins_html = "".join(
            f'<div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid var(--border);font-size:13px;color:#a0a0a8;font-weight:300"><span style="color:#10b981;flex-shrink:0">✓</span> {w}</div>'
            for w in audit["quick_wins"]
        )
        st.markdown(f'<div class="glass-card reveal">{wins_html}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="text-align:center;padding:32px 0 8px;font-size:11px;color:#6e6e78;letter-spacing:.06em;text-transform:uppercase">GTM Auditor — {domain} — Powered by Groq</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
