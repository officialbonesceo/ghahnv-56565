#!/usr/bin/env python3
"""Buffer GraphQL: account -> org -> channels -> optional createPost."""
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
        timeout=60,
    )
    print("gql status", r.status_code, file=sys.stderr)
    try:
        data = r.json()
    except Exception:
        print(r.text[:400], file=sys.stderr)
        return {}
    if data.get("errors"):
        print("gql errors", json.dumps(data["errors"])[:600], file=sys.stderr)
    return data


def rest_profiles(key: str) -> list[dict]:
    """Legacy REST fallback (some keys still work)."""
    try:
        r = requests.get(
            f"{REST}/profiles.json",
            params={"access_token": key},
            timeout=30,
        )
        print("rest status", r.status_code, file=sys.stderr)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception as e:
        print("rest fail", e, file=sys.stderr)
    return []


def get_org_id(key: str) -> str | None:
    env = os.environ.get("BUFFER_ORG_ID", "").strip()
    if env:
        return env
    data = gql(
        key,
        """query { account { id email organizations { id name } } }""",
    )
    orgs = ((data.get("data") or {}).get("account") or {}).get("organizations") or []
    Path("buffer_orgs.json").write_text(json.dumps(orgs, indent=2), encoding="utf-8")
    print("ORGS", json.dumps(orgs, indent=2))
    if orgs:
        return orgs[0].get("id")
    return None


def get_channels(key: str, org_id: str) -> list[dict]:
    q = f"""
    query {{
      channels(input: {{ organizationId: "{org_id}" }}) {{
        id
        name
        displayName
        service
      }}
    }}
    """
    data = gql(key, q)
    ch = (data.get("data") or {}).get("channels") or []
    return ch


def pick_channel(channels: list[dict], prefer: str = "tiktok") -> str | None:
    prefer = prefer.lower()
    for c in channels:
        blob = f"{c.get('service','')} {c.get('name','')} {c.get('displayName','')}".lower()
        if prefer in blob:
            return c.get("id")
    return channels[0].get("id") if channels else None


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("No BUFFER_API_KEY")
        return

    channels: list[dict] = []
    org_id = get_org_id(key)
    if org_id:
        channels = get_channels(key, org_id)

    if not channels:
        # legacy REST
        profiles = rest_profiles(key)
        channels = [
            {
                "id": p.get("id"),
                "name": p.get("formatted_username") or p.get("service_username"),
                "service": p.get("service"),
            }
            for p in profiles
            if p.get("id")
        ]

    Path("buffer_channels.json").write_text(json.dumps(channels, indent=2), encoding="utf-8")
    print("CHANNELS:", json.dumps(channels, indent=2))

    channel = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
    if not channel:
        channel = pick_channel(channels, "tiktok") or pick_channel(channels, "") or ""
        print("AUTO_CHANNEL", channel)

    if not channel:
        print("No channel id — set BUFFER_ORG_ID / BUFFER_CHANNEL_ID secrets after checking artifact JSON")
        return

    text = os.environ.get("BUFFER_TEXT", "").strip()
    if not text and Path("script.txt").exists():
        text = Path("script.txt").read_text(encoding="utf-8").strip()[:350]
    if not text:
        text = "New classroom explainer!"
    if Path("title_short.txt").exists():
        t = Path("title_short.txt").read_text(encoding="utf-8").strip()
        if t:
            text = f"{t}\n\n{text}"

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
