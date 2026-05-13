# Abyss

A 2D action-platformer through Hallownest, inspired by *Hollow Knight*. Single-file Python game using only `pygame` — no external assets. All sprites, palettes, parallax layers, and effects are generated at runtime.

```
 14 hand-crafted area intros
 99 procedurally generated sublevels per area  (≈1,400 levels total)
 5  telegraphed boss fights
 6  shop upgrades (currency: mites)
 Nail combat — 4 directions + downward pogo bounce
 Glide, double-jump, dash, wall-jump
 Light accumulator, area-specific ambient particles, multi-layer parallax
```

## Install

```
git clone https://github.com/the-priest/abyss.git
cd abyss
pip install -r requirements.txt
python3 abyss.py
```

Or use the bundled installer to put a launcher icon and binary on your system:

```
./install.sh
```

This places `abyss` in `~/.local/bin/`, the icon in `~/.local/share/abyss/`, and a `.desktop` entry in `~/.local/share/applications/` so the game shows up in your app launcher.

## Controls

### Keyboard
| Action | Key |
| --- | --- |
| Move | `A` / `D` or arrow keys |
| Jump (hold for higher) | `Space`, `W`, `Up` |
| Double jump | tap jump again midair |
| Glide | hold jump after double-jump |
| Dash | `Left Shift` |
| Nail attack | `J` |
| Upward slash | `Up` + `J` |
| Pogo slash | `Down` + `J` (in air) — bounces off enemies and hazards |
| Talk / Trade | `E` or `Up` near shopkeeper |
| Restart sublevel | `R` |
| Map | `Tab` |
| Quit | `Esc` |

### Gamepad (Xbox / 8BitDo layout)
| Action | Button |
| --- | --- |
| Move | left stick / D-pad |
| Jump | A (btn 0) |
| Dash | B (btn 1) |
| Nail | X (btn 2) |
| Next / previous sublevel | RB / LB |
| Map | Back (btn 6) |
| Quit | Start (btn 7) |

## How to play

You begin in **Dirtmouth** with a single life. Walk right past the NPC to find the **Merchant** (taller robed figure with a glowing lantern). Approach him and press `E` or `Up` to open the shop.

- Kill enemies to drop **mites** (yellow gems). Collect them; they also drop from floating mites scattered through levels.
- Reach the **door** at the end of each sublevel to advance. Dying costs you **half** your banked mites.
- Boss sublevels (sub 1 of areas with bosses) require you to defeat the boss before the door becomes passable.
- Complete enough sublevels in an area (threshold rises with progression: 70% → 100%) to unlock the next area.

## Save data

```
~/.local/share/abyss/save.json
```

Delete it to start fresh:

```
rm -f ~/.local/share/abyss/save.json
```

## Environment variables

| Variable | Effect |
| --- | --- |
| `ABYSS_WINDOW=1` | Run in a window instead of fullscreen |
| `ABYSS_NO_PAD=1` | Disable gamepad detection |

## Requirements

- Python 3.8+
- pygame 2.x

Runs on Linux, macOS, Windows. Tested on Kali NetHunter (sdm845, Phosh / Wayland, 1080×2280 display).

## License

MIT — see `LICENSE`.
