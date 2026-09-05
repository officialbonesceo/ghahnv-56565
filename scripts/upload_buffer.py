#!/usr/bin/env python3
"""Host mp4 (keep URL alive) -> Buffer video post. No invalid firstComment field."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

API = "https://api.buffer.com"


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
    """Public repo release URL. KEEP the release so Buffer can fetch later."""
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
            "body": "Media for Buffer/TikTok — do not delete until Buffer publishes",
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


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not key or not channel:
        print("Need BUFFER_API_KEY and BUFFER_CHANNEL_ID")
        return

    if Path("tiktok_caption.txt").exists():
        text = Path("tiktok_caption.txt").read_text(encoding="utf-8").strip()
    else:
        title = (
            Path("title_short.txt").read_text(encoding="utf-8").strip()
            if Path("title_short.txt").exists()
            else "Science"
        )
        text = (
            f"{title} explained in plain words by Mike\n\n"
            f"Follow @mike.the.tutor\n\n"
            f"#learntok #science #fyp #stem #studytok"
        )

    first_comment = ""
    if Path("tiktok_comment.txt").exists():
        first_comment = Path("tiktok_comment.txt").read_text(encoding="utf-8").strip()
        Path("FIRST_COMMENT.txt").write_text(
            first_comment
            + "\n\nPin this manually on TikTok (Buffer API has no firstComment field).\n",
            encoding="utf-8",
        )

    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    release_id = None
    if not video_url and Path("output.mp4").exists():
        # Prefer long-lived hosts; GitHub Release works because repo is public
        video_url = host_0x0(Path("output.mp4")) or ""
        if not video_url:
            video_url = host_litterbox(Path("output.mp4")) or ""
        if not video_url:
            video_url, release_id = host_github_release(Path("output.mp4"))
            video_url = video_url or ""

    if not video_url:
        print("No public video URL — abort video post (text-only not useful)")
        Path("buffer_result.json").write_text(
            json.dumps({"error": "no_public_video_url"}, indent=2), encoding="utf-8"
        )
        return

    print("VIDEO_URL", video_url)
    assets = (
        "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 2500 } } }]"
        % json.dumps(video_url)
    )

    # NO firstComment — Buffer schema rejects it
    mutation = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel)}
        schedulingType: automatic
        mode: addToQueue
        {assets}
      }}) {{
        ... on PostActionSuccess {{ post {{ id status dueAt }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = gql(key, mutation)
    print(json.dumps(data, indent=2))
    Path("buffer_result.json").write_text(
        json.dumps(
            {
                "result": data,
                "caption": text,
                "video_url": video_url,
                "release_id": release_id,
                "first_comment_manual": first_comment,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    post = ((data.get("data") or {}).get("createPost") or {}).get("post")
    if post:
        print("BUFFER_OK", post.get("id"), post.get("status"), post.get("dueAt"))
        # DO NOT delete GitHub release — Buffer fetches the file later
        if release_id:
            print("Keeping release", release_id, "for Buffer download", file=sys.stderr)
    else:
        print("BUFFER_FAIL")


if __name__ == "__main__":
    main()
