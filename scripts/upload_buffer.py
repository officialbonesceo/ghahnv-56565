#!/usr/bin/env python3
"""Buffer: org -> channel -> temp-host mp4 -> createPost with video asset."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

API = "https://api.buffer.com"
REST = "https://api.bufferapp.com/1"


def gql(key: str, query: str) -> dict:
    r = requests.post(
        API,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=90,
    )
    print("gql", r.status_code, file=sys.stderr)
    try:
        data = r.json()
    except Exception:
        print(r.text[:400], file=sys.stderr)
        return {}
    if data.get("errors"):
        print("errors", json.dumps(data["errors"])[:500], file=sys.stderr)
    return data


def get_org_id(key: str) -> str | None:
    env = os.environ.get("BUFFER_ORG_ID", "").strip()
    if env:
        return env
    data = gql(key, "query { account { organizations { id name } } }")
    orgs = ((data.get("data") or {}).get("account") or {}).get("organizations") or []
    Path("buffer_orgs.json").write_text(json.dumps(orgs, indent=2), encoding="utf-8")
    return orgs[0]["id"] if orgs else None


def get_channels(key: str, org_id: str) -> list[dict]:
    q = f'query {{ channels(input: {{ organizationId: "{org_id}" }}) {{ id name displayName service }} }}'
    data = gql(key, q)
    return (data.get("data") or {}).get("channels") or []


def pick_channel(channels: list[dict]) -> str | None:
    for c in channels:
        blob = f"{c.get('service','')} {c.get('name','')}".lower()
        if "tiktok" in blob:
            return c.get("id")
    return channels[0].get("id") if channels else None


def host_video(path: Path) -> str | None:
    """Buffer needs a public URL — try free temporary hosts."""
    if not path.exists():
        return None
    # 1) catbox
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (path.name, f, "video/mp4")},
                timeout=120,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("hosted catbox", url, file=sys.stderr)
            return url
        print("catbox", r.status_code, r.text[:200], file=sys.stderr)
    except Exception as e:
        print("catbox fail", e, file=sys.stderr)
    # 2) litterbox (temporary)
    try:
        with path.open("rb") as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "24h"},
                files={"fileToUpload": (path.name, f, "video/mp4")},
                timeout=120,
            )
        url = r.text.strip()
        if r.status_code == 200 and url.startswith("http"):
            print("hosted litterbox", url, file=sys.stderr)
            return url
    except Exception as e:
        print("litterbox fail", e, file=sys.stderr)
    return None


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("No BUFFER_API_KEY")
        return

    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not channel:
        org = get_org_id(key)
        channels = get_channels(key, org) if org else []
        Path("buffer_channels.json").write_text(json.dumps(channels, indent=2), encoding="utf-8")
        channel = pick_channel(channels) or ""
        print("AUTO_CHANNEL", channel)

    if not channel:
        print("No channel id")
        return

    text = ""
    if Path("title_short.txt").exists():
        text = Path("title_short.txt").read_text(encoding="utf-8").strip()
    if Path("script.txt").exists():
        body = Path("script.txt").read_text(encoding="utf-8").strip()[:280]
        text = f"{text}\n\n{body}".strip() if text else body
    if not text:
        text = "New classroom explainer!"

    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    if not video_url and Path("output.mp4").exists():
        video_url = host_video(Path("output.mp4")) or ""

    assets = ""
    if video_url:
        # current Buffer shape: assets: [{ video: { url } }]
        assets = (
            "assets: [{ video: { url: %s, metadata: { thumbnailOffset: 1500 } } }]"
            % json.dumps(video_url)
        )
        print("VIDEO_URL", video_url)
    else:
        print("No public video URL — posting text only")

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
    Path("buffer_result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
