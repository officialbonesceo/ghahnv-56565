#!/usr/bin/env python3
"""List Buffer organizations and connected channels (name, id, service)."""
from __future__ import annotations

import json
import os
import sys

import requests

API = "https://api.buffer.com"


def gql(key: str, query: str) -> dict:
    r = requests.post(
        API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": query},
        timeout=60,
    )
    try:
        data = r.json()
    except Exception:
        print(r.text[:800], file=sys.stderr)
        return {}
    if data.get("errors"):
        print("errors", json.dumps(data["errors"])[:800], file=sys.stderr)
    return data


def main() -> None:
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        print("Need BUFFER_API_KEY")
        sys.exit(1)

    org_id = os.environ.get("BUFFER_ORG_ID", "").strip()

    data = gql(
        key,
        """
        query {
          account {
            id
            email
            organizations { id name }
          }
        }
        """,
    )
    print("=== ACCOUNT / ORGS ===")
    print(json.dumps(data, indent=2))

    orgs = ((data.get("data") or {}).get("account") or {}).get("organizations") or []
    if not org_id and orgs:
        org_id = orgs[0].get("id") or ""
        print("Using first org:", org_id, file=sys.stderr)

    if not org_id:
        print("No organizationId — set BUFFER_ORG_ID")
        sys.exit(1)

    data2 = gql(
        key,
        f"""
        query {{
          channels(input: {{ organizationId: {json.dumps(org_id)} }}) {{
            id
            name
            displayName
            service
            isQueuePaused
          }}
        }}
        """,
    )
    print("=== CHANNELS ===")
    print(json.dumps(data2, indent=2))

    channels = (data2.get("data") or {}).get("channels") or []
    print("\n=== SUMMARY ===")
    for c in channels:
        print(
            f"- service={c.get('service')} | name={c.get('name')} | "
            f"display={c.get('displayName')} | id={c.get('id')} | paused={c.get('isQueuePaused')}"
        )
    if not channels:
        print("(no channels returned)")


if __name__ == "__main__":
    main()
