# ABYSS

A 2D atmospheric platformer with a Hollow Knight–flavored vibe, single-file
Python. 14 areas × 99 procedurally generated sublevels each, 5 bosses, nail
combat, glide, dash, shop, gamepad support, public-domain music.

```
14 areas · 99 sublevels per area · 5 bosses · single-file Python
nail combat · pogo · dash · glide · charged attack
procedural sublevels with consistent area aesthetics
seamless music playback (Doom-classical public domain)
gamepad support · save/load · shop
```

---

## One-command install (any Linux, macOS, or Termux)

```sh
curl -sL https://raw.githubusercontent.com/the-priest/abyss5/main/install.sh | sh
```

The installer:

- detects your OS and package manager (apt, dnf, pacman, zypper, apk,
  xbps, emerge, brew, pkg on Termux)
- installs whatever's missing: `git`, `python3`, `pip`, `pygame`
- clones the repo to `~/abyss5`
- creates an `abyss` command on your PATH
- creates an app-launcher entry with icon (Linux desktops)
- fetches public-domain music to `~/Music/abyss/`

Tap the icon, or run:

```sh
abyss
```

## Update

Just re-run the installer:

```sh
curl -sL https://raw.githubusercontent.com/the-priest/abyss5/main/install.sh | sh
```

---

## Controls

### Keyboard

```
A / D / arrows         move
Space / W / Up         jump (hold for glide; double-tap for dash)
J / Z / Left-Mouse     nail attack
K                      heal (uses focus)
Tab                    world map
R                      restart current sublevel
Esc                    quit
M                      mute / unmute music
N                      skip to next track
[ / ]                  volume down / up
```

### Gamepad

```
Left stick / D-pad     move
A                      jump (hold to glide)
B                      dash
X                      nail attack
Y                      heal
Start                  map
Back                   quit
```

---

## Music

The installer downloads ~5 public-domain orchestral pieces to
`~/Music/abyss/`. You can drop your own `.mp3` / `.ogg` / `.wav` / `.flac`
files there and they'll play shuffled in-game.

In-game music controls: `M` mute, `N` skip, `[` / `]` volume.

---

## Save data

`~/.local/share/abyss/save.json`

Reset: `rm ~/.local/share/abyss/save.json`

---

## License

MIT.
