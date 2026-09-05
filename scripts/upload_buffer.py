#!/usr/bin/env python3
"""Host mp4 publicly (catbox or GitHub Release) -> Buffer video post -> optional delete release."""
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
        timeout=90,
    )
    try:
        data = r.json()
    except Exception:
        print(r.text[:400], file=sys.stderr)
        return {}
    if data.get("errors"):
        print("gql errors", json.dumps(data["errors"])[:500], file=sys.stderr)
    return data


def host_catbox(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (path.name, f, "video/mp4")},
                timeout=180,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("catbox", url, file=sys.stderr)
            return url
        print("catbox fail", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("catbox", e, file=sys.stderr)
    return None


def host_github_release(path: Path) -> tuple[str | None, str | None]:
    """Returns (public_url, release_id). Only public if repo is public."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY", "")  # owner/name
    if not token or not repo:
        return None, None
    tag = f"clip-{int(time.time())}"
    # create release
    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": tag,
            "name": tag,
            "body": "temp media for Buffer",
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
            timeout=180,
        )
    if up.status_code not in (200, 201):
        print("asset upload", up.status_code, up.text[:300], file=sys.stderr)
        return None, release_id
    asset = up.json()
    url = asset.get("browser_download_url")
    print("gh release", url, file=sys.stderr)
    return url, release_id


def delete_release(release_id: str) -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo or not release_id:
        return
    r = requests.delete(
        f"https://api.github.com/repos/{repo}/releases/{release_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    print("delete release", release_id, r.status_code, file=sys.stderr)


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not key or not channel:
        print("Need BUFFER_API_KEY and BUFFER_CHANNEL_ID")
        return

    text = ""
    if Path("title_short.txt").exists():
        text = Path("title_short.txt").read_text(encoding="utf-8").strip()
    if Path("script.txt").exists():
        body = Path("script.txt").read_text(encoding="utf-8").strip()[:300]
        text = f"{text}\n\n{body}\n\n@mike.the.tutor".strip()

    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    release_id = None
    if not video_url and Path("output.mp4").exists():
        video_url = host_catbox(Path("output.mp4")) or ""
        if not video_url:
            video_url, release_id = host_github_release(Path("output.mp4"))
            video_url = video_url or ""

    assets = ""
    if video_url:
        assets = (
            "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 2000 } } }]"
            % json.dumps(video_url)
        )
        print("VIDEO_URL", video_url)
    else:
        print("text-only post (no public video URL)")

    mutation = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text or "New lesson from Mike")}
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
    Path("buffer_result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    ok = bool(((data.get("data") or {}).get("createPost") or {}).get("post"))
    if ok and release_id and os.environ.get("DELETE_RELEASE_AFTER", "1") == "1":
        delete_release(release_id)


if __name__ == "__main__":
    main()
