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
    ("BACKGROUND", "SCRIBE"),
    ("SCHOOL",     "FICTION"),
    ("ORIGIN",     "MUNCIE, IN, USA"),
    ("ERA",        "BORN 1982"),
    ("ALIGNMENT",  "CHAOTIC GOOD"),
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
.blog-date { font-family: 'VT323', monospace; font-size: 0.88rem; color: var(--text-dim); letter-spacing: 0.1em; padding-top: 0.2rem; white-space: nowrap; }
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
"""

SHARED_HEAD = """
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=VT323&family=IM+Fell+English:ital@0;1&display=swap" rel="stylesheet">
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
  <button class="nav-hamburger" id="hamburger" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
</nav>"""


def footer_html() -> str:
    return f"""
<footer>
  <p class="rune-line">✦ ─────────────────────── ✦</p>
  <p>JUSTIN GAYLOR &nbsp;·&nbsp; HANDBUILT BY THE SCRIBE &nbsp;·&nbsp;
  <span id="yr"></span> &nbsp;·&nbsp; NO DARK MAGIC. NO TRACKING SPELLS.</p>
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
        posts.append({
            "slug":    slug,
            "path":    p,
            "title":   meta.get("title", slug.replace("-", " ").title()),
            "date":    meta.get("date", date.today()),
            "summary": meta.get("summary", ""),
            "type":    meta.get("type", folder.rstrip("s").title()),
            "meta":    meta,
            "body":    body,
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
          <a href="stories/{s['slug']}.html" class="card-link">READ THE SCROLL</a>
        </div>""" for s in stories)
    else:
        story_cards = '<p style="color:var(--text-dim);font-style:italic;">No tales yet. Check back soon.</p>'

    # Blog section
    if blog:
        blog_entries = "\n".join(f"""
        <a href="blog/{b['slug']}.html" class="blog-entry reveal">
          <span class="blog-date">{fmt_date(b['date'])}</span>
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
  <p class="hero-quest">Each day is a quest.</p>
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
    back_href  = f"../#blog" if section == "blog" else f"../index.html#writing"

    body = f"""
<div class="post-wrap">
  <div class="post-header">
    <p class="post-kicker">{kicker}</p>
    <h1 class="post-title">{post['title']}</h1>
    <p class="post-meta">SCRIBED BY JUSTIN GAYLOR · {fmt_date_iso(post['date'])}</p>
  </div>
  <hr class="post-divider">
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
