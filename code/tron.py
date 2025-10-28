
---

### `tron_stylized.py` (complete — copy into a file)
```python
#!/usr/bin/env python3
"""
Tron Lightcycles — Terminal (Stylized)

- Option B: readable stylized version using double-block '██' for trails.
- Modes: Single-player (vs simple AI) or Two-player local (WASD vs Arrows).
- Controls: Player1 W/A/S/D, Player2 arrow keys. q to quit, r to restart.
- Windows: pip install windows-curses
"""

import curses
import time
import random
import sys

# ---- Config ----
START_TICK = 0.10     # initial frame interval (seconds)
SPEED_STEP = 0.005    # decrease tick each few seconds to speed up
SPEED_INCREASE_INTERVAL = 8.0  # seconds between speed increases
FIELD_H = 20          # default logical field (rows)
FIELD_W = 36          # default logical field (cols)
AI_RANDOMNESS = 0.12  # chance AI picks random valid move
BLOCK = "██"          # two-character block for nicer look
BORDER = True         # draw border
# -----------------

# Directions
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

KEYS_P1 = {ord('w'): UP, ord('W'): UP, ord('s'): DOWN, ord('S'): DOWN,
           ord('a'): LEFT, ord('A'): LEFT, ord('d'): RIGHT, ord('D'): RIGHT}
KEYS_P2 = {curses.KEY_UP: UP, curses.KEY_DOWN: DOWN, curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT}

def clamp_field(stdscr):
    maxy, maxx = stdscr.getmaxyx()
    # account for double width of BLOCK: each logical column uses 2 characters
    usable_h = maxy - 6
    usable_w = (maxx - 6) // 2
    h = min(FIELD_H, max(8, usable_h))
    w = min(FIELD_W, max(16, usable_w))
    return h, w

class Cycle:
    def __init__(self, y, x, direction, color_pair, name="Player"):
        self.y = y
        self.x = x
        self.dir = direction
        self.trail = set()
        self.alive = True
        self.color_pair = color_pair
        self.name = name
        # add initial head pos to trail so it shows immediate trail
        self.trail.add((y, x))

    def head(self):
        return (self.y, self.x)

    def next_pos(self):
        return (self.y + self.dir[0], self.x + self.dir[1])

    def move(self):
        self.y += self.dir[0]
        self.x += self.dir[1]
        self.trail.add((self.y, self.x))

def opposite(d1, d2):
    return d1[0] == -d2[0] and d1[1] == -d2[1]

def find_moves(cycle, h, w, occupied):
    moves = []
    for d in (UP, DOWN, LEFT, RIGHT):
        if opposite(d, cycle.dir):
            continue
        ny = cycle.y + d[0]
        nx = cycle.x + d[1]
        # out of bounds => invalid
        if ny < 0 or ny >= h or nx < 0 or nx >= w:
            continue
        if (ny, nx) in occupied:
            continue
        moves.append(d)
    return moves

def ai_choose(cycle, h, w, occupied):
    opts = find_moves(cycle, h, w, occupied)
    if not opts:
        return cycle.dir
    # small randomness
    if random.random() < AI_RANDOMNESS:
        return random.choice(opts)
    # prefer straight
    if cycle.dir in opts:
        return cycle.dir
    # otherwise choose option with max open cells ahead (small lookahead)
    best = None
    best_score = -1
    for opt in opts:
        score = lookahead(cycle.y + opt[0], cycle.x + opt[1], opt, h, w, occupied, depth=6)
        if score > best_score:
            best_score = score
            best = opt
    return best if best else random.choice(opts)

def lookahead(y, x, d, h, w, occupied, depth=6):
    score = 0
    cy, cx = y, x
    for _ in range(depth):
        if (cy, cx) in occupied:
            break
        score += 1
        cy += d[0]; cx += d[1]
        if cy < 0 or cy >= h or cx < 0 or cx >= w:
            break
    return score

def draw_border(win, top, left, h, w):
    # draw simple box using curses
    for col in range(left, left + w*2 + 2):
        win.addch(top, col, curses.ACS_HLINE)
        win.addch(top + h + 1, col, curses.ACS_HLINE)
    for row in range(top, top + h + 2):
        win.addch(row, left, curses.ACS_VLINE)
        win.addch(row, left + w*2 + 1, curses.ACS_VLINE)
    win.addch(top, left, curses.ACS_ULCORNER)
    win.addch(top, left + w*2 + 1, curses.ACS_URCORNER)
    win.addch(top + h + 1, left, curses.ACS_LLCORNER)
    win.addch(top + h + 1, left + w*2 + 1, curses.ACS_LRCORNER)

def center_text(win, y, text, attr=0):
    maxy, maxx = win.getmaxyx()
    x = max(0, (maxx - len(text)) // 2)
    win.addstr(y, x, text, attr)

def render_field(stdscr, top, left, h, w, occupied, p1, p2):
    # draw grid background
    for ry in range(h):
        for rx in range(w):
            screen_y = top + 1 + ry
            screen_x = left + 1 + rx*2
            stdscr.addstr(screen_y, screen_x, "  ")  # empty cell (two spaces)
    # draw trails
    for (ty, tx) in occupied:
        sy = top + 1 + ty
        sx = left + 1 + tx*2
        if 0 <= sy < stdscr.getmaxyx()[0] and 0 <= sx+1 < stdscr.getmaxyx()[1]:
            stdscr.addstr(sy, sx, BLOCK, curses.color_pair(3))
    # draw heads
    if p1.alive:
        stdscr.addstr(top + 1 + p1.y, left + 1 + p1.x*2, BLOCK, curses.color_pair(p1.color_pair) | curses.A_BOLD)
    if p2.alive:
        stdscr.addstr(top + 1 + p2.y, left + 1 + p2.x*2, BLOCK, curses.color_pair(p2.color_pair) | curses.A_BOLD)

def game_loop(stdscr, mode="2P"):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    stdscr.clear()
    h, w = clamp_field(stdscr)
    top = 3
    left = 3

    # init colors (if supported)
    curses.start_color()
    try:
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # p1
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # p2
        curses.init_pair(3, curses.COLOR_MAGENTA, -1) # trails/bg
    except:
        pass

    # init players
    p1 = Cycle(h//2, max(2, w//6), RIGHT, 1, "Player 1")
    p2 = Cycle(h//2, max(3, w - w//6), LEFT, 2, "Player 2" if mode=="2P" else "AI")
    occupied = set()
    occupied.update(p1.trail); occupied.update(p2.trail)

    tick = START_TICK
    last_speed_time = time.time()

    paused = False
    winner = None

    while True:
        stdscr.erase()
        maxy, maxx = stdscr.getmaxyx()

        center_text(stdscr, 0, "🔥 Tron Lightcycles — Stylized Terminal (q to quit)", curses.A_BOLD)
        stdscr.addstr(1, 2, f"Mode: {'2 Players' if mode=='2P' else 'Single Player (vs AI)'}  |  Speed: {tick:.3f}s")

        if BORDER:
            draw_border(stdscr, top - 1, left - 1, h, w)

        # render field and trails
        render_field(stdscr, top, left, h, w, occupied, p1, p2)
        stdscr.refresh()

        # input handling
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            break

        if key != -1:
            if key in KEYS_P1:
                nd = KEYS_P1[key]
                if not opposite(nd, p1.dir):
                    p1.dir = nd
            elif key in KEYS_P2 and mode == "2P":
                nd = KEYS_P2[key]
                if not opposite(nd, p2.dir):
                    p2.dir = nd
            elif key == ord('q') or key == ord('Q'):
                return None
            elif key == ord('p') or key == ord('P'):
                paused = not paused

        if paused:
            center_text(stdscr, top + h + 3, "-- PAUSED -- (press p to resume)", curses.A_BOLD)
            stdscr.refresh()
            time.sleep(0.12)
            continue

        # AI decision
        if mode != "2P":
            occ_snapshot = set(occupied)
            occ_snapshot.add((p1.y, p1.x))
            occ_snapshot.add((p2.y, p2.x))
            p2.dir = ai_choose(p2, h, w, occ_snapshot)

        # next positions
        np1 = (p1.y + p1.dir[0], p1.x + p1.dir[1])
        np2 = (p2.y + p2.dir[0], p2.x + p2.dir[1])

        crash1 = False; crash2 = False

        # wall collisions (no wrap)
        for idx, np in enumerate((np1, np2)):
            ny, nx = np
            if ny < 0 or ny >= h or nx < 0 or nx >= w:
                if idx == 0: crash1 = True
                else: crash2 = True

        # trail collisions
        if np1 in occupied:
            crash1 = True
        if np2 in occupied:
            crash2 = True

        # head-to-head (both move to same cell)
        if np1 == np2:
            crash1 = crash2 = True

        # apply moves
        if not crash1:
            p1.y, p1.x = np1
            occupied.add((p1.y, p1.x))
            p1.trail.add((p1.y, p1.x))
        else:
            p1.alive = False

        if not crash2:
            p2.y, p2.x = np2
            occupied.add((p2.y, p2.x))
            p2.trail.add((p2.y, p2.x))
        else:
            p2.alive = False

        # check winner
        if not p1.alive and not p2.alive:
            winner = None
        elif not p1.alive:
            winner = p2.name
        elif not p2.alive:
            winner = p1.name

        if winner is not None or (not p1.alive and not p2.alive):
            # final screen
            stdscr.erase()
            center_text(stdscr, 0, "🔥 Tron Lightcycles — Stylized Terminal", curses.A_BOLD)
            if BORDER:
                draw_border(stdscr, top - 1, left - 1, h, w)
            # draw final field
            render_field(stdscr, top, left, h, w, occupied, p1, p2)
            msg = "DRAW!" if winner is None else f"{winner} WINS!"
            center_text(stdscr, top + h + 2, msg, curses.A_BOLD)
            center_text(stdscr, top + h + 4, "Press 'r' to restart or 'q' to quit", curses.A_DIM)
            stdscr.refresh()
            # wait for choice
            while True:
                k = stdscr.getch()
                if k in (ord('q'), ord('Q')):
                    return None
                if k in (ord('r'), ord('R')):
                    return "RESTART"
                time.sleep(0.06)

        # speed up gradually
        if time.time() - last_speed_time > SPEED_INCREASE_INTERVAL:
            tick = max(0.03, tick - SPEED_STEP)
            last_speed_time = time.time()

        time.sleep(tick)

def main_menu(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    while True:
        stdscr.clear()
        center_text(stdscr, 2, "🔥 Tron Lightcycles — Stylized Terminal", curses.A_BOLD)
        center_text(stdscr, 4, "1) Single Player (vs AI)")
        center_text(stdscr, 5, "2) Two Players (WASD vs Arrows)")
        center_text(stdscr, 6, "q) Quit")
        center_text(stdscr, 8, "Choose: 1 or 2. During play: q to quit, p to pause.")
        stdscr.refresh()
        k = stdscr.getch()
        if k in (ord('1'), ord('2'), ord('q'), ord('Q')):
            if k == ord('1'):
                return "1P"
            if k == ord('2'):
                return "2P"
            return None

def launcher(stdscr):
    try:
        h_term, w_term = stdscr.getmaxyx()
        if h_term < 18 or w_term < 48:
            stdscr.clear()
            center_text(stdscr, 0, "Please enlarge your terminal window (min ~ 48x18).", curses.A_BOLD)
            stdscr.refresh()
            time.sleep(2.0)
            return
        while True:
            mode = main_menu(stdscr)
            if mode is None:
                break
            result = game_loop(stdscr, "2P" if mode=="2P" else "1P")
            if result is None:
                break
            # restart loop when "RESTART"
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0,0, f"Error: {e}\n")
        stdscr.refresh()
        time.sleep(2)

def run():
    try:
        curses.wrapper(launcher)
    except Exception as e:
        print("An error occurred:", e)
        print("On Windows: install windows-curses (pip install windows-curses)")
        sys.exit(1)

if __name__ == "__main__":
    run()
