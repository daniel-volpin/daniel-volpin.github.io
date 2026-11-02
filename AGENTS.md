# Volpin site agent guide

Static GitHub Pages user site (`daniel-volpin/daniel-volpin.github.io`) with a home page plus a landing, support and privacy page for each iPhone app. Pages serve from the root of `main`; `.nojekyll` disables Jekyll.

## Layout

- `index.html`: home page, one card per app.
- `<app>/index.html`, `<app>/support/index.html`, `<app>/privacy/index.html` for `divefolio`, `guandan` and `health-companion`.
- `guandan/zh/support/` and `guandan/zh/privacy/`: Simplified Chinese (`lang="zh-Hans"`), linked to the English pages with `hreflang` alternates (`en`, `zh-Hans`, `x-default`).
- `style.css`: the only stylesheet. Tokens on `:root`, light and dark (`prefers-color-scheme`), and per-app accents via `.theme-divefolio`, `.theme-guandan`, `.theme-health`.
- `<app>/icon.png`, `<app>/screenshots/*.jpg` (1280 px tall).
- `scripts/check_site.py`: pre-publish checker (stdlib only).

## Invariants

- URLs are in App Store Connect: never rename, move or remove a page folder. Use folder URLs (`/app/page/`), never `.html` links.
- Never create folders named `divefolio-site` or `health-companion-legal`; those paths belong to the older project Pages sites.
- `divefolio-ios` CI checks out `divefolio/privacy/index.html` and requires the phrases "Apple Maps receives" and "workout route"; keep them, and keep the retired phrases out (see that repo's `.github/workflows/quality.yml`).
- Copy policy and support text from each app repo (`PRIVACY.md`, `SUPPORT.md`, `STORE.md`, README). Every screen, tab and button a page names must exist in the app. Never change what a policy says without updating the app repo and the "Last updated" date.
- Only link to the App Store for an app that is live; otherwise show "Coming soon to the App Store".
- Plain semantic HTML5 and vanilla CSS: no JavaScript, build step, tracking, analytics, or external fonts and scripts. Every page shares the same header and footer, has a `<title>`, alt text on images, and visible focus states, and must not scroll horizontally at 375 px.
- Never put a personal address on a page; use the published support address only.

## Verification

```bash
python3 scripts/check_site.py          # links, images, titles, lang, hreflang, CI phrases
python3 scripts/check_site.py --live   # every published URL returns 200
python3 -m http.server 8000            # local preview at http://127.0.0.1:8000/
```

The Check workflow runs the file check on every pull request and push to `main`, and the live check every Monday and on demand.
