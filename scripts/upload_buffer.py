#!/usr/bin/env python3
"""
Queue a post to Buffer (GraphQL API).

Requires secrets (never commit keys):
  BUFFER_API_KEY   - personal API key (Bearer)
  BUFFER_CHANNEL_ID - TikTok (or other) channel id

Buffer needs a *public* media URL for video (not local files).
Set VIDEO_PUBLIC_URL to a publicly reachable mp4 link.
"""
from __future__ import annotations

import json
import os
import sys

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
    r.raise_for_status()
    return r.json()


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    text = os.environ.get("BUFFER_TEXT", "").strip()
    video_url = os.environ.get("VIDEO_PUBLIC_URL", "").strip()

    if not key or not channel:
        print("Skip Buffer: set BUFFER_API_KEY and BUFFER_CHANNEL_ID secrets")
        return
    if not text:
        if Path_script := __import__("pathlib").Path("script.txt"):
            if Path_script.exists():
                text = Path_script.read_text(encoding="utf-8").strip()[:400]
    if not text:
        text = "New Mezi explainer — follow for more science in plain words!"

    # Optional: list channels to help user find channel id
    if os.environ.get("BUFFER_LIST_CHANNELS") == "1":
        q = "{ channels { id name service } }"
        print(json.dumps(gql(key, q), indent=2))
        return

    media = ""
    if video_url:
        media = f'assets: [{{ url: "{video_url}" }}]'

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
    if "errors" in data or (data.get("data") or {}).get("createPost", {}).get("message"):
        sys.exit(1)


if __name__ == "__main__":
    main()
