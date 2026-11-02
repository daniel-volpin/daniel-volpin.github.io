#!/usr/bin/env python3
"""Check the Volpin site before publishing. Standard library only.

    python3 scripts/check_site.py [--allow-placeholder]

Checks that every page in REQUIRED_PAGES exists, that every internal link and
image resolves, that each page has a <title> and the right lang, that the
English and Chinese Guandan pages name each other with hreflang alternates,
that no page loads a script or anything from another host, that Divefolio's
privacy page keeps the phrases divefolio-ios CI requires, and that no page
shows the personal address or the unfilled support-email placeholder.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import sys

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = "https://daniel-volpin.github.io"

REQUIRED_PAGES = [
    "/",
    "/divefolio/", "/divefolio/support/", "/divefolio/privacy/",
    "/guandan/", "/guandan/support/", "/guandan/privacy/",
    "/guandan/zh/support/", "/guandan/zh/privacy/",
    "/health-companion/", "/health-companion/support/", "/health-companion/privacy/",
]
FORBIDDEN_DIRS = ["divefolio-site", "health-companion-legal"]
HREFLANG_PAIRS = [
    ("/guandan/support/", "/guandan/zh/support/"),
    ("/guandan/privacy/", "/guandan/zh/privacy/"),
]
DIVEFOLIO_PRIVACY_PHRASES = ["Apple Maps receives", "workout route"]
DIVEFOLIO_RETIRED_PHRASES = [
    "never leaves the device",
    "never sends health data anywhere",
    "does not collect, transmit",
]
BANNED_TEXT = ["danielvolpin01@gmail.com"]
PLACEHOLDER = "{{SUPPORT_EMAIL}}"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.title = ""
        self._in_title = False
        self.refs = []
        self.alternates = {}
        self.ids = set()
        self.scripts = 0
        self.imgs_without_alt = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "script":
            self.scripts += 1
        elif tag == "img":
            self.refs.append(("img", a.get("src", "")))
            if "alt" not in a:
                self.imgs_without_alt += 1
        elif tag == "a" and "href" in a:
            self.refs.append(("a", a["href"]))
        elif tag == "link" and "href" in a:
            rel = a.get("rel", "")
            if rel == "alternate" and "hreflang" in a:
                self.alternates[a["hreflang"]] = a["href"]
            elif rel != "canonical":
                self.refs.append(("link", a["href"]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def url_path(page_url, ref):
    """Resolves a reference on a page to a site path, or None when external."""
    parts = urlsplit(ref)
    if parts.scheme in ("mailto", "tel"):
        return None
    if parts.scheme or parts.netloc:
        if f"{parts.scheme}://{parts.netloc}" != ORIGIN:
            return "EXTERNAL"
        path = parts.path
    elif ref.startswith("#"):
        path = page_url
    elif parts.path.startswith("/"):
        path = parts.path
    else:
        base = page_url if page_url.endswith("/") else page_url.rsplit("/", 1)[0] + "/"
        path = str(Path(base + parts.path).resolve()) if parts.path else page_url
        if parts.path.endswith("/") and not path.endswith("/"):
            path += "/"
    return unquote(path), parts.fragment


def file_for(path):
    target = ROOT / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    return target


def main():
    allow_placeholder = "--allow-placeholder" in sys.argv
    errors, warnings = [], []
    pages = {}
    for html_file in sorted(ROOT.rglob("*.html")):
        if ".git" in html_file.parts:
            continue
        rel = "/" + html_file.relative_to(ROOT).as_posix()
        url = rel[: -len("index.html")] if rel.endswith("/index.html") or rel == "/index.html" else rel
        parser = Page()
        text = html_file.read_text(encoding="utf-8")
        parser.feed(text)
        pages[url] = (parser, text)

    for url in REQUIRED_PAGES:
        if url not in pages:
            errors.append(f"{url}: required page is missing")
    for name in FORBIDDEN_DIRS:
        if (ROOT / name).exists():
            errors.append(f"/{name}/ must not exist: it belongs to an existing project site")

    for url, (page, text) in pages.items():
        if not page.title.strip():
            errors.append(f"{url}: no <title>")
        expected_lang = "zh-Hans" if "/zh/" in url else "en"
        if page.lang != expected_lang:
            errors.append(f"{url}: lang is {page.lang!r}, expected {expected_lang!r}")
        if page.scripts:
            errors.append(f"{url}: has {page.scripts} <script> element(s)")
        if page.imgs_without_alt:
            errors.append(f"{url}: {page.imgs_without_alt} image(s) without alt")
        for banned in BANNED_TEXT:
            if banned in text:
                errors.append(f"{url}: contains {banned}")
        if PLACEHOLDER in text:
            (warnings if allow_placeholder else errors).append(f"{url}: support email not filled in")
        for kind, ref in page.refs:
            resolved = url_path(url, ref)
            if resolved is None:
                continue
            if resolved == "EXTERNAL":
                if kind != "a":
                    errors.append(f"{url}: loads an external resource {ref}")
                continue
            path, fragment = resolved
            target = file_for(path)
            if not target.is_file():
                errors.append(f"{url}: broken {kind} {ref}")
            elif fragment:
                target_url = path if path.endswith("/") else path
                target_page = pages.get(target_url)
                if target_page and fragment not in target_page[0].ids:
                    errors.append(f"{url}: {ref} points at a missing #{fragment}")

    for en, zh in HREFLANG_PAIRS:
        for url in (en, zh):
            if url not in pages:
                continue
            alternates = pages[url][0].alternates
            if alternates.get("en") != ORIGIN + en or alternates.get("zh-Hans") != ORIGIN + zh:
                errors.append(f"{url}: hreflang alternates must name {en} (en) and {zh} (zh-Hans)")

    privacy = pages.get("/divefolio/privacy/")
    if privacy:
        for phrase in DIVEFOLIO_PRIVACY_PHRASES:
            if phrase not in privacy[1]:
                errors.append(f"/divefolio/privacy/: missing phrase divefolio-ios CI requires: {phrase}")
        for phrase in DIVEFOLIO_RETIRED_PHRASES:
            if phrase.lower() in privacy[1].lower():
                errors.append(f"/divefolio/privacy/: retired claim present: {phrase}")

    for line in warnings:
        print(f"WARN  {line}")
    for line in errors:
        print(f"FAIL  {line}")
    print(f"{len(pages)} pages checked, {len(errors)} failure(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
