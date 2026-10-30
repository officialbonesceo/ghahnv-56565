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


def create_video_post(key: str, channel_id: str, service: str, text: str, video_url: str, due_at: str) -> dict:
    assets = "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 2500 } } }]" % json.dumps(video_url)
    meta = metadata_graphql(service, "video")
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
        return {"ok": True, "service": service, "kind": "video", "channel_id": channel_id, "post": post, "raw": data, "caption": text}
    if meta:
        print(f"{service}: retry video without metadata", file=sys.stderr)
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
            return {"ok": True, "service": service, "kind": "video", "channel_id": channel_id, "post": post, "raw": data, "caption": text}
    print(f"{service}: retry addToQueue video", file=sys.stderr)
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
    return {"ok": bool(post), "service": service, "kind": "video", "channel_id": channel_id, "post": post, "raw": data, "caption": text}


def create_image_post(key: str, channel_id: str, service: str, text: str, image_url: str, due_at: str) -> dict:
    assets = "assets: [{ image: { url: %s } }]" % json.dumps(image_url)
    meta = metadata_graphql(service, "image")
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
        return {"ok": True, "service": service, "kind": "image", "channel_id": channel_id, "post": post, "raw": data, "caption": text}
    for mode_line in (f'mode: customScheduled\n        dueAt: {json.dumps(due_at)}', "mode: addToQueue"):
        mutation2 = f"""
        mutation {{
          createPost(input: {{
            text: {json.dumps(text)}
            channelId: {json.dumps(channel_id)}
            schedulingType: automatic
            {mode_line}
            {assets}
          }}) {{
            ... on PostActionSuccess {{ post {{ id status dueAt }} }}
            ... on MutationError {{ message }}
          }}
        }}
        """
        data = gql(key, mutation2)
        post = ((data.get("data") or {}).get("createPost") or {}).get("post")
        if post:
            return {"ok": True, "service": service, "kind": "image", "channel_id": channel_id, "post": post, "raw": data, "caption": text}
    return {"ok": False, "service": service, "kind": "image", "channel_id": channel_id, "post": None, "raw": data, "caption": text}


def make_post_card(title: str, dyk: str) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print("PIL missing", e, file=sys.stderr)
        return None
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), (18, 22, 40))
    d = ImageDraw.Draw(img)
    try:
        title_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        body_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        small_f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        title_f = body_f = small_f = ImageFont.load_default()
    d.rectangle([0, 0, W, 16], fill=(255, 180, 40))
    d.rectangle([0, H - 16, W, H], fill=(255, 180, 40))
    d.text((60, 80), "Mike · Daily Lesson", font=small_f, fill=(180, 200, 255))
    words = (title or "Lesson").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=title_f)[2] > W - 120:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    y = 200
    for line in lines[:4]:
        d.text((60, y), line, font=title_f, fill=(255, 255, 255))
        y += 64
    y += 40
    d.text((60, y), "Did you know?", font=body_f, fill=(255, 220, 100))
    y += 60
    tip = dyk or "Save this for revision."
    words = tip.split()
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=body_f)[2] > W - 120:
            if cur:
                d.text((60, y), cur, font=body_f, fill=(230, 235, 255))
                y += 48
            cur = w
        else:
            cur = test
    if cur:
        d.text((60, y), cur, font=body_f, fill=(230, 235, 255))
    d.text((60, H - 120), "Save · Share · Follow", font=small_f, fill=(200, 210, 255))
    out = Path("post_card.jpg")
    img.save(out, quality=90)
    print("POST_CARD", out, file=sys.stderr)
    return out


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
    dyk = load_dyk()
    caps = captions_for(title, hook)
    img_caps = image_captions(title, hook, dyk)
    print("TITLE", title, file=sys.stderr)
    first_comment = Path("tiktok_comment.txt").read_text(encoding="utf-8").strip() if Path("tiktok_comment.txt").exists() else ""
    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    release_id = None
    if not video_url and Path("output.mp4").exists():
        video_url = host_file(Path("output.mp4"), "video/mp4") or ""
        if not video_url:
            video_url, release_id = host_github_release(Path("output.mp4"))
            video_url = video_url or ""
    if not video_url:
        print("No public video URL")
        Path("buffer_result.json").write_text(json.dumps({"error": "no_public_video_url"}, indent=2), encoding="utf-8")
        return
    print("VIDEO_URL", video_url)
    image_url = ""
    img_path = Path("topic_image.jpg") if Path("topic_image.jpg").exists() and Path("topic_image.jpg").stat().st_size > 500 else make_post_card(title, dyk)
    if img_path and img_path.exists():
        image_url = host_file(img_path, "image/jpeg") or ""
        if not image_url:
            u, rid = host_github_release(img_path)
            image_url = u or ""
            if rid and not release_id:
                release_id = rid
    print("IMAGE_URL", image_url or "none", file=sys.stderr)
    results = []
    for i, (service, channel_id) in enumerate(channels):
        due_at = schedule_due_at(2 + i)
        text = caps.get(service) or caps["tiktok"]
        print(f"POST video {service} -> {channel_id} due {due_at}", file=sys.stderr)
        res = create_video_post(key, channel_id, service, text, video_url, due_at)
        results.append(res)
        if res.get("ok"):
            p = res["post"] or {}
            print("BUFFER_OK video", service, p.get("id"), p.get("status"), p.get("dueAt"))
        else:
            print("BUFFER_FAIL video", service, file=sys.stderr)
            print(json.dumps(res.get("raw"), indent=2)[:600], file=sys.stderr)
    if image_url:
        for j, (service, channel_id) in enumerate(channels):
            if service not in ("instagram", "facebook"):
                continue
            due_at = schedule_due_at(8 + j)
            text = img_caps.get(service) or img_caps["instagram"]
            print(f"POST image {service} -> {channel_id} due {due_at}", file=sys.stderr)
            res = create_image_post(key, channel_id, service, text, image_url, due_at)
            results.append(res)
            if res.get("ok"):
                p = res["post"] or {}
                print("BUFFER_OK image", service, p.get("id"), p.get("status"), p.get("dueAt"))
            else:
                print("BUFFER_FAIL image", service, file=sys.stderr)
                print(json.dumps(res.get("raw"), indent=2)[:600], file=sys.stderr)
    else:
        print("skip image posts — no image URL", file=sys.stderr)
    Path("buffer_result.json").write_text(
        json.dumps(
            {
                "title": title,
                "video_url": video_url,
                "image_url": image_url,
                "release_id": release_id,
                "first_comment_manual": first_comment,
                "channels": [
                    {"service": r.get("service"), "kind": r.get("kind"), "channel_id": r.get("channel_id"), "ok": r.get("ok"), "post": r.get("post"), "caption": r.get("caption")}
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
