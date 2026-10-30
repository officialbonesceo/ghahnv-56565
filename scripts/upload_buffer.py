#!/usr/bin/env python3
"""Host mp4 -> Buffer video posts on TikTok, Instagram, Facebook + image/text cards on IG/FB."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://api.buffer.com"

DEFAULT_CHANNELS = {
    "tiktok": "6a9b6f3f065799be468f596b",
    "instagram": "6aa31c1dcd8b9c702c467a38",
    "facebook": "6aa31cd2cd8b9c702c468b52",
}


def gql(key: str, query: str) -> dict:
    r = requests.post(
        API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": query},
        timeout=120,
    )
    try:
        data = r.json()
    except Exception:
        print(r.text[:500], file=sys.stderr)
        return {}
    if data.get("errors"):
        print("errors", json.dumps(data["errors"])[:700], file=sys.stderr)
    return data


def schedule_due_at(offset_minutes: int = 2) -> str:
    due = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return due.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def host_file(path: Path, mime: str) -> str | None:
    name = path.name
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (name, f, mime)},
                timeout=300,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("litterbox", url, file=sys.stderr)
            return url
        print("litterbox", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("litterbox", e, file=sys.stderr)
    try:
        with path.open("rb") as f:
            r = requests.post("https://0x0.st", files={"file": (name, f, mime)}, timeout=300)
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("0x0", url, file=sys.stderr)
            return url
        print("0x0", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("0x0", e, file=sys.stderr)
    return None


def host_github_release(path: Path) -> tuple[str | None, str | None]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        return None, None
    tag = f"clip-{int(time.time())}"
    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"tag_name": tag, "name": f"Mike clip {tag}", "body": "Media for Buffer cross-post", "draft": False, "prerelease": True},
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print("release create", r.status_code, r.text[:300], file=sys.stderr)
        return None, None
    rel = r.json()
    release_id = str(rel.get("id") or "")
    upload_url = (rel.get("upload_url") or "").split("{")[0]
    mime = "video/mp4" if path.suffix.lower() == ".mp4" else "image/jpeg"
    with path.open("rb") as f:
        up = requests.post(
            upload_url + f"?name={path.name}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": mime},
            data=f.read(),
            timeout=300,
        )
    if up.status_code not in (200, 201):
        print("asset", up.status_code, up.text[:300], file=sys.stderr)
        return None, release_id
    url = up.json().get("browser_download_url")
    print("gh release KEEP", url, file=sys.stderr)
    return url, release_id


def load_title() -> str:
    for p in ("title_short.txt", "hook.txt"):
        if Path(p).exists():
            t = Path(p).read_text(encoding="utf-8").strip().splitlines()[0].strip()
            if t:
                return t[:80]
    if Path("script_job.json").exists():
        try:
            d = json.loads(Path("script_job.json").read_text(encoding="utf-8"))
            t = (d.get("short_title") or d.get("title") or "").strip()
            if t:
                return t[:80]
        except Exception:
            pass
    return "Today's science lesson"


def load_hook_line() -> str:
    if Path("script_job.json").exists():
        try:
            d = json.loads(Path("script_job.json").read_text(encoding="utf-8"))
            script = (d.get("script") or "").strip()
            if script:
                first = re.split(r"(?<=[.!?])\s+", script)[0].strip()
                if 8 <= len(first.split()) <= 28:
                    return first[:160]
        except Exception:
            pass
    return ""


def load_dyk() -> str:
    if Path("script_job.json").exists():
        try:
            d = json.loads(Path("script_job.json").read_text(encoding="utf-8"))
            dyk = (d.get("did_you_know") or "").strip()
            if dyk and "write the" not in dyk.lower() and len(dyk) > 20:
                return dyk[:180]
        except Exception:
            pass
    return ""


def captions_for(title: str, hook: str) -> dict[str, str]:
    t = title.strip() or "Science lesson"
    h = hook.strip()
    if h and re.search(r"(?i)steps? to answer|number one,", h):
        h = ""
    tiktok = Path("tiktok_caption.txt").read_text(encoding="utf-8").strip() if Path("tiktok_caption.txt").exists() else ""
    if not tiktok:
        tiktok = (
            f"{t} explained in under a minute\n\n"
            f"{h + chr(10) + chr(10) if h else ''}"
            f"Follow for daily exam-ready lessons\n\n"
            f"#learntok #sciencefacts #fyp #stem #edutok #studytok #education #learning #students #examprep"
        )
    ig_body = h or f"{t} — clear exam-ready explanation."
    instagram = (
        f"{ig_body}\n\nSave this for revision.\nFollow for daily student lessons.\n\n"
        f"#reels #science #education #stem #studytok #learnontiktok #examprep #students #learning #school #edutok"
    )
    fb_lead = h or f"Quick lesson: {t}"
    facebook = (
        f"{t}\n\n{fb_lead}\n\nWatch the short video, then save it for revision.\n"
        f"Daily lessons for secondary school and exam prep.\n\n"
        f"#Science #Education #Learn #STEM #StudyTips #ExamPrep #Students #Learning #School"
    )
    return {"tiktok": tiktok, "instagram": instagram, "facebook": facebook}


def image_captions(title: str, hook: str, dyk: str) -> dict[str, str]:
    t = title.strip() or "Science lesson"
    h = hook.strip() or f"{t} — clear and exam-ready."
    tip = dyk or "Save this for revision before your next test."
    ig = (
        f"{t}\n\n{h}\n\nDid you know: {tip}\n\n"
        f"Save · Share with a classmate · Follow for daily lessons\n\n"
        f"#science #education #stem #studytok #examprep #students #learning #edutok #school"
    )
    fb = (
        f"{t}\n\n{h}\n\nDid you know: {tip}\n\n"
        f"Daily science lessons for students worldwide.\n\n"
        f"#Science #Education #STEM #StudyTips #ExamPrep #Students #Learning"
    )
    return {"instagram": ig, "facebook": fb}


def metadata_graphql(service: str, kind: str = "video") -> str:
    if service == "instagram" and kind == "video":
        return "metadata: { instagram: { type: reel, shouldShareToFeed: true } }"
    if service == "instagram" and kind == "image":
        return "metadata: { instagram: { type: post, shouldShareToFeed: true } }"
    if service == "facebook" and kind == "video":
        return "metadata: { facebook: { type: reel } }"
    if service == "facebook" and kind == "image":
        return "metadata: { facebook: { type: post } }"
    return ""


def resolve_channels() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    mapping = {
        "tiktok": os.environ.get("BUFFER_CHANNEL_ID") or os.environ.get("BUFFER_TIKTOK_CHANNEL_ID") or DEFAULT_CHANNELS["tiktok"],
        "instagram": os.environ.get("BUFFER_INSTAGRAM_CHANNEL_ID") or DEFAULT_CHANNELS["instagram"],
        "facebook": os.environ.get("BUFFER_FACEBOOK_CHANNEL_ID") or DEFAULT_CHANNELS["facebook"],
    }
    for service, cid in mapping.items():
        if not cid:
            continue
        if os.environ.get(f"BUFFER_SKIP_{service.upper()}", "").strip() in ("1", "true", "yes"):
            print(f"skip {service}", file=sys.stderr)
            continue
        out.append((service, cid.strip()))
    return out
