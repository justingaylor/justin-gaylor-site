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

AUTHOR_EMAIL   = "justin.gaylor@proton.me"
GITHUB_URL     = "https://github.com/justingaylor"
BLUESKY_URL    = "https://bsky.app/profile/justingaylor.bsky.social"
LINKEDIN_URL   = "https://www.linkedin.com/in/justin-gaylor-a9326b2"
MASTODON_URL   = "https://mastodon.social/@justingaylor"

GOATCOUNTER_CODE = "justingaylor"  # goatcounter.com subdomain

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
PAGE_SIZE   = 6

THEMES_DIR  = Path("themes")

# ── CSS (shared across all pages) ─────────────────────────────────────────────

_CSS_CACHE: str | None = None
_THEME_FILES = [
    "base.css",
    "amber.css",
    "cyan.css",
    "medieval.css",
    "pirate.css",
    "typewriter.css",
    "typewriter-dark.css",
    "elvish.css",
    "infernal.css",
    "abyssal.css",
    "runic.css",
    "picker.css",
]

def load_css() -> str:
    global _CSS_CACHE
    if _CSS_CACHE is None:
        _CSS_CACHE = "\n".join(
            (THEMES_DIR / f).read_text(encoding="utf-8") for f in _THEME_FILES
        )
    return _CSS_CACHE

SHARED_HEAD = """
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=VT323&family=IM+Fell+English:ital@0;1&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Orbitron:wght@400;700&family=Share+Tech+Mono&family=Cinzel:wght@400;700&family=Pirata+One&family=Special+Elite&family=Skranji&family=Lora:ital,wght@0,400;0,700;1,400&family=Cinzel+Decorative:wght@400;700;900&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <link rel="me" href="https://mastodon.social/@justingaylor">
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
const THEMES = ['theme-green', 'theme-amber', 'theme-cyan', 'theme-medieval', 'theme-pirate', 'theme-typewriter', 'theme-typewriter-dark', 'theme-elvish', 'theme-infernal', 'theme-abyssal', 'theme-runic'];
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

TAG_FILTER_JS = """
(function() {
  const btns  = document.querySelectorAll('.tag-filter-btn');
  const items = document.querySelectorAll('[data-tags]');
  const empty = document.getElementById('tag-empty');
  if (!btns.length) return;
  btns.forEach(btn => btn.addEventListener('click', () => {
    const tag = btn.dataset.tag;
    btns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    items.forEach(item => {
      if (tag === '*') {
        item.hidden = false;
      } else {
        item.hidden = !(item.dataset.tags || '').split(',').includes(tag);
      }
    });
    if (empty) empty.hidden = Array.from(items).some(i => !i.hidden);
  }));
})();
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


def render_inline_md(text: str) -> str:
    """Render Markdown inline, stripping the outer <p> wrapper."""
    if not text:
        return ""
    html = render_md(text).strip()
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]
    return html


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
    <li><a href="{root_prefix}index.html#writing">WRITING</a></li>
    <li><a href="{root_prefix}index.html#blog">BLOG</a></li>
    <li><a href="{root_prefix}index.html#projects">PROJECTS</a></li>
    <li><a href="{root_prefix}index.html#about">ABOUT</a></li>
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
    <button class="theme-dot" data-theme="theme-elvish"          title="Elvish moonlight"></button>
    <button class="theme-dot" data-theme="theme-infernal"        title="Infernal"></button>
    <button class="theme-dot" data-theme="theme-abyssal"         title="Abyssal"></button>
    <button class="theme-dot" data-theme="theme-runic"           title="Runic"></button>
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
  <p class="footer-quest">Live each day like a quest.</p>
</footer>"""


def page_shell(title: str, body: str, extra_js: str = "", root_prefix: str = "") -> str:
    gc_script = (
        f'<script data-goatcounter="https://{GOATCOUNTER_CODE}.goatcounter.com/count"'
        f' async src="//gc.zgo.at/count.js"></script>'
        if GOATCOUNTER_CODE else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{SHARED_HEAD}
  <title>{title}</title>
  <style>{load_css()}</style>
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
{gc_script}
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

# ── Content renderers (reused by index and listing pages) ─────────────────────

def _tags_str(tags: list) -> str:
    return ",".join(tags)

def _tags_html(tags: list) -> str:
    return "".join(f'<span class="tag">{t}</span>' for t in tags)

def _collect_tags(items: list, key: str = 'meta') -> list[str]:
    tags: set[str] = set()
    for item in items:
        src = item.get('meta', {}) if key == 'meta' else item
        tags.update(src.get('tags', []) or [])
    return sorted(tags)

def render_tag_filter(tags: list) -> str:
    if not tags:
        return ''
    btns = "\n  ".join(
        f'<button class="tag-filter-btn" data-tag="{t}">{t.upper()}</button>'
        for t in tags
    )
    return f"""<div class="tag-filter">
  <button class="tag-filter-btn active" data-tag="*">ALL</button>
  {btns}
</div>"""


def render_story_cards(stories: list, show_tags: bool = False) -> str:
    if not stories:
        return '<p style="color:var(--text-dim);font-style:italic;">No tales yet. Check back soon.</p>'
    def card(s):
        tags = s['meta'].get('tags', []) or []
        tag_attr = f' data-tags="{_tags_str(tags)}"' if tags else ''
        tag_block = f'<div class="tags">{_tags_html(tags)}</div>' if show_tags and tags else ''
        return f"""
        <div class="writing-card reveal"{tag_attr}>
          <p class="card-tag">{s['type'].upper()}</p>
          <h3 class="card-title">{s['title']}</h3>
          <p class="card-excerpt">{render_inline_md(s['summary'])}</p>
          <p class="card-readtime">{s['wc']:,} words &nbsp;·&nbsp; {s['rt']}</p>
          {tag_block}
          <a href="stories/{s['slug']}.html" class="card-link">READ THE SCROLL</a>
        </div>"""
    return "\n".join(card(s) for s in stories)


def render_blog_entries(blog: list, show_tags: bool = False) -> str:
    if not blog:
        return '<p style="color:var(--text-dim);font-style:italic;">No dispatches yet.</p>'
    def entry(b):
        tags = b['meta'].get('tags', []) or []
        tag_attr = f' data-tags="{_tags_str(tags)}"' if tags else ''
        tag_block = f'<div class="tags" style="margin-top:0.5rem;">{_tags_html(tags)}</div>' if show_tags and tags else ''
        return f"""
        <a href="blog/{b['slug']}.html" class="blog-entry reveal"{tag_attr}>
          <div class="blog-date-col">
            <span class="blog-date">{fmt_date(b['date'])}</span>
            <span class="blog-readtime">{b['rt']}</span>
          </div>
          <div>
            <p class="blog-title">{b['title']}</p>
            <p class="blog-summary">{render_inline_md(b['summary'])}</p>
            {tag_block}
          </div>
        </a>"""
    return "\n".join(entry(b) for b in blog)


def render_project_items(projects: list) -> str:
    if not projects:
        return '<p style="color:var(--text-dim);font-style:italic;">Projects coming soon.</p>'
    def proj_html(p):
        tags = p.get("tags", []) or []
        url  = p.get("url", "#")
        return f"""
        <div class="project-item reveal" data-tags="{_tags_str(tags)}">
          <div>
            <p class="project-name">{p['name']}</p>
            <p class="project-desc">{p.get('description', '')}</p>
          </div>
          <div class="project-meta">
            <div class="tags">{_tags_html(tags)}</div>
            <a href="{url}" target="_blank" class="project-link">GITHUB</a>
          </div>
        </div>"""
    return "\n".join(proj_html(p) for p in projects)


def _more_link(href: str, label: str, total: int) -> str:
    if total <= PAGE_SIZE:
        return ''
    return f'<div class="section-more"><a href="{href}" class="btn">{label}</a></div>'


# ── Page builders ──────────────────────────────────────────────────────────────

def build_index(stories: list, blog: list, projects: list, about_html: str):
    body = f"""
<section id="hero">
  <h1 class="hero-name">JUSTIN<br>GAYLOR</h1>
  <p class="hero-subtitle">WRITER &nbsp;·&nbsp; BUILDER &nbsp;·&nbsp; WANDERER</p>
  <p class="hero-tagline"><span id="typed"></span><span class="cursor-blink"></span></p>
  <div class="hero-ctas">
    <a href="#writing" class="btn">READ MY WRITING</a>
    <a href="#contact" class="btn">CONTACT</a>
  </div>
</section>

<hr class="rule">

<div class="section-wrap" id="writing">
  <div class="section-header reveal">
    <h2 class="section-label"><a href="writing.html"><span class="glyph">✦</span>TALES & LORE</a></h2>
  </div>
  <div class="writing-grid">{render_story_cards(stories[:PAGE_SIZE])}</div>
  {_more_link("writing.html", "ALL TALES", len(stories))}
</div>

<hr class="rule">

<div class="section-wrap" id="blog">
  <div class="section-header reveal">
    <h2 class="section-label"><a href="blog.html"><span class="glyph">✦</span>CHRONICLES</a></h2>
  </div>
  <div class="blog-list">{render_blog_entries(blog[:PAGE_SIZE])}</div>
  {_more_link("blog.html", "ALL ENTRIES", len(blog))}
</div>

<hr class="rule">

<div class="section-wrap" id="projects">
  <div class="section-header reveal">
    <h2 class="section-label"><a href="projects.html"><span class="glyph">✦</span>THE WORKSHOP</a></h2>
  </div>
  <div class="project-list">{render_project_items(projects[:PAGE_SIZE])}</div>
  {_more_link("projects.html", "ALL PROJECTS", len(projects))}
</div>

<hr class="rule">

<div class="section-wrap" id="about">
  <div class="section-header reveal">
    <h2 class="section-label"><span class="glyph">✦</span>ABOUT</h2>
  </div>
  <div class="about-body reveal">{about_html}</div>
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
    <a href="{MASTODON_URL}" target="_blank" rel="me" class="contact-link">
      <span class="contact-icon">⊕</span><span class="contact-label">MASTODON</span>
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

    back_label = "BACK TO THE CHRONICLE" if section == "blog" else "BACK TO WRITING"
    back_href  = f"../index.html#blog" if section == "blog" else f"../index.html#writing"

    thoughts = post['meta'].get('thoughts', '')
    thoughts_html = f"""
  <aside class="post-thoughts">
    <p class="post-thoughts-label">✦ SCRIBE'S NOTE</p>
    {render_md(thoughts)}
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


# ── RSS ────────────────────────────────────────────────────────────────────────

def build_rss(stories: list, blog: list) -> str:
    def xml_escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def pub_date(d) -> str:
        if isinstance(d, (date, datetime)):
            return datetime(d.year, d.month, d.day).strftime("%a, %d %b %Y 00:00:00 +0000")
        return ""

    all_posts = (
        [{"section": "stories", **p} for p in stories] +
        [{"section": "blog",    **p} for p in blog]
    )
    all_posts.sort(key=lambda p: p["date"], reverse=True)

    items = "\n".join(f"""  <item>
    <title>{xml_escape(p['title'])}</title>
    <link>{BASE_URL}/{p['section']}/{p['slug']}.html</link>
    <description>{xml_escape(render_md(p.get('summary') or ''))}</description>
    <pubDate>{pub_date(p['date'])}</pubDate>
    <guid>{BASE_URL}/{p['section']}/{p['slug']}.html</guid>
  </item>""" for p in all_posts)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{xml_escape(SITE_TITLE)}</title>
    <link>{BASE_URL}</link>
    <description>{xml_escape(SITE_TAGLINE)}</description>
    <language>en-us</language>
{items}
  </channel>
</rss>"""


def build_writing_page(stories: list) -> str:
    tags = _collect_tags(stories)
    body = f"""
<div class="section-wrap" style="padding-top:7rem;">
  <div class="section-header">
    <h2 class="section-label"><span class="glyph">✦</span>TALES & LORE</h2>
    <p class="section-sub">SHORT FICTION · ESSAYS · WRITINGS</p>
  </div>
  {render_tag_filter(tags)}
  <div class="writing-grid">{render_story_cards(stories, show_tags=True)}</div>
  <p id="tag-empty" class="tag-empty" hidden>No tales match that tag.</p>
</div>"""
    return page_shell(title=f"Writing — {SITE_TITLE}", body=body, extra_js=TAG_FILTER_JS)


def build_blog_listing_page(blog: list) -> str:
    tags = _collect_tags(blog)
    body = f"""
<div class="section-wrap" style="padding-top:7rem;">
  <div class="section-header">
    <h2 class="section-label"><span class="glyph">✦</span>CHRONICLES</h2>
    <p class="section-sub">DISPATCHES FROM THE FIELD</p>
  </div>
  {render_tag_filter(tags)}
  <div class="blog-list">{render_blog_entries(blog, show_tags=True)}</div>
  <p id="tag-empty" class="tag-empty" hidden>No entries match that tag.</p>
</div>"""
    return page_shell(title=f"Blog — {SITE_TITLE}", body=body, extra_js=TAG_FILTER_JS)


def build_projects_page(projects: list) -> str:
    tags = _collect_tags(projects, key='direct')
    body = f"""
<div class="section-wrap" style="padding-top:7rem;">
  <div class="section-header">
    <h2 class="section-label"><span class="glyph">✦</span>THE WORKSHOP</h2>
    <p class="section-sub">SOFTWARE · OPEN SOURCE · CREATIONS</p>
  </div>
  {render_tag_filter(tags)}
  <div class="project-list">{render_project_items(projects)}</div>
  <p id="tag-empty" class="tag-empty" hidden>No projects match that tag.</p>
</div>"""
    return page_shell(title=f"Projects — {SITE_TITLE}", body=body, extra_js=TAG_FILTER_JS)


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

    # Copy static assets
    img_src = CONTENT_DIR / "img"
    if img_src.exists():
        img_dst = DIST_DIR / "img"
        if img_dst.exists():
            shutil.rmtree(img_dst)
        shutil.copytree(img_src, img_dst)
        print(f"  ✓  dist/img/ ({len(list(img_dst.iterdir()))} files)")

    # Report loaded themes
    _non_themes = {'base.css', 'picker.css'}
    _themes = [f.replace('.css', '') for f in _THEME_FILES if f not in _non_themes]
    print(f"  ✓  themes/ ({len(_THEME_FILES)} files: {len(_themes)} themes: {', '.join(_themes)})")

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

    # Build listing pages
    (DIST_DIR / "writing.html").write_text(build_writing_page(stories), encoding="utf-8")
    print(f"  ✓  dist/writing.html")
    (DIST_DIR / "blog.html").write_text(build_blog_listing_page(blog), encoding="utf-8")
    print(f"  ✓  dist/blog.html")
    (DIST_DIR / "projects.html").write_text(build_projects_page(projects), encoding="utf-8")
    print(f"  ✓  dist/projects.html")

    # Build RSS feed
    (DIST_DIR / "rss.xml").write_text(build_rss(stories, blog), encoding="utf-8")
    print(f"  ✓  dist/rss.xml")

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
