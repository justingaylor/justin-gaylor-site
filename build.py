#!/usr/bin/env python3
"""
build.py — Justin Gaylor's site builder
────────────────────────────────────────
Usage:
  python build.py          # build once into dist/
  python build.py --watch  # rebuild whenever content files change

Requirements:
  pip install pyyaml markdown

Content layout:
  content/about.md                     ← your about copy (Markdown, YAML front matter)
  content/projects.yaml                ← structured project list
  content/blog/YYYY-MM-DD-slug.md      ← blog posts (sorted by date automatically)
  content/stories/YYYY-MM-DD-slug.md  ← fiction (sorted by date automatically)

Output:
  dist/index.html
  dist/blog/<slug>.html
  dist/stories/<slug>.html
"""

import os, sys, re, shutil, time
from pathlib import Path
from datetime import date, datetime
import yaml
import markdown as md_lib

# ── Configuration ──────────────────────────────────────────────────────────────

SITE_TITLE    = "Justin Gaylor"
SITE_TAGLINE  = "Scribe · Artificer · Wanderer"
BASE_URL      = "https://gaylor.quest"

AUTHOR_EMAIL  = "justin.gaylor@proton.me"
GITHUB_URL    = "https://github.com/justingaylor"
BLUESKY_URL   = "https://bsky.app/profile/justingaylor.bsky.social"
LINKEDIN_URL  = "https://www.linkedin.com/in/justin-gaylor-a9326b2"

# Stat block on the About section — change these to whatever you like
CHAR_STATS = [
    ("CLASS",      "MAGIC USER"),
    ("SCHOOL",     "FICTION"),
    ("BACKGROUND", "SCRIBE"),
    ("ORIGIN",     "MUNCIE, IN, USA"),
    ("ERA",        "BORN 1982"),
    ("EQUIPMENT",  "KEYBOARD"),
]

CONTENT_DIR = Path("content")
DIST_DIR    = Path("dist")

# ── CSS (shared across all pages) ─────────────────────────────────────────────

CSS = """
:root {
  --bg:          #010901;
  --bg-solid:    #010901;
  --bg-panel:    #040d04;
  --bg-panel2:   #071007;
  --green:       #00e060;
  --green-hi:    #33ff88;
  --green-dim:   #3a9958;
  --green-faint: #0d2e16;
  --green-glow:  rgba(0,200,80,0.07);
  --text:        #4db87a;
  --text-dim:    #3d9e60;
  --border:      #0d2e16;
  --border-mid:  #174d27;
}
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg-solid);
  color: var(--text);
  font-family: 'IM Fell English', Georgia, serif;
  font-size: 17px;
  line-height: 1.78;
  overflow-x: hidden;
}
body::before {
  content: '';
  position: fixed; inset: 0;
  background: repeating-linear-gradient(
    0deg, rgba(0,0,0,0.07) 0px, rgba(0,0,0,0.07) 1px,
    transparent 1px, transparent 4px
  );
  pointer-events: none; z-index: 9000;
}
body::after {
  content: '';
  position: fixed; inset: 0;
  background: radial-gradient(ellipse at 50% 38%, transparent 50%, rgba(0,0,0,0.80) 100%);
  pointer-events: none; z-index: 9001;
}
@keyframes flicker {
  0%,91%,100% { opacity:1; } 92% { opacity:0.95; } 95% { opacity:0.98; } 97% { opacity:0.93; }
}
#wrap { animation: flicker 16s infinite; }

/* ── Nav ── */
nav {
  position: fixed; top:0; width:100%; z-index: 800;
  background: rgba(1,9,1,0.95);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(6px);
  padding: 0 2.5rem; height: 52px;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-logo {
  font-family: 'VT323', monospace; font-size: 1.25rem;
  color: var(--green); text-decoration: none;
  letter-spacing: 0.1em; text-shadow: 0 0 12px rgba(0,220,90,0.45);
}
.nav-logo span { color: var(--green-dim); margin-right: 0.25em; }
.nav-links { display: flex; gap: 2rem; list-style: none; }
.nav-links a {
  font-family: 'VT323', monospace; font-size: 1rem;
  color: var(--text-dim); text-decoration: none;
  letter-spacing: 0.12em; transition: color 0.2s, text-shadow 0.2s;
}
.nav-links a:hover { color: var(--green); text-shadow: 0 0 8px rgba(0,220,80,0.5); }
.nav-hamburger {
  display: none; flex-direction: column; gap: 5px;
  cursor: pointer; background: none; border: none; padding: 4px;
}
.nav-hamburger span { display: block; width: 22px; height: 1px; background: var(--green-dim); }

/* ── Layout ── */
.section-wrap { max-width: 980px; margin: 0 auto; padding: 5rem 5vw; }
hr.rule { border: none; border-top: 1px solid var(--border); max-width: 980px; margin: 0 auto; }
.section-header { margin-bottom: 2.5rem; }
.section-label {
  font-family: 'VT323', monospace; font-size: 2.3rem;
  color: var(--green); letter-spacing: 0.08em;
  text-shadow: 0 0 14px rgba(0,220,80,0.22); line-height: 1;
}
.section-label .glyph { color: var(--green-dim); margin-right: 0.35em; }
.section-sub {
  font-family: 'VT323', monospace; font-size: 0.8rem;
  color: var(--text-dim); letter-spacing: 0.22em; margin-top: 0.25rem;
}

/* ── Buttons ── */
.btn {
  font-family: 'VT323', monospace; font-size: 1.05rem;
  letter-spacing: 0.14em; padding: 0.45rem 1.4rem;
  border: 1px solid var(--border-mid); color: var(--green);
  background: transparent; text-decoration: none; cursor: pointer;
  transition: all 0.2s; display: inline-flex; align-items: center; gap: 0.4em;
}
.btn::before { content: '►'; font-size: 0.75em; opacity: 0; transition: opacity 0.2s; }
.btn:hover {
  background: var(--green-glow); border-color: var(--green);
  box-shadow: 0 0 16px rgba(0,210,80,0.15);
  text-shadow: 0 0 8px rgba(0,220,80,0.6);
}
.btn:hover::before { opacity: 1; }

/* ── Hero quest line ── */
.hero-quest {
  font-family: 'IM Fell English', serif;
  font-style: italic;
  font-size: clamp(1.35rem, 3vw, 1.9rem);
  color: var(--green-hi);
  text-shadow: 0 0 22px rgba(0,220,80,0.35);
  letter-spacing: 0.01em;
  margin-bottom: 1.75rem;
  line-height: 1.3;
}

/* ── Hero ── */
#hero {
  min-height: 100vh; display: flex; flex-direction: column;
  justify-content: center; padding: 7rem 5vw 5rem;
  max-width: 980px; margin: 0 auto; position: relative;
}
#hero::before {
  content: '✦ ─────────────────────────────── ✦';
  font-family: 'VT323', monospace; color: var(--green-dim);
  font-size: 0.9rem; letter-spacing: 0.1em; display: block; margin-bottom: 2rem;
}
.hero-sys {
  font-family: 'VT323', monospace; font-size: 0.95rem;
  color: var(--text-dim); letter-spacing: 0.2em; margin-bottom: 1rem; line-height: 1.5;
}
.hero-name {
  font-family: 'VT323', monospace;
  font-size: clamp(4.2rem, 13vw, 9.5rem);
  color: var(--green); line-height: 0.88; letter-spacing: 0.02em;
  text-shadow: 0 0 20px rgba(0,220,80,0.38), 0 0 60px rgba(0,220,80,0.10);
  margin-bottom: 0.6rem;
}
.hero-subtitle {
  font-family: 'VT323', monospace; font-size: 1.4rem;
  color: var(--green-dim); letter-spacing: 0.25em; margin-bottom: 1.5rem;
}
.hero-tagline {
  font-style: italic; font-size: 1.1rem; color: var(--text);
  max-width: 540px; min-height: 2.2em; margin-bottom: 2.75rem; line-height: 1.65;
}
.cursor-blink {
  display: inline-block; width: 9px; height: 1em;
  background: var(--green); vertical-align: text-bottom; margin-left: 2px;
  animation: blink 0.85s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.hero-ctas { display: flex; gap: 1.25rem; flex-wrap: wrap; margin-bottom: 2rem; }
.hero-after {
  font-family: 'VT323', monospace; font-size: 0.85rem;
  color: var(--text-dim); letter-spacing: 0.15em;
}

/* ── About ── */
.about-layout { display: grid; grid-template-columns: 1fr 220px; gap: 3rem; align-items: start; }
.about-body p { color: var(--text); margin-bottom: 1.1rem; font-size: 1rem; }
.about-body p:last-child { margin-bottom: 0; }
.about-body em { color: var(--green); font-style: italic; }
.char-sheet {
  border: 1px solid var(--border-mid); background: var(--bg-panel2);
  padding: 1.25rem 1rem; position: relative;
}
.char-sheet::before {
  content: '✦ CHARACTER ✦'; font-family: 'VT323', monospace;
  font-size: 0.8rem; color: var(--green-dim); letter-spacing: 0.2em;
  display: block; text-align: center; margin-bottom: 1rem;
  padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);
}
.stat-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 0.3rem 0; border-bottom: 1px solid var(--border);
}
.stat-row:last-child { border-bottom: none; }
.stat-name { font-family: 'VT323', monospace; font-size: 0.82rem; color: var(--text-dim); letter-spacing: 0.15em; }
.stat-val  { font-family: 'VT323', monospace; font-size: 1rem; color: var(--green); }

/* ── Writing cards ── */
.writing-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(265px, 1fr)); gap: 1.25rem; }
.writing-card {
  border: 1px solid var(--border); padding: 1.6rem;
  background: var(--bg-panel); position: relative; overflow: hidden;
  transition: border-color 0.25s, background 0.25s;
}
.writing-card::after {
  content: '✦'; font-family: 'VT323', monospace;
  position: absolute; bottom: 0.75rem; right: 1rem;
  font-size: 1rem; color: var(--border-mid); transition: color 0.3s;
}
.writing-card::before {
  content:''; position:absolute; top:0; left:0; width:3px; height:100%;
  background: var(--green); transform: scaleY(0); transform-origin: top; transition: transform 0.3s;
}
.writing-card:hover { border-color: var(--border-mid); background: rgba(0,200,80,0.02); }
.writing-card:hover::before { transform: scaleY(1); }
.writing-card:hover::after { color: var(--green-dim); }
.card-tag { font-family: 'VT323', monospace; font-size: 0.8rem; color: var(--text-dim); letter-spacing: 0.2em; margin-bottom: 0.4rem; }
.card-title { font-family: 'IM Fell English', serif; font-size: 1.3rem; color: var(--green); line-height: 1.2; margin-bottom: 0.7rem; }
.card-excerpt { font-style: italic; font-size: 0.9rem; color: var(--text-dim); line-height: 1.7; margin-bottom: 1.2rem; }
.card-readtime { font-family: 'VT323', monospace; font-size: 0.78rem; color: var(--text-dim); letter-spacing: 0.12em; margin-bottom: 1rem; }
.card-link { font-family: 'VT323', monospace; font-size: 0.9rem; color: var(--text-dim); text-decoration: none; letter-spacing: 0.12em; transition: color 0.2s; }
.card-link::before { content: '► '; font-size: 0.8em; }
.card-link:hover { color: var(--green); }

/* ── Blog list ── */
.blog-list { display: flex; flex-direction: column; }
.blog-entry {
  display: grid; grid-template-columns: 115px 1fr; gap: 1.5rem;
  padding: 1.35rem 0; border-bottom: 1px solid var(--border);
  text-decoration: none; transition: background 0.2s, padding-left 0.2s;
}
.blog-entry:first-child { border-top: 1px solid var(--border); }
.blog-entry:hover { background: var(--green-glow); padding-left: 0.6rem; }
.blog-date-col { display: flex; flex-direction: column; gap: 0.1rem; }
.blog-date { font-family: 'VT323', monospace; font-size: 0.88rem; color: var(--text-dim); letter-spacing: 0.1em; padding-top: 0.2rem; white-space: nowrap; }
.blog-readtime { font-family: 'VT323', monospace; font-size: 0.78rem; color: var(--text-dim); letter-spacing: 0.08em; opacity: 0.7; }
.blog-title { font-family: 'IM Fell English', serif; font-size: 1.05rem; color: var(--text); margin-bottom: 0.3rem; transition: color 0.2s; }
.blog-entry:hover .blog-title { color: var(--green); }
.blog-summary { font-style: italic; font-size: 0.88rem; color: var(--text-dim); }

/* ── Projects ── */
.project-list { display: flex; flex-direction: column; gap: 1rem; }
.project-item {
  border: 1px solid var(--border); padding: 1.3rem 1.5rem;
  background: var(--bg-panel); display: grid;
  grid-template-columns: 1fr auto; gap: 1.5rem; align-items: center;
  transition: border-color 0.2s, background 0.2s;
}
.project-item:hover { border-color: var(--border-mid); background: rgba(0,200,80,0.02); }
.project-name { font-family: 'VT323', monospace; font-size: 1.25rem; color: var(--green); margin-bottom: 0.25rem; letter-spacing: 0.04em; }
.project-name::before { content: '$ '; color: var(--green-dim); }
.project-desc { font-style: italic; font-size: 0.9rem; color: var(--text-dim); }
.project-meta { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; }
.tags { display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }
.tag { font-family: 'VT323', monospace; font-size: 0.8rem; padding: 0.05rem 0.4rem; border: 1px solid var(--border); color: var(--text-dim); letter-spacing: 0.1em; }
.project-link { font-family: 'VT323', monospace; font-size: 0.9rem; color: var(--text-dim); text-decoration: none; letter-spacing: 0.12em; white-space: nowrap; transition: color 0.2s; }
.project-link::before { content: '► '; font-size: 0.75em; }
.project-link:hover { color: var(--green); }

/* ── Contact ── */
.contact-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(185px, 1fr)); gap: 1rem; }
.contact-link { border: 1px solid var(--border); padding: 1rem 1.25rem; background: var(--bg-panel); display: flex; align-items: center; gap: 0.75rem; text-decoration: none; transition: all 0.2s; }
.contact-link:hover { border-color: var(--border-mid); background: var(--green-glow); }
.contact-icon { font-family: 'VT323', monospace; font-size: 1.15rem; color: var(--green-dim); line-height: 1; }
.contact-label { font-family: 'VT323', monospace; font-size: 1.05rem; color: var(--text); letter-spacing: 0.12em; }

/* ── Post / prose pages ── */
.post-wrap { max-width: 680px; margin: 0 auto; padding: 7rem 5vw 5rem; }
.post-header { margin-bottom: 2.5rem; }
.post-kicker { font-family: 'VT323', monospace; font-size: 0.85rem; color: var(--text-dim); letter-spacing: 0.2em; margin-bottom: 0.5rem; }
.post-title { font-family: 'IM Fell English', serif; font-size: clamp(2rem, 6vw, 3.2rem); color: var(--green); line-height: 1.12; margin-bottom: 0.75rem; text-shadow: 0 0 18px rgba(0,220,80,0.2); }
.post-meta { font-family: 'VT323', monospace; font-size: 0.88rem; color: var(--text-dim); letter-spacing: 0.12em; }
.post-divider { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
.post-body { font-size: 1.05rem; line-height: 1.85; color: var(--text); }
.post-body p  { margin-bottom: 1.4rem; }
.post-body h2 { font-family: 'VT323', monospace; font-size: 1.6rem; color: var(--green); letter-spacing: 0.06em; margin: 2.2rem 0 0.8rem; }
.post-body h3 { font-family: 'VT323', monospace; font-size: 1.25rem; color: var(--green-dim); letter-spacing: 0.06em; margin: 1.8rem 0 0.6rem; }
.post-body em { color: var(--green-hi); font-style: italic; }
.post-body strong { color: var(--green); font-weight: bold; }
.post-body a { color: var(--green); text-decoration: underline; text-underline-offset: 3px; }
.post-body code { font-family: 'VT323', monospace; font-size: 1rem; color: var(--green-hi); background: var(--bg-panel); padding: 0.1em 0.35em; border: 1px solid var(--border); }
.post-body pre { background: var(--bg-panel); border: 1px solid var(--border); padding: 1.25rem; margin: 1.5rem 0; overflow-x: auto; }
.post-body pre code { background: none; border: none; padding: 0; font-size: 0.92rem; }
.post-body blockquote { border-left: 3px solid var(--green-dim); padding-left: 1.25rem; margin: 1.5rem 0; color: var(--text-dim); font-style: italic; }
.post-thoughts {
  border-left: 3px solid var(--green-dim); background: var(--bg-panel2);
  padding: 1.1rem 1.4rem; margin: 2rem 0 2.5rem;
}
.post-thoughts-label {
  font-family: 'VT323', monospace; font-size: 0.78rem; color: var(--green-dim);
  letter-spacing: 0.22em; margin-bottom: 0.6rem;
}
.post-thoughts p {
  font-style: italic; font-size: 0.95rem; color: var(--text-dim); line-height: 1.75; margin: 0;
}
.post-footer { margin-top: 3.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }
.back-link { font-family: 'VT323', monospace; font-size: 1rem; color: var(--text-dim); text-decoration: none; letter-spacing: 0.12em; transition: color 0.2s; }
.back-link::before { content: '◄ '; }
.back-link:hover { color: var(--green); }

/* ── Footer ── */
footer { border-top: 1px solid var(--border); padding: 2rem 5vw; text-align: center; font-family: 'VT323', monospace; font-size: 0.9rem; color: var(--text-dim); letter-spacing: 0.15em; }
footer .rune-line { margin-bottom: 0.5rem; color: var(--border-mid); }

/* ── Scroll reveal ── */
.reveal { opacity: 0; transform: translateY(16px); transition: opacity 0.55s ease, transform 0.55s ease; }
.reveal.visible { opacity:1; transform:translateY(0); }

/* ── Mobile ── */
@media (max-width: 620px) {
  nav { padding: 0 1.25rem; }
  .nav-links { display:none; flex-direction:column; gap:0; position:fixed; top:52px; left:0; width:100%; background:rgba(1,9,1,0.97); border-bottom:1px solid var(--border); }
  .nav-links.open { display:flex; }
  .nav-links li a { display:block; padding:0.9rem 1.5rem; border-bottom:1px solid var(--border); font-size:1.2rem; }
  .nav-hamburger { display:flex; }
  #hero { padding: 6rem 1.5rem 3.5rem; }
  .section-wrap { padding: 3.5rem 1.5rem; }
  .about-layout { grid-template-columns: 1fr; }
  .blog-entry { grid-template-columns: 1fr; gap: 0.2rem; }
  .project-item { grid-template-columns: 1fr; }
  .project-meta { align-items: flex-start; }
  .tags { justify-content: flex-start; }
  .post-wrap { padding: 5.5rem 1.5rem 3rem; }
}

/* ── Theme: Amber phosphor ── */
html.theme-amber {
  --bg: #0e0900; --bg-solid: #0e0900;
  --bg-panel: #160c00; --bg-panel2: #1c1100;
  --green: #ffb000; --green-hi: #ffd060;
  --green-dim: #8a5a00; --green-faint: #1c0f00;
  --green-glow: rgba(200,130,0,0.08);
  --text: #cc8800; --text-dim: #8a6000;
  --border: #2e1800; --border-mid: #5c3200;
}
/* Typewriter font stack replaces VT323 + IM Fell */
html.theme-amber body { font-family: 'Courier Prime', 'Courier New', monospace; }
html.theme-amber .nav-logo,
html.theme-amber .nav-links a,
html.theme-amber .section-label,
html.theme-amber .section-sub,
html.theme-amber .hero-sys,
html.theme-amber .hero-subtitle,
html.theme-amber .hero-after,
html.theme-amber .btn,
html.theme-amber .hero-quest,
html.theme-amber .card-tag,
html.theme-amber .card-title,
html.theme-amber .card-link,
html.theme-amber .blog-date,
html.theme-amber .stat-name,
html.theme-amber .stat-val,
html.theme-amber .project-name,
html.theme-amber .project-link,
html.theme-amber .back-link,
html.theme-amber .post-kicker,
html.theme-amber .post-meta,
html.theme-amber .post-thoughts-label,
html.theme-amber .contact-label,
html.theme-amber .contact-icon,
html.theme-amber footer { font-family: 'Courier Prime', 'Courier New', monospace; }
html.theme-amber .hero-name {
  font-family: 'Courier Prime', monospace;
  font-size: clamp(2.8rem, 9vw, 7rem);
  font-weight: 700; letter-spacing: 0.04em; line-height: 0.95;
}
html.theme-amber .hero-quest { font-style: italic; letter-spacing: 0.02em; }
html.theme-amber .section-label { font-size: 2rem; letter-spacing: 0.04em; }
/* No phosphor glow — typewriters don't shine */
html.theme-amber .hero-name,
html.theme-amber .section-label,
html.theme-amber .nav-logo,
html.theme-amber .post-title { text-shadow: none; }
html.theme-amber .post-title { font-family: 'Courier Prime', monospace; font-size: clamp(1.8rem, 5vw, 2.8rem); }
/* No scan lines — paper feel */
html.theme-amber body::before { background: none; }
html.theme-amber body::after { background: radial-gradient(ellipse at 50% 38%, transparent 65%, rgba(0,0,0,0.45) 100%); }
/* Heavier borders, solid print feel */
html.theme-amber .char-sheet,
html.theme-amber .writing-card,
html.theme-amber .project-item,
html.theme-amber .contact-link { border-width: 2px; }
html.theme-amber .writing-card::before { display: none; }
html.theme-amber .btn { letter-spacing: 0.06em; }
html.theme-amber .char-sheet::before { font-family: 'Courier Prime', monospace; letter-spacing: 0.1em; }
html.theme-amber .stat-name { font-family: 'Courier Prime', monospace; font-size: 0.68rem; letter-spacing: 0.03em; }
html.theme-amber .stat-val  { font-family: 'Courier Prime', monospace; font-size: 0.8rem; }

/* ── Theme: Cyan grimdark ── */
html.theme-cyan {
  --bg: #060f14; --bg-solid: #060f14;
  --bg-panel: #0a1a20; --bg-panel2: #0d2028;
  --green: #2dd4d4; --green-hi: #4affff;
  --green-dim: #1a6b7a; --green-faint: #0a1f25;
  --green-glow: rgba(45,212,212,0.08);
  --text: #4da8b8; --text-dim: #2d7a8a;
  --border: #0f3a47; --border-mid: #1a5a6a;
}
/* Orbitron for display, Share Tech Mono for everything else */
html.theme-cyan body { font-family: 'Share Tech Mono', monospace; line-height: 1.65; }
html.theme-cyan .hero-name {
  font-family: 'Orbitron', sans-serif;
  font-size: clamp(2.2rem, 6.5vw, 5.2rem);
  font-weight: 700; letter-spacing: 0.1em; line-height: 1.05;
}
html.theme-cyan .section-label {
  font-family: 'Orbitron', sans-serif;
  font-size: 1.4rem; letter-spacing: 0.14em; font-weight: 700;
}
html.theme-cyan .nav-logo { font-family: 'Orbitron', sans-serif; font-size: 0.9rem; letter-spacing: 0.18em; }
html.theme-cyan .card-title { font-family: 'Orbitron', sans-serif; font-size: 1rem; letter-spacing: 0.06em; }
html.theme-cyan .post-title { font-family: 'Orbitron', sans-serif; font-size: clamp(1.5rem, 4vw, 2.4rem); letter-spacing: 0.08em; }
html.theme-cyan .nav-links a,
html.theme-cyan .hero-sys,
html.theme-cyan .hero-subtitle,
html.theme-cyan .hero-after,
html.theme-cyan .btn,
html.theme-cyan .section-sub,
html.theme-cyan .card-tag,
html.theme-cyan .card-link,
html.theme-cyan .blog-date,
html.theme-cyan .stat-name,
html.theme-cyan .stat-val,
html.theme-cyan .project-name,
html.theme-cyan .project-link,
html.theme-cyan .back-link,
html.theme-cyan .post-kicker,
html.theme-cyan .post-meta,
html.theme-cyan .post-thoughts-label,
html.theme-cyan .contact-label,
html.theme-cyan .contact-icon,
html.theme-cyan footer { font-family: 'Share Tech Mono', monospace; }
html.theme-cyan .hero-quest { font-family: 'Share Tech Mono', monospace; font-style: normal; letter-spacing: 0.08em; }
html.theme-cyan .hero-subtitle { letter-spacing: 0.3em; }
html.theme-cyan .btn { letter-spacing: 0.18em; }
/* Tinted blue scan lines instead of dark */
html.theme-cyan body::before {
  background: repeating-linear-gradient(
    0deg, rgba(0,50,80,0.18) 0px, rgba(0,50,80,0.18) 1px,
    transparent 1px, transparent 3px
  );
}
/* Sharper vignette for grimdark feel */
html.theme-cyan body::after {
  background: radial-gradient(ellipse at 50% 38%, transparent 40%, rgba(0,0,0,0.88) 100%);
}
/* Tighter border styling — angular, clinical */
html.theme-cyan .writing-card,
html.theme-cyan .project-item,
html.theme-cyan .char-sheet,
html.theme-cyan .contact-link { border-style: solid; }
html.theme-cyan .char-sheet::before { font-family: 'Share Tech Mono', monospace; }
html.theme-cyan .post-thoughts-label { font-family: 'Share Tech Mono', monospace; }
html.theme-cyan .stat-name { font-family: 'Share Tech Mono', monospace; font-size: 0.68rem; letter-spacing: 0.03em; }
html.theme-cyan .stat-val  { font-family: 'Share Tech Mono', monospace; font-size: 0.8rem; }

/* ── Theme: Medieval parchment ── */
html.theme-medieval {
  --bg: #f2e8cb; --bg-solid: #f2e8cb;
  --bg-panel: #e8dab8; --bg-panel2: #ddd0a2;
  --green: #2e6b20; --green-hi: #1a4f14;
  --green-dim: #6a8840; --green-faint: #d4e8c0;
  --green-glow: rgba(46,107,32,0.07);
  --text: #1a0c00; --text-dim: #5a3820;
  --border: #bfa068; --border-mid: #8a6030;
}
html.theme-medieval body { font-family: 'IM Fell English', Georgia, serif; }
html.theme-medieval nav {
  background: rgba(242,232,203,0.97);
  border-bottom-color: var(--border);
}
html.theme-medieval .nav-hamburger span { background: var(--text-dim); }
html.theme-medieval .nav-logo,
html.theme-medieval .nav-links a,
html.theme-medieval .section-label,
html.theme-medieval .section-sub,
html.theme-medieval .hero-sys,
html.theme-medieval .hero-subtitle,
html.theme-medieval .hero-after,
html.theme-medieval .btn,
html.theme-medieval .card-tag,
html.theme-medieval .card-link,
html.theme-medieval .blog-date,
html.theme-medieval .stat-name,
html.theme-medieval .stat-val,
html.theme-medieval .project-name,
html.theme-medieval .project-link,
html.theme-medieval .back-link,
html.theme-medieval .post-kicker,
html.theme-medieval .post-meta,
html.theme-medieval .post-thoughts-label,
html.theme-medieval .contact-label,
html.theme-medieval .contact-icon,
html.theme-medieval .post-body h2,
html.theme-medieval .post-body h3,
html.theme-medieval footer { font-family: 'Cinzel', Georgia, serif; }
html.theme-medieval .hero-name {
  font-family: 'Cinzel', serif;
  font-size: clamp(3rem, 10vw, 7.5rem);
  font-weight: 700; letter-spacing: 0.06em; line-height: 0.92;
}
html.theme-medieval .hero-quest { font-style: italic; letter-spacing: 0.01em; }
html.theme-medieval .section-label { font-size: 1.8rem; letter-spacing: 0.1em; font-weight: 700; }
html.theme-medieval .card-title { font-family: 'Cinzel', serif; font-size: 1.15rem; letter-spacing: 0.04em; }
html.theme-medieval .post-title {
  font-family: 'Cinzel', serif;
  font-size: clamp(1.8rem, 5vw, 3rem); letter-spacing: 0.06em;
}
/* Ink on parchment is silent — no glows */
html.theme-medieval .hero-name,
html.theme-medieval .section-label,
html.theme-medieval .nav-logo,
html.theme-medieval .hero-quest,
html.theme-medieval .post-title { text-shadow: none; }
html.theme-medieval .nav-links a:hover { text-shadow: none; }
html.theme-medieval .btn:hover { box-shadow: none; text-shadow: none; }
/* Subtle vertical parchment grain */
html.theme-medieval body::before {
  background: repeating-linear-gradient(
    90deg, rgba(100,60,10,0.02) 0px, rgba(100,60,10,0.02) 1px,
    transparent 1px, transparent 12px
  );
}
/* Brown edge vignette — aged parchment */
html.theme-medieval body::after {
  background: radial-gradient(ellipse at 50% 38%, transparent 55%, rgba(80,40,0,0.28) 100%);
}
html.theme-medieval #wrap { animation: none; }
html.theme-medieval .char-sheet,
html.theme-medieval .writing-card,
html.theme-medieval .project-item,
html.theme-medieval .contact-link { border-width: 2px; }
html.theme-medieval .theme-dot.active { outline-color: rgba(0,0,0,0.3); }
html.theme-medieval .btn::before { content: '⚔'; }
html.theme-medieval .project-name::before { content: '⚜ '; }
html.theme-medieval .char-sheet::before { content: '⚜ CHARACTER ⚜'; font-family: 'Cinzel', serif; letter-spacing: 0.12em; }
html.theme-medieval .stat-name { font-family: 'Cinzel', serif; font-size: 0.65rem; letter-spacing: 0.08em; }
html.theme-medieval .stat-val  { font-family: 'Cinzel', serif; font-size: 0.9rem; }
@media (max-width: 620px) {
  html.theme-medieval .nav-links { background: rgba(242,232,203,0.99); }
}

/* ── Theme: Pirate worn parchment ── */
html.theme-pirate {
  --bg: #06080e; --bg-solid: #06080e;
  --bg-panel: #0a1018; --bg-panel2: #0e1620;
  --green: #4a9880; --green-hi: #65b5a0;
  --green-dim: #2d6858; --green-faint: #0b1010;
  --green-glow: rgba(74,152,128,0.12);
  --text: #9e9878; --text-dim: #4a7a6a;
  --border: #101a22; --border-mid: #1e3840;
}
html.theme-pirate body { font-family: 'IM Fell English', Georgia, serif; }
html.theme-pirate .nav-logo,
html.theme-pirate .nav-links a,
html.theme-pirate .section-label,
html.theme-pirate .section-sub,
html.theme-pirate .hero-sys,
html.theme-pirate .hero-subtitle,
html.theme-pirate .hero-after,
html.theme-pirate .btn,
html.theme-pirate .card-tag,
html.theme-pirate .card-link,
html.theme-pirate .blog-date,
html.theme-pirate .stat-name,
html.theme-pirate .stat-val,
html.theme-pirate .project-name,
html.theme-pirate .project-link,
html.theme-pirate .back-link,
html.theme-pirate .post-kicker,
html.theme-pirate .post-meta,
html.theme-pirate .post-thoughts-label,
html.theme-pirate .contact-label,
html.theme-pirate .contact-icon,
html.theme-pirate .post-body h2,
html.theme-pirate .post-body h3,
html.theme-pirate footer { font-family: 'Pirata One', cursive; }
/* Hero name stays treasure gold — everything else is sea-worn verdigris */
html.theme-pirate .hero-name {
  font-family: 'Pirata One', cursive;
  font-size: clamp(3.5rem, 11vw, 9rem);
  font-weight: 400; letter-spacing: 0.03em; line-height: 0.90;
  color: #9e9878; text-shadow: none;
}
html.theme-pirate .hero-quest {
  font-family: 'IM Fell English', serif; font-style: italic;
  color: #9e9878; text-shadow: none;
}
html.theme-pirate .section-label { font-family: 'Pirata One', cursive; font-size: 2.2rem; letter-spacing: 0.04em; }
html.theme-pirate .card-title { font-family: 'Pirata One', cursive; font-size: 1.3rem; }
html.theme-pirate .post-title {
  font-family: 'Pirata One', cursive;
  font-size: clamp(2rem, 6vw, 3.5rem); letter-spacing: 0.03em;
}
/* Sea-green verdigris glows for chrome elements */
html.theme-pirate .section-label,
html.theme-pirate .nav-logo { text-shadow: 0 0 14px rgba(74,152,128,0.30); }
html.theme-pirate .post-title { text-shadow: 0 0 12px rgba(74,152,128,0.22); }
html.theme-pirate .nav-links a:hover { text-shadow: 0 0 8px rgba(74,152,128,0.5); }
html.theme-pirate .btn:hover {
  box-shadow: 0 0 16px rgba(74,152,128,0.18);
  text-shadow: 0 0 8px rgba(74,152,128,0.5);
}
/* Override hardcoded green rgba hover backgrounds from base CSS */
html.theme-pirate .writing-card:hover { background: rgba(74,152,128,0.03); }
html.theme-pirate .project-item:hover { background: rgba(74,152,128,0.03); }
/* Subtle nautical chart crosshatch — old navigation grid */
html.theme-pirate body::before {
  background:
    repeating-linear-gradient(45deg, rgba(20,50,70,0.06) 0px, rgba(20,50,70,0.06) 1px, transparent 1px, transparent 40px),
    repeating-linear-gradient(-45deg, rgba(20,50,70,0.06) 0px, rgba(20,50,70,0.06) 1px, transparent 1px, transparent 40px);
}
/* Heavy vignette — lantern in a dark ship's hold */
html.theme-pirate body::after {
  background: radial-gradient(ellipse at 50% 38%, transparent 40%, rgba(0,0,0,0.88) 100%);
}
html.theme-pirate #wrap { animation: none; }
html.theme-pirate .char-sheet,
html.theme-pirate .writing-card,
html.theme-pirate .project-item,
html.theme-pirate .contact-link { border-width: 2px; }
html.theme-pirate .btn::before { content: '⚓'; }
html.theme-pirate .project-name::before { content: '☠ '; }
html.theme-pirate .char-sheet::before { content: '☠ CHARACTER ☠'; font-family: 'Pirata One', cursive; letter-spacing: 0.1em; }
html.theme-pirate .stat-name { font-family: 'Pirata One', cursive; font-size: 0.78rem; letter-spacing: 0.04em; }
html.theme-pirate .stat-val  { font-family: 'Pirata One', cursive; font-size: 1rem; }

/* ── Theme: Typewriter ── */
html.theme-typewriter {
  --bg: #faf6ea; --bg-solid: #faf6ea;
  --bg-panel: #f2ece0; --bg-panel2: #e8e0d0;
  --green: #1a1208; --green-hi: #0d0a06;
  --green-dim: #5a4838; --green-faint: #ede5d0;
  --green-glow: rgba(26,18,8,0.05);
  --text: #2a1a0a; --text-dim: #6a5040;
  --border: #d0c0a8; --border-mid: #a88e70;
}
html.theme-typewriter body { font-family: 'Special Elite', 'Courier New', monospace; line-height: 1.9; }
html.theme-typewriter nav {
  background: rgba(250,246,234,0.97);
  border-bottom-color: var(--border);
}
html.theme-typewriter .nav-hamburger span { background: var(--text-dim); }
html.theme-typewriter .nav-logo,
html.theme-typewriter .nav-links a,
html.theme-typewriter .section-label,
html.theme-typewriter .section-sub,
html.theme-typewriter .hero-sys,
html.theme-typewriter .hero-subtitle,
html.theme-typewriter .hero-after,
html.theme-typewriter .btn,
html.theme-typewriter .card-tag,
html.theme-typewriter .card-link,
html.theme-typewriter .blog-date,
html.theme-typewriter .stat-name,
html.theme-typewriter .stat-val,
html.theme-typewriter .project-name,
html.theme-typewriter .project-link,
html.theme-typewriter .back-link,
html.theme-typewriter .post-kicker,
html.theme-typewriter .post-meta,
html.theme-typewriter .post-thoughts-label,
html.theme-typewriter .contact-label,
html.theme-typewriter .contact-icon,
html.theme-typewriter .post-body h2,
html.theme-typewriter .post-body h3,
html.theme-typewriter footer { font-family: 'Special Elite', 'Courier New', monospace; }
html.theme-typewriter .hero-name {
  font-family: 'Special Elite', monospace;
  font-size: clamp(2.8rem, 9vw, 7rem);
  font-weight: 400; letter-spacing: 0.04em; line-height: 0.96;
}
html.theme-typewriter .hero-quest { font-family: 'Special Elite', monospace; font-style: normal; letter-spacing: 0.02em; }
html.theme-typewriter .section-label { font-size: 2rem; letter-spacing: 0.06em; }
html.theme-typewriter .card-title { font-family: 'Special Elite', monospace; font-size: 1.2rem; letter-spacing: 0.02em; }
html.theme-typewriter .post-title {
  font-family: 'Special Elite', monospace;
  font-size: clamp(1.8rem, 5vw, 2.9rem); letter-spacing: 0.04em;
}
/* Ink on paper makes no light */
html.theme-typewriter .hero-name,
html.theme-typewriter .section-label,
html.theme-typewriter .nav-logo,
html.theme-typewriter .hero-quest,
html.theme-typewriter .post-title { text-shadow: none; }
html.theme-typewriter .nav-links a:hover { text-shadow: none; }
html.theme-typewriter .btn:hover { box-shadow: none; text-shadow: none; }
/* Ruled paper lines — standard typewriter sheet */
html.theme-typewriter body::before {
  background: repeating-linear-gradient(
    0deg, rgba(150,120,80,0.07) 0px, rgba(150,120,80,0.07) 1px,
    transparent 1px, transparent 28px
  );
}
/* Gentle sepia aging at the paper edges */
html.theme-typewriter body::after {
  background: radial-gradient(ellipse at 50% 38%, transparent 58%, rgba(60,30,0,0.18) 100%);
}
html.theme-typewriter #wrap { animation: none; }
html.theme-typewriter .char-sheet,
html.theme-typewriter .writing-card,
html.theme-typewriter .project-item,
html.theme-typewriter .contact-link { border-width: 2px; }
html.theme-typewriter .theme-dot.active { outline-color: rgba(0,0,0,0.3); }
html.theme-typewriter .btn::before { content: '↳'; }
html.theme-typewriter .project-name::before { content: '§ '; }
html.theme-typewriter .char-sheet::before { content: '-- CHARACTER --'; font-family: 'Special Elite', monospace; letter-spacing: 0.08em; }
html.theme-typewriter .stat-name { font-family: 'Special Elite', monospace; font-size: 0.7rem; letter-spacing: 0.04em; }
html.theme-typewriter .stat-val  { font-family: 'Special Elite', monospace; font-size: 0.88rem; }
@media (max-width: 620px) {
  html.theme-typewriter .nav-links { background: rgba(250,246,234,0.99); }
}

/* ── Theme: Typewriter dark ── */
html.theme-typewriter-dark {
  --bg: #0e0c0a; --bg-solid: #0e0c0a;
  --bg-panel: #181410; --bg-panel2: #201c16;
  --green: #ddd0b0; --green-hi: #f0e8c8;
  --green-dim: #7a7058; --green-faint: #181410;
  --green-glow: rgba(220,208,176,0.06);
  --text: #b8aa88; --text-dim: #7a7058;
  --border: #282018; --border-mid: #4a4030;
}
html.theme-typewriter-dark body { font-family: 'Special Elite', 'Courier New', monospace; line-height: 1.9; }
html.theme-typewriter-dark .nav-logo,
html.theme-typewriter-dark .nav-links a,
html.theme-typewriter-dark .section-label,
html.theme-typewriter-dark .section-sub,
html.theme-typewriter-dark .hero-sys,
html.theme-typewriter-dark .hero-subtitle,
html.theme-typewriter-dark .hero-after,
html.theme-typewriter-dark .btn,
html.theme-typewriter-dark .card-tag,
html.theme-typewriter-dark .card-link,
html.theme-typewriter-dark .blog-date,
html.theme-typewriter-dark .stat-name,
html.theme-typewriter-dark .stat-val,
html.theme-typewriter-dark .project-name,
html.theme-typewriter-dark .project-link,
html.theme-typewriter-dark .back-link,
html.theme-typewriter-dark .post-kicker,
html.theme-typewriter-dark .post-meta,
html.theme-typewriter-dark .post-thoughts-label,
html.theme-typewriter-dark .contact-label,
html.theme-typewriter-dark .contact-icon,
html.theme-typewriter-dark .post-body h2,
html.theme-typewriter-dark .post-body h3,
html.theme-typewriter-dark footer { font-family: 'Special Elite', 'Courier New', monospace; }
html.theme-typewriter-dark .hero-name {
  font-family: 'Special Elite', monospace;
  font-size: clamp(2.8rem, 9vw, 7rem);
  font-weight: 400; letter-spacing: 0.04em; line-height: 0.96;
}
html.theme-typewriter-dark .hero-quest { font-family: 'Special Elite', monospace; font-style: normal; letter-spacing: 0.02em; }
html.theme-typewriter-dark .section-label { font-size: 2rem; letter-spacing: 0.06em; }
html.theme-typewriter-dark .card-title { font-family: 'Special Elite', monospace; font-size: 1.2rem; letter-spacing: 0.02em; }
html.theme-typewriter-dark .post-title {
  font-family: 'Special Elite', monospace;
  font-size: clamp(1.8rem, 5vw, 2.9rem); letter-spacing: 0.04em;
}
html.theme-typewriter-dark .hero-name,
html.theme-typewriter-dark .section-label,
html.theme-typewriter-dark .nav-logo,
html.theme-typewriter-dark .hero-quest,
html.theme-typewriter-dark .post-title { text-shadow: none; }
html.theme-typewriter-dark .nav-links a:hover { text-shadow: none; }
html.theme-typewriter-dark .btn:hover { box-shadow: none; text-shadow: none; }
/* Faint ruled lines, barely visible on dark paper */
html.theme-typewriter-dark body::before {
  background: repeating-linear-gradient(
    0deg, rgba(200,180,140,0.04) 0px, rgba(200,180,140,0.04) 1px,
    transparent 1px, transparent 28px
  );
}
html.theme-typewriter-dark body::after {
  background: radial-gradient(ellipse at 50% 38%, transparent 55%, rgba(0,0,0,0.75) 100%);
}
html.theme-typewriter-dark #wrap { animation: none; }
html.theme-typewriter-dark .char-sheet,
html.theme-typewriter-dark .writing-card,
html.theme-typewriter-dark .project-item,
html.theme-typewriter-dark .contact-link { border-width: 2px; }
html.theme-typewriter-dark .btn::before { content: '↳'; }
html.theme-typewriter-dark .project-name::before { content: '§ '; }
html.theme-typewriter-dark .char-sheet::before { content: '-- CHARACTER --'; font-family: 'Special Elite', monospace; letter-spacing: 0.08em; }
html.theme-typewriter-dark .stat-name { font-family: 'Special Elite', monospace; font-size: 0.7rem; letter-spacing: 0.04em; }
html.theme-typewriter-dark .stat-val  { font-family: 'Special Elite', monospace; font-size: 0.88rem; }

/* ── Theme picker ── */
.theme-picker { display: flex; gap: 0.5rem; align-items: center; margin-left: 1rem; }
.theme-dot {
  width: 10px; height: 10px; border-radius: 50%; cursor: pointer;
  border: 1px solid rgba(255,255,255,0.12); padding: 0;
  transition: transform 0.15s, box-shadow 0.15s;
}
.theme-dot:hover { transform: scale(1.4); }
.theme-dot.active { transform: scale(1.3); outline: 1px solid rgba(255,255,255,0.4); outline-offset: 2px; }
.theme-dot[data-theme="theme-green"]    { background: #00e060; }
.theme-dot[data-theme="theme-amber"]    { background: #ffb000; }
.theme-dot[data-theme="theme-cyan"]     { background: #2dd4d4; }
.theme-dot[data-theme="theme-medieval"]    { background: #3a7525; }
.theme-dot[data-theme="theme-pirate"]      { background: #4a9880; }
.theme-dot[data-theme="theme-typewriter"]       { background: #d4c090; }
.theme-dot[data-theme="theme-typewriter-dark"]  { background: #b8aa88; }
"""

SHARED_HEAD = """
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=VT323&family=IM+Fell+English:ital@0;1&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Orbitron:wght@400;700&family=Share+Tech+Mono&family=Cinzel:wght@400;700&family=Pirata+One&family=Special+Elite&display=swap" rel="stylesheet">
  <script>(function(){document.documentElement.classList.add(localStorage.getItem('site-theme')||'theme-typewriter');})();</script>
"""

NAV_JS = """
const ham = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');
if (ham) {
  ham.addEventListener('click', () => navLinks.classList.toggle('open'));
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => navLinks.classList.remove('open')));
}
const revealObs = new IntersectionObserver((entries) => {
  entries.forEach((e, i) => {
    if (e.isIntersecting) { setTimeout(() => e.target.classList.add('visible'), i * 90); revealObs.unobserve(e.target); }
  });
}, { threshold: 0.06 });
document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));
document.getElementById('yr').textContent = new Date().getFullYear();
const THEMES = ['theme-green', 'theme-amber', 'theme-cyan', 'theme-medieval', 'theme-pirate', 'theme-typewriter', 'theme-typewriter-dark'];
function applyTheme(t) {
  document.documentElement.classList.remove(...THEMES);
  document.documentElement.classList.add(t);
  document.querySelectorAll('.theme-dot').forEach(d => d.classList.toggle('active', d.dataset.theme === t));
  localStorage.setItem('site-theme', t);
}
applyTheme(localStorage.getItem('site-theme') || 'theme-typewriter');
document.querySelectorAll('.theme-dot').forEach(d => d.addEventListener('click', () => applyTheme(d.dataset.theme)));
"""

TYPEWRITER_JS = """
const phrases = [
  "Teller of tales. Conjurer of code.",
  "Words by night. Code by day.",
  "Born of the '80s. Shaped by the screen.",
  "Stories for those who stayed up past midnight.",
  "Wandering the frontier between page and program.",
];
let pIdx = 0, cIdx = 0, deleting = false;
const typed = document.getElementById('typed');
function tick() {
  const phrase = phrases[pIdx];
  if (!deleting) {
    typed.textContent = phrase.slice(0, ++cIdx);
    if (cIdx === phrase.length) { deleting = true; setTimeout(tick, 2600); return; }
  } else {
    typed.textContent = phrase.slice(0, --cIdx);
    if (cIdx === 0) { deleting = false; pIdx = (pIdx + 1) % phrases.length; }
  }
  setTimeout(tick, deleting ? 36 : 58);
}
tick();
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_file(path: Path) -> tuple[dict, str]:
    """Return (front_matter_dict, body_text) from a Markdown file."""
    raw = path.read_text(encoding="utf-8")
    front, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                front = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                print(f"  ⚠  YAML error in {path}: {e}")
            body = parts[2].lstrip("\n")
    return front, body


def render_md(text: str) -> str:
    return md_lib.markdown(text, extensions=["fenced_code", "tables"])


def word_stats(body: str) -> tuple[int, str]:
    """Return (word_count, read_time_str) for a markdown body."""
    text = re.sub(r'```.*?```', ' ', body, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[#*_~>|]', ' ', text)
    wc = len(text.split())
    minutes = max(1, round(wc / 200))
    return wc, f"{minutes} min read"


def slugify(path: Path) -> str:
    """Strip leading YYYY-MM-DD- from filename to get URL slug."""
    name = path.stem
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return name


def fmt_date(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.strftime("YE %Y / %B").upper()
    return str(d).upper()


def fmt_date_iso(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def nav_html(root_prefix="") -> str:
    return f"""
<nav>
  <a class="nav-logo" href="{root_prefix}index.html"><span>✦</span>JUSTIN GAYLOR</a>
  <ul class="nav-links" id="nav-links">
    <li><a href="{root_prefix}index.html#about">GREETINGS</a></li>
    <li><a href="{root_prefix}index.html#writing">TALES</a></li>
    <li><a href="{root_prefix}index.html#blog">CHRONICLE</a></li>
    <li><a href="{root_prefix}index.html#projects">CRAFTS</a></li>
    <li><a href="{root_prefix}index.html#contact">CONTACT</a></li>
  </ul>
  <div class="theme-picker" aria-label="Theme">
    <button class="theme-dot" data-theme="theme-green"    title="Green phosphor"></button>
    <button class="theme-dot" data-theme="theme-amber"    title="Amber phosphor"></button>
    <button class="theme-dot" data-theme="theme-cyan"     title="Cyan grimdark"></button>
    <button class="theme-dot" data-theme="theme-medieval" title="Medieval parchment"></button>
    <button class="theme-dot" data-theme="theme-pirate"      title="Pirate parchment"></button>
    <button class="theme-dot" data-theme="theme-typewriter"      title="Typewriter"></button>
    <button class="theme-dot" data-theme="theme-typewriter-dark" title="Typewriter (dark)"></button>
  </div>
  <button class="nav-hamburger" id="hamburger" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
</nav>"""


def footer_html() -> str:
    return f"""
<footer>
  <p class="rune-line">✦ ─────────────────────── ✦</p>
  <p>JUSTIN GAYLOR &nbsp;·&nbsp; <span id="yr"></span> &nbsp;·&nbsp; NO DARK MAGIC. NO TRACKING SPELLS.</p>
</footer>"""


def page_shell(title: str, body: str, extra_js: str = "", root_prefix: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{SHARED_HEAD}
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
<div id="wrap">
{nav_html(root_prefix)}
{body}
{footer_html()}
</div>
<script>
{NAV_JS}
{extra_js}
</script>
</body>
</html>"""


# ── Content loaders ────────────────────────────────────────────────────────────

def load_posts(folder: str) -> list[dict]:
    """Load all .md files from a content subfolder, sorted by date descending."""
    content_path = CONTENT_DIR / folder
    if not content_path.exists():
        return []
    posts = []
    for p in sorted(content_path.glob("*.md")):
        meta, body = parse_file(p)
        slug = slugify(p)
        wc, rt = word_stats(body)
        posts.append({
            "slug":    slug,
            "path":    p,
            "title":   meta.get("title", slug.replace("-", " ").title()),
            "date":    meta.get("date", date.today()),
            "summary": meta.get("summary", ""),
            "type":    meta.get("type", folder.rstrip("s").title()),
            "meta":    meta,
            "body":    body,
            "wc":      wc,
            "rt":      rt,
        })
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


def load_projects() -> list[dict]:
    path = CONTENT_DIR / "projects.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    pinned   = [p for p in data if p.get("pinned")]
    unpinned = [p for p in data if not p.get("pinned")]
    unpinned.sort(key=lambda x: x.get("date", date.today()), reverse=True)
    return pinned + unpinned


def load_about() -> str:
    path = CONTENT_DIR / "about.md"
    if not path.exists():
        return "<p>About copy coming soon.</p>"
    _, body = parse_file(path)
    return render_md(body)


# ── Page builders ──────────────────────────────────────────────────────────────

def build_index(stories: list, blog: list, projects: list, about_html: str):
    # About section
    char_stats_html = "\n".join(
        f'<div class="stat-row"><span class="stat-name">{k}</span>'
        f'<span class="stat-val">{v}</span></div>'
        for k, v in CHAR_STATS
    )

    # Stories section
    if stories:
        story_cards = "\n".join(f"""
        <div class="writing-card reveal">
          <p class="card-tag">{s['type'].upper()}</p>
          <h3 class="card-title">{s['title']}</h3>
          <p class="card-excerpt">{s['summary']}</p>
          <p class="card-readtime">{s['wc']:,} words &nbsp;·&nbsp; {s['rt']}</p>
          <a href="stories/{s['slug']}.html" class="card-link">READ THE SCROLL</a>
        </div>""" for s in stories)
    else:
        story_cards = '<p style="color:var(--text-dim);font-style:italic;">No tales yet. Check back soon.</p>'

    # Blog section
    if blog:
        blog_entries = "\n".join(f"""
        <a href="blog/{b['slug']}.html" class="blog-entry reveal">
          <div class="blog-date-col">
            <span class="blog-date">{fmt_date(b['date'])}</span>
            <span class="blog-readtime">{b['rt']}</span>
          </div>
          <div>
            <p class="blog-title">{b['title']}</p>
            <p class="blog-summary">{b['summary']}</p>
          </div>
        </a>""" for b in blog)
    else:
        blog_entries = '<p style="color:var(--text-dim);font-style:italic;">No dispatches yet.</p>'

    # Projects section
    if projects:
        def proj_html(p):
            tags = "".join(f'<span class="tag">{t}</span>' for t in p.get("tags", []))
            url  = p.get("url", "#")
            return f"""
        <div class="project-item reveal">
          <div>
            <p class="project-name">{p['name']}</p>
            <p class="project-desc">{p.get('description', '')}</p>
          </div>
          <div class="project-meta">
            <div class="tags">{tags}</div>
            <a href="{url}" target="_blank" class="project-link">GITHUB</a>
          </div>
        </div>"""
        project_items = "\n".join(proj_html(p) for p in projects)
    else:
        project_items = '<p style="color:var(--text-dim);font-style:italic;">Projects coming soon.</p>'

    body = f"""
<section id="hero">
  <p class="hero-sys">
    REALM OS v2.4 · SCRIBE TERMINAL ACTIVE<br>
    LOADING ADVENTURER PROFILE... <span style="color:var(--green)">DONE</span>
  </p>
  <h1 class="hero-name">JUSTIN<br>GAYLOR</h1>
  <p class="hero-subtitle">SCRIBE &nbsp;·&nbsp; ARTIFICER &nbsp;·&nbsp; WANDERER</p>
  <p class="hero-quest">Live each day like a quest.</p>
  <p class="hero-tagline"><span id="typed"></span><span class="cursor-blink"></span></p>
  <div class="hero-ctas">
    <a href="#writing" class="btn">TALES &amp; LORE</a>
    <a href="#projects" class="btn">THE WORKSHOP</a>
    <a href="#contact" class="btn">SEND RAVEN</a>
  </div>
  <p class="hero-after">✦ ─────────────────────────────── ✦</p>
</section>

<hr class="rule">

<div class="section-wrap" id="about">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>GREETINGS</h2>
    <p class="section-sub">WHO WALKS THESE PAGES</p>
  </div>
  <div class="about-layout">
    <div class="about-body reveal">{about_html}</div>
    <div class="char-sheet reveal">{char_stats_html}</div>
  </div>
</div>

<hr class="rule">

<div class="section-wrap" id="writing">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>TALES &amp; LORE</h2>
    <p class="section-sub">SHORT FICTION · ESSAYS · WRITINGS</p>
  </div>
  <div class="writing-grid">{story_cards}</div>
</div>

<hr class="rule">

<div class="section-wrap" id="blog">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>THE CHRONICLE</h2>
    <p class="section-sub">DISPATCHES FROM THE FIELD</p>
  </div>
  <div class="blog-list">{blog_entries}</div>
</div>

<hr class="rule">

<div class="section-wrap" id="projects">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>THE WORKSHOP</h2>
    <p class="section-sub">SOFTWARE · OPEN SOURCE · CREATIONS</p>
  </div>
  <div class="project-list">{project_items}</div>
</div>

<hr class="rule">

<div class="section-wrap" id="contact">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>SEND A RAVEN</h2>
    <p class="section-sub">WHERE TO FIND THE SCRIBE</p>
  </div>
  <div class="contact-grid reveal">
    <a href="mailto:{AUTHOR_EMAIL}" class="contact-link">
      <span class="contact-icon">✉</span><span class="contact-label">EMAIL</span>
    </a>
    <a href="{GITHUB_URL}" target="_blank" class="contact-link">
      <span class="contact-icon">⌥</span><span class="contact-label">GITHUB</span>
    </a>
    <a href="{BLUESKY_URL}" target="_blank" class="contact-link">
      <span class="contact-icon">◈</span><span class="contact-label">BLUESKY</span>
    </a>
    <a href="{LINKEDIN_URL}" target="_blank" class="contact-link">
      <span class="contact-icon">◉</span><span class="contact-label">LINKEDIN</span>
    </a>
    <a href="rss.xml" class="contact-link">
      <span class="contact-icon">◎</span><span class="contact-label">RSS SCROLL</span>
    </a>
  </div>
</div>"""

    return page_shell(
        title=f"{SITE_TITLE} — {SITE_TAGLINE}",
        body=body,
        extra_js=TYPEWRITER_JS,
        root_prefix=""
    )


def build_post_page(post: dict, section: str) -> str:
    """Build an individual story or blog post page."""
    root   = "../"
    kicker = f"{section.upper()} · {fmt_date(post['date'])}"
    if post.get("type"):
        kicker = f"{post['type'].upper()} · {fmt_date(post['date'])}"

    back_label = "BACK TO THE CHRONICLE" if section == "blog" else "BACK TO TALES &amp; LORE"
    back_href  = f"../index.html#blog" if section == "blog" else f"../index.html#writing"

    thoughts = post['meta'].get('thoughts', '')
    thoughts_html = f"""
  <aside class="post-thoughts">
    <p class="post-thoughts-label">✦ SCRIBE'S NOTE</p>
    <p>{thoughts}</p>
  </aside>""" if thoughts else ''

    body = f"""
<div class="post-wrap">
  <div class="post-header">
    <p class="post-kicker">{kicker}</p>
    <h1 class="post-title">{post['title']}</h1>
    <p class="post-meta">SCRIBED BY JUSTIN GAYLOR · {fmt_date_iso(post['date'])} · {post['wc']:,} WORDS · {post['rt'].upper()}</p>
  </div>
  <hr class="post-divider">{thoughts_html}
  <div class="post-body">
    {render_md(post['body'])}
  </div>
  <div class="post-footer">
    <a href="{back_href}" class="back-link">{back_label}</a>
  </div>
</div>"""

    return page_shell(
        title=f"{post['title']} — {SITE_TITLE}",
        body=body,
        root_prefix=root
    )


# ── Main build ─────────────────────────────────────────────────────────────────

def build():
    print("\n✦  Building site...\n")

    # Prepare dist folders
    DIST_DIR.mkdir(exist_ok=True)
    (DIST_DIR / "blog").mkdir(exist_ok=True)
    (DIST_DIR / "stories").mkdir(exist_ok=True)

    # Load content
    stories  = load_posts("stories")
    blog     = load_posts("blog")
    projects = load_projects()
    about    = load_about()

    print(f"  ► {len(stories)} stories")
    print(f"  ► {len(blog)} blog posts")
    print(f"  ► {len(projects)} projects")

    # Custom domain for GitHub Pages
    (DIST_DIR / "CNAME").write_text("gaylor.quest\n", encoding="utf-8")
    print(f"  ✓  dist/CNAME")

    # Build index
    (DIST_DIR / "index.html").write_text(
        build_index(stories, blog, projects, about), encoding="utf-8"
    )
    print(f"  ✓  dist/index.html")

    # Build story pages
    for post in stories:
        html = build_post_page(post, "stories")
        out  = DIST_DIR / "stories" / f"{post['slug']}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  ✓  dist/stories/{post['slug']}.html")

    # Build blog pages
    for post in blog:
        html = build_post_page(post, "blog")
        out  = DIST_DIR / "blog" / f"{post['slug']}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  ✓  dist/blog/{post['slug']}.html")

    print(f"\n✦  Done. Open dist/index.html in your browser.\n")


def watch():
    """Rebuild whenever content files change. Requires: pip install watchdog"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    class Rebuilder(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory and event.src_path.endswith((".md", ".yaml")):
                print(f"  ↻  Changed: {event.src_path}")
                build()

    build()
    observer = Observer()
    observer.schedule(Rebuilder(), str(CONTENT_DIR), recursive=True)
    observer.start()
    print("  👁  Watching content/ for changes. Ctrl-C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        build()
