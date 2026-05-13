#!/usr/bin/env python3
"""
spount - Spotify song stream checker
Usage:
    spount "song name"
    spount "song name" "artist name"
"""

import sys
import json
import argparse
import base64
import urllib.request
import urllib.parse
import urllib.error
import re
from pathlib import Path

CONFIG_FILE = Path.home() / ".spount_config.json"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BAR_FULL  = "█"
BAR_EMPTY = "░"


# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def setup_credentials():
    print(f"\n{BOLD}spount setup{RESET}")
    print(f"{DIM}You need a free Spotify Developer account.{RESET}")
    print(f"{DIM}1. Go to https://developer.spotify.com/dashboard{RESET}")
    print(f"{DIM}2. Create an app (any name){RESET}")
    print(f"{DIM}3. Copy your Client ID and Client Secret{RESET}\n")
    client_id     = input("Paste your Client ID:     ").strip()
    client_secret = input("Paste your Client Secret: ").strip()
    if not client_id or not client_secret:
        print(f"{RED}Error: Both fields are required.{RESET}")
        sys.exit(1)
    save_config({"client_id": client_id, "client_secret": client_secret})
    print(f"\n{GREEN}Credentials saved to ~/.spount_config.json{RESET}\n")
    return client_id, client_secret


# ── Spotify API ───────────────────────────────────────────────────────────────

def get_token(client_id, client_secret):
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "invalid_client" in body:
            print(f"{RED}Invalid credentials. Run 'spount --setup' to fix.{RESET}")
        else:
            print(f"{RED}Auth error: {e.code}{RESET}")
        sys.exit(1)


def get_track_by_id(token, track_id):
    req = urllib.request.Request(
        f"https://api.spotify.com/v1/tracks/{track_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError:
        return None


def search_tracks(token, song, artist=None, limit=8):
    query = f"track:{song}"
    if artist:
        query += f" artist:{artist}"
    params = urllib.parse.urlencode({"q": query, "type": "track", "limit": limit})
    req = urllib.request.Request(
        f"https://api.spotify.com/v1/search?{params}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["tracks"]["items"]
    except urllib.error.HTTPError as e:
        print(f"{RED}Search failed: {e.code}{RESET}")
        sys.exit(1)


# ── Kworb stream scraper ──────────────────────────────────────────────────────

def fetch_streams_kworb(spotify_track_id):
    """Fetch real stream count from kworb.net using the Spotify track ID."""
    url = f"https://kworb.net/spotify/track/{spotify_track_id}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

    # kworb puts stream counts in table cells as large comma-separated numbers
    matches = re.findall(r'<td[^>]*>([\d,]+)</td>', page)
    candidates = []
    for m in matches:
        n = int(m.replace(",", ""))
        if n > 500_000:
            candidates.append(n)

    if not candidates:
        return None

    # Return the largest plausible number (total streams)
    return max(candidates)


# ── Display helpers ───────────────────────────────────────────────────────────

def format_streams(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def streams_bar(n, width=20):
    MAX = 2_000_000_000  # 2B = full bar (Shape of You territory)
    filled = min(width, round(n / MAX * width))
    bar = BAR_FULL * filled + BAR_EMPTY * (width - filled)
    if n >= 1_000_000_000:
        color = GREEN
    elif n >= 300_000_000:
        color = CYAN
    elif n >= 50_000_000:
        color = YELLOW
    else:
        color = DIM
    return f"{color}{bar}{RESET} {BOLD}{format_streams(n)}{RESET}"


def streams_label(n):
    if n >= 2_000_000_000:
        return f"{GREEN}All-time legend{RESET}"
    elif n >= 1_000_000_000:
        return f"{GREEN}Billion-stream club{RESET}"
    elif n >= 500_000_000:
        return f"{GREEN}Massive global hit{RESET}"
    elif n >= 200_000_000:
        return f"{CYAN}Huge hit{RESET}"
    elif n >= 50_000_000:
        return f"{CYAN}Very popular{RESET}"
    elif n >= 10_000_000:
        return f"{YELLOW}Popular{RESET}"
    elif n >= 1_000_000:
        return f"{YELLOW}Decent following{RESET}"
    else:
        return f"{DIM}Underground / niche{RESET}"


def format_duration(ms):
    total_sec = ms // 1000
    return f"{total_sec // 60}:{total_sec % 60:02d}"


def popularity_bar(score, width=20):
    filled = round(score / 100 * width)
    bar = BAR_FULL * filled + BAR_EMPTY * (width - filled)
    if score >= 75:
        color = GREEN
    elif score >= 45:
        color = YELLOW
    else:
        color = DIM
    return f"{color}{bar}{RESET} {BOLD}{score}{RESET}/100"


def popularity_label(score):
    if score >= 85:
        return f"{GREEN}Global phenomenon{RESET}"
    elif score >= 70:
        return f"{GREEN}Massive hit{RESET}"
    elif score >= 55:
        return f"{CYAN}Very popular{RESET}"
    elif score >= 40:
        return f"{YELLOW}Moderately popular{RESET}"
    elif score >= 20:
        return f"{DIM}Niche / underground{RESET}"
    else:
        return f"{DIM}Obscure / rare{RESET}"


def display_track(track, streams, popularity=None):
    name      = track["name"]
    artists   = ", ".join(a["name"] for a in track["artists"])
    album     = track["album"]["name"]
    release   = track["album"]["release_date"][:4]
    duration  = format_duration(track["duration_ms"])
    explicit  = f" {RED}[E]{RESET}" if track["explicit"] else ""
    track_url = track["external_urls"].get("spotify", "")

    print(f"\n{'─'*52}")
    print(f"\n  {BOLD}{name}{RESET}{explicit}")
    print(f"  {CYAN}{artists}{RESET}  {DIM}.  {album}  ({release})  .  {duration}{RESET}")

    if streams:
        print(f"\n  Streams   {streams_bar(streams)}")
        print(f"            {streams_label(streams)}")
        print(f"  {DIM}Source: kworb.net (total Spotify streams){RESET}")
    else:
        print(f"\n  {YELLOW}Stream count not available for this track.{RESET}")
        if popularity is not None and popularity > 0:
            print(f"\n  Popularity  {popularity_bar(popularity)}")
            print(f"              {popularity_label(popularity)}")
            print(f"  {DIM}(Spotify popularity score, 0-100){RESET}")
        else:
            print(f"  {DIM}No data available — track may not be widely tracked.{RESET}")

    if track_url:
        print(f"\n  {DIM}{track_url}{RESET}")
    print()


# ── Track picker ──────────────────────────────────────────────────────────────

def pick_track(tracks, song):
    if not tracks:
        print(f"\n{RED}No results found for \"{song}\"{RESET}\n")
        sys.exit(0)

    print(f"\n{BOLD}Results for \"{song}\"{RESET}")
    print(f"{'─'*52}")

    for i, t in enumerate(tracks, 1):
        artists  = ", ".join(a["name"] for a in t["artists"])
        album    = t["album"]["name"]
        release  = t["album"]["release_date"][:4]
        explicit = f" {RED}[E]{RESET}" if t["explicit"] else ""
        print(f"  {DIM}{i:>2}.{RESET} {BOLD}{t['name']}{RESET}{explicit}")
        print(f"       {CYAN}{artists}{RESET}  {DIM}. {album} ({release}){RESET}")

    print(f"\n  {DIM}0.  Cancel{RESET}")
    print(f"{'─'*52}")

    while True:
        try:
            choice = input(f"\nChoose [1-{len(tracks)}]: ").strip()
            if choice == "0":
                print("Cancelled.")
                sys.exit(0)
            idx = int(choice) - 1
            if 0 <= idx < len(tracks):
                return tracks[idx]
            print(f"{YELLOW}Enter a number between 1 and {len(tracks)}.{RESET}")
        except (ValueError, EOFError):
            print(f"{YELLOW}Enter a number.{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="spount",
        description="Check Spotify song stream counts",
    )
    parser.add_argument("song",   nargs="?", help="Song name")
    parser.add_argument("artist", nargs="?", help="Artist name (optional)")
    parser.add_argument("--setup", action="store_true", help="Configure Spotify credentials")
    args = parser.parse_args()

    if args.setup:
        setup_credentials()
        return

    if not args.song:
        parser.print_help()
        sys.exit(0)

    config = load_config()
    if not config.get("client_id") or not config.get("client_secret"):
        print(f"{YELLOW}No credentials found. Let's set up spount.{RESET}")
        client_id, client_secret = setup_credentials()
    else:
        client_id     = config["client_id"]
        client_secret = config["client_secret"]

    token  = get_token(client_id, client_secret)
    tracks = search_tracks(token, args.song, args.artist)

    if args.artist and len(tracks) == 1:
        track = tracks[0]
    elif args.artist and len(tracks) > 0:
        track = pick_track(tracks, f"{args.song} - {args.artist}")
    else:
        track = pick_track(tracks, args.song)

    print(f"\n{DIM}Fetching stream count...{RESET}", end="", flush=True)
    streams = fetch_streams_kworb(track["id"])
    print(f"\r{' ' * 30}\r", end="", flush=True)

    popularity = None
    if not streams:
        full_track = get_track_by_id(token, track["id"])
        if full_track:
            popularity = full_track.get("popularity", 0)

    display_track(track, streams, popularity)


if __name__ == "__main__":
    main()