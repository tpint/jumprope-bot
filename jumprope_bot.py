"""Jump-rope auto-jumper.

Watches the yellow-haired boy; when the "!" bubble pops above his head,
waits DELAY seconds and presses F.

  python jumprope_bot.py                 run live (starts PAUSED)
  python jumprope_bot.py --video x.mp4   dry-run the detector on a recording

Live hotkeys:  F8 = start/pause   F6 / F7 = delay -/+ 10 ms   F10 = quit
"""
import argparse
import ctypes
import os
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = cv2.cvtColor(cv2.imread(os.path.join(HERE, "bubble.png")), cv2.COLOR_BGR2GRAY)

DELAY = 0.15          # seconds between "!" detected and pressing F
MATCH_THRESH = 0.65   # template score that counts as "bubble visible" (floor scores ~0.45)
LOCK_THRESH = 0.85    # score needed to lock in the on-screen scale
COOLDOWN = 0.45       # ignore new bubbles this long after a press
SCALES = np.arange(0.5, 2.01, 0.05)  # 1.0 = game view about 1278x918
REACQUIRE_EVERY = 30  # frames between whole-screen checks for the boy


# ---------------------------------------------------------------- detection

def find_boy(bgr, min_area):
    """Centre-x and top-y of the largest yellow-hair blob, or None."""
    a = bgr.astype(np.int16)
    b, g, r = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 170) & (g > 130) & (b < 110) & (r - b > 90) & (g - b > 50)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = st[k]
    return (x + w // 2, y) if area >= min_area else None


def match(gray, tmpl):
    if gray.shape[0] < tmpl.shape[0] or gray.shape[1] < tmpl.shape[1]:
        return 0.0, (0, 0)
    _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED))
    return score, (loc[0] + tmpl.shape[1] // 2, loc[1] + tmpl.shape[0] // 2)


class Detector:
    """Tracks the boy by his hair and scores the "!" bubble above him.

    If no scale is given, every scale is tried until the first clear
    bubble over the boy, then that scale is locked in.
    """
    def __init__(self, scale=None):
        self.boy = None  # (x, top of hair)
        self.cand, self.gone = None, 0  # best (score, scale) seen before locking
        self.frames, self.votes, self.pending = 0, 0, None
        self.set_scale(scale)

    def set_scale(self, scale):
        self.scale = scale
        if scale:
            self.tmpl = cv2.resize(TEMPLATE, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            print(f"scale locked at {scale:.2f}")

    def reacquire(self, bgr):
        """Lanterns are yellow too. Every so often check the whole screen and
        move to the biggest hair blob if it wins 3 checks in a row."""
        self.frames += 1
        if self.boy is not None and self.frames % REACQUIRE_EVERY:
            return
        top = find_boy(bgr, 80)
        if top is None or self.boy is None:
            self.boy = self.boy or top
            return
        near = lambda p, q: abs(p[0] - q[0]) < 40 and abs(p[1] - q[1]) < 80
        if near(top, self.boy):
            self.votes = 0
            return
        self.votes = self.votes + 1 if self.pending and near(top, self.pending) else 1
        self.pending = top
        if self.votes >= 3:
            self.boy, self.votes = top, 0

    def bubble_score(self, bgr):
        s = self.scale or 1.0
        H, W = bgr.shape[:2]
        min_area = int(150 * s * s) if self.scale else 80
        self.reacquire(bgr)
        if self.boy is None:
            return 0.0
        bx, by = self.boy
        r = int(90 * s) if self.scale else 160
        x0, y0 = max(0, bx - r), max(0, by - r)
        found = find_boy(bgr[y0:by + r, x0:bx + r], min_area)
        if found is None:
            self.boy = None
            return 0.0
        # follow sideways drift; ignore the up/down bob of jumping
        fx, fy = x0 + found[0], y0 + found[1]
        self.boy = (fx, by if abs(fy - by) < 60 * s else fy)
        bx, by = self.boy

        if self.scale:
            x0, x1 = max(0, bx - int(55 * s)), min(W, bx + int(55 * s))
            y0, y1 = max(0, by - int(100 * s)), min(H, by + int(70 * s))
            return match(cv2.cvtColor(bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), self.tmpl)[0]

        # not calibrated: search a wide box at every scale
        x0, x1 = max(0, bx - 110), min(W, bx + 110)
        y0, y1 = max(0, by - 180), min(H, by + 100)
        roi = cv2.cvtColor(bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        best = (0.0, None)
        for sc in SCALES:
            t = cv2.resize(TEMPLATE, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            score, (cx, _) = match(roi, t)
            if score > best[0] and abs(x0 + cx - bx) < 40 * sc:  # must be over HIS head
                best = (score, sc)
        # the bubble grows as it pops in, so once it is gone for a few
        # frames, lock the scale of its fullest frame
        if best[0] >= LOCK_THRESH:
            self.cand, self.gone = max(self.cand or best, best), 0
            return best[0]
        if self.cand:
            self.gone += 1
            if self.gone >= 5:
                self.set_scale(self.cand[1])
        return 0.0  # multi-scale search scores the floor higher; don't trust weak hits


class Trigger:
    """Rising edge of the bubble -> one press, `delay` later."""
    def __init__(self):
        self.visible = False
        self.press_at = None
        self.last_press = -1e9

    def update(self, now, score, delay):
        seen = score >= MATCH_THRESH
        if seen and not self.visible and self.press_at is None and now - self.last_press > COOLDOWN:
            self.press_at = now + delay
        self.visible = seen
        if self.press_at is not None and now >= self.press_at:
            self.press_at = None
            self.last_press = now
            return True
        return False


# ---------------------------------------------------------------- key input

SC_F = 0x21
KEYEVENTF_SCANCODE, KEYEVENTF_KEYUP = 0x0008, 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def _send(scan, flags):
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | flags, 0, None)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def press_f():
    _send(SC_F, 0)
    time.sleep(0.04)  # hold long enough for the game's input poll
    _send(SC_F, KEYEVENTF_KEYUP)


_keys = {}


def key_hit(vk):
    down = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    hit = down and not _keys.get(vk)
    _keys[vk] = down
    return hit


VK_F6, VK_F7, VK_F8, VK_F10 = 0x75, 0x76, 0x77, 0x79


# ---------------------------------------------------------------- modes

def run_live(args):
    # DXGI capture: GDI-based grabbers (mss, PIL) see fullscreen games as black
    import dxcam
    delay = args.delay
    det, trig, active = Detector(args.scale), Trigger(), False
    cam = dxcam.create(output_idx=args.monitor, output_color="BGR")
    print(f"watching monitor {args.monitor}, delay={delay*1000:.0f}ms")
    print("F8 = start/pause   F6/F7 = delay -/+10ms   F10 = quit   (PAUSED)")
    frame, score, next_status = None, 0.0, 0.0
    while True:
        if key_hit(VK_F10):
            break
        if key_hit(VK_F8):
            active = not active
            trig = Trigger()
            print("\nRUNNING" if active else "\nPAUSED")
        if key_hit(VK_F6):
            delay = max(0.0, delay - 0.01)
            print(f"\ndelay={delay*1000:.0f}ms")
        if key_hit(VK_F7):
            delay += 0.01
            print(f"\ndelay={delay*1000:.0f}ms")
        if not active:
            time.sleep(0.02)
            continue
        new = cam.grab()  # None when the screen hasn't changed
        now = time.perf_counter()
        if new is not None:
            frame = new
            score = det.bubble_score(frame)
        if frame is None:
            continue
        if trig.update(now, score, delay):
            press_f()
            print(f"\nJUMP  (boy at {det.boy})")
        if now >= next_status:
            next_status = now + 0.25
            boy = "boy NOT found" if det.boy is None else f"boy at {tuple(map(int, det.boy))}"
            sc = f"scale {det.scale:.2f}" if det.scale else "calibrating (do 1st jump yourself)"
            print(f"\r{boy}  '!' score {score:.2f}  {sc}      ", end="", flush=True)


def run_video(args):
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    det, trig, n = Detector(args.scale), Trigger(), 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        score = det.bubble_score(frame)
        if args.verbose:
            print(n, f"{score:.2f}", det.boy)
        if trig.update(n / fps, score, args.delay):
            print(f"PRESS F at frame {n} ({n/fps:.2f}s)")
        n += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=DELAY, help="seconds after '!' to press F")
    ap.add_argument("--scale", type=float, help="skip auto-scale (1.0 = 1278x918 game view)")
    ap.add_argument("--monitor", type=int, default=0, help="monitor to watch (0 = primary)")
    ap.add_argument("--video", help="test the detector on a recording instead of the screen")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    run_video(a) if a.video else run_live(a)
