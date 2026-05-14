#!/usr/bin/env python3
"""
fetch_music.py — pull public-domain doom-classical for ABYSS.

Downloads about 5 orchestral tracks (all in the public domain) into
~/Music/abyss/.  ABYSS will pick them up automatically next time you run it.

Tracks fetched:
    Bach        - Toccata and Fugue in D Minor (pipe organ, full)
    Bach        - Toccata and Fugue in D Minor (US Marine Band brass version)
    Wagner      - Ride of the Valkyries (1921 American Symphony Orchestra)
    Wagner      - Ride of the Valkyries (NPS / Edison Diamond Disc, 1921)
    Mussorgsky  - Night on Bald Mountain

All five are confirmed public domain.

Run once:
    python3 fetch_music.py

Re-running is safe — already-downloaded files are skipped.
"""
import urllib.request
import urllib.parse
import json
import sys
from pathlib import Path

OUT = Path.home() / "Music" / "abyss"
OUT.mkdir(parents=True, exist_ok=True)

UA = "abyss-music-fetcher/1.0 (+https://archive.org)"
TIMEOUT = 60


def _http(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  ✓ already have   {dest.name}")
        return True
    print(f"  ↓ downloading    {dest.name}")
    try:
        with _http(url) as r, open(dest, "wb") as f:
            total = 0
            while True:
                chunk = r.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        print(f"      saved ({total // 1024} KB)")
        return True
    except Exception as e:
        print(f"      FAILED: {e}")
        try:
            dest.unlink()
        except Exception:
            pass
        return False


def from_archive_org(identifier, save_as=None):
    """Look up archive.org item via its metadata API, find an MP3, download."""
    meta_url = f"https://archive.org/metadata/{identifier}"
    print(f"\n[archive.org / {identifier}]")
    try:
        with _http(meta_url) as r:
            meta = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  metadata FAILED: {e}")
        return False
    files = meta.get("files", [])
    # prefer VBR MP3 if present, otherwise any mp3
    pick = None
    for fmt in ("VBR MP3", "128Kbps MP3", "96Kbps MP3", "64Kbps MP3"):
        for f in files:
            if f.get("format") == fmt and f.get("name", "").lower().endswith(".mp3"):
                pick = f
                break
        if pick:
            break
    if not pick:
        for f in files:
            if f.get("name", "").lower().endswith(".mp3"):
                pick = f
                break
    if not pick:
        print("  no mp3 found in item")
        return False
    url = (f"https://archive.org/download/{identifier}/"
           + urllib.parse.quote(pick["name"]))
    filename = save_as or f"{identifier}__{pick['name']}".replace(" ", "_")
    return download(url, OUT / filename)


def from_url(url, filename):
    host = url.split("/")[2]
    print(f"\n[{host}]")
    return download(url, OUT / filename)


def main():
    print(f"ABYSS music fetcher")
    print(f"Saving to: {OUT}\n")

    n = 0

    # Bach – Toccata and Fugue in D Minor (pipe organ; PD)
    if from_archive_org("ToccataAndFugueInDMinor",
                        save_as="Bach_-_Toccata_and_Fugue_organ.mp3"):
        n += 1

    # Bach – Toccata and Fugue in D Minor (US Marine Band; PD govt work)
    if from_archive_org("ToccataAndFugue",
                        save_as="Bach_-_Toccata_and_Fugue_Marine_Band.mp3"):
        n += 1

    # Wagner – Ride of the Valkyries (Project Gutenberg, 1921 recording, PD)
    if from_url(
        "https://www.gutenberg.org/files/10177/10177-m/10177-m-001.mp3",
        "Wagner_-_Ride_of_the_Valkyries_1921.mp3"
    ):
        n += 1

    # Wagner – Ride of the Valkyries (NPS Edison Diamond Disc, 1921, PD)
    if from_archive_org("EDIS-SRP-0197-06",
                        save_as="Wagner_-_Ride_of_the_Valkyries_NPS.mp3"):
        n += 1

    # Mussorgsky – Night on Bald Mountain (carport orchestra arrangement, PD)
    if from_archive_org("a-night-on-bald-mountain",
                        save_as="Mussorgsky_-_Night_on_Bald_Mountain.mp3"):
        n += 1

    print(f"\n────────────────────────────")
    print(f"Done. {n} track(s) saved.")
    print(f"Folder: {OUT}")
    if n == 0:
        print("\nNothing downloaded. Check internet and try again.")
        sys.exit(1)
    print("\nIn ABYSS:  V mute  /  N next track  /  -/= volume")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(1)
