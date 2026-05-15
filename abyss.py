#!/usr/bin/env python3
"""
abyss.py — Hollow Knight-flavored platformer through Hallownest.

A 2D action-platformer with nail combat, glide, currency-based upgrades,
14 hand-crafted area intros, 99 procedurally generated sublevels per area,
and 5 telegraphed boss fights. Built on pygame, single file, no assets.

Repository: https://github.com/yourname/abyss
License: MIT

Keyboard:
  A/D, arrows .............. move
  Space/W/Up ............... jump (hold = higher; x2 = double jump;
                                   hold after double jump = glide)
  Left Shift ............... dash
  J ........................ nail attack
  Up + J ................... upward slash
  Down + J (in air) ........ pogo slash (bounce off enemies / hazards)
  E / Up near shopkeeper ... open shop
  R ........................ restart sublevel
  Tab ...................... map
  Esc ...................... quit

Music (drop your own tracks into ~/Music/abyss/  —  .mp3 .ogg .wav .flac):
  V ........................ mute / unmute
  N ........................ skip to next track
  -  /  = .................. volume down / up

Gamepad (8BitDo / Xbox layout):
  Left stick / D-pad ....... move
  A (btn 0) ................ jump / hold for glide
  B (btn 1) ................ dash
  X (btn 2) ................ nail attack
  RB / LB .................. next / previous sublevel
  Back (btn 6) ............. map
  Start (btn 7) ............ quit

Save:  ~/.local/share/abyss/save.json
Reset save:  rm -f ~/.local/share/abyss/save.json
Disable pad:  ABYSS_NO_PAD=1 abyss
Windowed mode:  ABYSS_WINDOW=1 abyss   (default = fullscreen)
"""
import pygame, sys, math, random, os, json, hashlib
from pathlib import Path

pygame.init()
# Audio: try to init mixer with metal-friendly settings. Safe if it fails.
try:
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
    pygame.mixer.init()
    _AUDIO_OK = True
except Exception:
    _AUDIO_OK = False

WIDTH, HEIGHT = 1280, 720
if os.environ.get('ABYSS_WINDOW') == '1':
    SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
else:
    SCREEN = pygame.display.set_mode((WIDTH, HEIGHT),
        pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Abyss - Hallownest")
pygame.mouse.set_visible(False)
CLOCK = pygame.time.Clock()
FPS = 60

SAVE_DIR = Path.home() / ".local" / "share" / "abyss"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
SAVE_FILE = SAVE_DIR / "save.json"

try:
    FONT = pygame.font.SysFont("dejavusansmono", 18)
    BIG = pygame.font.SysFont("dejavusansmono", 46, bold=True)
    HUGE = pygame.font.SysFont("dejavusansmono", 64, bold=True)
    MID = pygame.font.SysFont("dejavusansmono", 26, bold=True)
    SMALL = pygame.font.SysFont("dejavusansmono", 13)
except Exception:
    FONT = pygame.font.Font(None, 20)
    BIG = pygame.font.Font(None, 50)
    HUGE = pygame.font.Font(None, 68)
    MID = pygame.font.Font(None, 28)
    SMALL = pygame.font.Font(None, 15)

# Physics
TILE = 32
GRAVITY = 0.55
TERMINAL = 14
GLIDE_FALL = 1.6
JUMP_VEL = -11.5
JUMP_CUT = 0.45
WALK = 4.5
AIR_ACCEL = 0.35
GROUND_ACCEL = 0.7
FRICTION = 0.78
WALL_SLIDE_MAX = 2.5
WALL_JUMP_X = 7.5
WALL_JUMP_Y = -10.5
DASH_VEL = 12
DASH_FRAMES = 11
DASH_COOLDOWN = 28
COYOTE = 6
BUFFER = 6

# Combat
NAIL_BASE_DAMAGE = 1
NAIL_BASE_REACH = 48
NAIL_HEIGHT = 40
NAIL_ACTIVE_FRAMES = 8
NAIL_COOLDOWN = 14
NAIL_POGO_VEL = -10
HIT_PAUSE_FRAMES = 4
SLOWMO_FRAMES = 8

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# Palettes — now with ambient effect and light color per area
def P(sky_t, sky_b, far, mid, near, plat, edge, accent, fog, motes,
      ambient='dust', light_c=None, rain=False):
    return dict(sky_top=sky_t, sky_bot=sky_b, far=far, mid=mid, near=near,
                platform=plat, edge=edge, accent=accent, fog=fog,
                motes=motes, ambient=ambient,
                light=light_c if light_c else accent, rain=rain)

PAL = {
    'dirtmouth': P((60,50,85), (22,18,40), (36,30,58), (24,20,44),
                   (14,12,28), (40,34,60), (70,60,95), (180,230,255),
                   (90,100,150,22), (180,220,255), ambient='snow'),
    'crossroads': P((50,30,50), (18,12,24), (48,28,50), (34,22,42),
                    (20,14,28), (46,28,48), (80,50,80), (255,180,100),
                    (110,70,90,26), (255,200,130), ambient='embers'),
    'greenpath': P((38,70,55), (12,28,22), (28,58,42), (20,42,30),
                   (10,24,16), (28,52,36), (60,110,70), (140,240,160),
                   (70,130,90,28), (170,255,180), ambient='leaves'),
    'fungal': P((60,40,70), (22,14,30), (54,32,60), (40,22,46),
                (20,12,28), (52,30,58), (120,70,130), (230,140,230),
                (120,70,130,28), (240,180,240), ambient='spores'),
    'city': P((38,52,80), (12,18,36), (34,46,70), (22,32,54),
              (12,18,32), (32,42,65), (70,90,130), (180,220,255),
              (100,130,190,36), (200,230,255), ambient='rain', rain=True),
    'waterways': P((20,40,60), (6,16,26), (18,38,56), (12,26,40),
                   (6,14,22), (18,34,48), (60,110,150), (120,200,240),
                   (70,130,170,34), (140,220,255), ambient='bubbles'),
    'crystal': P((40,30,70), (14,10,28), (38,28,70), (26,18,50),
                 (14,10,28), (34,26,60), (140,100,220), (220,150,255),
                 (90,60,140,26), (220,180,255), ambient='sparkles'),
    'resting': P((40,36,50), (14,12,22), (36,32,46), (26,22,38),
                 (14,12,24), (34,30,46), (110,100,130), (220,210,240),
                 (80,72,100,30), (220,210,240), ambient='ghosts'),
    'cliffs': P((70,65,90), (30,26,50), (54,48,70), (36,32,54),
                (20,18,36), (44,38,60), (110,100,140), (220,220,240),
                (140,130,170,24), (230,230,250), ambient='wind'),
    'deepnest': P((20,10,22), (6,2,10), (18,10,22), (12,6,16),
                  (4,2,8), (16,8,20), (60,30,60), (200,60,90),
                  (50,20,50,50), (200,60,90), ambient='eyes',
                  light_c=(220,60,80)),
    'gardens': P((45,30,55), (16,10,22), (40,26,50), (28,18,38),
                 (14,10,22), (38,22,46), (120,60,130), (255,130,200),
                 (110,50,110,28), (255,170,220), ambient='petals'),
    'edge': P((60,40,30), (22,14,12), (50,32,26), (36,22,18),
              (20,12,10), (44,28,24), (130,80,50), (255,180,100),
              (120,70,50,26), (255,200,130), ambient='ash'),
    'basin': P((20,18,30), (6,6,14), (18,16,28), (12,10,22),
               (6,6,14), (16,14,26), (60,50,90), (160,200,240),
               (50,40,80,38), (180,210,250), ambient='mist'),
    'abyss': P((8,6,16), (1,1,4), (10,8,18), (5,4,12),
               (2,2,6), (14,12,24), (40,35,55), (220,220,220),
               (30,25,50,50), (220,220,220), ambient='void',
               light_c=(180,180,200)),
}

AREAS = [
    dict(id='dirtmouth', pal='dirtmouth', name="Dirtmouth",
         npc="Elder Brood",
         npc_line="The wind from below carries old voices. Tread softly.",
         shop="Merchant Brime", enemies=[], boss=None, danger=0),
    dict(id='crossroads', pal='crossroads', name="Forgotten Crossroads",
         npc="Cartographer Pinn",
         npc_line="Take this map. The roads have forgotten themselves.",
         shop=None, enemies=['crawler'], boss='warden', danger=1),
    dict(id='greenpath', pal='greenpath', name="Greenpath",
         npc="Hermit Mosk",
         npc_line="Acid runs in the veins of this place. Mind your step.",
         shop=None, enemies=['crawler', 'flyer'],
         boss='mantis_lord', danger=2),
    dict(id='fungal', pal='fungal', name="Fungal Wastes",
         npc="Sporeling Yvi",
         npc_line="Spores cloud the mind. Hold your breath when the bulbs burst.",
         shop=None, enemies=['flyer', 'spitter'], boss=None, danger=2),
    dict(id='city', pal='city', name="City of Tears",
         npc="Lamplighter Vess",
         npc_line="The rain never stops. It washes nothing clean.",
         shop="Trinketmaster Vor",
         enemies=['crawler', 'spitter'], boss='soul_tyrant', danger=3),
    dict(id='waterways', pal='waterways', name="Royal Waterways",
         npc="Drainsmith Orro",
         npc_line="Below the city, water carries every secret eventually.",
         shop=None, enemies=['flyer', 'spitter'], boss=None, danger=3),
    dict(id='crystal', pal='crystal', name="Crystal Peak",
         npc="Miner Carric",
         npc_line="The crystal sings if you listen. Don't listen too long.",
         shop=None, enemies=['crawler', 'flyer'], boss=None, danger=3),
    dict(id='resting', pal='resting', name="Resting Grounds",
         npc="Dreamer Thrane",
         npc_line="The dreamers stir. So must you, when called.",
         shop=None, enemies=['flyer'], boss=None, danger=2),
    dict(id='cliffs', pal='cliffs', name="Howling Cliffs",
         npc="Pilgrim Kael",
         npc_line="The wind here knows your name. It will not return it.",
         shop=None, enemies=['flyer', 'spitter'], boss=None, danger=2),
    dict(id='deepnest', pal='deepnest', name="Deepnest",
         npc="Spinner Talis",
         npc_line="Many eyes watch you here. Most belong to spiders.",
         shop=None, enemies=['crawler', 'flyer', 'spitter'],
         boss='nosk', danger=4),
    dict(id='gardens', pal='gardens', name="Queen's Gardens",
         npc="Vinekeeper Mira",
         npc_line="These gardens bloomed for a queen once. Now only thorns.",
         shop=None, enemies=['crawler', 'spitter'], boss=None, danger=4),
    dict(id='edge', pal='edge', name="Kingdom's Edge",
         npc="Wanderer Brask",
         npc_line="The husks here remember a god. They remember poorly.",
         shop="Old Salvager Quel",
         enemies=['crawler', 'flyer'], boss=None, danger=4),
    dict(id='basin', pal='basin', name="Ancient Basin",
         npc="Scholar Voss",
         npc_line="Below all kingdoms lies the older one. Below that, the wound.",
         shop=None, enemies=['crawler', 'flyer', 'spitter'],
         boss=None, danger=5),
    dict(id='abyss', pal='abyss', name="The Abyss",
         npc=None, npc_line=None, shop=None,
         enemies=['crawler', 'flyer', 'spitter'], boss='hollow', danger=5),
]
AREA_INDEX = {a['id']: i for i, a in enumerate(AREAS)}
SUBLEVELS_PER_AREA = 100

UPGRADES = [
    dict(id='nail_damage', name="Sharper Nail",
         desc="Each rank adds +1 nail damage.",
         base_cost=80, scale=1.6, max_rank=5),
    dict(id='nail_range', name="Longer Nail",
         desc="Each rank extends nail reach.",
         base_cost=240, scale=2.0, max_rank=2),
    dict(id='dash_cd', name="Quick Dash",
         desc="Each rank cuts dash cooldown.",
         base_cost=180, scale=1.7, max_rank=3),
    dict(id='triple_jump', name="Monarch Wings",
         desc="Gain a third air jump.",
         base_cost=800, scale=1.0, max_rank=1),
    dict(id='max_hp', name="Vessel Fragment",
         desc="Each rank adds +1 max HP.",
         base_cost=150, scale=1.8, max_rank=3),
    dict(id='iframes', name="Soul Shroud",
         desc="Longer i-frames after taking a hit.",
         base_cost=200, scale=1.6, max_rank=2),
]
UPGRADE_INDEX = {u['id']: i for i, u in enumerate(UPGRADES)}

def upgrade_cost(u, current_rank):
    return int(u['base_cost'] * (u['scale'] ** current_rank))

DEFAULT_SAVE = {
    'unlocked': ['dirtmouth'], 'completed': {}, 'mites': 0,
    'last_area': 'dirtmouth', 'last_sub': 0,
    'upgrades': {u['id']: 0 for u in UPGRADES},
}

def load_save():
    if SAVE_FILE.exists():
        try:
            data = json.loads(SAVE_FILE.read_text())
            for k, v in DEFAULT_SAVE.items():
                data.setdefault(k, v)
            for u in UPGRADES:
                data['upgrades'].setdefault(u['id'], 0)
            return data
        except Exception:
            pass
    return dict(DEFAULT_SAVE, completed={},
                upgrades={u['id']: 0 for u in UPGRADES})

def save_state(state):
    try:
        SAVE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass

def unlock_threshold(area_idx):
    if area_idx <= 0:
        return 0.0
    n = len(AREAS) - 1
    if n <= 1:
        return 1.0
    progress = (area_idx - 1) / (n - 1)
    return 0.70 + progress * 0.30


# ===========================================================================
# Particles — multiple particle kinds with proper physics, gravity, fade,
# additive blending, and rotation. Used for combat, ambience, and effects.
# ===========================================================================
class Particles:
    """Single particle pool used for all effects. Each particle is a dict.
    'kind' picks rendering style: 'glow' (additive radial), 'dust' (alpha
    soft disc), 'spark' (additive line trail), 'ember' (additive flickering).
    """
    def __init__(self):
        self.list = []
    def emit(self, x, y, n=1, color=(255,255,255), vel=(0,0), spread=0.6,
             life=50, size=2, gravity=0.0, glow=False, kind=None,
             friction=0.99):
        if kind is None:
            kind = 'glow' if glow else 'dust'
        for _ in range(n):
            self.list.append({
                'x': x, 'y': y,
                'vx': vel[0] + random.uniform(-spread, spread),
                'vy': vel[1] + random.uniform(-spread, spread),
                'life': max(4, life + random.randint(-life // 3, life // 3)),
                'max_life': life, 'color': color, 'size': size,
                'g': gravity, 'kind': kind, 'fric': friction,
                'flicker': random.random(),
            })
    def emit_spark_burst(self, x, y, n=12, color=(255,255,255), speed=3.0,
                        life=24):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(speed * 0.5, speed)
            self.list.append({
                'x': x, 'y': y, 'vx': math.cos(a)*sp, 'vy': math.sin(a)*sp,
                'life': life, 'max_life': life, 'color': color, 'size': 2,
                'g': 0.0, 'kind': 'spark', 'fric': 0.94,
                'flicker': random.random(),
            })
    def emit_shockwave(self, x, y, color=(255,255,255), n=24, speed=5.0,
                       life=30):
        for i in range(n):
            a = i / n * math.tau
            sp = speed
            self.list.append({
                'x': x, 'y': y, 'vx': math.cos(a)*sp, 'vy': math.sin(a)*sp,
                'life': life, 'max_life': life, 'color': color, 'size': 3,
                'g': 0.0, 'kind': 'spark', 'fric': 0.92,
                'flicker': random.random(),
            })
    def update(self):
        for p in self.list[:]:
            p['x'] += p['vx']; p['y'] += p['vy']
            p['vy'] += p['g']; p['vx'] *= p['fric']; p['vy'] *= p['fric']
            p['life'] -= 1
            p['flicker'] = (p['flicker'] + 0.15) % 1.0
            if p['life'] <= 0:
                self.list.remove(p)
    def draw(self, surf, camx, camy):
        for p in self.list:
            life_pct = p['life'] / max(1, p['max_life'])
            a = max(0, min(255, int(255 * life_pct)))
            r, g, b = p['color']
            s = max(1, int(p['size']))
            sx, sy = int(p['x'] - camx), int(p['y'] - camy)
            if sx < -20 or sx > WIDTH + 20 or sy < -20 or sy > HEIGHT + 20:
                continue
            kind = p['kind']
            if kind == 'glow':
                tmp = pygame.Surface((s*8, s*8), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (r,g,b,a//4), (s*4, s*4), s*4)
                pygame.draw.circle(tmp, (r,g,b,a//2), (s*4, s*4), s*2)
                pygame.draw.circle(tmp, (r,g,b,a), (s*4, s*4), s)
                surf.blit(tmp, (sx - s*4, sy - s*4),
                          special_flags=pygame.BLEND_ADD)
            elif kind == 'dust':
                tmp = pygame.Surface((s*4, s*4), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (r,g,b,a//2), (s*2, s*2), s*2)
                pygame.draw.circle(tmp, (r,g,b,a), (s*2, s*2), s)
                surf.blit(tmp, (sx - s*2, sy - s*2))
            elif kind == 'spark':
                # short trailing line in direction of motion
                tx = sx - p['vx'] * 1.5
                ty = sy - p['vy'] * 1.5
                tmp = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                # actually just draw direct — surface allocation each
                # particle is too expensive. Draw additively on a small
                # local surface instead.
                ssize = 16
                local = pygame.Surface((ssize*2, ssize*2), pygame.SRCALPHA)
                lx1, ly1 = ssize - p['vx']*1.5, ssize - p['vy']*1.5
                lx2, ly2 = ssize, ssize
                pygame.draw.line(local, (r,g,b,a), (lx1, ly1), (lx2, ly2), 2)
                pygame.draw.circle(local, (255,255,255,a), (int(lx2), int(ly2)), 2)
                surf.blit(local, (sx - ssize, sy - ssize),
                          special_flags=pygame.BLEND_ADD)
            elif kind == 'ember':
                # flickering brightness
                flick = 0.6 + p['flicker'] * 0.4
                aa = int(a * flick)
                tmp = pygame.Surface((s*8, s*8), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (r,g,b,aa//4), (s*4, s*4), s*4)
                pygame.draw.circle(tmp, (r,g,b,aa//2), (s*4, s*4), s*2)
                pygame.draw.circle(tmp, (255,255,200,aa), (s*4, s*4), 1)
                surf.blit(tmp, (sx - s*4, sy - s*4),
                          special_flags=pygame.BLEND_ADD)


# ===========================================================================
# Lights — collected each frame, blitted additively at end of world pass
# to give a real "glow" feel to lanterns, projectiles, the player's halo.
# ===========================================================================
class Lights:
    """Accumulates light sources during the frame; one additive blit at end."""
    def __init__(self):
        self.surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    def clear(self):
        self.surf.fill((0, 0, 0, 0))
    def add(self, x, y, radius, color, intensity=1.0):
        """Add a soft radial light at screen coordinates."""
        if x < -radius or x > WIDTH + radius:
            return
        if y < -radius or y > HEIGHT + radius:
            return
        r, g, b = color
        size = int(radius * 2)
        tmp = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        # 3-layer radial: faint outer, mid, bright core
        for steps, ar, mul in ((radius, 30, 0.5),
                                (radius * 0.6, 60, 0.7),
                                (radius * 0.3, 120, 1.0)):
            aa = int(ar * intensity * mul)
            pygame.draw.circle(tmp, (r, g, b, aa), (cx, cx), int(steps))
        self.surf.blit(tmp, (int(x) - cx, int(y) - cx))
    def blit(self, target):
        target.blit(self.surf, (0, 0), special_flags=pygame.BLEND_ADD)


# ===========================================================================
# Music — plays whatever audio files live in any of these folders:
#   ~/Music/abyss/
#   ~/.local/share/abyss/music/
#   ./music/              (next to abyss.py)
# Drop your own Metallica / Slipknot / Tool / Tenacious D tracks in there.
# Supported: .mp3 .ogg .wav .flac
# Controls: M = mute, [ = vol down, ] = vol up, N = next track
# ===========================================================================
class Music:
    EXTS = ('.mp3', '.ogg', '.wav', '.flac')
    # pygame user event id for "the current track just finished"
    END_EVENT = pygame.USEREVENT + 7

    def __init__(self):
        self.enabled = _AUDIO_OK
        self.tracks = []
        self.idx = -1
        self.next_idx = -1       # index of the queued-up next track
        self.muted = False
        self.volume = 0.55
        self.now_playing = ""
        self.now_playing_t = 0
        self.next_check = 0
        if not self.enabled:
            return
        self._scan()
        if self.tracks:
            try:
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.set_endevent(Music.END_EVENT)
            except Exception:
                self.enabled = False
                return
            self._play_next()
        # also ensure the music folder exists with a README so user
        # knows where to put files
        self._write_readme()

    def _candidate_dirs(self):
        home = Path.home()
        here = Path(__file__).parent if '__file__' in globals() else Path('.')
        return [
            home / "Music" / "abyss",
            home / ".local" / "share" / "abyss" / "music",
            here / "music",
        ]

    def _scan(self):
        seen = set()
        out = []
        for d in self._candidate_dirs():
            try:
                if d.is_dir():
                    for p in sorted(d.iterdir()):
                        if p.suffix.lower() in self.EXTS and p.name not in seen:
                            out.append(p)
                            seen.add(p.name)
            except Exception:
                continue
        random.shuffle(out)
        self.tracks = out

    def _write_readme(self):
        try:
            target = Path.home() / "Music" / "abyss"
            target.mkdir(parents=True, exist_ok=True)
            readme = target / "README.txt"
            if not readme.exists():
                readme.write_text(
                    "Drop .mp3 / .ogg / .wav / .flac files in this folder.\n"
                    "ABYSS will play them shuffled while you play.\n"
                    "\n"
                    "In-game controls:\n"
                    "  M  = mute / unmute\n"
                    "  N  = skip to next track\n"
                    "  [  = volume down\n"
                    "  ]  = volume up\n"
                )
        except Exception:
            pass

    def _queue_next_track(self):
        """Queue the next track so pygame plays it seamlessly after the
        current one ends. Sets self.next_idx so we know what's coming."""
        if not self.tracks:
            return
        self.next_idx = (self.idx + 1) % len(self.tracks)
        track = self.tracks[self.next_idx]
        try:
            pygame.mixer.music.queue(str(track))
        except Exception:
            # bad file — drop it and try the one after
            try:
                self.tracks.pop(self.next_idx)
            except Exception:
                pass
            self.next_idx = -1

    def _play_next(self):
        """Start playing the next track (or first track) immediately."""
        if not self.tracks:
            return
        self.idx = (self.idx + 1) % len(self.tracks)
        track = self.tracks[self.idx]
        try:
            pygame.mixer.music.load(str(track))
            pygame.mixer.music.set_volume(self.volume)  # re-apply each load
            pygame.mixer.music.play()
            self.now_playing = track.stem
            self.now_playing_t = 240
            self.next_idx = -1
            # Pre-queue the one that comes after so transitions are gapless.
            self._queue_next_track()
        except Exception:
            # bad file — skip
            self.tracks.pop(self.idx)
            self.idx -= 1
            if self.tracks:
                self._play_next()

    def handle_event(self, event):
        """Pump end-event from main loop so we can re-queue instantly."""
        if not self.enabled or not self.tracks:
            return
        if event.type == Music.END_EVENT:
            # The track that just ended was either the active one (the
            # queued track is now playing automatically) or we hit an
            # end without a queue. Either way, slide the idx forward
            # and queue another.
            if self.next_idx >= 0:
                self.idx = self.next_idx
                self.next_idx = -1
                self.now_playing = self.tracks[self.idx].stem
                self.now_playing_t = 240
                self._queue_next_track()
            else:
                # nothing was queued — just play the next one cold
                self._play_next()

    def tick(self):
        """Call once per frame. Fallback if endevent didn't fire (rare)."""
        if not self.enabled or not self.tracks:
            return
        if self.now_playing_t > 0:
            self.now_playing_t -= 1
        # safety net: if we're not muted and pygame says music isn't busy,
        # restart playback. Check less often to avoid spamming.
        self.next_check += 1
        if self.next_check >= 120:  # ~2 sec
            self.next_check = 0
            try:
                if not pygame.mixer.music.get_busy() and not self.muted:
                    self._play_next()
            except Exception:
                pass

    def toggle_mute(self):
        if not self.enabled: return
        self.muted = not self.muted
        try:
            if self.muted:
                pygame.mixer.music.pause()
            else:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.unpause()
                else:
                    self._play_next()
        except Exception:
            pass
        self.now_playing = "MUTED" if self.muted else self.tracks[self.idx].stem if self.tracks else ""
        self.now_playing_t = 90

    def skip(self):
        if not self.enabled or not self.tracks: return
        try: pygame.mixer.music.stop()
        except Exception: pass
        self._play_next()

    def vol_up(self):
        if not self.enabled: return
        self.volume = min(1.0, self.volume + 0.1)
        try: pygame.mixer.music.set_volume(self.volume)
        except Exception: pass
        self.now_playing = f"vol {int(self.volume * 100)}%"
        self.now_playing_t = 60

    def vol_down(self):
        if not self.enabled: return
        self.volume = max(0.0, self.volume - 0.1)
        try: pygame.mixer.music.set_volume(self.volume)
        except Exception: pass
        self.now_playing = f"vol {int(self.volume * 100)}%"
        self.now_playing_t = 60

    def draw_overlay(self, surf):
        if self.now_playing_t <= 0 or not self.now_playing:
            return
        # fade in over 15 frames, hold, fade out over 30 frames
        if self.now_playing_t > 210:
            a = int(255 * (240 - self.now_playing_t) / 30)
        elif self.now_playing_t < 30:
            a = int(255 * self.now_playing_t / 30)
        else:
            a = 255
        text = "♪ " + self.now_playing if not self.muted else "♪ muted"
        s = SMALL.render(text, True, (220, 220, 230))
        s.set_alpha(a)
        bg = pygame.Surface((s.get_width() + 16, s.get_height() + 8),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, int(a * 0.55)))
        x = WIDTH - bg.get_width() - 16
        y = HEIGHT - bg.get_height() - 16
        surf.blit(bg, (x, y))
        surf.blit(s, (x + 8, y + 4))


# ===========================================================================
# Gamepad
# ===========================================================================
PAD_JUMP = (0,); PAD_DASH = (1,); PAD_NAIL = (2,)
PAD_NEXT = (5,); PAD_PREV = (4,); PAD_MAP = (6,); PAD_QUIT = (7,)
PAD_AXIS_X = 0; PAD_AXIS_Y = 1; PAD_DEADZONE = 0.30


class Pad:
    def __init__(self):
        self.disabled = os.environ.get('ABYSS_NO_PAD') == '1'
        self.js = None; self.instance_id = None
        if self.disabled: return
        try: pygame.joystick.init()
        except pygame.error:
            self.disabled = True; return
        self._connect_first()
    def _is_real(self, js):
        try:
            return (js.get_numbuttons() + js.get_numaxes()
                    + js.get_numhats()) >= 2
        except pygame.error: return False
    def _connect_first(self):
        try: n = pygame.joystick.get_count()
        except pygame.error: return
        for i in range(n):
            try:
                js = pygame.joystick.Joystick(i); js.init()
                if not self._is_real(js): continue
                self.js = js
                self.instance_id = js.get_instance_id(); return
            except pygame.error: continue
    def on_added(self, idx):
        if self.disabled or self.js is not None: return
        try:
            js = pygame.joystick.Joystick(idx); js.init()
            if not self._is_real(js): return
            self.js = js; self.instance_id = js.get_instance_id()
        except pygame.error: pass
    def on_removed(self, instance_id):
        if self.disabled: return
        if self.js is not None and self.instance_id == instance_id:
            self.js = None; self.instance_id = None
            self._connect_first()
    def axis_x(self):
        if not self.js: return 0.0
        try: v = self.js.get_axis(PAD_AXIS_X)
        except pygame.error: return 0.0
        return v if abs(v) >= PAD_DEADZONE else 0.0
    def axis_y(self):
        if not self.js: return 0.0
        try: v = self.js.get_axis(PAD_AXIS_Y)
        except pygame.error: return 0.0
        return v if abs(v) >= PAD_DEADZONE else 0.0
    def dpad_x(self):
        if not self.js or self.js.get_numhats() == 0: return 0
        try: return self.js.get_hat(0)[0]
        except pygame.error: return 0
    def dpad_y(self):
        if not self.js or self.js.get_numhats() == 0: return 0
        try: return self.js.get_hat(0)[1]
        except pygame.error: return 0
    def jump_held(self):
        if not self.js: return False
        try:
            for b in PAD_JUMP:
                if self.js.get_button(b): return True
        except pygame.error: pass
        return False
    def name(self):
        return self.js.get_name() if self.js else "none"


# ===========================================================================
# Sprite drawing — polished, layered renderings with shading, glow, and
# subtle animation. Each function takes screen coords (already cam-offset).
# Functions never emit lights themselves — lights are added by callers.
# ===========================================================================
def draw_knight(surf, x, y, facing=1, walk_t=0, in_air=False,
                dashing=False, gliding=False, hit_flash=False,
                light=None):
    """The Knight. Small, round-masked, cloaked, two horns."""
    cx, cy = int(x), int(y)
    body_c = (255, 255, 255) if hit_flash else (10, 8, 18)
    mask_c = (255, 255, 255) if hit_flash else (245, 240, 225)
    mask_shade = (130, 125, 110)

    # cape — gliding spreads it wide as wings
    if gliding:
        wing_r = [(cx - facing*4, cy - 4),
                  (cx - facing*22, cy - 8),
                  (cx - facing*30, cy + 4),
                  (cx - facing*26, cy + 14),
                  (cx - facing*14, cy + 12),
                  (cx - facing*4, cy + 8)]
        wing_l = [(cx + facing*4, cy - 4),
                  (cx + facing*22, cy - 4),
                  (cx + facing*28, cy + 6),
                  (cx + facing*18, cy + 14),
                  (cx + facing*6, cy + 10)]
        pygame.draw.polygon(surf, (28, 24, 40), wing_r)
        pygame.draw.polygon(surf, (60, 50, 80), wing_r, 2)
        pygame.draw.polygon(surf, (28, 24, 40), wing_l)
        pygame.draw.polygon(surf, (60, 50, 80), wing_l, 2)
    elif dashing:
        cape = [(cx - facing*4, cy - 4), (cx - facing*22, cy - 2),
                (cx - facing*26, cy + 10), (cx - facing*14, cy + 14),
                (cx - facing*2, cy + 8)]
        pygame.draw.polygon(surf, (40, 36, 50), cape)
        pygame.draw.polygon(surf, (90, 80, 110), cape, 2)
    else:
        sway = math.sin(walk_t * 0.18) * 2
        cape = [(cx - facing*4, cy - 4),
                (cx - facing*10, cy + 2 + sway),
                (cx - facing*13, cy + 12),
                (cx - facing*7, cy + 16),
                (cx - facing*2, cy + 8)]
        pygame.draw.polygon(surf, (40, 36, 50), cape)
        pygame.draw.polygon(surf, (90, 80, 110), cape, 2)

    # body — rounded torso with shading
    pygame.draw.ellipse(surf, body_c, (cx - 6, cy - 2, 12, 16))
    # body highlight
    if not hit_flash:
        pygame.draw.ellipse(surf, (28, 22, 40),
                            (cx - 4, cy - 1, 4, 8))

    # legs
    if in_air or gliding:
        pygame.draw.line(surf, body_c, (cx - 3, cy + 12), (cx - 3, cy + 16), 3)
        pygame.draw.line(surf, body_c, (cx + 3, cy + 12), (cx + 3, cy + 16), 3)
    else:
        lp = math.sin(walk_t * 0.35) * 2
        pygame.draw.line(surf, body_c,
                         (cx - 2, cy + 12), (cx - 2, cy + 17 + int(lp)), 3)
        pygame.draw.line(surf, body_c,
                         (cx + 2, cy + 12), (cx + 2, cy + 17 - int(lp)), 3)

    # head — round dark silhouette
    pygame.draw.ellipse(surf, body_c, (cx - 7, cy - 14, 14, 16))

    # face mask (white)
    pygame.draw.ellipse(surf, mask_c, (cx - 5, cy - 12, 10, 12))
    pygame.draw.ellipse(surf, mask_shade, (cx - 5, cy - 12, 10, 12), 1)
    # subtle mask shading bottom curve
    pygame.draw.arc(surf, mask_shade,
                    (cx - 5, cy - 12, 10, 12), -2.2, -1.0, 1)
    # eye slits — black, slightly angled
    pygame.draw.line(surf, (6, 4, 12), (cx - 3, cy - 8), (cx - 2, cy - 6), 2)
    pygame.draw.line(surf, (6, 4, 12), (cx + 2, cy - 8), (cx + 3, cy - 6), 2)

    # two horns — drawn after mask so they overlap properly
    # left
    horn_l = [(cx - 5, cy - 13),(cx - 7, cy - 16),(cx - 9, cy - 19),
              (cx - 6, cy - 16),(cx - 4, cy - 14)]
    pygame.draw.polygon(surf, mask_c, horn_l)
    pygame.draw.polygon(surf, mask_shade, horn_l, 1)
    # right
    horn_r = [(cx + 5, cy - 13),(cx + 7, cy - 16),(cx + 9, cy - 19),
              (cx + 6, cy - 16),(cx + 4, cy - 14)]
    pygame.draw.polygon(surf, mask_c, horn_r)
    pygame.draw.polygon(surf, mask_shade, horn_r, 1)

    # (player ambient halo removed — no more blue ball)


def draw_dash_afterimage(surf, x, y, facing, alpha):
    """Translucent ghost of the player from a previous frame."""
    cx, cy = int(x), int(y)
    body = pygame.Surface((30, 36), pygame.SRCALPHA)
    pygame.draw.ellipse(body, (180, 220, 255, alpha), (9, 10, 12, 16))
    pygame.draw.ellipse(body, (180, 220, 255, alpha), (8, -2, 14, 16))
    surf.blit(body, (cx - 15, cy - 18), special_flags=pygame.BLEND_ADD)


def draw_npc(surf, x, y, t=0, accent=(220, 220, 220), light=None):
    """A bug NPC — round-bodied, hooded."""
    cx, cy = int(x), int(y)
    bob = math.sin(t * 0.05) * 1.5
    # cloak
    pygame.draw.ellipse(surf, (50, 35, 28),
                        (cx - 14, cy - 4 + bob, 28, 24))
    pygame.draw.ellipse(surf, (80, 60, 48),
                        (cx - 14, cy - 4 + bob, 28, 24), 1)
    # head
    pygame.draw.ellipse(surf, (235, 225, 200),
                        (cx - 9, cy - 18 + bob, 18, 18))
    pygame.draw.ellipse(surf, (140, 130, 110),
                        (cx - 9, cy - 18 + bob, 18, 18), 1)
    # eyes
    pygame.draw.ellipse(surf, (8, 6, 16), (cx - 4, cy - 12 + bob, 3, 4))
    pygame.draw.ellipse(surf, (8, 6, 16), (cx + 1, cy - 12 + bob, 3, 4))
    # hood/cap
    pygame.draw.polygon(surf, (40, 28, 22),
        [(cx - 10, cy - 16 + bob), (cx + 10, cy - 16 + bob),
         (cx + 6, cy - 26 + bob), (cx - 6, cy - 26 + bob)])
    pygame.draw.polygon(surf, (90, 70, 50),
        [(cx - 10, cy - 16 + bob), (cx + 10, cy - 16 + bob),
         (cx + 6, cy - 26 + bob), (cx - 6, cy - 26 + bob)], 1)
    # ambient glow — very subtle so the NPC doesn't pulse like a beacon
    if light is not None:
        lights, lc = light
        lights.add(cx, cy - 10, 18, lc, intensity=0.08)


def draw_shopkeeper(surf, x, y, t=0, accent=(255, 210, 140), light=None):
    """Taller robed figure with a glowing lantern. Big, obvious presence."""
    cx, cy = int(x), int(y)
    bob = math.sin(t * 0.04) * 1.2
    # base / robe (tall conical)
    pygame.draw.polygon(surf, (60, 40, 32),
        [(cx - 16, cy + 8 + bob), (cx + 16, cy + 8 + bob),
         (cx + 12, cy - 22 + bob), (cx - 12, cy - 22 + bob)])
    pygame.draw.polygon(surf, (95, 70, 50),
        [(cx - 16, cy + 8 + bob), (cx + 16, cy + 8 + bob),
         (cx + 12, cy - 22 + bob), (cx - 12, cy - 22 + bob)], 2)
    # robe fold details
    pygame.draw.line(surf, (40, 28, 22),
        (cx - 4, cy - 22 + bob), (cx - 8, cy + 6 + bob), 2)
    pygame.draw.line(surf, (40, 28, 22),
        (cx + 4, cy - 22 + bob), (cx + 8, cy + 6 + bob), 2)
    # head
    pygame.draw.ellipse(surf, (240, 225, 195),
                        (cx - 11, cy - 36 + bob, 22, 22))
    pygame.draw.ellipse(surf, (140, 130, 110),
                        (cx - 11, cy - 36 + bob, 22, 22), 2)
    # eye slits
    pygame.draw.line(surf, (8, 6, 16),
        (cx - 5, cy - 27 + bob), (cx - 2, cy - 24 + bob), 3)
    pygame.draw.line(surf, (8, 6, 16),
        (cx + 2, cy - 27 + bob), (cx + 5, cy - 24 + bob), 3)
    # mouth shadow
    pygame.draw.line(surf, (90, 70, 60),
        (cx - 3, cy - 19 + bob), (cx + 3, cy - 19 + bob), 1)
    # big pointed hat
    pygame.draw.polygon(surf, (30, 20, 18),
        [(cx - 14, cy - 33 + bob), (cx + 14, cy - 33 + bob),
         (cx + 2, cy - 56 + bob), (cx - 2, cy - 56 + bob)])
    pygame.draw.polygon(surf, (90, 60, 40),
        [(cx - 14, cy - 33 + bob), (cx + 14, cy - 33 + bob),
         (cx + 2, cy - 56 + bob), (cx - 2, cy - 56 + bob)], 2)
    # hat brim
    pygame.draw.ellipse(surf, (40, 28, 22),
                        (cx - 18, cy - 36 + bob, 36, 7))
    pygame.draw.ellipse(surf, (90, 60, 40),
                        (cx - 18, cy - 36 + bob, 36, 7), 1)
    # lantern — glowing right side
    lx = cx + 18
    ly = cy - 4 + int(bob)
    pulse = (math.sin(t * 0.08) + 1) * 0.5
    glow_a = int(120 + pulse * 60)
    r, g, b = accent
    halo = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(halo, (r, g, b, 28), (20, 20), 18)
    pygame.draw.circle(halo, (r, g, b, 70), (20, 20), 11)
    pygame.draw.circle(halo, (r, g, b, glow_a), (20, 20), 6)
    pygame.draw.circle(halo, (255, 255, 220, glow_a), (20, 20), 3)
    surf.blit(halo, (lx - 20, ly - 20), special_flags=pygame.BLEND_ADD)
    # lantern cage
    pygame.draw.rect(surf, (30, 22, 18), (lx - 4, ly - 6, 8, 12))
    pygame.draw.line(surf, (60, 50, 40), (lx - 4, ly - 6), (lx + 3, ly - 6), 1)
    pygame.draw.line(surf, (60, 50, 40), (lx - 4, ly), (lx + 3, ly), 1)
    # lantern hanger
    pygame.draw.line(surf, (40, 28, 22), (lx, ly - 6), (lx, ly - 12), 1)
    # "SHOP" indicator dancing above
    if int(t * 0.15) % 60 < 50:
        tag = SMALL.render("trade", True, (255, 220, 140))
        tag.set_alpha(int(160 + pulse * 80))
        surf.blit(tag, (cx - tag.get_width()//2, cy - 70 + int(bob) - int(pulse*4)))
    # accumulate lantern light — soft, not blinding
    if light is not None:
        lights, _lc = light
        lights.add(lx, ly, 50, accent, intensity=0.4)


def draw_crawler(surf, x, y, facing=1, t=0, hp_pct=1.0, hit_flash=False):
    """Spiky-backed crawler. Walks platforms."""
    cx, cy = int(x), int(y)
    if hit_flash:
        body_c = (255, 255, 255)
    elif hp_pct < 0.5:
        body_c = (90, 30, 35)
    else:
        body_c = (18, 12, 22)
    # body
    pygame.draw.ellipse(surf, body_c, (cx - 14, cy - 12, 28, 16))
    # belly shading
    if not hit_flash:
        pygame.draw.arc(surf, (60, 25, 35) if hp_pct < 0.5 else (8, 6, 14),
                        (cx - 14, cy - 12, 28, 16), 3.4, 6.0, 2)
    # back spines
    for i, off in enumerate((-10, -5, 0, 5, 10)):
        h = 8 + (i % 2) * 2
        pygame.draw.polygon(surf, (50, 35, 50),
            [(cx + off - 3, cy - 12),(cx + off + 3, cy - 12),
             (cx + off, cy - 12 - h)])
        pygame.draw.line(surf, (90, 60, 90),
            (cx + off, cy - 12), (cx + off, cy - 12 - h), 1)
    # animated legs
    leg = math.sin(t * 0.3) * 2.5
    for off in (-9, 0, 9):
        pygame.draw.line(surf, (12, 8, 16),
            (cx + off, cy + 2), (cx + off + int(leg), cy + 8), 2)
    # eye — glowing red, single
    pygame.draw.circle(surf, (40, 10, 14), (cx + facing*6, cy - 8), 3)
    pygame.draw.circle(surf, (220, 50, 60), (cx + facing*6, cy - 8), 2)
    pygame.draw.circle(surf, (255, 220, 220), (cx + facing*6 - 1, cy - 9), 1)


def draw_flyer(surf, x, y, facing=1, t=0, hp_pct=1.0, hit_flash=False):
    """Flying enemy. Wings flap."""
    cx, cy = int(x), int(y)
    flap = math.sin(t * 0.4) * 5
    if hit_flash:
        body_c = (255, 255, 255)
    elif hp_pct < 0.5:
        body_c = (90, 30, 35)
    else:
        body_c = (16, 12, 24)
    # wings — translucent rendering for depth
    wing = pygame.Surface((40, 20), pygame.SRCALPHA)
    pygame.draw.polygon(wing, (200, 200, 220, 220),
        [(20, 10), (4, 4 + flap), (8, 14)])
    pygame.draw.polygon(wing, (140, 140, 170, 255),
        [(20, 10), (4, 4 + flap), (8, 14)], 1)
    surf.blit(wing, (cx - 20, cy - 10))
    wing2 = pygame.Surface((40, 20), pygame.SRCALPHA)
    pygame.draw.polygon(wing2, (200, 200, 220, 220),
        [(20, 10), (36, 4 + flap), (32, 14)])
    pygame.draw.polygon(wing2, (140, 140, 170, 255),
        [(20, 10), (36, 4 + flap), (32, 14)], 1)
    surf.blit(wing2, (cx - 20, cy - 10))
    # body
    pygame.draw.ellipse(surf, body_c, (cx - 7, cy - 7, 14, 16))
    pygame.draw.ellipse(surf, (60, 40, 60) if not hit_flash else (255,255,255),
                        (cx - 7, cy - 7, 14, 16), 1)
    # eyes glow
    pygame.draw.circle(surf, (220, 40, 60), (cx - 2, cy - 2), 1)
    pygame.draw.circle(surf, (220, 40, 60), (cx + 2, cy - 2), 1)


def draw_spitter(surf, x, y, t=0, hp_pct=1.0, hit_flash=False):
    """Stationary projectile spawner. Pulses."""
    cx, cy = int(x), int(y)
    pulse = math.sin(t * 0.06) * 2
    if hit_flash:
        body_c = (255, 255, 255)
    elif hp_pct < 0.5:
        body_c = (110, 30, 50)
    else:
        body_c = (24, 12, 24)
    # body bulb
    pygame.draw.ellipse(surf, body_c,
        (cx - 14, cy - 14 - pulse, 28, 28 + int(pulse * 2)))
    # outer rim
    pygame.draw.ellipse(surf, (60, 40, 60) if not hit_flash else (255,255,255),
        (cx - 14, cy - 14 - pulse, 28, 28 + int(pulse * 2)), 1)
    # mouth
    pygame.draw.ellipse(surf, (120, 40, 60), (cx - 6, cy - 6, 12, 10))
    pygame.draw.ellipse(surf, (60, 20, 30), (cx - 6, cy - 6, 12, 10), 1)
    # core glow inside mouth
    pygame.draw.circle(surf, (255, 220, 100), (cx, cy - 4), 3)
    pygame.draw.circle(surf, (255, 255, 220), (cx, cy - 5), 1)
    # spines bottom
    for off in (-8, -3, 2, 7):
        pygame.draw.line(surf, (12, 8, 16),
            (cx + off, cy + 10), (cx + off, cy + 14), 2)


def draw_projectile(surf, x, y, color):
    """Glowing projectile orb."""
    cx, cy = int(x), int(y)
    halo = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*color, 70), (15, 15), 14)
    pygame.draw.circle(halo, (*color, 160), (15, 15), 8)
    pygame.draw.circle(halo, (255, 255, 255, 240), (15, 15), 3)
    surf.blit(halo, (cx - 15, cy - 15), special_flags=pygame.BLEND_ADD)


def draw_platform(surf, rect, pal, seed=0):
    """Tile rendering with beveled edge, hatching, and deterministic detail.
    seed = tile position to give consistent variation."""
    rng = random.Random(seed)
    base = pal['platform']
    edge = pal['edge']
    deep = (max(0, base[0] - 12), max(0, base[1] - 12), max(0, base[2] - 12))
    light = (min(255, base[0] + 14), min(255, base[1] + 14),
             min(255, base[2] + 14))
    pygame.draw.rect(surf, base, rect)
    # top highlight
    pygame.draw.line(surf, light,
                     (rect.left, rect.top + 1),
                     (rect.right - 1, rect.top + 1), 2)
    # bottom shadow
    pygame.draw.line(surf, deep,
                     (rect.left, rect.bottom - 2),
                     (rect.right - 1, rect.bottom - 2), 2)
    # edge top
    pygame.draw.line(surf, edge, (rect.left, rect.top),
                     (rect.right - 1, rect.top), 1)
    # left/right inner shading
    pygame.draw.line(surf, deep,
                     (rect.right - 1, rect.top + 2),
                     (rect.right - 1, rect.bottom - 1), 1)
    # internal hatching
    for i in range(0, rect.width, 6):
        x = rect.left + i + rng.randint(0, 2)
        pygame.draw.line(surf, deep,
            (x, rect.top + 4), (x, rect.bottom - 3), 1)
    # occasional crack / detail
    if rng.random() < 0.2:
        cx = rect.left + rng.randint(4, rect.width - 4)
        cy = rect.top + rng.randint(4, rect.height - 4)
        pygame.draw.line(surf, deep, (cx, cy), (cx + 4, cy + 2), 1)
        pygame.draw.line(surf, deep, (cx + 4, cy + 2), (cx + 7, cy), 1)


def draw_spike(surf, rect, direction='up'):
    """Sharp, shaded spikes with proper orientation."""
    if direction == 'up':
        n = max(1, rect.width // 8)
        for i in range(n):
            x0 = rect.left + i * 8
            tip = (x0 + 4, rect.top)
            l = (x0, rect.bottom); r = (x0 + 8, rect.bottom)
            pygame.draw.polygon(surf, (230, 230, 240), [tip, l, r])
            pygame.draw.polygon(surf, (160, 160, 180), [tip, l, r], 1)
            # inner shadow
            pygame.draw.polygon(surf, (90, 90, 110),
                [(x0 + 4, rect.top + 4), (x0 + 1, rect.bottom),
                 (x0 + 4, rect.bottom - 2)])
    elif direction == 'down':
        n = max(1, rect.width // 8)
        for i in range(n):
            x0 = rect.left + i * 8
            tip = (x0 + 4, rect.bottom)
            l = (x0, rect.top); r = (x0 + 8, rect.top)
            pygame.draw.polygon(surf, (230, 230, 240), [tip, l, r])
            pygame.draw.polygon(surf, (160, 160, 180), [tip, l, r], 1)
            pygame.draw.polygon(surf, (90, 90, 110),
                [(x0 + 4, rect.bottom - 4), (x0 + 1, rect.top),
                 (x0 + 4, rect.top + 2)])
    elif direction == 'left':
        n = max(1, rect.height // 8)
        for i in range(n):
            y0 = rect.top + i * 8
            tip = (rect.left, y0 + 4)
            t = (rect.right, y0); b = (rect.right, y0 + 8)
            pygame.draw.polygon(surf, (230, 230, 240), [tip, t, b])
            pygame.draw.polygon(surf, (160, 160, 180), [tip, t, b], 1)
    elif direction == 'right':
        n = max(1, rect.height // 8)
        for i in range(n):
            y0 = rect.top + i * 8
            tip = (rect.right, y0 + 4)
            t = (rect.left, y0); b = (rect.left, y0 + 8)
            pygame.draw.polygon(surf, (230, 230, 240), [tip, t, b])
            pygame.draw.polygon(surf, (160, 160, 180), [tip, t, b], 1)


def draw_door(surf, rect, pal, t=0, light=None):
    """Glowing portal door."""
    pygame.draw.rect(surf, (4, 3, 10), rect)
    # animated runes
    r, g, b = pal['accent']
    pulse = (math.sin(t * 0.05) + 1) * 0.5
    for i in range(3):
        x = rect.left + 8 + i * (rect.width - 16) // 2
        phase = pulse * (1 + i * 0.2)
        a = int(120 + phase * 80)
        pygame.draw.line(surf, (r, g, b, a),
            (x, rect.top + 8), (x, rect.bottom - 8), 2)
        pygame.draw.circle(surf, (r, g, b),
            (x, rect.top + 8 + int(phase * 8)), 2)
    # accumulate strong door light
    if light is not None:
        lights, _ = light
        lights.add(rect.centerx, rect.centery, 120,
                   pal['accent'], intensity=0.8 + pulse * 0.3)


def draw_mite(surf, x, y, t, pal, light=None):
    """Floating currency gem with facet shimmer."""
    bob = math.sin(t * 0.08 + x * 0.01) * 3
    cx, cy = int(x), int(y + bob)
    r, g, b = (255, 230, 140)
    # halo — small + soft so it reads as a gem, not a moon
    halo = pygame.Surface((22, 22), pygame.SRCALPHA)
    pygame.draw.circle(halo, (r, g, b, 28), (11, 11), 10)
    pygame.draw.circle(halo, (r, g, b, 70), (11, 11), 6)
    surf.blit(halo, (cx - 11, cy - 11), special_flags=pygame.BLEND_ADD)
    # gem facets
    top, right, bot, left = (cx, cy - 7), (cx + 5, cy), (cx, cy + 7), (cx - 5, cy)
    pygame.draw.polygon(surf, (255, 230, 140), [top, right, bot, left])
    pygame.draw.polygon(surf, (180, 140, 60),
                        [top, right, bot, left], 1)
    # facet split lines
    pygame.draw.line(surf, (180, 140, 60), top, bot, 1)
    pygame.draw.line(surf, (180, 140, 60), left, right, 1)
    # shimmer
    flash = (math.sin(t * 0.1 + x) + 1) * 0.5
    pygame.draw.polygon(surf, (255, 255, 220),
        [(cx, cy - 5), (cx + 2, cy - 2), (cx, cy), (cx - 2, cy - 2)])
    if light is not None:
        lights, _ = light
        lights.add(cx, cy, 14, (255, 230, 140),
                   intensity=0.15 + flash * 0.1)


def draw_slash(surf, x, y, direction, t_active, max_active, color, range_px):
    """Sweeping nail arc with motion-trail multi-pass."""
    cx, cy = int(x), int(y)
    r, g, b = color
    progress = 1.0 - (t_active / max_active)
    # arc base angles per direction
    if direction == 'right':
        center = (cx + 4, cy); a0 = -math.pi/2.4; a1 = math.pi/2.4
    elif direction == 'left':
        center = (cx - 4, cy)
        a0 = math.pi - math.pi/2.4; a1 = math.pi + math.pi/2.4
    elif direction == 'up':
        center = (cx, cy - 4)
        a0 = -math.pi/2 - math.pi/2.4; a1 = -math.pi/2 + math.pi/2.4
    else:
        center = (cx, cy + 4)
        a0 = math.pi/2 - math.pi/2.4; a1 = math.pi/2 + math.pi/2.4
    sweep = min(1.0, progress * 1.8)
    cur_a1 = a0 + (a1 - a0) * sweep
    # draw three trail passes for motion blur, smallest/brightest first
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for trail_i in range(3):
        trail_pct = 1.0 - trail_i * 0.2
        if trail_pct <= 0:
            continue
        ra = int(range_px * trail_pct)
        if ra < 6:
            continue
        a = int(255 * (1 - progress * 0.5) * trail_pct)
        seg = 14
        inner, outer = [], []
        for i in range(seg + 1):
            tt = i / seg
            ang = a0 + (cur_a1 - a0) * tt
            inner.append((center[0] + math.cos(ang) * (ra * 0.45),
                          center[1] + math.sin(ang) * (ra * 0.45)))
            outer.append((center[0] + math.cos(ang) * ra,
                          center[1] + math.sin(ang) * ra))
        poly = inner + outer[::-1]
        if len(poly) < 3:
            continue
        col = (r, g, b, max(0, a - 80 + trail_i * 30))
        pygame.draw.polygon(overlay, col, poly)
        # bright edge
        for i in range(len(outer) - 1):
            pygame.draw.line(overlay,
                (255, 255, 255, max(0, a - trail_i * 50)),
                outer[i], outer[i+1], 2)
        for i in range(len(inner) - 1):
            pygame.draw.line(overlay, (r, g, b, max(0, a - trail_i * 40)),
                inner[i], inner[i+1], 2)
    surf.blit(overlay, (0, 0), special_flags=pygame.BLEND_ADD)


def draw_mask_icon(surf, x, y, full=True, breathe_phase=0.0):
    """HP mask. Subtle breathing scale animation when full."""
    if full:
        s = 1.0 + math.sin(breathe_phase) * 0.04
        ry = int(10 * s)
        pygame.draw.circle(surf, (245, 240, 225), (x, y), ry)
        pygame.draw.circle(surf, (180, 175, 160), (x, y), ry, 1)
        # subtle face shading
        pygame.draw.arc(surf, (180, 175, 160),
                        (x - ry, y - ry, ry*2, ry*2), -2.5, -0.6, 1)
        pygame.draw.polygon(surf, (245, 240, 225),
            [(x - 7, y - 6),(x - 12, y - 12),(x - 5, y - 8)])
        pygame.draw.polygon(surf, (245, 240, 225),
            [(x + 7, y - 6),(x + 12, y - 12),(x + 5, y - 8)])
        pygame.draw.line(surf, (8, 6, 16), (x - 3, y - 2), (x - 2, y), 2)
        pygame.draw.line(surf, (8, 6, 16), (x + 2, y - 2), (x + 3, y), 2)
    else:
        pygame.draw.circle(surf, (60, 50, 70), (x, y), 10, 1)
        pygame.draw.polygon(surf, (60, 50, 70),
            [(x - 7, y - 6),(x - 12, y - 12),(x - 5, y - 8)], 1)
        pygame.draw.polygon(surf, (60, 50, 70),
            [(x + 7, y - 6),(x + 12, y - 12),(x + 5, y - 8)], 1)


# ===========================================================================
# Ambient atmospheric particle systems per area. Spawn into the particle
# pool each frame to give each area a distinct living feel.
# ===========================================================================
def spawn_ambient(particles, area_id, t, cam_x, cam_y, density=1.0):
    """Spawn area-specific ambient particles into the particle pool."""
    pal = PAL[area_id]
    ambient = pal.get('ambient', 'dust')
    # spawn in a band around the camera viewport
    if ambient == 'snow':
        if random.random() < 0.4 * density:
            x = cam_x + random.uniform(-100, WIDTH + 100)
            y = cam_y - 100 + random.uniform(0, 100)
            particles.emit(x, y, 1, color=(220, 230, 255),
                vel=(random.uniform(-0.4, 0.4), random.uniform(0.5, 1.4)),
                life=240, size=1, gravity=0.0, kind='dust', friction=1.0)
    elif ambient == 'embers':
        if random.random() < 0.35 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + HEIGHT + random.uniform(0, 60)
            particles.emit(x, y, 1, color=(255, 160, 80),
                vel=(random.uniform(-0.3, 0.3), random.uniform(-1.8, -0.8)),
                life=140, size=1, kind='ember', friction=0.99)
    elif ambient == 'leaves':
        if random.random() < 0.3 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y - 30 + random.uniform(0, 80)
            particles.emit(x, y, 1, color=(140, 220, 130),
                vel=(random.uniform(-1.5, 0.5), random.uniform(0.3, 0.9)),
                life=320, size=3, gravity=0.02, kind='dust', friction=0.99)
    elif ambient == 'spores':
        if random.random() < 0.4 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + HEIGHT + random.uniform(-200, 50)
            particles.emit(x, y, 1, color=(220, 170, 220),
                vel=(random.uniform(-0.4, 0.4), random.uniform(-0.7, -0.2)),
                life=240, size=1, kind='dust', friction=1.0)
    elif ambient == 'rain':
        for _ in range(int(8 * density)):
            x = cam_x + random.uniform(-50, WIDTH + 50)
            y = cam_y - 50
            particles.emit(x, y, 1, color=(140, 180, 230),
                vel=(random.uniform(-0.4, 0), random.uniform(10, 14)),
                life=70, size=1, kind='spark', friction=1.0)
    elif ambient == 'bubbles':
        if random.random() < 0.3 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + HEIGHT + 30
            sz = random.randint(1, 2)
            particles.emit(x, y, 1, color=(140, 220, 255),
                vel=(random.uniform(-0.3, 0.3), random.uniform(-1.6, -0.8)),
                life=200, size=sz, kind='dust', friction=1.0)
    elif ambient == 'sparkles':
        if random.random() < 0.3 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + random.uniform(0, HEIGHT)
            particles.emit(x, y, 1, color=(255, 200, 255),
                vel=(0, 0), life=20, size=1, kind='dust', friction=1.0)
    elif ambient == 'ghosts':
        if random.random() < 0.1 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + random.uniform(40, HEIGHT - 100)
            particles.emit(x, y, 1, color=(220, 210, 240),
                vel=(random.uniform(-0.3, 0.3), random.uniform(-0.4, -0.2)),
                life=320, size=2, kind='dust', friction=1.0)
    elif ambient == 'wind':
        if random.random() < 0.4 * density:
            x = cam_x - 40 + random.uniform(0, 80)
            y = cam_y + random.uniform(80, HEIGHT - 80)
            particles.emit(x, y, 1, color=(220, 220, 240),
                vel=(random.uniform(7, 11), random.uniform(-0.4, 0.4)),
                life=80, size=1, kind='spark', friction=1.0)
    elif ambient == 'eyes':
        # rare; eyes blink in foreground (handled separately)
        if random.random() < 0.3 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + HEIGHT + random.uniform(-200, 30)
            particles.emit(x, y, 1, color=(180, 40, 60),
                vel=(random.uniform(-0.3, 0.3), random.uniform(-0.5, -0.2)),
                life=180, size=2, kind='ember', friction=1.0)
    elif ambient == 'petals':
        if random.random() < 0.35 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y - 40 + random.uniform(0, 80)
            particles.emit(x, y, 1, color=(255, 160, 200),
                vel=(random.uniform(-1.0, 0.5), random.uniform(0.4, 0.9)),
                life=320, size=3, kind='dust', friction=0.99)
    elif ambient == 'ash':
        if random.random() < 0.5 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y - 40 + random.uniform(0, 80)
            particles.emit(x, y, 1, color=(180, 130, 90),
                vel=(random.uniform(-0.6, 0.3), random.uniform(0.4, 0.9)),
                life=260, size=2, kind='dust', friction=1.0)
    elif ambient == 'mist':
        if random.random() < 0.2 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + random.uniform(40, HEIGHT - 100)
            particles.emit(x, y, 1, color=(160, 200, 240),
                vel=(random.uniform(-0.4, 0.4), 0),
                life=240, size=5, kind='dust', friction=1.0)
    elif ambient == 'void':
        # white pinpoints drifting
        if random.random() < 0.4 * density:
            x = cam_x + random.uniform(0, WIDTH)
            y = cam_y + random.uniform(0, HEIGHT)
            particles.emit(x, y, 1, color=(220, 220, 230),
                vel=(0, random.uniform(-0.3, -0.1)),
                life=180, size=1, kind='dust', friction=1.0)


def draw_eye_blink_fg(surf, t, cam_x, cam_y):
    """Foreground decoration for Deepnest — blinking red eye pairs in the
    dark below the camera."""
    rng = random.Random(int(cam_x / 200))
    for _ in range(12):
        x_seed = rng.uniform(0, WIDTH * 4)
        y_seed = rng.uniform(HEIGHT * 0.6, HEIGHT * 1.2)
        # parallax tied to cam
        x = (x_seed - cam_x * 0.6) % WIDTH
        y = y_seed
        if y > HEIGHT - 4:
            continue
        # blink phase based on x_seed
        phase = (t * 0.02 + x_seed * 0.03) % math.tau
        if math.sin(phase) > 0.6:
            pygame.draw.circle(surf, (140, 20, 30),
                              (int(x) - 4, int(y)), 2)
            pygame.draw.circle(surf, (220, 50, 70),
                              (int(x) - 4, int(y)), 1)
            pygame.draw.circle(surf, (140, 20, 30),
                              (int(x) + 4, int(y)), 2)
            pygame.draw.circle(surf, (220, 50, 70),
                              (int(x) + 4, int(y)), 1)


def draw_vignette(surf, intensity=1.0, color=(0, 0, 0)):
    """Edge darkening for cinematic feel."""
    v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(14):
        a = int((6 + i * 4) * intensity)
        pygame.draw.rect(v, (*color, a),
            (i * 7, i * 4, WIDTH - i * 14, HEIGHT - i * 8), 6)
    surf.blit(v, (0, 0))


def draw_damage_pulse(surf, intensity):
    """Red flash overlay when hit."""
    if intensity <= 0:
        return
    a = int(120 * intensity)
    pulse = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse.fill((200, 30, 50, a))
    surf.blit(pulse, (0, 0))


def draw_boss_intro(surf, name, t, pal):
    """Slide-in boss name banner."""
    duration = 90
    if t >= duration:
        return
    # ease in/out
    if t < 15:
        progress = t / 15
    elif t > duration - 30:
        progress = (duration - t) / 30
    else:
        progress = 1.0
    alpha = int(255 * progress)
    bw, bh = 800, 90
    bx = WIDTH // 2 - bw // 2
    by = HEIGHT // 2 - bh // 2 - 80
    banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
    banner.fill((10, 5, 16, int(220 * progress)))
    # accent lines top/bottom
    r, g, b = pal['accent']
    pygame.draw.line(banner, (r, g, b, alpha), (0, 4), (bw, 4), 3)
    pygame.draw.line(banner, (r, g, b, alpha), (0, bh - 4), (bw, bh - 4), 3)
    # name centered
    txt = HUGE.render(name, True, (r, g, b))
    txt.set_alpha(alpha)
    banner.blit(txt, (bw // 2 - txt.get_width() // 2,
                      bh // 2 - txt.get_height() // 2))
    sub = FONT.render("- challenger appears -", True, (200, 200, 220))
    sub.set_alpha(int(180 * progress))
    banner.blit(sub, (bw // 2 - sub.get_width() // 2, bh - 24))
    surf.blit(banner, (bx, by))


# ===========================================================================
# Hand-crafted "key" levels — one per area, plays as sublevel 1 of that area.
# Symbols:
#   #=solid  ^=spike  v=ceiling spike  <,>=side spikes  ~=saw
#   P=spawn  D=door  N=npc  K=shopkeeper  o=mite
#   c/f/s=crawler/flyer/spitter  B=boss arena
# ===========================================================================
KEYS = {
    'dirtmouth': [
        ".................................................................",
        ".................................................................",
        ".................................................................",
        ".................................................................",
        "............o..........o...................o.....................",
        "..........#####......#####...............#####...................",
        "................................................................D",
        "...........................###.............................#####",
        ".................................................................",
        ".....................o....................o.....................",
        "...##.............#######...............#####...##..............#",
        "...##....N..............................K.........##............#",
        "...##.P......^^.................^^^......................########",
        "##########.#############################.########################",
    ],
    'crossroads': [
        ".......................................................................",
        ".......................................................................",
        ".......o.......c..........f................o.................c........",
        ".....#####...##############...........#######..............########....",
        ".......................................................................",
        "............o..........................o..........................o...",
        ".........#####.........#####.........#####........................##.D.",
        ".................................................................######",
        "....##..........o................f...........................##........",
        "....##........#####.............................o..........##..........",
        "....##.P..........................^^^^^......#######.....##............",
        "....##.....N....^^.......##########...............s.....##.............",
        "##########.######........##########............########################",
    ],
    'greenpath': [
        ".....................................................................",
        ".......f...........................f.................f..............",
        "..............o................o.................o..................",
        "............#####............#####..............#####...............",
        ".....................................................................",
        "....................c...........................c...................D",
        "................########..............o....................########",
        ".................................###############.....................",
        "..........o..............................................c..........",
        ".......#####..........#######.........................########......",
        "....##........o........................^^^^^^.......................",
        "....##.P...N.....^^^^^..............##############...................",
        "###########.###############.##########################.##############",
    ],
    'fungal': [
        ".................................................................",
        "..s.........f.................s..............f...............s..",
        "...............o..........o.............o........................",
        "............######......######.........######....................",
        ".................................................................",
        "............................................................D....",
        "....................o..........................o.........#######",
        "................###############..............######..............",
        "...##......f....................f..........................##...",
        "...##.........................................o.............##..",
        "...##.P...N.......^^^........###############................##...",
        "...##....^^^..^^^^^^^^^..............................^^^^.....##.",
        "##########.################################.######################",
    ],
    'city': [
        ".......................................................................",
        ".......................................................................",
        ".......c..........s.................c..........s..................c....",
        "....########...########.........########.....########............######",
        ".......................................................................",
        "..........o..........o..........o...........o..........o.............D",
        ".......######......#####......######......#####.......######......#####",
        ".......................................................................",
        "...##........c..................................^^^^^.................",
        "...##......#####..........s....................##############.........",
        "...##.P..N.................K..o....s.................................",
        "...##....^^^....######.....######......######......^^^^....######.....",
        "##########.################.##########################.###############",
    ],
    'waterways': [
        ".................................................................",
        "..............f.................f...............f...............",
        "........o..............o.............o.................o........",
        "......#####..........#####.........#####..............######....",
        ".................................................................",
        "................................................................D",
        "............s..............s..............s..............######",
        "........#######..........#######........#######.................",
        "...##.................................................f..........",
        "...##......o..........o..........o........................##....",
        "...##.P.N..........................................^^^......##..",
        "...##....^^^^^...########....########..............###........##",
        "##########.##############################################.######",
    ],
    'crystal': [
        ".......................................................................",
        ".......c..............f...............c................f..............",
        "................o..........o................o.........................",
        "..............#####......#####............#####........................",
        ".......................................................................",
        "...................c................f.......................D.........",
        "..............########.........#######.....................#######....",
        ".......................................................................",
        "...##....o.....................................o.............##.......",
        "...##..#####.................c..............#######...........##......",
        "...##.P..N.................########..^^^^^.....................##.....",
        "...##....^^^.......^^^^^.........................^^^^^^^^........##....",
        "##########.################################.##########################",
    ],
    'resting': [
        ".................................................................",
        "................f.................f...................f.........",
        "..........o..............o................o.....................",
        "........#####..........#####............#####...................",
        ".................................................................",
        "................................................................D",
        ".................f..............f.........................######",
        "..............######.........######.............................",
        "..##........................................f..............##...",
        "..##......o..............o................o.................##..",
        "..##.P.N.....^^^...####################........^^^^......##.....",
        "..##....^^^^^^^^^...................................^^^^^.##....",
        "##########.###############################.#######################",
    ],
    'cliffs': [
        ".................................................................",
        "..f..............s............f.................s..........f....",
        "..........o..........................o..........................",
        "........#####......................######........................",
        ".................................................................",
        "....................f...........................f..............D",
        "................########......................######......######",
        ".................................................................",
        "...##.........o..........s....................o..................",
        "...##.......######......######............########.............##",
        "...##.P.N.......................^^^^^.......................##..",
        "...##....^^^.........^^^^^...##########............^^^........##",
        "##########.################################.####################",
    ],
    'deepnest': [
        "..............................................................................",
        "..c....f....s.......c...........f...........s..........c.......f...........s.",
        "......................o..............o..................o....................",
        "...................#####...........#####.................#####...............",
        "..............................................................................",
        ".....................c..............f...............s.......................D",
        ".................#######.........#######............######...........#########",
        "..............................................................................",
        "...##......o..............o.....................o.............c..............",
        "...##....######.........######........^^^^^^...#####.......########...........",
        "...##.P.N......................##############.............^^^^^^..............",
        "...##....^^^^^......^^^^^^^^^......................^^^^^^.........^^^^^.......",
        "##########.####################.##########################.##############.####",
    ],
    'gardens': [
        ".................................................................",
        "....c..........s.................c.............s............c...",
        "..........o.............o.............o..............o..........",
        "........#####.........#####.........#####..........#####........",
        ".................................................................",
        "................................................................D",
        "...........s..............c..............s................######",
        "........#######........#######........#######...................",
        "...##......o..................o................^^^^^............",
        "...##....#####...............#####............##############....",
        "...##.P.N....^^^........^^^^^......c.............................",
        "...##....^^^^^^^^^^.................########.........^^^^^......",
        "##########.##############################.######################",
    ],
    'edge': [
        ".................................................................",
        ".....c.........f..............c..............f...........c......",
        "............o..............o..............o.....................",
        "..........#####..........#####...........#####..................",
        ".................................................................",
        ".........................f.....................................D",
        "....................#######...............................######",
        "................................f..............f................",
        "...##......c..............c..............................##.....",
        "...##....#####..........#####.........o.................K.##....",
        "...##.P.N....^^^........^^^^^......######....^^^^^.......##.....",
        "...##....^^^^^^^^^........................^^^^^^^^^........##...",
        "##########.################################.####################",
    ],
    'basin': [
        "....................................................................",
        "...c......f.....s..........c.......f.......s.........c.....f.....s.",
        "...........o..........o..............o...............o.............",
        ".........#####......#####...........#####...........#####..........",
        "....................................................................",
        "................................................................D...",
        "..........s............f...........s............c.............#####",
        "........######.......######.......######.......######...............",
        "..##......o..........................................o..............",
        "..##....######.........^^^^^^^^^^...##############..######........##",
        "..##.P.N.....^^^.....##############..............................##",
        "..##....^^^^^^^^^^^...........................^^^^^^^^^^^.........##",
        "##########.################.#######################.################",
    ],
    'abyss': [
        ".......................................................................",
        ".....c....f....s.........c....f....s..........c....f....s..............",
        "..........o.................o.................o........................",
        ".........#####.............#####...............#####...................",
        ".......................................................................",
        "................................................................B......",
        "................o....................o.........................#######",
        "..............######.................######............................",
        "...##......c..............f.................s...............c..........",
        "...##....#####...........######............######........#######.......",
        "...##.P........^^^^^...##############.............^^^^^.................",
        "...##....^^^^^^^^^^^......................^^^^^^^.........^^^^.........",
        "##########.################.#######################.###################",
    ],
}


def gen_sublevel(area_id, sub_index):
    """Procedural level generation. Aggressive difficulty curve."""
    seed = int(hashlib.sha256(f"{area_id}:{sub_index}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    area = AREAS[AREA_INDEX[area_id]]
    danger = area['danger']; enemies = area['enemies']
    base = danger * 0.10
    prog = sub_index / SUBLEVELS_PER_AREA
    diff = min(1.0, base + prog * 0.95)
    cols = rng.randint(60, 90) + int(diff * 30)
    rows = 14
    grid = [['.'] * cols for _ in range(rows)]
    for x in range(cols):
        grid[rows-1][x] = '#'
    for _ in range(int(2 + diff * 10)):
        gx = rng.randint(10, cols-10)
        gw = rng.randint(2, 3 + int(diff * 7))
        for x in range(gx, min(cols, gx+gw)):
            grid[rows-1][x] = '.'
    plat_count = int(5 + diff * 8)
    min_w = max(1, 4 - int(diff * 3))
    max_w = max(min_w + 1, 6 - int(diff * 3))
    for _ in range(plat_count):
        py = rng.randint(2, rows-4)
        px = rng.randint(4, cols-8)
        pw = rng.randint(min_w, max_w)
        for x in range(px, min(cols, px+pw)):
            grid[py][x] = '#'
    if diff > 0.3:
        for _ in range(int(1 + diff * 4)):
            wx = rng.randint(8, cols-8)
            wh = rng.randint(3, 7)
            wy = rows-2
            for h in range(wh):
                if wy-h >= 1: grid[wy-h][wx] = '#'
    for _ in range(int(diff * 14)):
        sx = rng.randint(6, cols-6)
        sw = rng.randint(2, 4 + int(diff * 3))
        for x in range(sx, min(cols-2, sx+sw)):
            if grid[rows-2][x] == '.':
                grid[rows-2][x] = '^'
    spike_prob = 0.03 + diff * 0.15
    if diff > 0.35:
        for r in range(rows-5, 1, -1):
            for x in range(1, cols-1):
                if grid[r][x] == '#' and rng.random() < spike_prob:
                    if grid[r-1][x] == '.':
                        grid[r-1][x] = '^'
    if diff > 0.45:
        for _ in range(int(diff * 5)):
            cx_ = rng.randint(4, cols-8)
            cw = rng.randint(3, 6 + int(diff * 4))
            cy_ = rng.randint(2, 5)
            for x in range(cx_, min(cols-1, cx_+cw)):
                if grid[cy_][x] == '.':
                    grid[cy_][x] = 'v'
    if diff > 0.55:
        for r in range(2, rows-2):
            for x in range(2, cols-2):
                if grid[r][x] == '#' and rng.random() < diff * 0.10:
                    if grid[r][x-1] == '.': grid[r][x-1] = '>'
                    elif grid[r][x+1] == '.': grid[r][x+1] = '<'
    if diff > 0.4:
        for _ in range(int((diff - 0.4) * 8)):
            for _t in range(20):
                sx = rng.randint(10, cols-10)
                sy = rng.randint(3, rows-4)
                if grid[sy][sx] == '.':
                    grid[sy][sx] = '~'; break
    if enemies:
        for _ in range(int(4 + diff * 10)):
            kind = rng.choice(enemies)
            if kind == 'crawler':
                for _t in range(20):
                    x = rng.randint(4, cols-4); y = rng.randint(2, rows-2)
                    if grid[y][x] == '#' and grid[y-1][x] == '.':
                        grid[y-1][x] = 'c'; break
            elif kind == 'flyer':
                for _t in range(20):
                    x = rng.randint(4, cols-4); y = rng.randint(1, rows-5)
                    if grid[y][x] == '.':
                        grid[y][x] = 'f'; break
            elif kind == 'spitter':
                for _t in range(20):
                    x = rng.randint(4, cols-4); y = rng.randint(2, rows-2)
                    if grid[y][x] == '#' and grid[y-1][x] == '.':
                        grid[y-1][x] = 's'; break
    orb_count = max(1, rng.randint(2, 6) - int(diff * 2))
    for _ in range(orb_count):
        for _t in range(20):
            x = rng.randint(4, cols-4); y = rng.randint(1, rows-3)
            if grid[y][x] == '.':
                grid[y][x] = 'o'; break
    grid[rows-2][2] = 'P'
    for x in range(0, 6):
        grid[rows-1][x] = '#'
        for y in range(rows-5, rows-1):
            if grid[y][x] in ('^','v','<','>','~','c','f','s'):
                grid[y][x] = '.'
    grid[rows-2][cols-3] = 'D'
    for x in range(cols-6, cols):
        grid[rows-1][x] = '#'
        for y in range(rows-5, rows-1):
            if grid[y][x] in ('^','v','<','>','~','c','f','s'):
                grid[y][x] = '.'
    return [''.join(r) for r in grid]


def get_level_rows(area_id, sub_index):
    if sub_index == 0:
        return KEYS[area_id]
    return gen_sublevel(area_id, sub_index)


class Camera:
    def __init__(self):
        self.x = 0.0; self.y = 0.0
        self.shake = 0; self.shake_t = 0
        self.breathe = 0.0
    def follow(self, tx, ty):
        self.x += ((tx - WIDTH//2) - self.x) * 0.12
        self.y += ((ty - HEIGHT//2 - 60) - self.y) * 0.12
    def kick(self, amount=6):
        self.shake = max(self.shake, amount); self.shake_t = max(self.shake_t, 12)
    def offset(self):
        ox = oy = 0
        if self.shake_t > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
            self.shake_t -= 1; self.shake *= 0.85
        return self.x + ox, self.y + oy


class Enemy:
    def __init__(self, x, y, kind, level):
        self.x = float(x); self.y = float(y); self.kind = kind
        self.t = random.randint(0, 200)
        self.facing = random.choice([-1, 1])
        self.origin = (x, y)
        self.shoot_cd = random.randint(30, 90)
        self.hit_flash = 0
        self.knockback_vx = 0
        self.alive = True
        self.dead_t = 0
        danger = level.area['danger']
        if kind == 'crawler':
            self.w, self.h, self.speed = 26, 24, 1.2
            self.max_hp = 1 + danger // 2
            self.mites_drop = 2 + danger
        elif kind == 'flyer':
            self.w, self.h, self.speed = 20, 14, 1.6
            self.max_hp = 1 + danger // 2
            self.mites_drop = 3 + danger
        elif kind == 'spitter':
            self.w, self.h = 28, 28
            self.max_hp = 2 + danger // 2
            self.mites_drop = 5 + danger * 2
        self.hp = self.max_hp
    def rect(self):
        return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h/2),
                           self.w, self.h)
    def take_hit(self, damage, dir_x, particles, cam):
        if not self.alive: return False
        self.hp -= damage
        self.hit_flash = 6
        self.knockback_vx = dir_x * 4
        cam.kick(3)
        particles.emit_spark_burst(self.x, self.y, n=10,
            color=(255, 230, 140), speed=3.0, life=22)
        if self.hp <= 0:
            self.die(particles, cam)
            return True
        return False
    def die(self, particles, cam):
        self.alive = False
        self.dead_t = 0
        cam.kick(5)
        particles.emit_spark_burst(self.x, self.y, n=20,
            color=(220, 80, 80), speed=3.5, life=30)
        particles.emit_shockwave(self.x, self.y, color=(180, 40, 60),
            n=18, speed=3.5, life=24)
    def update(self, level, projectiles, player):
        if not self.alive:
            self.dead_t += 1
            return
        self.t += 1
        if self.hit_flash > 0: self.hit_flash -= 1
        self.x += self.knockback_vx
        self.knockback_vx *= 0.7
        if abs(self.knockback_vx) < 0.1: self.knockback_vx = 0
        if self.kind == 'crawler':
            self.x += self.facing * self.speed
            probe = pygame.Rect(int(self.x + self.facing*(self.w//2 + 2)),
                                int(self.y + self.h//2), 4, 6)
            has_floor = any(probe.colliderect(s) for s in level.solids)
            wall = any(self.rect().colliderect(s) for s in level.solids
                       if s.top < self.y < s.bottom)
            if not has_floor or wall:
                self.facing *= -1
                self.x += self.facing * 2
        elif self.kind == 'flyer':
            ox, oy = self.origin
            self.x = ox + math.sin(self.t*0.04)*60 + self.knockback_vx * 0.5
            self.y = oy + math.cos(self.t*0.05)*24
            self.facing = 1 if math.cos(self.t*0.04) > 0 else -1
        elif self.kind == 'spitter':
            self.shoot_cd -= 1
            if self.shoot_cd <= 0:
                self.shoot_cd = 110
                dx = player.x - self.x
                dy = (player.y - 22) - self.y
                d = max(1, math.hypot(dx, dy))
                if d < 400:
                    projectiles.append({'x': self.x, 'y': self.y - 6,
                        'vx': dx/d*3.5, 'vy': dy/d*3.5, 'life': 180,
                        'color': (255, 220, 100)})
    def draw(self, surf, camx, camy, lights):
        if not self.alive: return
        x, y = self.x - camx, self.y - camy
        hp_pct = self.hp / self.max_hp if self.max_hp > 0 else 1.0
        flash = self.hit_flash > 0
        if self.kind == 'crawler':
            draw_crawler(surf, x, y+4, self.facing, self.t, hp_pct, flash)
        elif self.kind == 'flyer':
            draw_flyer(surf, x, y, self.facing, self.t, hp_pct, flash)
            lights.add(int(x), int(y), 20, (220, 40, 60), intensity=0.3)
        elif self.kind == 'spitter':
            draw_spitter(surf, x, y, self.t, hp_pct, flash)
            lights.add(int(x), int(y - 4), 24, (255, 220, 100), intensity=0.5)
        # HP bar when damaged
        if self.hp < self.max_hp and self.max_hp > 1:
            bw = 28; bh = 4
            bx = int(x) - bw // 2
            by = int(y) - self.h // 2 - 12
            pygame.draw.rect(surf, (10, 8, 20), (bx-1, by-1, bw+2, bh+2))
            pygame.draw.rect(surf, (40, 30, 50), (bx, by, bw, bh))
            pygame.draw.rect(surf, (220, 80, 100),
                             (bx, by, int(bw * hp_pct), bh))


class Saw:
    def __init__(self, x, y, level):
        self.origin_x = float(x); self.origin_y = float(y)
        self.x = float(x); self.y = float(y)
        self.t = random.randint(0, 200)
        self.r = 18
        self.range = 90
        self.speed = 0.04
        self.axis = 'h'
        probe_l = pygame.Rect(int(x) - 32, int(y) - 4, 8, 8)
        probe_r = pygame.Rect(int(x) + 24, int(y) - 4, 8, 8)
        probe_d = pygame.Rect(int(x) - 4, int(y) + 24, 8, 8)
        if any(probe_l.colliderect(s) for s in level.solids) or \
           any(probe_r.colliderect(s) for s in level.solids):
            self.axis = 'v'
        elif not any(probe_d.colliderect(s) for s in level.solids):
            self.axis = 'h'
    def rect(self):
        return pygame.Rect(int(self.x - self.r + 4), int(self.y - self.r + 4),
                           (self.r - 4) * 2, (self.r - 4) * 2)
    def update(self):
        self.t += 1
        phase = math.sin(self.t * self.speed)
        if self.axis == 'h': self.x = self.origin_x + phase * self.range
        else: self.y = self.origin_y + phase * self.range
    def draw(self, surf, camx, camy, particles, lights):
        cx, cy = self.x - camx, self.y - camy
        spin = self.t * 0.5
        # teeth
        for i in range(12):
            a = spin + i * math.tau / 12
            x1 = cx + math.cos(a) * 14
            y1 = cy + math.sin(a) * 14
            x2 = cx + math.cos(a + 0.15) * 19
            y2 = cy + math.sin(a + 0.15) * 19
            x3 = cx + math.cos(a + 0.30) * 14
            y3 = cy + math.sin(a + 0.30) * 14
            pygame.draw.polygon(surf, (210, 210, 225),
                                [(x1, y1), (x2, y2), (x3, y3)])
            pygame.draw.line(surf, (160, 160, 180),
                             (x1, y1), (x2, y2), 1)
        # body
        pygame.draw.circle(surf, (90, 90, 110), (int(cx), int(cy)), 11)
        pygame.draw.circle(surf, (140, 140, 160), (int(cx), int(cy)), 9)
        pygame.draw.circle(surf, (50, 50, 70), (int(cx), int(cy)), 5)
        pygame.draw.circle(surf, (200, 200, 220), (int(cx) - 2, int(cy) - 2), 2)
        # red light
        lights.add(int(cx), int(cy), 60, (220, 60, 80), intensity=0.6)
        if self.t % 5 == 0:
            particles.emit(self.x + random.uniform(-14, 14),
                           self.y + random.uniform(-14, 14), 1,
                           color=(255, 180, 80),
                           vel=(random.uniform(-1, 1), random.uniform(-1, 1)),
                           life=16, size=2, kind='ember')


class Slash:
    def __init__(self, owner, direction, damage, reach):
        self.owner = owner
        self.direction = direction
        self.damage = damage
        self.reach = reach
        self.t = NAIL_ACTIVE_FRAMES
        self.hit_targets = set()
        self.pogo_used = False
    def rect(self):
        ow = self.owner
        if self.direction == 'right':
            return pygame.Rect(int(ow.x) + 2, int(ow.y - ow.h + 4),
                               self.reach, NAIL_HEIGHT)
        elif self.direction == 'left':
            return pygame.Rect(int(ow.x) - 2 - self.reach,
                               int(ow.y - ow.h + 4),
                               self.reach, NAIL_HEIGHT)
        elif self.direction == 'up':
            return pygame.Rect(int(ow.x) - NAIL_HEIGHT // 2,
                               int(ow.y - ow.h - self.reach + 8),
                               NAIL_HEIGHT, self.reach)
        elif self.direction == 'down':
            return pygame.Rect(int(ow.x) - NAIL_HEIGHT // 2,
                               int(ow.y - 4),
                               NAIL_HEIGHT, self.reach)
    def update(self):
        self.t -= 1


class Boss:
    HP_TABLE = {'warden': 8, 'mantis_lord': 10, 'soul_tyrant': 12,
                'nosk': 14, 'hollow': 18}
    NAME_TABLE = {'warden': "FALSE WARDEN", 'mantis_lord': "MANTIS LORD",
                  'soul_tyrant': "SOUL TYRANT", 'nosk': "NOSK",
                  'hollow': "THE HOLLOW"}
    def __init__(self, x, y, kind):
        self.x = float(x); self.y = float(y); self.kind = kind
        self.t = 0
        self.hp = self.HP_TABLE.get(kind, 8)
        self.max_hp = self.hp
        self.state = 'idle'
        self.state_t = 40
        self.facing = -1
        self.invuln = 0
        self.dead_t = 0
        self.w, self.h = 60, 80
        self.charge_vx = 0
        self.intro_t = 0
    def rect(self):
        return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h),
                           self.w, self.h)
    def take_hit(self, damage, particles, cam):
        if self.invuln > 0 or self.state == 'dead': return False
        self.hp -= damage
        self.state_t = max(self.state_t, 8)
        self.invuln = 24
        cam.kick(7)
        particles.emit_spark_burst(self.x, self.y - 40, n=18,
            color=(255, 230, 140), speed=3.5, life=30)
        if self.hp <= 0:
            self.state = 'dead'; self.state_t = 120
            particles.emit_shockwave(self.x, self.y - 40,
                color=(255, 220, 140), n=32, speed=5, life=40)
        return True
    def update(self, player, projectiles, particles, cam):
        self.t += 1
        self.intro_t += 1
        if self.state == 'dead':
            self.dead_t += 1
            if self.dead_t % 3 == 0:
                a = random.uniform(0, math.tau)
                particles.emit(self.x + random.uniform(-30,30),
                    self.y - 40 + random.uniform(-30,30), 1,
                    color=(255,220,120),
                    vel=(math.cos(a)*2, math.sin(a)*2 - 1),
                    life=44, size=4, kind='glow')
            return
        if self.invuln > 0: self.invuln -= 1
        self.facing = -1 if player.x < self.x else 1
        self.state_t -= 1
        if self.state_t <= 0: self._next_state(player)
        if self.kind == 'warden':
            if self.state == 'strike' and self.state_t == 12:
                projectiles.append({'x': self.x - 30, 'y': self.y - 6,
                    'vx': -4, 'vy': 0, 'life': 80, 'color': (220,180,100)})
                projectiles.append({'x': self.x + 30, 'y': self.y - 6,
                    'vx': 4, 'vy': 0, 'life': 80, 'color': (220,180,100)})
                cam.kick(8)
        elif self.kind == 'mantis_lord':
            if self.state == 'strike':
                if self.state_t == 18:
                    self.charge_vx = -self.facing * 9
                self.x += self.charge_vx
                self.charge_vx *= 0.93
                if self.state_t % 3 == 0:
                    particles.emit(self.x, self.y - 30, 1,
                        color=(180,255,200),
                        vel=(self.facing*2, random.uniform(-1,1)),
                        life=20, size=2, kind='glow')
            if self.hp <= self.max_hp // 2 and self.state == 'strike' \
                    and self.state_t == 8:
                for ang in (-0.5, -0.2, 0.1):
                    dx = -self.facing * 4 * math.cos(ang)
                    dy = math.sin(ang) * 4 - 0.5
                    projectiles.append({'x': self.x, 'y': self.y - 40,
                        'vx': dx, 'vy': dy, 'life': 130,
                        'color': (180,240,180)})
        elif self.kind == 'soul_tyrant':
            if self.state == 'strike' and self.state_t == 14:
                for ang in (-0.6, -0.3, 0, 0.3, 0.6):
                    dx = math.cos(ang) * (-self.facing) * 3.5
                    dy = math.sin(ang) * 3.5
                    projectiles.append({'x': self.x, 'y': self.y - 40,
                        'vx': dx, 'vy': dy, 'life': 140,
                        'color': (180,230,255)})
        elif self.kind == 'nosk':
            if self.state == 'strike' and self.state_t == 20:
                cam.kick(10)
                projectiles.append({'x': self.x - 20, 'y': self.y - 6,
                    'vx': -5, 'vy': 0, 'life': 100, 'color': (220,60,90)})
                projectiles.append({'x': self.x + 20, 'y': self.y - 6,
                    'vx': 5, 'vy': 0, 'life': 100, 'color': (220,60,90)})
            if self.state == 'strike' and self.state_t == 8 \
                    and self.hp <= self.max_hp // 2:
                dx = player.x - self.x
                dy = (player.y - 22) - (self.y - 50)
                d = max(1, math.hypot(dx, dy))
                projectiles.append({'x': self.x, 'y': self.y - 50,
                    'vx': dx/d*3.5, 'vy': dy/d*3.5, 'life': 160,
                    'color': (255, 80, 120)})
        elif self.kind == 'hollow':
            if self.state == 'strike' and self.state_t == 18:
                for ang in (-0.4, 0, 0.4):
                    dx = (-self.facing) * 4 * math.cos(ang)
                    dy = math.sin(ang) * 4 - 1
                    projectiles.append({'x': self.x, 'y': self.y - 50,
                        'vx': dx, 'vy': dy, 'life': 150,
                        'color': (240,240,240)})
            elif self.state == 'strike' and self.state_t == 6 \
                    and self.hp <= self.max_hp // 2:
                dx = player.x - self.x
                dy = (player.y - 22) - (self.y - 50)
                d = max(1, math.hypot(dx, dy))
                projectiles.append({'x': self.x, 'y': self.y - 50,
                    'vx': dx/d*3, 'vy': dy/d*3, 'life': 160,
                    'color': (160,100,220)})
    def _next_state(self, player):
        if self.kind == 'mantis_lord':
            if   self.state == 'idle':       self.state, self.state_t = 'windup', 26
            elif self.state == 'windup':     self.state, self.state_t = 'strike', 30
            elif self.state == 'strike':     self.state, self.state_t = 'vulnerable', 40
            elif self.state == 'vulnerable': self.state, self.state_t = 'idle', 24
            return
        if   self.state == 'idle':       self.state, self.state_t = 'windup', 40
        elif self.state == 'windup':     self.state, self.state_t = 'strike', 30
        elif self.state == 'strike':     self.state, self.state_t = 'vulnerable', 60
        elif self.state == 'vulnerable': self.state, self.state_t = 'idle', 40
    def draw(self, surf, camx, camy, lights):
        cx, cy = self.x - camx, self.y - camy
        if self.state == 'dead' and self.dead_t > 100: return
        flash = self.invuln > 14
        if flash:
            body_c, edge_c = (255,255,255), (255,255,255)
        elif self.state == 'windup':
            body_c, edge_c = (50,30,30), (220,80,80)
        elif self.state == 'strike':
            body_c, edge_c = (90,40,40), (255,120,80)
        elif self.state == 'vulnerable':
            body_c, edge_c = (40,60,80), (120,220,255)
        else:
            body_c, edge_c = (28,22,38), (90,80,120)
        # big light under boss
        lights.add(int(cx), int(cy - 40), 140, edge_c, intensity=0.7)
        if self.kind == 'warden':
            # large armored knight
            pygame.draw.ellipse(surf, body_c, (cx-36, cy-60, 72, 60))
            pygame.draw.ellipse(surf, edge_c, (cx-36, cy-60, 72, 60), 2)
            # head
            pygame.draw.ellipse(surf, body_c, (cx-22, cy-92, 44, 36))
            pygame.draw.ellipse(surf, edge_c, (cx-22, cy-92, 44, 36), 2)
            # eyes
            pygame.draw.line(surf, edge_c, (cx-12, cy-76), (cx-4, cy-76), 4)
            pygame.draw.line(surf, edge_c, (cx+4, cy-76), (cx+12, cy-76), 4)
            # crown spikes
            for off in (-30, -15, 15, 30):
                pygame.draw.polygon(surf, edge_c,
                    [(cx+off, cy-58),(cx+off-5, cy-44),(cx+off+5, cy-44)])
            # cape behind
            cape = [(cx-20, cy-50),(cx-50, cy-30),(cx-40, cy-10),(cx-10, cy-30)]
            pygame.draw.polygon(surf, (40, 30, 50), cape)
        elif self.kind == 'mantis_lord':
            # tall lean insectoid
            pygame.draw.polygon(surf, body_c,
                [(cx-22, cy),(cx+22, cy),(cx+12, cy-60),(cx-12, cy-60)])
            pygame.draw.ellipse(surf, body_c, (cx-16, cy-92, 32, 36))
            pygame.draw.ellipse(surf, edge_c, (cx-14, cy-90, 28, 32), 2)
            # large mantis eyes
            pygame.draw.ellipse(surf, edge_c, (cx-8, cy-80, 6, 8))
            pygame.draw.ellipse(surf, edge_c, (cx+2, cy-80, 6, 8))
            # sickle arms
            arm_sway = math.sin(self.t * 0.1) * 6
            pygame.draw.lines(surf, edge_c, False,
                [(cx-20, cy-44),(cx-34, cy-32+arm_sway),
                 (cx-30, cy-12), (cx-22, cy-4)], 4)
            pygame.draw.polygon(surf, edge_c,
                [(cx-22, cy-4),(cx-30, cy-12),(cx-26, cy+2)])
            pygame.draw.lines(surf, edge_c, False,
                [(cx+20, cy-44),(cx+34, cy-32-arm_sway),
                 (cx+30, cy-12), (cx+22, cy-4)], 4)
            pygame.draw.polygon(surf, edge_c,
                [(cx+22, cy-4),(cx+30, cy-12),(cx+26, cy+2)])
            # antennae
            sw = math.sin(self.t * 0.06) * 3
            pygame.draw.line(surf, edge_c, (cx-6, cy-92), (cx-10-sw, cy-108), 2)
            pygame.draw.line(surf, edge_c, (cx+6, cy-92), (cx+10+sw, cy-108), 2)
        elif self.kind == 'soul_tyrant':
            # robed sorcerer
            pygame.draw.polygon(surf, body_c,
                [(cx-32, cy),(cx+32, cy),(cx+18, cy-66),(cx-18, cy-66)])
            pygame.draw.ellipse(surf, body_c, (cx-18, cy-88, 36, 28))
            pygame.draw.ellipse(surf, edge_c, (cx-16, cy-86, 32, 24), 2)
            pygame.draw.circle(surf, edge_c, (cx-6, cy-76), 2)
            pygame.draw.circle(surf, edge_c, (cx+6, cy-76), 2)
            # floating rune above
            rune_y = cy - 110 + int(math.sin(self.t*0.08) * 4)
            pygame.draw.circle(surf, edge_c, (cx, rune_y), 8, 2)
            pygame.draw.circle(surf, edge_c, (cx, rune_y), 4, 1)
            lights.add(int(cx), int(rune_y), 50, edge_c, intensity=0.6)
        elif self.kind == 'nosk':
            # wide hunched mimic
            pygame.draw.polygon(surf, body_c,
                [(cx-36, cy),(cx+36, cy),(cx+24, cy-58),(cx-24, cy-58)])
            pygame.draw.ellipse(surf, body_c, (cx-24, cy-90, 48, 36))
            pygame.draw.ellipse(surf, (200, 40, 60), (cx-14, cy-78, 28, 20))
            pygame.draw.ellipse(surf, (140, 20, 40), (cx-14, cy-78, 28, 20), 2)
            # teeth
            for i in range(6):
                tx = cx - 12 + i*4
                pygame.draw.polygon(surf, (240, 240, 240),
                    [(tx, cy-78), (tx+3, cy-78), (tx+1, cy-72)])
                pygame.draw.polygon(surf, (240, 240, 240),
                    [(tx, cy-62), (tx+3, cy-62), (tx+1, cy-68)])
            # multiple eyes
            for ox, oy in [(-18,-78),(-12,-86),(12,-86),(18,-78)]:
                pygame.draw.circle(surf, (240, 60, 80), (cx+ox, cy+oy), 2)
                pygame.draw.circle(surf, (255, 200, 200), (cx+ox, cy+oy-1), 1)
            # legs
            for off in (-32, -20, 20, 32):
                pygame.draw.line(surf, body_c,
                    (cx+off, cy-12), (cx+off + (1 if off>0 else -1)*8, cy+10), 4)
        elif self.kind == 'hollow':
            # tall ghostly figure
            pygame.draw.ellipse(surf, body_c, (cx-18, cy, 36, 32))
            pygame.draw.polygon(surf, body_c,
                [(cx-22, cy),(cx+22, cy),(cx+14, cy-56),(cx-14, cy-56)])
            pygame.draw.ellipse(surf, body_c, (cx-18, cy-90, 36, 36))
            pygame.draw.ellipse(surf, (245, 240, 225), (cx-14, cy-86, 28, 30))
            pygame.draw.ellipse(surf, (140, 130, 110), (cx-14, cy-86, 28, 30), 2)
            # empty eye sockets
            pygame.draw.ellipse(surf, (8, 6, 16), (cx-7, cy-76, 5, 8))
            pygame.draw.ellipse(surf, (8, 6, 16), (cx+2, cy-76, 5, 8))
            # tear streaks
            pygame.draw.line(surf, (140, 130, 110),
                             (cx-4, cy-70), (cx-4, cy-60), 1)
            pygame.draw.line(surf, (140, 130, 110),
                             (cx+4, cy-70), (cx+4, cy-60), 1)
            # crown of 5 horns
            for off, h in [(-14,10),(-7,16),(0,22),(7,16),(14,10)]:
                pygame.draw.polygon(surf, (245, 240, 225),
                    [(cx+off-3, cy-90),(cx+off+3, cy-90),(cx+off, cy-90-h)])
                pygame.draw.polygon(surf, (140, 130, 110),
                    [(cx+off-3, cy-90),(cx+off+3, cy-90),(cx+off, cy-90-h)], 1)
            if self.hp <= self.max_hp // 2:
                # leaking void tendrils
                pygame.draw.line(surf, (160, 100, 220),
                    (cx - self.facing*30, cy-40),
                    (cx - self.facing*12, cy-30), 2)
                pygame.draw.line(surf, (160, 100, 220),
                    (cx - self.facing*22, cy-20),
                    (cx - self.facing*10, cy-12), 2)


class Player:
    def __init__(self, x, y, state):
        self.x = float(x); self.y = float(y)
        self.w = 14; self.h = 36
        self.vx = 0.0; self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.on_wall = 0
        self.coyote = 0; self.buffer = 0
        ups = state['upgrades']
        self.max_jumps = 2 + ups.get('triple_jump', 0)
        self.jumps_left = self.max_jumps
        self.dash_cd = 0
        self.dash_t = 0; self.dash_dir = 1
        cd_reduce = ups.get('dash_cd', 0) * 6
        self.dash_cooldown_max = max(8, DASH_COOLDOWN - cd_reduce)
        self.nail_damage = NAIL_BASE_DAMAGE + ups.get('nail_damage', 0)
        self.nail_reach = NAIL_BASE_REACH + ups.get('nail_range', 0) * 14
        self.max_hp = 1 + ups.get('max_hp', 0)
        self.hp = self.max_hp
        iframe_bonus = ups.get('iframes', 0) * 18
        self.iframes_max = 36 + iframe_bonus
        self.iframes = 20
        self.has_glide = True
        self.gliding = False
        self.walk_t = 0
        self.alive = True; self.dead_t = 0
        self.mites = 0
        self.hit_flash = 0
        self.attack_cd = 0
        self.active_slash = None
        # afterimage trail buffer: list of (x, y, facing, age_max)
        self.afterimages = []
        self.damage_flash = 0   # red-pulse screen overlay
    def rect(self):
        return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h),
                           self.w, self.h)
    def update(self, level, keys, particles, cam, pad=None, jump_held=False):
        if not self.alive:
            self.dead_t += 1; return
        if self.iframes > 0: self.iframes -= 1
        if self.hit_flash > 0: self.hit_flash -= 1
        if self.attack_cd > 0: self.attack_cd -= 1
        if self.damage_flash > 0: self.damage_flash -= 1
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        wish = (1 if right else 0) - (1 if left else 0)
        if pad is not None and wish == 0:
            dp = pad.dpad_x(); ax = pad.axis_x()
            if dp != 0: wish = dp
            elif ax > 0: wish = 1
            elif ax < 0: wish = -1
        if wish != 0: self.facing = wish
        accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
        if self.dash_t > 0:
            self.vx = self.dash_dir * DASH_VEL
            self.dash_t -= 1
            # afterimage trail — every other frame to keep trail readable
            if self.dash_t % 2 == 0:
                self.afterimages.append([self.x, self.y, self.dash_dir, 14, 14])
            if self.dash_t % 2 == 0:
                particles.emit(self.x, self.y - 18, 1,
                    color=(220, 235, 255), life=14, size=2, kind='glow')
        else:
            if wish == 0:
                self.vx *= FRICTION
                if abs(self.vx) < 0.1: self.vx = 0
            else:
                self.vx += (wish * WALK - self.vx) * accel
        self.gliding = (self.has_glide and not self.on_ground
                        and self.jumps_left <= 0
                        and self.dash_t <= 0
                        and jump_held
                        and self.vy > -2)
        if self.dash_t <= 0:
            self.vy += GRAVITY
            if self.on_wall != 0 and self.vy > WALL_SLIDE_MAX and wish == self.on_wall:
                self.vy = WALL_SLIDE_MAX
                if random.random() < 0.4:
                    particles.emit(self.x + self.on_wall*8, self.y - 18, 1,
                        color=(120, 110, 130), life=18, size=1, kind='dust')
            if self.gliding:
                self.vy = min(self.vy, GLIDE_FALL)
                if random.random() < 0.4:
                    particles.emit(self.x - self.facing*8, self.y - 8, 1,
                        color=(200, 200, 240),
                        vel=(-self.facing*0.2, 0.3), life=24, size=2,
                        kind='glow')
            else:
                self.vy = min(self.vy, TERMINAL)
        if self.buffer > 0: self.buffer -= 1
        if self.coyote > 0: self.coyote -= 1
        if self.dash_cd > 0: self.dash_cd -= 1
        self.x += self.vx
        self._collide_x(level)
        self.y += self.vy
        self._collide_y(level, particles)
        self.on_wall = 0
        pl = pygame.Rect(int(self.x - self.w/2)-1,
                         int(self.y - self.h + 6), 2, self.h - 12)
        pr = pygame.Rect(int(self.x + self.w/2)-1,
                         int(self.y - self.h + 6), 2, self.h - 12)
        for s in level.solids:
            if pl.colliderect(s): self.on_wall = -1; break
            if pr.colliderect(s): self.on_wall = 1; break
        r = self.rect()
        if self.iframes == 0:
            for sp, _dir in level.spikes:
                if r.colliderect(sp):
                    self.take_damage(particles, cam); return
        for orb in level.orbs:
            if orb[2]:
                d2 = (orb[0] - self.x)**2 + (orb[1] - (self.y - 18))**2
                if d2 < 30*30:
                    orb[2] = False
                    self.mites += random.randint(2, 5)
                    particles.emit_spark_burst(orb[0], orb[1], n=14,
                        color=(255, 230, 140), speed=3, life=40)
        # advance afterimages
        for ai in self.afterimages[:]:
            ai[3] -= 1
            if ai[3] <= 0:
                self.afterimages.remove(ai)
        self.walk_t += 1
        if self.on_ground and abs(self.vx) > 1 and self.walk_t % 6 == 0:
            particles.emit(self.x - self.facing*4, self.y - 2, 1,
                color=(120, 110, 140), vel=(-self.facing*0.5, -0.4),
                life=20, size=2, kind='dust')
        if self.active_slash:
            self.active_slash.update()
            if self.active_slash.t <= 0:
                self.active_slash = None
    def jump(self, particles):
        if self.on_ground or self.coyote > 0:
            self.vy = JUMP_VEL
            self.on_ground = False; self.coyote = 0
            self.jumps_left = self.max_jumps - 1
            particles.emit(self.x, self.y, 10, color=(200, 190, 220),
                vel=(0,-1), spread=2, life=20, size=2, kind='dust')
            return True
        if self.on_wall != 0 and not self.on_ground:
            self.vy = WALL_JUMP_Y
            self.vx = -self.on_wall * WALL_JUMP_X
            self.facing = -self.on_wall
            self.jumps_left = self.max_jumps - 1
            particles.emit(self.x + self.on_wall*8, self.y - 18, 12,
                color=(200, 190, 220), spread=2, life=22, size=2, kind='dust')
            return True
        if self.jumps_left > 0:
            self.vy = JUMP_VEL * 0.92
            self.jumps_left -= 1
            # double jump burst
            for i in range(16):
                a = i / 16 * math.tau
                particles.emit(self.x + math.cos(a)*8,
                    self.y - 18 + math.sin(a)*8,
                    1, color=(220, 240, 255),
                    vel=(math.cos(a)*1.8, math.sin(a)*1.8),
                    life=28, size=2, kind='glow')
            return True
        return False
    def jump_release(self):
        if self.vy < 0: self.vy *= JUMP_CUT
    def try_dash(self, particles):
        if self.dash_cd > 0 or self.dash_t > 0: return
        self.dash_t = DASH_FRAMES
        self.dash_cd = self.dash_cooldown_max
        self.dash_dir = self.facing; self.vy = 0
        self.iframes = max(self.iframes, DASH_FRAMES)
        for i in range(12):
            particles.emit(self.x, self.y - 18, 1, color=(240,240,250),
                vel=(-self.dash_dir*2, random.uniform(-1,1)),
                life=24, size=3, kind='glow')
    def attack(self, keys, pad, particles, cam):
        if self.attack_cd > 0 or self.active_slash:
            return
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        dn = keys[pygame.K_s] or keys[pygame.K_DOWN]
        if pad:
            if pad.dpad_y() == 1 or pad.axis_y() < -0.3: up = True
            if pad.dpad_y() == -1 or pad.axis_y() > 0.3: dn = True
        if up:
            direction = 'up'
        elif dn and not self.on_ground:
            direction = 'down'
        else:
            direction = 'right' if self.facing > 0 else 'left'
        self.active_slash = Slash(self, direction, self.nail_damage,
                                  self.nail_reach)
        self.attack_cd = NAIL_COOLDOWN
        cam.kick(2)
        # whoosh particles in the slash direction
        for _ in range(10):
            ang_off = random.uniform(-0.5, 0.5)
            if direction == 'right': ang = 0 + ang_off
            elif direction == 'left': ang = math.pi + ang_off
            elif direction == 'up': ang = -math.pi/2 + ang_off
            else: ang = math.pi/2 + ang_off
            d = self.nail_reach * 0.7
            particles.emit(self.x + math.cos(ang)*d,
                           self.y - self.h//2 + math.sin(ang)*d,
                           1, color=(220, 240, 255),
                           vel=(math.cos(ang)*2, math.sin(ang)*2),
                           life=14, size=2, kind='glow')
    def pogo(self):
        self.vy = NAIL_POGO_VEL
        self.jumps_left = max(self.jumps_left, 1)
    def _collide_x(self, level):
        r = self.rect()
        for s in level.solids:
            if r.colliderect(s):
                if self.vx > 0: self.x = s.left - self.w/2
                elif self.vx < 0: self.x = s.right + self.w/2
                self.vx = 0; r = self.rect()
    def _collide_y(self, level, particles):
        r = self.rect()
        was_air = not self.on_ground
        self.on_ground = False
        for s in level.solids:
            if r.colliderect(s):
                if self.vy > 0:
                    self.y = s.top
                    if was_air and self.vy > 4:
                        particles.emit(self.x, self.y, 10,
                            color=(120, 110, 140),
                            vel=(0, -0.4), spread=2, life=22, size=2,
                            kind='dust')
                    self.vy = 0
                    self.on_ground = True
                    self.jumps_left = self.max_jumps
                    self.coyote = COYOTE
                elif self.vy < 0:
                    self.y = s.bottom + self.h
                    self.vy = 0
                r = self.rect()
        if not self.on_ground and was_air is False:
            self.coyote = COYOTE
    def take_damage(self, particles, cam):
        if self.iframes > 0: return
        self.hp -= 1
        self.iframes = self.iframes_max
        self.hit_flash = 12
        self.damage_flash = 24
        cam.kick(10)
        self.vx = -self.facing * 4
        self.vy = -5
        particles.emit_spark_burst(self.x, self.y - 18, n=30,
            color=(220, 80, 100), speed=4, life=30)
        particles.emit_shockwave(self.x, self.y - 18,
            color=(255, 80, 100), n=20, speed=3.5, life=20)
        if self.hp <= 0:
            self.die(particles, cam)
    def die(self, particles, cam):
        self.alive = False; cam.kick(14)
        particles.emit_spark_burst(self.x, self.y - 18, n=60,
            color=(220, 80, 100), speed=5, life=50)
        particles.emit_shockwave(self.x, self.y - 18,
            color=(255, 100, 120), n=40, speed=6, life=40)
    def draw(self, surf, camx, camy, lights, pal):
        if not self.alive: return
        # afterimages first (behind player)
        for ai in self.afterimages:
            ax, ay, af, life, mlife = ai
            alpha = int(50 * (life / mlife))
            draw_dash_afterimage(surf, ax - camx, ay - 18 - camy, af, alpha)
        # invisibility flicker on iframes
        if self.iframes > 0 and (self.iframes // 3) % 2 == 0:
            return
        draw_knight(surf, self.x - camx, self.y - 18 - camy,
            facing=self.facing, walk_t=self.walk_t,
            in_air=not self.on_ground, dashing=self.dash_t > 0,
            gliding=self.gliding, hit_flash=self.hit_flash > 0)
        # (player halo light removed — no more blue circle)


class Level:
    def __init__(self, rows, area):
        self.rows = rows; self.area = area
        self.pal = PAL[area['pal']]
        self.h = len(rows)
        self.w = max(len(r) for r in rows)
        self.solids = []           # individual tiles for both drawing and collision
        self.tiles = []            # (Rect, seed) for stable per-tile detail
        self.spikes = []
        self.orbs = []
        self.enemy_specs = []
        self.saw_specs = []
        self.npc_pos = None
        self.shop_pos = None
        self.spawn = (100, 100); self.door = None
        self.boss_arena = None; self.is_boss_level = False
        for ty, row in enumerate(rows):
            for tx, ch in enumerate(row):
                px, py = tx * TILE, ty * TILE
                if ch == '#':
                    rect = pygame.Rect(px, py, TILE, TILE)
                    self.solids.append(rect)
                    self.tiles.append((rect, tx * 17 + ty * 31))
                elif ch == '^':
                    self.spikes.append((pygame.Rect(px+2, py+12, TILE-4, TILE-14),'up'))
                elif ch == 'v':
                    self.spikes.append((pygame.Rect(px+2, py, TILE-4, TILE-14),'down'))
                elif ch == '<':
                    self.spikes.append((pygame.Rect(px+12, py+2, TILE-14, TILE-4),'left'))
                elif ch == '>':
                    self.spikes.append((pygame.Rect(px, py+2, TILE-14, TILE-4),'right'))
                elif ch == 'P':
                    self.spawn = (px + TILE//2, py + TILE - 16)
                elif ch == 'D':
                    self.door = pygame.Rect(px, py - TILE, TILE, TILE*2)
                elif ch == 'N':
                    self.npc_pos = (px + TILE//2, py + TILE - 8)
                elif ch == 'K':
                    self.shop_pos = (px + TILE//2, py + TILE - 8)
                elif ch == 'o':
                    self.orbs.append([px + TILE//2, py + TILE//2, True])
                elif ch in ('c', 'f', 's'):
                    kinds = {'c':'crawler','f':'flyer','s':'spitter'}
                    self.enemy_specs.append((px + TILE//2, py + TILE//2, kinds[ch]))
                elif ch == '~':
                    self.saw_specs.append((px + TILE//2, py + TILE//2))
                elif ch == 'B':
                    self.boss_arena = (px + TILE//2, py + TILE)
                    self.is_boss_level = True
        self._merge_solids()
    def _merge_solids(self):
        """Merge horizontally-adjacent tiles in self.solids for cheap collision.
        Keeps self.tiles intact so drawing still has per-tile granularity."""
        by_y = {}
        for r in self.solids:
            by_y.setdefault(r.top, []).append(r)
        merged = []
        for y, rs in by_y.items():
            rs.sort(key=lambda r: r.left)
            cur = rs[0]
            for r in rs[1:]:
                if r.left == cur.right:
                    cur = pygame.Rect(cur.left, cur.top,
                                      cur.width + r.width, cur.height)
                else:
                    merged.append(cur); cur = r
            merged.append(cur)
        self.solids = merged


class Background:
    """Multi-layer parallax + atmospheric depth. Five layers:
       sky gradient -> far silhouettes -> mid silhouettes -> near silhouettes
       -> distant mote field -> fog overlay.
    """
    def __init__(self, pal):
        self.pal = pal
        self.sky = self._sky()
        # multiple silhouette layers at different colors and heights
        self.far = self._silhouette(pal['far'], 200, 5, 60, 1.0)
        self.mid = self._silhouette(pal['mid'], 280, 8, 50, 0.9)
        self.near = self._silhouette(pal['near'], 360, 12, 36, 0.85)
        # additional towers/structures at the deepest layer
        self.structures = self._structures(pal['mid'], pal['edge'])
        self.motes = [(random.randint(0, WIDTH), random.randint(0, HEIGHT),
                       random.uniform(0.1, 0.4), random.uniform(0.3, 1.0))
                      for _ in range(80)]
        self.rain = pal.get('rain', False)
        if self.rain:
            self.drops = [(random.randint(0, WIDTH),
                          random.randint(-HEIGHT, HEIGHT),
                          random.uniform(8, 13))
                         for _ in range(180)]
    def _sky(self):
        s = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(self.pal['sky_top'][0]*(1-t) + self.pal['sky_bot'][0]*t)
            g = int(self.pal['sky_top'][1]*(1-t) + self.pal['sky_bot'][1]*t)
            b = int(self.pal['sky_top'][2]*(1-t) + self.pal['sky_bot'][2]*t)
            pygame.draw.line(s, (r, g, b), (0, y), (WIDTH, y))
        return s
    def _silhouette(self, color, height, count, jitter, opacity=1.0):
        """Generate a silhouette band — jagged mountain shapes."""
        s = pygame.Surface((WIDTH*2, HEIGHT), pygame.SRCALPHA)
        base_y = HEIGHT - 60
        pts = [(0, HEIGHT)]
        step = (WIDTH * 2) / count
        for i in range(count + 1):
            x = int(i * step)
            y = base_y - height + random.randint(-jitter, jitter)
            pts.append((x, y))
        pts.append((WIDTH * 2, HEIGHT))
        color_a = (*color, int(255 * opacity))
        pygame.draw.polygon(s, color_a, pts)
        # spire details
        for _ in range(count * 2):
            x = random.randint(0, WIDTH * 2)
            h = random.randint(60, 180)
            top_y = base_y - height + 40
            pygame.draw.polygon(s, color_a,
                [(x - 14, top_y), (x + 14, top_y), (x, top_y - h)])
        return s
    def _structures(self, color_base, color_edge):
        """Add silhouetted architectural details to mid layer."""
        s = pygame.Surface((WIDTH*2, HEIGHT), pygame.SRCALPHA)
        base_y = HEIGHT - 80
        for _ in range(10):
            x = random.randint(0, WIDTH * 2)
            w = random.randint(40, 90)
            h = random.randint(100, 220)
            pygame.draw.rect(s, color_base, (x, base_y - h, w, h))
            # arches
            arch_top = base_y - h + 12
            for ai in range(2):
                ax = x + 8 + ai * (w // 2)
                aw = w // 3
                pygame.draw.rect(s, (10, 8, 18),
                                 (ax, arch_top + 16, aw, 60))
            # spire
            pygame.draw.polygon(s, color_base,
                [(x, base_y - h), (x + w, base_y - h),
                 (x + w // 2, base_y - h - 40)])
        return s
    def draw(self, surf, camx, camy, t):
        surf.blit(self.sky, (0, 0))
        # structures at far layer
        off = int(-camx * 0.15) % (WIDTH * 2)
        surf.blit(self.structures, (off - WIDTH * 2, 0))
        surf.blit(self.structures, (off, 0))
        for layer, factor in [(self.far, 0.1), (self.mid, 0.25),
                               (self.near, 0.5)]:
            off = int(-camx * factor) % (WIDTH * 2)
            surf.blit(layer, (off - WIDTH*2, 0))
            surf.blit(layer, (off, 0))
        # ambient motes (independent of camera)
        for i, (mx, my, sp, sz) in enumerate(self.motes):
            x = (mx + t*sp) % WIDTH
            y = (my + math.sin(t*0.02 + i)*6) % HEIGHT
            c = self.pal['motes']
            tmp = pygame.Surface((int(sz*6), int(sz*6)), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*c, 20),
                (int(sz*3), int(sz*3)), int(sz*3))
            pygame.draw.circle(tmp, (*c, 100),
                (int(sz*3), int(sz*3)), max(1, int(sz)))
            surf.blit(tmp, (x, y), special_flags=pygame.BLEND_ADD)
        if self.rain:
            new = []
            for x, y, sp in self.drops:
                pygame.draw.line(surf, (140, 180, 240),
                                 (x, y), (x - 2, y + 14), 1)
                y += sp
                if y > HEIGHT:
                    y = -10; x = random.randint(0, WIDTH)
                new.append((x, y, sp))
            self.drops = new
        # fog overlay
        fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fog.fill(self.pal['fog'])
        surf.blit(fog, (0, 0))


# ===========================================================================
# Level loading + helpers
# ===========================================================================
def load_level(area_id, sub_idx, state):
    area = AREAS[AREA_INDEX[area_id]]
    rows = get_level_rows(area_id, sub_idx)
    level = Level(rows, area)
    player = Player(level.spawn[0], level.spawn[1], state)
    bg = Background(level.pal)
    cam = Camera()
    particles = Particles()
    lights = Lights()
    enemies = [Enemy(x, y, kind, level)
               for (x, y, kind) in level.enemy_specs]
    projectiles = []
    saws = [Saw(x, y, level) for (x, y) in level.saw_specs]
    boss = None
    if level.is_boss_level and area['boss']:
        bx, by = level.boss_arena
        boss = Boss(bx, by, area['boss'])
    return level, player, bg, cam, particles, lights, enemies, projectiles, boss, saws


def unlock_next_if_needed(state, area_id, sub_idx):
    """Advance area unlock if the threshold of completed sublevels is hit."""
    area_idx = AREA_INDEX[area_id]
    if area_idx + 1 >= len(AREAS):
        return None
    next_area = AREAS[area_idx + 1]
    if next_area['id'] in state['unlocked']:
        return None
    threshold = unlock_threshold(area_idx + 1)
    required = int(threshold * SUBLEVELS_PER_AREA)
    completed_here = state['completed'].get(area_id, [])
    if len(completed_here) >= required:
        state['unlocked'].append(next_area['id'])
        return next_area
    return None


def try_buy(state, idx):
    """Attempt to buy upgrade `idx`. Returns (ok, message)."""
    u = UPGRADES[idx]
    rank = state['upgrades'].get(u['id'], 0)
    if rank >= u['max_rank']:
        return False, "Maxed out."
    cost = upgrade_cost(u, rank)
    if state['mites'] < cost:
        return False, f"Need {cost} mites."
    state['mites'] -= cost
    state['upgrades'][u['id']] = rank + 1
    return True, f"Acquired: {u['name']} {rank+1}/{u['max_rank']}"


# ===========================================================================
# HUD, shop, map drawing
# ===========================================================================
def draw_hud(surf, t, state, player, area, sub_idx, npc_msg=None,
             shop_prompt=False, boss=None):
    """Top-left HP masks, top-right mites, dash/nail cooldown bars,
    area name, controls hint, optional NPC dialogue, optional shop prompt,
    optional boss HP bar."""
    # framed HP panel
    hp_panel = pygame.Rect(20, 16, 30 + player.max_hp * 28, 44)
    pygame.draw.rect(surf, (10, 8, 18, 200), hp_panel)
    pygame.draw.rect(surf, (60, 50, 80), hp_panel, 2)
    breathe = t * 0.04
    for i in range(player.max_hp):
        cx = hp_panel.left + 24 + i * 28
        draw_mask_icon(surf, cx, hp_panel.centery,
                       full=i < player.hp,
                       breathe_phase=breathe + i * 0.5)
    # mites — top-right with gem icon
    mites_total = state['mites'] + (player.mites if player.alive else 0)
    mtxt = MID.render(f"{mites_total}", True, (255, 230, 140))
    pad = 16
    panel_w = mtxt.get_width() + 60
    mp = pygame.Rect(WIDTH - panel_w - 20, 16, panel_w, 44)
    pygame.draw.rect(surf, (10, 8, 18, 200), mp)
    pygame.draw.rect(surf, (80, 60, 30), mp, 2)
    # mini-gem icon
    gx, gy = mp.left + 24, mp.centery
    pygame.draw.polygon(surf, (255, 230, 140),
        [(gx, gy - 8),(gx + 6, gy),(gx, gy + 8),(gx - 6, gy)])
    pygame.draw.polygon(surf, (180, 140, 60),
        [(gx, gy - 8),(gx + 6, gy),(gx, gy + 8),(gx - 6, gy)], 1)
    surf.blit(mtxt, (mp.left + 42, mp.centery - mtxt.get_height()//2))
    # area label
    label = MID.render(area['name'], True, (220, 220, 240))
    sub = SMALL.render(f"sub {sub_idx+1} / {SUBLEVELS_PER_AREA}",
                       True, (180, 180, 200))
    surf.blit(label, (WIDTH//2 - label.get_width()//2, 18))
    surf.blit(sub, (WIDTH//2 - sub.get_width()//2, 48))
    # cooldown bars bottom-left
    bar_y = HEIGHT - 36
    # dash cooldown
    dpx = 24; dpy = bar_y
    pygame.draw.rect(surf, (10, 8, 18), (dpx, dpy, 80, 8))
    if player.dash_cd <= 0:
        pygame.draw.rect(surf, (140, 220, 255), (dpx, dpy, 80, 8))
    else:
        ratio = 1 - (player.dash_cd / player.dash_cooldown_max)
        pygame.draw.rect(surf, (90, 140, 200),
                         (dpx, dpy, int(80 * ratio), 8))
    pygame.draw.rect(surf, (90, 100, 140), (dpx, dpy, 80, 8), 1)
    surf.blit(SMALL.render("DASH", True, (180, 200, 220)), (dpx, dpy - 14))
    # nail cooldown
    npx = dpx + 100
    pygame.draw.rect(surf, (10, 8, 18), (npx, dpy, 80, 8))
    if player.attack_cd <= 0:
        pygame.draw.rect(surf, (255, 240, 200), (npx, dpy, 80, 8))
    else:
        ratio = 1 - (player.attack_cd / NAIL_COOLDOWN)
        pygame.draw.rect(surf, (200, 180, 140),
                         (npx, dpy, int(80 * ratio), 8))
    pygame.draw.rect(surf, (140, 130, 100), (npx, dpy, 80, 8), 1)
    surf.blit(SMALL.render("NAIL", True, (220, 210, 180)), (npx, dpy - 14))
    # controls hint bottom-right
    hint = SMALL.render(
        "A/D move  Space jump (hold glide)  Shift dash  J nail  Tab map  R restart  Esc quit",
        True, (160, 160, 180))
    surf.blit(hint, (WIDTH - hint.get_width() - 20, HEIGHT - 22))
    # NPC dialogue box
    if npc_msg:
        bw, bh = 760, 80
        bx = WIDTH//2 - bw//2
        by = HEIGHT - bh - 60
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((10, 8, 18, 220))
        pygame.draw.rect(box, (90, 80, 120), (0, 0, bw, bh), 2)
        surf.blit(box, (bx, by))
        speaker, line = npc_msg
        sp_txt = FONT.render(speaker, True, (220, 200, 140))
        surf.blit(sp_txt, (bx + 16, by + 10))
        ln_txt = FONT.render(line, True, (220, 220, 240))
        surf.blit(ln_txt, (bx + 16, by + 38))
    # shop prompt
    if shop_prompt:
        msg = FONT.render("press UP / W / E to trade", True,
                          (255, 220, 140))
        bx = WIDTH//2 - msg.get_width()//2 - 14
        by = HEIGHT - 160
        bg = pygame.Surface((msg.get_width() + 28, msg.get_height() + 12),
                            pygame.SRCALPHA)
        bg.fill((10, 8, 18, 220))
        pygame.draw.rect(bg, (180, 140, 60), bg.get_rect(), 2)
        surf.blit(bg, (bx, by))
        surf.blit(msg, (bx + 14, by + 6))
    # boss HP bar
    if boss and boss.state != 'dead':
        bw, bh = 640, 18
        bx = WIDTH//2 - bw//2
        by = 78
        pygame.draw.rect(surf, (10, 8, 18, 230), (bx-2, by-2, bw+4, bh+4))
        pygame.draw.rect(surf, (40, 30, 50), (bx, by, bw, bh))
        ratio = boss.hp / boss.max_hp if boss.max_hp > 0 else 0
        col = (220, 80, 100) if ratio > 0.5 else (255, 130, 60)
        if ratio < 0.25: col = (255, 60, 60)
        pygame.draw.rect(surf, col, (bx, by, int(bw * ratio), bh))
        pygame.draw.rect(surf, (200, 200, 220), (bx, by, bw, bh), 2)
        name = MID.render(Boss.NAME_TABLE.get(boss.kind, "BOSS"), True,
                          (255, 255, 255))
        surf.blit(name, (WIDTH//2 - name.get_width()//2, by - 30))


def draw_shop(surf, t, state, cursor, message=None, message_t=0):
    """Six-row upgrade shop overlay."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 3, 10, 220))
    surf.blit(overlay, (0, 0))
    # panel
    pw, ph = 880, 540
    px = WIDTH // 2 - pw // 2
    py = HEIGHT // 2 - ph // 2
    pygame.draw.rect(surf, (16, 12, 24), (px, py, pw, ph))
    pygame.draw.rect(surf, (180, 140, 60), (px, py, pw, ph), 3)
    # title
    title = BIG.render("MERCHANT", True, (255, 220, 140))
    surf.blit(title, (WIDTH//2 - title.get_width()//2, py + 18))
    # mites
    mtxt = MID.render(f"mites: {state['mites']}", True, (255, 230, 140))
    surf.blit(mtxt, (WIDTH//2 - mtxt.get_width()//2, py + 80))
    # rows
    row_y = py + 130
    for i, u in enumerate(UPGRADES):
        rank = state['upgrades'].get(u['id'], 0)
        maxed = rank >= u['max_rank']
        cost = upgrade_cost(u, rank) if not maxed else 0
        selected = (i == cursor)
        rect = pygame.Rect(px + 30, row_y + i * 56, pw - 60, 48)
        if selected:
            pygame.draw.rect(surf, (40, 30, 50), rect)
            pygame.draw.rect(surf, (255, 220, 140), rect, 2)
        else:
            pygame.draw.rect(surf, (24, 18, 32), rect)
            pygame.draw.rect(surf, (80, 60, 100), rect, 1)
        name = MID.render(u['name'], True,
            (255, 230, 140) if selected else (220, 210, 230))
        surf.blit(name, (rect.left + 16, rect.top + 6))
        desc = SMALL.render(u['desc'], True, (180, 180, 200))
        surf.blit(desc, (rect.left + 16, rect.top + 30))
        # rank pips
        for r in range(u['max_rank']):
            cx = rect.right - 200 + r * 18
            cy = rect.centery
            if r < rank:
                pygame.draw.circle(surf, (255, 220, 140), (cx, cy), 6)
                pygame.draw.circle(surf, (180, 140, 60), (cx, cy), 6, 1)
            else:
                pygame.draw.circle(surf, (60, 50, 70), (cx, cy), 6, 2)
        # cost
        if maxed:
            ct = FONT.render("MAX", True, (140, 220, 140))
        else:
            can = state['mites'] >= cost
            ct = FONT.render(f"{cost} mites", True,
                             (255, 230, 140) if can else (160, 80, 100))
        surf.blit(ct, (rect.right - 90, rect.centery - ct.get_height()//2))
    # toast
    if message and message_t > 0:
        toast = MID.render(message, True, (255, 240, 200))
        surf.blit(toast, (WIDTH//2 - toast.get_width()//2, py + ph - 60))
    # footer
    foot = SMALL.render(
        "W/S or Up/Down to move    Enter / E to buy    Esc / E to leave",
        True, (180, 180, 200))
    surf.blit(foot, (WIDTH//2 - foot.get_width()//2, py + ph - 28))


def draw_map(surf, t, state, current_area, current_sub):
    """Area list + sublevel grid + unlock progress."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 3, 10, 230))
    surf.blit(overlay, (0, 0))
    # title
    title = BIG.render("MAP OF HALLOWNEST", True, (200, 220, 255))
    surf.blit(title, (WIDTH//2 - title.get_width()//2, 30))
    # area list on left
    list_x = 60; list_y = 110
    for i, area in enumerate(AREAS):
        unlocked = area['id'] in state['unlocked']
        is_current = area['id'] == current_area
        col = (220, 220, 240) if unlocked else (60, 55, 70)
        if is_current: col = (255, 240, 180)
        prefix = '> ' if is_current else '  '
        suffix = '' if unlocked else '  (locked)'
        txt = FONT.render(f"{prefix}{area['name']}{suffix}", True, col)
        surf.blit(txt, (list_x, list_y + i * 26))
        # sublevels completed
        if unlocked:
            comp = len(state['completed'].get(area['id'], []))
            ct = SMALL.render(f"{comp}/{SUBLEVELS_PER_AREA}",
                              True, (180, 180, 220))
            surf.blit(ct, (list_x + 280, list_y + i * 26 + 4))
    # unlock progress hint
    cur_idx = AREA_INDEX[current_area]
    if cur_idx + 1 < len(AREAS):
        next_area = AREAS[cur_idx + 1]
        thresh = unlock_threshold(cur_idx + 1)
        req = int(thresh * SUBLEVELS_PER_AREA)
        comp = len(state['completed'].get(current_area, []))
        if next_area['id'] not in state['unlocked']:
            line = (f"complete {req} sublevels here to unlock "
                    f"{next_area['name']} ({comp}/{req})")
            txt = SMALL.render(line, True, (255, 220, 140))
            surf.blit(txt, (list_x, HEIGHT - 110))
    # sublevel grid on right
    grid_x = WIDTH - 460; grid_y = 110
    g_title = MID.render(AREAS[AREA_INDEX[current_area]]['name'],
                         True, (255, 240, 180))
    surf.blit(g_title, (grid_x, grid_y - 36))
    cell = 38
    completed = set(state['completed'].get(current_area, []))
    for s in range(SUBLEVELS_PER_AREA):
        col_i = s % 10; row_i = s // 10
        cx = grid_x + col_i * cell; cy = grid_y + row_i * cell
        if s == current_sub:
            pygame.draw.rect(surf, (255, 240, 180),
                             (cx, cy, cell - 2, cell - 2))
        elif s in completed:
            pygame.draw.rect(surf, (90, 140, 200),
                             (cx, cy, cell - 2, cell - 2))
        else:
            pygame.draw.rect(surf, (40, 30, 50),
                             (cx, cy, cell - 2, cell - 2))
        pygame.draw.rect(surf, (80, 70, 100),
                         (cx, cy, cell - 2, cell - 2), 1)
        num = SMALL.render(str(s + 1), True,
            (8, 6, 12) if s == current_sub else (200, 200, 220))
        surf.blit(num, (cx + (cell - 2) // 2 - num.get_width()//2,
                       cy + (cell - 2) // 2 - num.get_height()//2))
    # footer
    foot = SMALL.render(
        "Tab / Esc close    PgUp/PgDown previous/next sublevel    "
        "[ / ] previous/next unlocked area",
        True, (180, 180, 220))
    surf.blit(foot, (WIDTH//2 - foot.get_width()//2, HEIGHT - 36))


# ===========================================================================
# Main loop
# ===========================================================================
def main():
    state = load_save()
    pad = Pad()
    music = Music()
    area_id = state.get('last_area', 'dirtmouth')
    if area_id not in [a['id'] for a in AREAS] or area_id not in state['unlocked']:
        area_id = 'dirtmouth'
    sub_idx = state.get('last_sub', 0)
    if not (0 <= sub_idx < SUBLEVELS_PER_AREA):
        sub_idx = 0
    level, player, bg, cam, particles, lights, enemies, projectiles, boss, saws = \
        load_level(area_id, sub_idx, state)
    mode = 'play'   # 'play' | 'map' | 'shop'
    shop_cursor = 0; shop_msg = None; shop_msg_t = 0
    npc_dialog_t = 240  # show NPC line at start of intro levels
    fade = 0          # >0 = fading out, <0 = fading in
    pending_transition = None
    hit_pause = 0
    slowmo = 0
    boss_just_killed = False
    t = 0
    running = True

    def cur_area():
        return AREAS[AREA_INDEX[area_id]]

    def reload_current():
        nonlocal level, player, bg, cam, particles, lights
        nonlocal enemies, projectiles, boss, saws, npc_dialog_t
        # bank mites earned in the run
        state['mites'] += player.mites if player.alive else 0
        level, player, bg, cam, particles, lights, enemies, projectiles, boss, saws = \
            load_level(area_id, sub_idx, state)
        npc_dialog_t = 240 if sub_idx == 0 else 0

    def goto(new_area, new_sub):
        nonlocal area_id, sub_idx
        area_id = new_area
        sub_idx = max(0, min(SUBLEVELS_PER_AREA - 1, new_sub))
        state['last_area'] = area_id
        state['last_sub'] = sub_idx
        reload_current()

    while running:
        for ev in pygame.event.get():
            # Music: catch the track-ended event from pygame's mixer.
            music.handle_event(ev)
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.JOYDEVICEADDED:
                pad.on_added(ev.device_index)
            elif ev.type == pygame.JOYDEVICEREMOVED:
                pad.on_removed(ev.instance_id)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if mode == 'shop':
                        # apply purchased upgrades on exit
                        mode = 'play'
                        save_state(state)
                        reload_current()
                    elif mode != 'play':
                        mode = 'play'
                    else:
                        running = False
                elif ev.key == pygame.K_TAB:
                    if mode == 'shop':
                        # exit shop properly before showing map
                        save_state(state); reload_current()
                        mode = 'map'
                    else:
                        mode = 'map' if mode != 'map' else 'play'
                elif ev.key == pygame.K_r and mode == 'play':
                    state['mites'] += player.mites if player.alive else 0
                    save_state(state)
                    reload_current()
                elif mode == 'play':
                    if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        if level.shop_pos and player.alive:
                            d2 = ((player.x - level.shop_pos[0])**2
                                  + (player.y - level.shop_pos[1])**2)
                            if d2 < 70*70:
                                mode = 'shop'; shop_cursor = 0
                                save_state(state)
                                continue
                        if player.alive:
                            player.jump(particles)
                    elif ev.key == pygame.K_e and mode == 'play':
                        if level.shop_pos and player.alive:
                            d2 = ((player.x - level.shop_pos[0])**2
                                  + (player.y - level.shop_pos[1])**2)
                            if d2 < 70*70:
                                mode = 'shop'; shop_cursor = 0
                                save_state(state)
                    elif ev.key == pygame.K_LSHIFT and player.alive:
                        player.try_dash(particles)
                    elif ev.key == pygame.K_j and player.alive:
                        keys = pygame.key.get_pressed()
                        player.attack(keys, pad, particles, cam)
                    elif ev.key == pygame.K_v:
                        music.toggle_mute()
                    elif ev.key == pygame.K_n:
                        music.skip()
                    elif ev.key == pygame.K_MINUS:
                        music.vol_down()
                    elif ev.key == pygame.K_EQUALS:
                        music.vol_up()
                    elif ev.key == pygame.K_PAGEUP:
                        if sub_idx + 1 < SUBLEVELS_PER_AREA:
                            goto(area_id, sub_idx + 1)
                    elif ev.key == pygame.K_PAGEDOWN:
                        if sub_idx > 0:
                            goto(area_id, sub_idx - 1)
                    elif ev.key == pygame.K_LEFTBRACKET:
                        # previous unlocked area
                        unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                        i = unl.index(area_id) if area_id in unl else 0
                        if i > 0: goto(unl[i-1], 0)
                    elif ev.key == pygame.K_RIGHTBRACKET:
                        unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                        i = unl.index(area_id) if area_id in unl else 0
                        if i + 1 < len(unl): goto(unl[i+1], 0)
                elif mode == 'shop':
                    if ev.key in (pygame.K_w, pygame.K_UP):
                        shop_cursor = (shop_cursor - 1) % len(UPGRADES)
                    elif ev.key in (pygame.K_s, pygame.K_DOWN):
                        shop_cursor = (shop_cursor + 1) % len(UPGRADES)
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        ok, msg = try_buy(state, shop_cursor)
                        shop_msg = msg; shop_msg_t = 90
                        if ok: save_state(state)
                    elif ev.key in (pygame.K_e, pygame.K_q, pygame.K_m,
                                    pygame.K_BACKSPACE):
                        mode = 'play'; save_state(state)
                        # re-apply upgrades by reloading player
                        reload_current()
                elif mode == 'map':
                    # any of these close the map — covers phone keyboards
                    # without a working Tab or Esc
                    if ev.key in (pygame.K_m, pygame.K_RETURN,
                                  pygame.K_BACKSPACE, pygame.K_q,
                                  pygame.K_e):
                        mode = 'play'
                    elif ev.key in (pygame.K_PAGEUP, pygame.K_d,
                                    pygame.K_RIGHT):
                        if sub_idx + 1 < SUBLEVELS_PER_AREA:
                            goto(area_id, sub_idx + 1)
                    elif ev.key in (pygame.K_PAGEDOWN, pygame.K_a,
                                    pygame.K_LEFT):
                        if sub_idx > 0:
                            goto(area_id, sub_idx - 1)
                    elif ev.key in (pygame.K_LEFTBRACKET, pygame.K_w,
                                    pygame.K_UP):
                        unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                        i = unl.index(area_id) if area_id in unl else 0
                        if i > 0: goto(unl[i-1], 0)
                    elif ev.key in (pygame.K_RIGHTBRACKET, pygame.K_s,
                                    pygame.K_DOWN):
                        unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                        i = unl.index(area_id) if area_id in unl else 0
                        if i + 1 < len(unl): goto(unl[i+1], 0)
            elif ev.type == pygame.KEYUP:
                if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if mode == 'play' and player.alive:
                        player.jump_release()
            elif ev.type == pygame.JOYBUTTONDOWN and mode == 'play':
                if ev.button in PAD_JUMP and player.alive:
                    if level.shop_pos:
                        d2 = ((player.x - level.shop_pos[0])**2
                              + (player.y - level.shop_pos[1])**2)
                        if d2 < 70*70:
                            mode = 'shop'; shop_cursor = 0
                            save_state(state)
                            continue
                    player.jump(particles)
                elif ev.button in PAD_DASH and player.alive:
                    player.try_dash(particles)
                elif ev.button in PAD_NAIL and player.alive:
                    keys = pygame.key.get_pressed()
                    player.attack(keys, pad, particles, cam)
                elif ev.button in PAD_NEXT:
                    if sub_idx + 1 < SUBLEVELS_PER_AREA:
                        goto(area_id, sub_idx + 1)
                elif ev.button in PAD_PREV:
                    if sub_idx > 0:
                        goto(area_id, sub_idx - 1)
                elif ev.button in PAD_MAP:
                    mode = 'map'
                elif ev.button in PAD_QUIT:
                    running = False
            elif ev.type == pygame.JOYBUTTONUP and mode == 'play':
                if ev.button in PAD_JUMP and player.alive:
                    player.jump_release()
            elif ev.type == pygame.JOYBUTTONDOWN and mode == 'shop':
                if ev.button in PAD_JUMP:
                    ok, msg = try_buy(state, shop_cursor)
                    shop_msg = msg; shop_msg_t = 90
                    if ok: save_state(state)
                elif ev.button in PAD_NAIL or ev.button in PAD_DASH \
                        or ev.button in PAD_MAP:
                    mode = 'play'; save_state(state); reload_current()
                elif ev.button in PAD_NEXT:
                    shop_cursor = (shop_cursor + 1) % len(UPGRADES)
                elif ev.button in PAD_PREV:
                    shop_cursor = (shop_cursor - 1) % len(UPGRADES)
            elif ev.type == pygame.JOYBUTTONDOWN and mode == 'map':
                # any face button or Map/Back closes the map
                if (ev.button in PAD_JUMP or ev.button in PAD_DASH
                        or ev.button in PAD_NAIL or ev.button in PAD_MAP):
                    mode = 'play'
                elif ev.button in PAD_NEXT:
                    if sub_idx + 1 < SUBLEVELS_PER_AREA:
                        goto(area_id, sub_idx + 1)
                elif ev.button in PAD_PREV:
                    if sub_idx > 0:
                        goto(area_id, sub_idx - 1)
                elif ev.button in PAD_QUIT:
                    running = False
            elif ev.type == pygame.JOYHATMOTION and mode == 'map':
                hx, hy = ev.value
                if hx > 0:
                    if sub_idx + 1 < SUBLEVELS_PER_AREA:
                        goto(area_id, sub_idx + 1)
                elif hx < 0:
                    if sub_idx > 0:
                        goto(area_id, sub_idx - 1)
                elif hy > 0:
                    unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                    i = unl.index(area_id) if area_id in unl else 0
                    if i > 0: goto(unl[i-1], 0)
                elif hy < 0:
                    unl = [a['id'] for a in AREAS if a['id'] in state['unlocked']]
                    i = unl.index(area_id) if area_id in unl else 0
                    if i + 1 < len(unl): goto(unl[i+1], 0)

        keys = pygame.key.get_pressed()
        jump_held = (keys[pygame.K_SPACE] or keys[pygame.K_w]
                     or keys[pygame.K_UP] or pad.jump_held())

        # --- update --------------------------------------------------------
        if mode == 'play':
            if hit_pause > 0:
                hit_pause -= 1
            else:
                player.update(level, keys, particles, cam, pad,
                              jump_held=jump_held)
                # slash hits
                if player.active_slash:
                    sl = player.active_slash
                    sr = sl.rect()
                    # hits enemies
                    for en in enemies:
                        if not en.alive: continue
                        if id(en) in sl.hit_targets: continue
                        if sr.colliderect(en.rect()):
                            killed = en.take_hit(sl.damage,
                                player.facing if sl.direction in ('left','right') else 0,
                                particles, cam)
                            sl.hit_targets.add(id(en))
                            hit_pause = HIT_PAUSE_FRAMES
                            if killed:
                                player.mites += en.mites_drop
                            if sl.direction == 'down' and not sl.pogo_used:
                                player.pogo(); sl.pogo_used = True
                    # hits boss
                    if boss and boss.state != 'dead' and id(boss) not in sl.hit_targets:
                        if sr.colliderect(boss.rect()):
                            hit = boss.take_hit(sl.damage, particles, cam)
                            if hit:
                                sl.hit_targets.add(id(boss))
                                hit_pause = HIT_PAUSE_FRAMES
                                if boss.state == 'vulnerable':
                                    slowmo = SLOWMO_FRAMES
                                if sl.direction == 'down' and not sl.pogo_used:
                                    player.pogo(); sl.pogo_used = True
                    # hits saws? saws aren't destructible; just bounce pogo
                    for sw in saws:
                        if sr.colliderect(sw.rect()):
                            if sl.direction == 'down' and not sl.pogo_used:
                                player.pogo(); sl.pogo_used = True
                            sl.hit_targets.add(id(sw))
                for en in enemies:
                    en.update(level, projectiles, player)
                for sw in saws:
                    sw.update()
                # projectile update
                for p in projectiles[:]:
                    p['x'] += p['vx']; p['y'] += p['vy']
                    p['life'] -= 1
                    if p['life'] <= 0:
                        projectiles.remove(p); continue
                    pr = pygame.Rect(int(p['x']-6), int(p['y']-6), 12, 12)
                    for s in level.solids:
                        if pr.colliderect(s):
                            projectiles.remove(p); break
                    else:
                        if player.alive and player.iframes == 0:
                            if pr.colliderect(player.rect()):
                                projectiles.remove(p)
                                player.take_damage(particles, cam)
                                continue
                # contact damage
                if player.alive and player.iframes == 0:
                    pr = player.rect()
                    for en in enemies:
                        if not en.alive: continue
                        if pr.colliderect(en.rect()):
                            player.take_damage(particles, cam); break
                    else:
                        for sw in saws:
                            if pr.colliderect(sw.rect()):
                                player.take_damage(particles, cam); break
                        else:
                            if boss and boss.state != 'dead':
                                if pr.colliderect(boss.rect()):
                                    player.take_damage(particles, cam)
                # door / completion
                if player.alive and level.door:
                    # require boss dead if boss level
                    can_exit = True
                    if boss and boss.state != 'dead':
                        can_exit = False
                    if can_exit and level.door.colliderect(player.rect()):
                        comp = state['completed'].setdefault(area_id, [])
                        if sub_idx not in comp:
                            comp.append(sub_idx)
                        state['mites'] += player.mites
                        player.mites = 0
                        unlocked = unlock_next_if_needed(state, area_id, sub_idx)
                        if sub_idx + 1 < SUBLEVELS_PER_AREA:
                            sub_idx += 1
                        elif unlocked:
                            area_id = unlocked['id']; sub_idx = 0
                        save_state(state)
                        goto(area_id, sub_idx)
                # dying state
                if not player.alive and player.dead_t > 90:
                    state['mites'] = max(0, state['mites'] // 2)
                    player.mites = 0
                    save_state(state)
                    reload_current()
            # always update particles, even during hit-pause
            particles.update()
            # ambient spawn — at fewer rate during slowmo to keep readable
            density = 0.5 if slowmo > 0 else 1.0
            spawn_ambient(particles, area_id, t,
                          cam.x, cam.y, density)
            if slowmo > 0: slowmo -= 1
            # follow camera
            if player.alive:
                cam.follow(player.x, player.y)
        elif mode == 'shop':
            if shop_msg_t > 0: shop_msg_t -= 1

        # --- render --------------------------------------------------------
        lights.clear()
        bg.draw(SCREEN, cam.x, cam.y, t)
        camx, camy = cam.offset()

        # tiles
        for rect, seed in level.tiles:
            r = rect.move(-camx, -camy)
            if r.right < -32 or r.left > WIDTH + 32: continue
            if r.bottom < -32 or r.top > HEIGHT + 32: continue
            draw_platform(SCREEN, r, level.pal, seed)
        # spikes
        for sp, direction in level.spikes:
            r = sp.move(-camx, -camy)
            if r.right < -32 or r.left > WIDTH + 32: continue
            if r.bottom < -32 or r.top > HEIGHT + 32: continue
            draw_spike(SCREEN, r, direction)
        # door
        if level.door:
            r = level.door.move(-camx, -camy)
            draw_door(SCREEN, r, level.pal, t, light=(lights, None))
        # orbs (mites)
        for orb in level.orbs:
            if orb[2]:
                draw_mite(SCREEN, orb[0] - camx, orb[1] - camy, t, level.pal,
                          light=(lights, None))
        # NPC
        if level.npc_pos:
            draw_npc(SCREEN, level.npc_pos[0] - camx,
                     level.npc_pos[1] - camy, t,
                     accent=level.pal['accent'],
                     light=(lights, level.pal['light']))
        # shopkeeper
        if level.shop_pos:
            draw_shopkeeper(SCREEN, level.shop_pos[0] - camx,
                            level.shop_pos[1] - camy, t,
                            accent=(255, 210, 140),
                            light=(lights, None))
        # saws
        for sw in saws:
            sw.draw(SCREEN, camx, camy, particles, lights)
        # enemies
        for en in enemies:
            en.draw(SCREEN, camx, camy, lights)
        # boss
        if boss:
            boss.draw(SCREEN, camx, camy, lights)
        # projectiles
        for p in projectiles:
            draw_projectile(SCREEN, p['x'] - camx, p['y'] - camy,
                            p['color'])
            lights.add(int(p['x'] - camx), int(p['y'] - camy), 30,
                       p['color'], intensity=0.7)
        # player
        player.draw(SCREEN, camx, camy, lights, level.pal)
        # slash effect on top
        if player.active_slash:
            sl = player.active_slash
            draw_slash(SCREEN, player.x - camx,
                       player.y - player.h // 2 - camy,
                       sl.direction, sl.t, NAIL_ACTIVE_FRAMES,
                       (220, 240, 255), sl.reach)
        # particles
        particles.draw(SCREEN, camx, camy)
        # lights pass (additive)
        lights.blit(SCREEN)
        # foreground decoration
        if area_id == 'deepnest':
            draw_eye_blink_fg(SCREEN, t, camx, camy)
        # vignette + damage flash
        draw_vignette(SCREEN, intensity=0.7)
        if not player.alive:
            draw_damage_pulse(SCREEN, min(1.0, player.dead_t / 30))
        else:
            draw_damage_pulse(SCREEN, player.damage_flash / 24
                              if player.damage_flash > 0 else 0)
        # boss intro banner
        if boss and boss.intro_t < 90 and mode == 'play':
            draw_boss_intro(SCREEN, Boss.NAME_TABLE.get(boss.kind, "BOSS"),
                            boss.intro_t, level.pal)
        # HUD
        if mode == 'play':
            npc_msg = None
            if level.npc_pos and npc_dialog_t > 0:
                npc_msg = (cur_area()['npc'], cur_area()['npc_line'])
                npc_dialog_t -= 1
            shop_prompt = False
            if level.shop_pos and player.alive:
                d2 = ((player.x - level.shop_pos[0])**2
                      + (player.y - level.shop_pos[1])**2)
                if d2 < 70*70:
                    shop_prompt = True
            draw_hud(SCREEN, t, state, player, cur_area(), sub_idx,
                     npc_msg=npc_msg, shop_prompt=shop_prompt, boss=boss)
            # death overlay
            if not player.alive:
                msg = BIG.render("YOU DIED", True, (220, 60, 80))
                SCREEN.blit(msg, (WIDTH//2 - msg.get_width()//2,
                                  HEIGHT//2 - 40))
                sub = FONT.render("respawning... (half mites lost)",
                                  True, (200, 200, 220))
                SCREEN.blit(sub, (WIDTH//2 - sub.get_width()//2,
                                  HEIGHT//2 + 20))
        elif mode == 'shop':
            draw_shop(SCREEN, t, state, shop_cursor, shop_msg, shop_msg_t)
        elif mode == 'map':
            draw_map(SCREEN, t, state, area_id, sub_idx)

        # music: advance state + draw "now playing" toast
        music.tick()
        music.draw_overlay(SCREEN)

        pygame.display.flip()
        CLOCK.tick(FPS)
        t += 1

    # save on quit
    state['mites'] += player.mites if player.alive else 0
    state['last_area'] = area_id
    state['last_sub'] = sub_idx
    save_state(state)
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit(); sys.exit(0)
