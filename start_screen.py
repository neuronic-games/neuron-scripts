# start_screen.py
# Neuronic 2025
#
# The animated start screen guard.py shows on every display while the app
# starts or restarts: a night sky of softly coloured, twinkling stars,
# with a shooting star now and then. Pure Tk canvas drawing - no extra
# packages.
#
# Kept as light as possible: 10 frames a second, the stars never move
# (only their colour changes, in a few steps, so most frames recolour just
# a handful of them), nothing is created or deleted after the first frame,
# and guard.py only animates it while the app isn't showing.
#
# Preview it on any PC:   py -3 start_screen.py          (window, Esc to close)
# Render a GIF (needs Pillow):  py -3 start_screen.py --gif preview.gif

import math
import random

FPS = 10
STAR_COLORS = [(255, 244, 200), (255, 200, 225), (190, 225, 255), (255, 255, 255)]
STAR_COUNT = 80
TWINKLE_LEVELS = 5                 # brightness steps per star
SHOOTING_EVERY = 7.0               # seconds between shooting stars
SHOOTING_FOR = 0.9                 # seconds each one takes to cross


def _hex(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(c))) for c in rgb)


def _rgb(hexstr):
    h = hexstr.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


class Scene:
    """Works out what to draw at time t (seconds) for a w x h display.
    shapes(t) returns simple drawing commands - always the same number, in
    the same order, so canvas items can be reused - which Tk (on the
    exhibit) or Pillow (for a GIF preview) draws:
        ('poly', [x, y, x, y, ...], fill)
        ('line', x0, y0, x1, y1, fill, width)
        ('text', x, y, text, pixel_size, color)
    """

    def __init__(self, w, h, bg_rgb, message='', message_color='#ffffff'):
        self.w, self.h = w, h
        self.bg = bg_rgb
        self.message = message
        self.message_color = message_color
        s = min(w, h)
        self.unit = s
        rnd = random.Random(7)                       # same sky every time
        self.stars = []
        for _ in range(STAR_COUNT):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            size = s * (0.022 if rnd.random() < 0.15 else rnd.uniform(0.006, 0.013))
            color = rnd.choice(STAR_COLORS)
            # Precompute every brightness step, so frames only pick one.
            shades = [_hex(_mix(bg_rgb, color, 0.15 + 0.85 * k / (TWINKLE_LEVELS - 1)))
                      for k in range(TWINKLE_LEVELS)]
            self.stars.append((self._sparkle(x, y, size), shades,
                               rnd.uniform(0.4, 1.2), rnd.uniform(0, 6.3)))
        self.rnd = random.Random(11)
        self.shooting_index = -1
        self.shooting = None

    @staticmethod
    def _sparkle(x, y, size):
        pts = []
        for k in range(8):                           # 4-pointed sparkle
            ang = math.pi / 4 * k - math.pi / 2
            rad = size * (1.0 if k % 2 == 0 else 0.32)
            pts += [x + rad * math.cos(ang), y + rad * math.sin(ang)]
        return pts

    def _shooting_star(self, t):
        """Line coords for the shooting star, or None when there isn't one."""
        n, into = divmod(t, SHOOTING_EVERY)
        if into > SHOOTING_FOR:
            return None
        if n != self.shooting_index:                 # pick a new path
            self.shooting_index = n
            r = self.rnd
            x0, y0 = r.uniform(0.1, 0.7) * self.w, r.uniform(0.05, 0.4) * self.h
            length = self.unit * r.uniform(0.35, 0.55)
            ang = math.radians(r.uniform(20, 40))
            self.shooting = (x0, y0, length * math.cos(ang), length * math.sin(ang))
        x0, y0, dx, dy = self.shooting
        p = into / SHOOTING_FOR                      # 0 -> 1 across the sky
        head = min(1.0, p * 1.3)
        tail = max(0.0, p * 1.3 - 0.35)
        return (x0 + dx * tail, y0 + dy * tail, x0 + dx * head, y0 + dy * head)

    def shapes(self, t):
        out = []
        for pts, shades, speed, phase in self.stars:
            twinkle = 0.5 + 0.5 * math.sin(t * speed * 2 + phase)
            out.append(('poly', pts, shades[round(twinkle * (TWINKLE_LEVELS - 1))]))

        line = self._shooting_star(t)
        if line:
            out.append(('line', *line, '#fffbe8', max(2, self.unit * 0.004)))
        else:
            out.append(('line', -10, -10, -10, -10, '#fffbe8', 1))   # parked off-screen

        if self.message:
            out.append(('text', self.w / 2, self.h / 2, self.message,
                        max(18, int(self.h / 18)), self.message_color))
        return out


class TkStartScreen:
    """Draws a Scene onto a Tk canvas. Call draw(t) for each frame. The
    canvas items are created on the first frame; after that an item is
    only touched when its colour or position actually changes."""

    def __init__(self, canvas, w, h, bg, message='', message_color='white'):
        self.canvas = canvas
        bg_rgb = tuple(c // 257 for c in canvas.winfo_rgb(bg))
        self.scene = Scene(w, h, bg_rgb, message, message_color)
        self.items = []     # [item id, last fill, last coords]

    def _create(self, s):
        c, kind = self.canvas, s[0]
        if kind == 'poly':
            return [c.create_polygon(*s[1], fill=s[2], outline=''), s[2], None]
        if kind == 'line':
            return [c.create_line(*s[1:5], fill=s[5], width=s[6], capstyle='round'),
                    s[5], tuple(s[1:5])]
        return [c.create_text(s[1], s[2], text=s[3], fill=s[5],
                              font=('Segoe UI', -s[4], 'bold')), s[5], None]

    def draw(self, t):
        shapes = self.scene.shapes(t)
        if len(shapes) != len(self.items):           # first frame
            self.canvas.delete('all')
            self.items = [self._create(s) for s in shapes]
            return
        c = self.canvas
        for entry, s in zip(self.items, shapes):
            if s[0] == 'poly':                       # stars: colour only
                if s[2] != entry[1]:
                    c.itemconfigure(entry[0], fill=s[2])
                    entry[1] = s[2]
            elif s[0] == 'line':                     # shooting star: position only
                coords = tuple(s[1:5])
                if coords != entry[2]:
                    c.coords(entry[0], *coords)
                    c.itemconfigure(entry[0], width=s[6])
                    entry[2] = coords


def render_gif(path, w=960, h=540, seconds=8.0, bg='#403a7a', message=''):
    """Preview the animation as a GIF (needs Pillow)."""
    from PIL import Image, ImageDraw, ImageFont
    bg_rgb = _rgb(bg)
    scene = Scene(w, h, bg_rgb, message)
    frames = []
    for f in range(int(seconds * FPS)):
        img = Image.new('RGB', (w, h), bg_rgb)
        d = ImageDraw.Draw(img)
        for s in scene.shapes(f / FPS):
            if s[0] == 'poly':
                d.polygon(list(zip(s[1][::2], s[1][1::2])), fill=s[2])
            elif s[0] == 'line':
                d.line(s[1:5], fill=s[5], width=int(s[6]))
            elif s[0] == 'text':
                try:
                    font = ImageFont.load_default(size=s[4])
                except TypeError:
                    font = ImageFont.load_default()
                d.text((s[1], s[2]), s[3], fill=s[5], font=font, anchor='mm')
        frames.append(img)
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0)


if __name__ == '__main__':
    import sys
    if '--gif' in sys.argv:
        out = sys.argv[sys.argv.index('--gif') + 1]
        render_gif(out)
        print(f'Wrote {out}')
    else:
        import time
        import tkinter as tk
        root = tk.Tk()
        root.title('Start screen preview (Esc to close)')
        W, H = 960, 540
        canvas = tk.Canvas(root, width=W, height=H, bg='#403a7a', highlightthickness=0)
        canvas.pack()
        screen = TkStartScreen(canvas, W, H, '#403a7a')
        t0 = time.monotonic()

        def tick():
            screen.draw(time.monotonic() - t0)
            root.after(int(1000 / FPS), tick)

        root.bind('<Escape>', lambda e: root.destroy())
        tick()
        root.mainloop()
