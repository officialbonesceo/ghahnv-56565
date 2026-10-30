#!/usr/bin/env python3
"""Upload output.mp4 to YouTube as a Short using OAuth refresh token.
Works for both full clips (script_job.json) and teasers (teaser_job.json).
"""
from __future__ import annotations
import json, os, re, sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def clean_yt_title(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"(?i)^(intro(duction)?|basics?)\s+(to|of)\s+", "", t).strip()
    t = re.sub(r"\s+", " ", t).strip(" -|#")
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t or "Daily science lesson"

def load_title() -> str:
    for p in ("title_short.txt", "hook.txt"):
        if Path(p).exists():
            t = Path(p).read_text(encoding="utf-8").strip().splitlines()[0].strip()
            if t:
                return clean_yt_title(t)[:95]
    for job_name in ("script_job.json", "teaser_job.json"):
        if Path(job_name).exists():
            try:
                d = json.loads(Path(job_name).read_text(encoding="utf-8"))
                t = (d.get("short_title") or d.get("title") or "").strip()
                if t:
                    return clean_yt_title(t)[:95]
            except Exception:
                pass
    return "Daily science lesson"

def load_description(title: str) -> str:
    parts = [title.strip(), ""]
    if Path("script.txt").exists():
        script = Path("script.txt").read_text(encoding="utf-8").strip()
        first = re.split(r"(?<=[.!?])\s+", script)
        snippet = " ".join(first[:2]).strip()[:280]
        if snippet:
            parts.extend([snippet, ""])
    if Path("teaser_job.json").exists():
        try:
            d = json.loads(Path("teaser_job.json").read_text(encoding="utf-8"))
            qs = d.get("questions") or []
            if qs:
                parts.append("Try these before the answers:")
                for q in qs[:3]:
                    parts.append(f"Q{q.get('index', '')}: {(q.get('question') or '')[:120]}")
                parts.append("")
                parts.append("Answers:")
                for q in qs[:3]:
                    parts.append(f"Q{q.get('index', '')}: {q.get('answer', '')} — {(q.get('reason') or '')[:100]}")
                parts.append("")
        except Exception:
            pass
    if Path("script_job.json").exists():
        try:
            d = json.loads(Path("script_job.json").read_text(encoding="utf-8"))
            dyk = (d.get("did_you_know") or "").strip()
            if dyk and "write the" not in dyk.lower():
                parts.extend([f"Did you know: {dyk[:200]}", ""])
        except Exception:
            pass
    parts.append("Daily lessons for students worldwide — exam-ready and clear.")
    parts.append("Subscribe for more with Mike.")
    parts.append("")
    parts.append(
        "#Shorts #Science #Education #Learning #STEM #StudyTips #ExamPrep "
        "#Quiz #Students #School #Edutok #LearnOnYouTube"
    )
    return "\n".join(parts)[:4800]

def credentials_from_env() -> Credentials:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh):
        raise SystemExit("Need YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN")
    creds = Credentials(
        token=None, refresh_token=refresh, token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret, scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds

def main() -> None:
    video = Path("output.mp4")
    if not video.exists() or video.stat().st_size < 1000:
        print("No output.mp4 — skip YouTube")
        Path("youtube_result.json").write_text(json.dumps({"error": "no_output_mp4"}, indent=2), encoding="utf-8")
        return
    try:
        creds = credentials_from_env()
    except Exception as e:
        print("AUTH_FAIL", e, file=sys.stderr)
        Path("youtube_result.json").write_text(json.dumps({"error": "auth_fail", "detail": str(e)[:500]}, indent=2), encoding="utf-8")
        return
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID", "").strip()
    try:
        ch = youtube.channels().list(part="id,snippet", mine=True).execute()
        items = ch.get("items") or []
        if items:
            got = items[0]["id"]
            print("CHANNEL", got, items[0].get("snippet", {}).get("title", ""))
            if not channel_id:
                channel_id = got
    except Exception as e:
        print("channel list", e, file=sys.stderr)
    title = load_title().strip()
    if "#shorts" not in title.lower():
        title = f"{title[:88].rstrip(' -|#')} #Shorts"
    description = load_description(title)
    privacy = os.environ.get("YOUTUBE_PRIVACY", "public").strip().lower()
    if privacy not in ("public", "unlisted", "private"):
        privacy = "public"
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "categoryId": "27",
            "tags": ["Shorts", "science", "education", "STEM", "learning", "study", "students", "exam", "quiz", "Mike"],
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "madeForKids": False},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True, chunksize=256 * 1024)
    print("UPLOAD_START", title, privacy, video.stat().st_size)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"progress {int(status.progress() * 100)}%", file=sys.stderr)
    except HttpError as e:
        err = e.content.decode("utf-8", errors="replace") if e.content else str(e)
        print("UPLOAD_FAIL", e.resp.status, err[:800], file=sys.stderr)
        Path("youtube_result.json").write_text(json.dumps({"error": "upload_fail", "status": e.resp.status, "detail": err[:1500], "title": title, "privacy": privacy, "channel_id": channel_id}, indent=2), encoding="utf-8")
        return
    vid = (response or {}).get("id") or ""
    url = f"https://youtu.be/{vid}" if vid else ""
    print("YOUTUBE_OK", vid, url)
    Path("youtube_result.json").write_text(json.dumps({"ok": True, "video_id": vid, "url": url, "title": title, "privacy": privacy, "channel_id": channel_id, "response": {"id": vid, "snippet": (response or {}).get("snippet", {}), "status": (response or {}).get("status", {})}}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
