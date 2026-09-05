#!/usr/bin/env python3
"""Public host mp4 -> Buffer with TikTok-style caption + first comment CTA."""
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
        print("errors", json.dumps(data["errors"])[:600], file=sys.stderr)
    return data


def host_catbox(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (path.name, f, "video/mp4")},
                timeout=300,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("catbox", url, file=sys.stderr)
            return url
        print("catbox", r.status_code, url[:200], file=sys.stderr)
    except Exception as e:
        print("catbox", e, file=sys.stderr)
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
            "name": tag,
            "body": "temp Buffer media",
            "draft": False,
            "prerelease": True,
        },
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print("release", r.status_code, r.text[:300], file=sys.stderr)
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

    if Path("tiktok_caption.txt").exists():
        text = Path("tiktok_caption.txt").read_text(encoding="utf-8").strip()
    else:
        title = Path("title_short.txt").read_text(encoding="utf-8").strip() if Path("title_short.txt").exists() else "Science"
        text = (
            f"{title} explained in plain words\n\n"
            f"Follow @mike.the.tutor\n\n"
            f"#learntok #science #fyp #stem #studytok"
        )

    first_comment = ""
    if Path("tiktok_comment.txt").exists():
        first_comment = Path("tiktok_comment.txt").read_text(encoding="utf-8").strip()

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
            "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 2500 } } }]"
            % json.dumps(video_url)
        )
        print("VIDEO_URL", video_url)

    # TikTok first comment via channel metadata when supported
    meta = ""
    if first_comment:
        meta = f'tiktok: {{ firstComment: {json.dumps(first_comment)} }}'

    mutation = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel)}
        schedulingType: automatic
        mode: addToQueue
        {assets}
        {('metadata: { ' + meta + ' }') if meta else ''}
      }}) {{
        ... on PostActionSuccess {{ post {{ id status dueAt }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = gql(key, mutation)
    print(json.dumps(data, indent=2))
    Path("buffer_result.json").write_text(json.dumps({"result": data, "caption": text, "first_comment": first_comment}, indent=2), encoding="utf-8")

    ok = bool(((data.get("data") or {}).get("createPost") or {}).get("post"))
    # If metadata shape fails, retry without metadata
    if not ok and meta:
        print("retry without metadata", file=sys.stderr)
        mutation2 = f"""
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
        data = gql(key, mutation2)
        print(json.dumps(data, indent=2))
        Path("buffer_result.json").write_text(
            json.dumps({"result": data, "caption": text, "first_comment": first_comment, "note": "comment may need manual pin"}, indent=2),
            encoding="utf-8",
        )
        ok = bool(((data.get("data") or {}).get("createPost") or {}).get("post"))

    if ok and release_id and os.environ.get("DELETE_RELEASE_AFTER", "1") == "1":
        delete_release(release_id)

    if first_comment:
        Path("FIRST_COMMENT.txt").write_text(
            first_comment + "\n\n(Pin this as first comment on TikTok if Buffer did not attach it)\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
