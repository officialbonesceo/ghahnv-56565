#!/usr/bin/env python3
"""Fetch one free educational image from Wikipedia / Wikimedia Commons.

Writes topic_image.jpg when possible. Skips quietly if none found.
Does NOT use Getty or other paid stock (license/TOS).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

UA = {
    "User-Agent": "MikeTutor/1.0 (educational; github.com/officialbonesceo/ghahnv-56565)",
}
OUT = Path("topic_image.jpg")
META = Path("topic_image.json")


def page_image(title: str) -> str | None:
    """Primary image from Wikipedia page summary."""
    for lang in ("en", "simple"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                + requests.utils.quote(title.replace(" ", "_")),
                headers=UA,
                timeout=25,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            thumb = (data.get("originalimage") or data.get("thumbnail") or {})
            src = thumb.get("source") or ""
            if src and re.search(r"\.(jpe?g|png|webp)", src, re.I):
                # Prefer larger original if present
                return src
        except Exception as e:
            print("summary img fail", lang, e, file=sys.stderr)
    return None


def commons_search(title: str) -> str | None:
    """Fallback: Commons image search (educational files)."""
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": title,
                "gsrlimit": 8,
                "gsrnamespace": 6,  # File:
                "prop": "imageinfo",
                "iiprop": "url|mime|size",
                "iiurlwidth": 1600,
            },
            headers=UA,
            timeout=30,
        )
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or {}
        best = None
        best_w = 0
        for p in pages.values():
            for info in p.get("imageinfo") or []:
                mime = (info.get("mime") or "").lower()
                if "jpeg" not in mime and "png" not in mime and "webp" not in mime:
                    continue
                url = info.get("thumburl") or info.get("url") or ""
                w = int(info.get("thumbwidth") or info.get("width") or 0)
                if url and w >= best_w:
                    best, best_w = url, w
        return best
    except Exception as e:
        print("commons fail", e, file=sys.stderr)
        return None


def download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=UA, timeout=60, stream=True)
        r.raise_for_status()
        data = r.content
        if len(data) < 8_000:
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print("download fail", e, file=sys.stderr)
        return False


def main() -> None:
    title = "Science"
    if Path("topic.json").exists():
        try:
            title = json.loads(Path("topic.json").read_text(encoding="utf-8")).get("title") or title
        except Exception:
            pass
    if Path("title_short.txt").exists():
        t = Path("title_short.txt").read_text(encoding="utf-8").strip()
        if t:
            title = t

    url = page_image(title) or commons_search(title)
    if not url:
        print("NO_IMAGE", title, file=sys.stderr)
        META.write_text(json.dumps({"ok": False, "title": title}), encoding="utf-8")
        return

    if not download(url, OUT):
        print("NO_IMAGE_DOWNLOAD", title, file=sys.stderr)
        META.write_text(json.dumps({"ok": False, "title": title, "url": url}), encoding="utf-8")
        if OUT.exists():
            OUT.unlink()
        return

    META.write_text(
        json.dumps({"ok": True, "title": title, "url": url, "path": str(OUT)}, indent=2),
        encoding="utf-8",
    )
    print("IMAGE_OK", title, url, file=sys.stderr)
    print(json.dumps({"ok": True, "path": str(OUT), "url": url}))


if __name__ == "__main__":
    main()
