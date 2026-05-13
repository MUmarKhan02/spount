# spount 

Check a Spotify song's real stream count from the terminal.

---

## Install

**Requirements:** Python 3.6+ (no extra packages — uses stdlib only)

### 1. Get Spotify credentials (free, 2 min)

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account (free accounts work)
3. Click **Create app** → give it any name/description
4. Under **Redirect URIs** add `https://localhost` → click **Add**
5. Check **Web API** → agree to terms → Save
6. Click **Settings** → copy your **Client ID** and **Client Secret**

### 2. Run setup

```bash
python spount.py --setup
# Paste your Client ID and Client Secret when prompted
# Credentials are saved to ~/.spount_config.json
```

### 3. (Optional) Make it a global command

**Mac/Linux:**
```bash
chmod +x spount.py
sudo mv spount.py /usr/local/bin/spount
```

**Windows:**

Create `spount.bat` in the same folder:
```bat
@echo off
python "C:\path\to\spount.py" %*
```
Then copy both `spount.py` and `spount.bat` to `C:\Windows\System32`.

---

## Usage

```bash
# Search by song name → pick from a list
spount "levitating"

# Narrow with artist name
spount "levitating" "dua lipa"
```

---

## Output

Stream counts are pulled from **kworb.net**, which tracks real Spotify stream totals updated daily.

```
────────────────────────────────────────────────────
  Blinding Lights [E]
  The Weeknd  .  After Hours (2020)  .  3:20

  Streams   ████████████████████  4.28B
            Billion-stream club
  Source: kworb.net (total Spotify streams)

  https://open.spotify.com/track/...
```

If kworb doesn't track the song (common for non-Western/foreign music), spount falls back to showing Spotify's popularity score (0–100) instead.

---

## Notes

- Stream counts are **not** available via Spotify's public API — they removed that years ago. spount scrapes kworb.net as a workaround.
- kworb.net primarily tracks mainstream Western music. Non-English tracks may show no stream data.
- Credentials are stored locally in `~/.spount_config.json`. To reconfigure: `spount --setup`
