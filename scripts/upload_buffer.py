#!/usr/bin/env python3
"""Host mp4 -> Buffer video posts on TikTok, Instagram, Facebook."""
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

# Defaults from data/buffer_channels.json inventory (override via env)
DEFAULT_CHANNELS = {
    "tiktok": "6a9b6f3f065799be468f596b",       # godswillchiemezie
    "instagram": "6aa31c1dcd8b9c702c467a38",   # bones_ceo
    "facebook": "6aa31cd2cd8b9c702c468b52",    # Voxam Fact
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


def host_0x0(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://0x0.st",
                files={"file": (path.name, f, "video/mp4")},
                timeout=300,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("0x0", url, file=sys.stderr)
            return url
        print("0x0", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("0x0", e, file=sys.stderr)
    return None


def host_litterbox(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (path.name, f, "video/mp4")},
                timeout=300,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("litterbox", url, file=sys.stderr)
            return url
        print("litterbox", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("litterbox", e, file=sys.stderr)
    return None


def host_github_release(path: Path) -> tuple[str | None, str | None]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        return None, None
    tag = f"clip-{int(time.time())}"
    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": tag,
            "name": f"Mike clip {tag}",
            "body": "Media for Buffer cross-post",
            "draft": False,
            "prerelease": True,
        },
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print("release create", r.status_code, r.text[:300], file=sys.stderr)
        return None, None
    rel = r.json()
    release_id = str(rel.get("id") or "")
    upload_url = (rel.get("upload_url") or "").split("{")[0]
    with path.open("rb") as f:
        up = requests.post(
            upload_url + f"?name={path.name}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "video/mp4",
            },
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


def captions_for(title: str, hook: str) -> dict[str, str]:
    """Platform-specific post text. Facebook always starts with a real title (no Untitled)."""
    t = title.strip() or "Science lesson"
    h = hook.strip()
    if h and __import__("re").search(r"(?i)steps? to answer|number one,", h):
        h = ""

    tiktok = (
        Path("tiktok_caption.txt").read_text(encoding="utf-8").strip()
        if Path("tiktok_caption.txt").exists()
        else ""
    )
    if not tiktok:
        tiktok = (
            f"{t} explained in under a minute\n\n"
            f"{h + chr(10) + chr(10) if h else ''}"
            f"Follow for daily WAEC / JAMB lessons\n\n"
            f"#learntok #sciencefacts #fyp #WAEC #JAMB #NECO #stem #edutok #studytok"
        )

    ig_body = h or f"{t} — clear exam-ready explanation."
    instagram = (
        f"{ig_body}\n\n"
        f"Save this for revision.\n"
        f"Follow @bones_ceo for daily student lessons.\n\n"
        f"#reels #science #education #WAEC #JAMB #NECO #studytok #nigeria #learnontiktok #examprep #secondaryschool #stem"
    )

    # Facebook Page: first line = title so Feed never shows "Untitled"
    fb_lead = h or f"Quick lesson: {t}"
    facebook = (
        f"{t}\n\n"
        f"{fb_lead}\n\n"
        f"Watch the short video, then save it for revision.\n"
        f"Daily lessons for secondary school & exam prep.\n\n"
        f"#Science #Education #WAEC #JAMB #NECO #Learn #STEM #StudyTips #ExamPrep"
    )

    return {"tiktok": tiktok, "instagram": instagram, "facebook": facebook}


def metadata_graphql(service: str) -> str:
    """Channel-specific metadata fragment for createPost input."""
    if service == "instagram":
        # Post as Reel when Buffer accepts type
        return "metadata: { instagram: { type: reel, shouldShareToFeed: true } }"
    if service == "facebook":
        return ""  # title is carried in text first line
    return ""


def resolve_channels() -> list[tuple[str, str]]:
    """List of (service, channel_id). Env overrides defaults."""
    out: list[tuple[str, str]] = []
    mapping = {
        "tiktok": os.environ.get("BUFFER_CHANNEL_ID")
        or os.environ.get("BUFFER_TIKTOK_CHANNEL_ID")
        or DEFAULT_CHANNELS["tiktok"],
        "instagram": os.environ.get("BUFFER_INSTAGRAM_CHANNEL_ID") or DEFAULT_CHANNELS["instagram"],
        "facebook": os.environ.get("BUFFER_FACEBOOK_CHANNEL_ID") or DEFAULT_CHANNELS["facebook"],
    }
    # Optional: disable a platform with BUFFER_SKIP_INSTAGRAM=1 etc.
    for service, cid in mapping.items():
        if not cid:
            continue
        if os.environ.get(f"BUFFER_SKIP_{service.upper()}", "").strip() in ("1", "true", "yes"):
            print(f"skip {service}", file=sys.stderr)
            continue
        out.append((service, cid.strip()))
    return out


def create_post(key: str, channel_id: str, service: str, text: str, video_url: str, due_at: str) -> dict:
    assets = (
        "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 2500 } } }]"
        % json.dumps(video_url)
    )
    meta = metadata_graphql(service)
    meta_line = (meta + "\n") if meta else ""

    mutation = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel_id)}
        schedulingType: automatic
        mode: customScheduled
        dueAt: {json.dumps(due_at)}
        {meta_line}{assets}
      }}) {{
        ... on PostActionSuccess {{ post {{ id status dueAt }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = gql(key, mutation)
    post = ((data.get("data") or {}).get("createPost") or {}).get("post")
    if post:
        return {"ok": True, "service": service, "channel_id": channel_id, "post": post, "raw": data, "caption": text}

    # Retry without metadata (some orgs reject reel type)
    if meta:
        print(f"{service}: retry without metadata", file=sys.stderr)
        mutation_b = f"""
        mutation {{
          createPost(input: {{
            text: {json.dumps(text)}
            channelId: {json.dumps(channel_id)}
            schedulingType: automatic
            mode: customScheduled
            dueAt: {json.dumps(due_at)}
            {assets}
          }}) {{
            ... on PostActionSuccess {{ post {{ id status dueAt }} }}
            ... on MutationError {{ message }}
          }}
        }}
        """
        data = gql(key, mutation_b)
        post = ((data.get("data") or {}).get("createPost") or {}).get("post")
        if post:
            return {"ok": True, "service": service, "channel_id": channel_id, "post": post, "raw": data, "caption": text}

    # Queue fallback
    print(f"{service}: retry addToQueue", file=sys.stderr)
    mutation2 = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel_id)}
        schedulingType: automatic
        mode: addToQueue
        {assets}
      }}) {{
        ... on PostActionSuccess {{ post {{ id status dueAt }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = gql(key, mutation2)
    post = ((data.get("data") or {}).get("createPost") or {}).get("post")
    return {
        "ok": bool(post),
        "service": service,
        "channel_id": channel_id,
        "post": post,
        "raw": data,
        "caption": text,
    }


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("Need BUFFER_API_KEY")
        return

    channels = resolve_channels()
    if not channels:
        print("No Buffer channels configured")
        return

    title = load_title()
    hook = load_hook_line()
    caps = captions_for(title, hook)
    print("TITLE", title, file=sys.stderr)

    first_comment = ""
    if Path("tiktok_comment.txt").exists():
        first_comment = Path("tiktok_comment.txt").read_text(encoding="utf-8").strip()

    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    release_id = None
    if not video_url and Path("output.mp4").exists():
        video_url = host_0x0(Path("output.mp4")) or ""
        if not video_url:
            video_url = host_litterbox(Path("output.mp4")) or ""
        if not video_url:
            video_url, release_id = host_github_release(Path("output.mp4"))
            video_url = video_url or ""

    if not video_url:
        print("No public video URL")
        Path("buffer_result.json").write_text(
            json.dumps({"error": "no_public_video_url"}, indent=2), encoding="utf-8"
        )
        return

    print("VIDEO_URL", video_url)
    results = []
    # Stagger due times slightly so Buffer can fetch the same URL for each channel
    for i, (service, channel_id) in enumerate(channels):
        due_at = schedule_due_at(2 + i)
        text = caps.get(service) or caps["tiktok"]
        print(f"POST {service} -> {channel_id} due {due_at}", file=sys.stderr)
        res = create_post(key, channel_id, service, text, video_url, due_at)
        results.append(res)
        if res.get("ok"):
            p = res["post"] or {}
            print("BUFFER_OK", service, p.get("id"), p.get("status"), p.get("dueAt"))
        else:
            print("BUFFER_FAIL", service, file=sys.stderr)
            print(json.dumps(res.get("raw"), indent=2)[:600], file=sys.stderr)

    Path("buffer_result.json").write_text(
        json.dumps(
            {
                "title": title,
                "video_url": video_url,
                "release_id": release_id,
                "first_comment_manual": first_comment,
                "channels": [
                    {
                        "service": r.get("service"),
                        "channel_id": r.get("channel_id"),
                        "ok": r.get("ok"),
                        "post": r.get("post"),
                        "caption": r.get("caption"),
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    ok_n = sum(1 for r in results if r.get("ok"))
    print(f"CROSSPOST {ok_n}/{len(results)} ok")
    if release_id:
        print("Keeping release", release_id, file=sys.stderr)


if __name__ == "__main__":
    main()
