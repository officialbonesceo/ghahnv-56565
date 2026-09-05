#!/usr/bin/env python3
"""Buffer GraphQL: list channels and/or queue a post. Uses BUFFER_API_KEY secret."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

API = "https://api.buffer.com"


def gql(key: str, query: str) -> dict:
    r = requests.post(
        API,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=60,
    )
    print("status", r.status_code, file=sys.stderr)
    try:
        return r.json()
    except Exception:
        print(r.text[:500], file=sys.stderr)
        return {}


def list_channels(key: str) -> list[dict]:
    # try a few common schema shapes
    queries = [
        "{ channels { id name service } }",
        "{ account { channels { id name service } } }",
        "{ organizations { channels { id name service } } }",
    ]
    for q in queries:
        data = gql(key, q)
        print("query result keys", list(data.keys()), file=sys.stderr)
        print(json.dumps(data)[:800], file=sys.stderr)
        ch = None
        d = data.get("data") or {}
        if "channels" in d:
            ch = d["channels"]
        elif "account" in d and isinstance(d["account"], dict):
            ch = d["account"].get("channels")
        elif "organizations" in d:
            orgs = d["organizations"] or []
            ch = []
            for o in orgs:
                ch.extend(o.get("channels") or [])
        if ch:
            return ch
    return []


def pick_channel(channels: list[dict], prefer: str = "tiktok") -> str | None:
    prefer = prefer.lower()
    for c in channels:
        svc = str(c.get("service") or c.get("type") or "").lower()
        name = str(c.get("name") or "").lower()
        if prefer in svc or prefer in name:
            return c.get("id")
    return channels[0].get("id") if channels else None


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("No BUFFER_API_KEY")
        return

    channels = list_channels(key)
    Path("buffer_channels.json").write_text(json.dumps(channels, indent=2), encoding="utf-8")
    print("CHANNELS:", json.dumps(channels, indent=2))

    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not channel:
        channel = pick_channel(channels, "tiktok") or pick_channel(channels, "") or ""
        print("AUTO_CHANNEL", channel)

    if not channel:
        print("No channel id found — open buffer_channels.json in the artifact")
        return

    text = os.environ.get("BUFFER_TEXT", "").strip()
    if not text and Path("script.txt").exists():
        text = Path("script.txt").read_text(encoding="utf-8").strip()[:350]
    if not text:
        text = "New Mezi classroom explainer!"

    title = ""
    if Path("title_short.txt").exists():
        title = Path("title_short.txt").read_text(encoding="utf-8").strip()
    if title:
        text = f"{title}\n\n{text}"

    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()
    media = f'assets: [{{ url: "{video_url}" }}]' if video_url else ""

    mutation = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel)}
        schedulingType: automatic
        mode: addToQueue
        {media}
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
