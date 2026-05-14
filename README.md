# ABYSS

A Hollow Knight–flavored 2D action-platformer in a single Python file.
Pygame. No external assets — every sprite, particle, and tile is drawn
procedurally at runtime.

```
14 hand-crafted area intros · 99 procedurally generated sublevels per area
5 telegraphed boss fights · nail combat · double-jump · dash · glide
parallax · particle lights · gamepad support · doom-classical soundtrack
```

---

## One-command install

After editing `install.sh` and replacing `REPLACE-ME` with your GitHub
username, anyone (including you, on a fresh machine) can install with:

```sh
curl -sL https://raw.githubusercontent.com/the-priest/abyss5/main/install.sh | sh
```

This clones the repo to `~/abyss5`, installs `pygame`, and downloads ~5
public-domain doom-classical tracks into `~/Music/abyss/`.

Then:

```sh
cd ~/abyss5 && python3 abyss.py
```

---

## Manual install

```sh
git clone https://github.com/the-priest/abyss5.git ~/abyss5
cd ~/abyss5
pip install pygame --break-system-packages
python3 fetch_music.py
python3 abyss.py
```

---

## Update an existing install

From inside the clone (both PC and phone):

```sh
./update.sh
```

That's just:

```sh
git pull --ff-only
python3 fetch_music.py
```

---

## Controls

### Keyboard

```
A / D / arrows         move
Space / W / Up         jump (hold = higher; x2 = double jump;
                       hold after double jump = glide)
Left Shift             dash
J                      nail attack
Up + J                 upward slash
Down + J (in air)      pogo slash (bounce off enemies / hazards)
E / Up near shopkeeper open shop
R                      restart sublevel
Tab                    map
Esc                    quit
```

### Music controls (any time)

```
V    mute / unmute
N    next track
-    volume down
=    volume up
```

### Gamepad (8BitDo / Xbox layout, auto-detected)

```
Left stick / D-pad     move
A (btn 0)              jump / hold for glide
B (btn 1)              dash
X (btn 2)              nail attack
RB / LB                next / previous sublevel
Back (btn 6)           map
Start (btn 7)          quit
```

To disable the gamepad: `ABYSS_NO_PAD=1 python3 abyss.py`
To run windowed instead of fullscreen: `ABYSS_WINDOW=1 python3 abyss.py`

---

## Soundtrack

`fetch_music.py` downloads ~80 MB of public-domain orchestral tracks into
`~/Music/abyss/`:

- Bach — Toccata and Fugue in D Minor (pipe organ)
- Bach — Toccata and Fugue (US Marine Band brass)
- Wagner — Ride of the Valkyries (American Symphony Orchestra, 1921)
- Wagner — Ride of the Valkyries (NPS Edison Diamond Disc, 1921)
- Mussorgsky — Night on Bald Mountain

ABYSS also scans these folders, in order:

```
~/Music/abyss/
~/.local/share/abyss/music/
./music/    (next to abyss.py)
```

Drop your own `.mp3`, `.ogg`, `.wav`, or `.flac` files in any of them. They
join the shuffle. **Don't commit copyrighted audio to the repo** — the
`.gitignore` already excludes audio files for that reason.

---

## Save data

`~/.local/share/abyss/save.json`

To reset: `rm -f ~/.local/share/abyss/save.json`

---

## License

MIT (code). Music files are public-domain recordings; ABYSS does not bundle
or distribute them in this repo — `fetch_music.py` downloads them from the
Internet Archive and Project Gutenberg on first run.
