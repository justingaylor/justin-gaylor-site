# Justin Gaylor's Site

A plain-HTML static site with a green phosphor CRT / fantasy RPG aesthetic.
No framework. No CMS. Just Markdown files and one build script.

---

## Quick start

```bash
# 1. Install uv (one-time, if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create a virtual environment and install dependencies (one-time)
uv venv
uv pip install pyyaml markdown

# 3. Build the site
uv run build.py

# 4. Open in browser
open dist/index.html
```

The `.venv` folder will be created in the project directory and used automatically by `uv run`.

---

## Adding content

### Blog post

Create a file in `content/blog/` named `YYYY-MM-DD-your-slug.md`:

```markdown
---
title: My Post Title
date: 2025-06-15
summary: One sentence that hooks the reader.
---

Your post content goes here, in Markdown.

## A heading

More content...
```

Run `uv run build.py`. Done.

---

### Short story or essay

Same pattern, in `content/stories/`:

```markdown
---
title: The Long Way Home
date: 2025-06-10
type: Short Story          # Flash Fiction, Essay, Poem, etc.
summary: A teaser line.
---

Story content here...
```

---

### About page

Edit `content/about.md` directly. Plain Markdown, no required front matter.

---

### Projects

Edit `content/projects.yaml`. Each project is a list entry:

```yaml
- name: my-tool
  description: What it does and why you built it.
  tags: [Python, CLI]
  url: https://github.com/yourusername/my-tool
  date: 2025-01-01
  pinned: true     # Optional: puts this project at the top
```

---

## Configuring the site

Open `build.py` and edit the variables near the top:

```python
SITE_TITLE    = "Justin Gaylor"
AUTHOR_EMAIL  = "you@example.com"
GITHUB_URL    = "https://github.com/yourusername"
TWITTER_URL   = "https://twitter.com/yourusername"
LINKEDIN_URL  = "https://linkedin.com/in/yourusername"
CHAR_STATS    = [...]    # The character sheet on the About section
```

---

## Auto-rebuild on save (optional)

```bash
uv pip install watchdog
uv run build.py --watch
```

Watches `content/` and rebuilds whenever you save a file.

---

## Deploying

The `dist/` folder is your deployable site. Options:

**Netlify** (free, drag-and-drop):
1. Build once: `uv run build.py`
2. Drag the `dist/` folder to netlify.com/drop

**GitHub Pages**:
1. Push the `dist/` folder to a repo
2. Enable Pages in repo Settings → Pages → Deploy from branch

**Any static host**: upload the contents of `dist/`.

---

## File structure

```
my-site/
├── build.py                        ← run this to build
├── README.md
├── .venv/                          ← created by `uv venv` (don't commit this)
├── content/
│   ├── about.md                    ← your about copy
│   ├── projects.yaml               ← project list
│   ├── blog/
│   │   └── YYYY-MM-DD-slug.md      ← blog posts (auto-discovered)
│   └── stories/
│       └── YYYY-MM-DD-slug.md      ← stories (auto-discovered)
└── dist/                           ← generated output (deploy this)
    ├── index.html
    ├── blog/
    │   └── slug.html
    └── stories/
        └── slug.html
```

If using git, add `.venv/` to your `.gitignore`. Commit `content/` and `build.py`; optionally commit `dist/` if deploying via GitHub Pages.
