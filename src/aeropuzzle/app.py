import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import time
import random
import threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import pygame
except ImportError:
    pygame = None

try:
    import winsound
except ImportError:
    winsound = None

from aeropuzzle.hand_tracking import HandTracker
from aeropuzzle.maze import Puzzle


# ================= GORGEOUS HUD HELPERS =================
def draw_panel(img, x, y, w, h, bg_color=(15, 17, 26), opacity=0.75, border_color=(254, 242, 0), border_thickness=1):
    """Draws a glassy translucent panel with a colored border (color in BGR)."""
    h_img, w_img, _ = img.shape
    x = max(0, min(x, w_img))
    y = max(0, min(y, h_img))
    w = min(w, w_img - x)
    h = min(h, h_img - y)
    
    if w <= 0 or h <= 0:
        return
        
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
    cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
    if border_thickness > 0:
        cv2.rectangle(img, (x, y), (x + w, y + h), border_color, border_thickness)


def draw_premium_text(img, text, position, font_size=20, color=(255, 255, 255), bold=False):
    """Draws anti-aliased Segoe UI or Arial text onto the OpenCV image."""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    font = None
    font_names = ["segoeui.ttf", "segoeuib.ttf" if bold else "segoeui.ttf", "arial.ttf", "Arial.ttf"]
    for font_name in font_names:
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except IOError:
            continue
            
    if font is None:
        font = ImageFont.load_default()
        
    draw.text(position, text, font=font, fill=color)
    
    # Return BGR image
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def inside_box(px, py, x1, y1, x2, y2, w, h):
    fx = px * w
    fy = py * h
    return x1 <= fx <= x2 and y1 <= fy <= y2


def to_local(px, py, x1, y1, x2, y2, w, h):
    fx = px * w
    fy = py * h

    if fx < x1 or fx > x2 or fy < y1 or fy > y2:
        return None

    lx = (fx - x1) / (x2 - x1)
    ly = (fy - y1) / (y2 - y1)

    return lx, ly


def draw_grid(img, x1, y1, x2, y2, rows=3, cols=3):
    cell_w = (x2 - x1) // cols
    cell_h = (y2 - y1) // rows

    # Neon blue/cyan grids (254, 242, 0 is BGR for #00f2fe)
    for i in range(1, cols):
        cv2.line(img, (x1 + i*cell_w, y1), (x1 + i*cell_w, y2), (254, 242, 0), 2)

    for i in range(1, rows):
        cv2.line(img, (x1, y1 + i*cell_h), (x2, y1 + i*cell_h), (254, 242, 0), 2)


class SoundEffects:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.backend = None

        if pygame is None:
            self._setup_winsound_fallback()
            return

        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.sounds = {
                "shuffle": self._tone(330, 120, 0.25),
                "start": self._tone(523, 110, 0.30),
                "grab": self._tone(659, 70, 0.30),
                "drop": self._tone(392, 90, 0.28),
                "swap": self._tone(784, 120, 0.35),
                "solve": self._tone(988, 220, 0.40),
            }
            self.backend = "pygame"
            self.enabled = True
        except Exception:
            self._setup_winsound_fallback()

    def _setup_winsound_fallback(self):
        if winsound is not None:
            self.backend = "winsound"
            self.enabled = True
        else:
            self.enabled = False
            self.backend = None

    def _tone(self, frequency, duration_ms, volume):
        sample_rate = 22050
        sample_count = max(1, int(sample_rate * duration_ms / 1000.0))
        t = np.linspace(0, duration_ms / 1000.0, sample_count, endpoint=False)
        wave = np.sin(2.0 * np.pi * frequency * t)

        attack = max(1, int(sample_count * 0.08))
        release = max(1, int(sample_count * 0.18))
        envelope = np.ones(sample_count)
        envelope[:attack] = np.linspace(0.0, 1.0, attack, endpoint=False)
        envelope[-release:] = np.linspace(1.0, 0.0, release, endpoint=False)

        samples = np.int16(wave * envelope * volume * 32767)
        return pygame.sndarray.make_sound(samples)

    def _winsound_pattern(self, name):
        patterns = {
            "shuffle": [(330, 70), (440, 70)],
            "start": [(523, 120)],
            "grab": [(659, 60)],
            "drop": [(392, 80)],
            "swap": [(784, 90)],
            "solve": [(988, 120), (1318, 140)],
        }

        return patterns.get(name, [])

    def _play_winsound(self, name):
        if winsound is None:
            return

        def runner():
            for frequency, duration in self._winsound_pattern(name):
                try:
                    winsound.Beep(frequency, duration)
                except Exception:
                    break

        threading.Thread(target=runner, daemon=True).start()

    def play(self, name):
        if not self.enabled:
            return

        if self.backend == "pygame" and name in self.sounds:
            self.sounds[name].play()
        elif self.backend == "winsound":
            self._play_winsound(name)


# ================= MAIN ENTRY POINT =================
def main():
    # ================= CAMERA =================
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)

    cv2.namedWindow("Live Puzzle", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Live Puzzle", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    tracker = HandTracker()
    puzzle = Puzzle(3)
    sound = SoundEffects()

    mode = "camera"

    # selection box
    sel_x1 = sel_y1 = sel_x2 = sel_y2 = None

    # states
    start_time = None
    end_time = None
    solved = False

    prev_pinch = False
    dragging = False
    drag_src_idx = None   # index of the tile being dragged

    # cursor position (pixel coords)
    cursor_x, cursor_y = 0, 0
    cursor_alpha = 0.35   # smoothing for non-pinch pointer

    # shuffle
    shuffling = False
    shuffle_start = 0


    # ================= LOOP =================
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)

        tracker.find_hands(frame)
        tracker.draw_hands(frame)

        pinch, px, py = tracker.get_pinch()
        detected, ix, iy = tracker.get_index_pos()
        two_hands, p1, p2 = tracker.get_two_hand_indices()

        h, w, _ = frame.shape

        # ================= CAMERA MODE =================
        if mode == "camera":
            # Draw sleek white border and header
            border_margin = 20
            cv2.rectangle(frame, (border_margin, border_margin), (w - border_margin, h - border_margin), (255, 255, 255), 6)
            
            # Header Box Top Center
            title_w, title_h = 320, 60
            tx = w // 2 - title_w // 2
            ty = border_margin
            cv2.rectangle(frame, (tx, ty), (tx + title_w, ty + title_h), (255, 255, 255), -1)
            frame = draw_premium_text(frame, "AeroPuzzle", (tx + 65, ty + 8), font_size=32, color=(15, 17, 26), bold=True)
            
            status_text = "TWO HANDS NOT DETECTED"
            status_color = (127, 0, 255) # Pink/Red
            if two_hands:
                status_text = "PINCH TO SNAP & START"
                status_color = (160, 245, 0) # Neon Green

            # Draw status pill
            draw_panel(frame, w - 380, 32, 340, 45, bg_color=(30, 25, 20), opacity=0.8, border_color=status_color, border_thickness=1)
            frame = draw_premium_text(frame, status_text, (w - 360, 43), font_size=16, color=status_color, bold=True)

            if two_hands:
                x1 = int(p1[0] * w)
                y1 = int(p1[1] * h)

                x2 = int(p2[0] * w)
                y2 = int(p2[1] * h)

                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)

                color = (254, 242, 0) # Cyan
                if pinch:
                    color = (127, 0, 255) # Hot Pink

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

                if pinch and not prev_pinch:
                    if abs(x2 - x1) > 100 and abs(y2 - y1) > 100:
                        sel_x1, sel_y1, sel_x2, sel_y2 = x1, y1, x2, y2
                        crop = frame[sel_y1:sel_y2, sel_x1:sel_x2]

                        if crop.size != 0:
                            puzzle.create(crop)
                            shuffling = True
                            shuffle_start = time.time()
                            sound.play("shuffle")
                            mode = "puzzle"
                            start_time = None

            prev_pinch = pinch
            
            # Onboarding hint at the bottom
            draw_panel(frame, w // 2 - 250, h - 60, 500, 40, bg_color=(20, 16, 13), opacity=0.8, border_color=(255, 255, 255), border_thickness=1)
            frame = draw_premium_text(frame, "Use index fingers of both hands to frame your photo.", (w // 2 - 210, h - 50), font_size=14, color=(200, 200, 200))
            
            cv2.imshow("Live Puzzle", frame)

        # ================= PUZZLE MODE =================
        else:
            output = frame.copy()

            if sel_x1 is not None:
                puzzle_img = puzzle.combine()
                puzzle_img = cv2.resize(puzzle_img, (sel_x2 - sel_x1, sel_y2 - sel_y1))
                output[sel_y1:sel_y2, sel_x1:sel_x2] = puzzle_img
                draw_grid(output, sel_x1, sel_y1, sel_x2, sel_y2)

            # ===== CURSOR POSITION =====
            # During pinch: use the 1€-filtered pinch coords directly from tracker
            # Otherwise: smooth the index finger position for hover
            if pinch and detected:
                cursor_x = int(px * w)
                cursor_y = int(py * h)
            elif detected:
                raw_cx = int(ix * w)
                raw_cy = int(iy * h)
                cursor_x = int(cursor_alpha * raw_cx + (1 - cursor_alpha) * cursor_x)
                cursor_y = int(cursor_alpha * raw_cy + (1 - cursor_alpha) * cursor_y)

            # Clamp to puzzle area
            if sel_x1 is not None:
                cursor_x = max(sel_x1, min(cursor_x, sel_x2))
                cursor_y = max(sel_y1, min(cursor_y, sel_y2))

            cursor_nx = cursor_x / w
            cursor_ny = cursor_y / h

            # ===== SHUFFLE =====
            last_shuffle = 0
            if shuffling:
                if time.time() - shuffle_start < 1.8:
                    if time.time() - last_shuffle > 0.05:
                        i = random.randint(0, len(puzzle.tiles)-1)
                        j = random.randint(0, len(puzzle.tiles)-1)
                        puzzle.swap(i, j)
                        last_shuffle = time.time()
                else:
                    shuffling = False
                    start_time = time.time()
                    sound.play("start")

            # ===== INTERACTION =====
            if not shuffling and detected:
                # --- PINCH START: grab a tile ---
                if pinch and not prev_pinch:
                    if inside_box(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h):
                        local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                        if local is not None:
                            lx, ly = local
                            idx = puzzle.get_index(lx, ly)
                            if idx is not None:
                                drag_src_idx = idx
                                puzzle.selected = idx
                                dragging = True
                                sound.play("grab")

                # --- PINCH RELEASE: drop the tile ---
                elif not pinch and prev_pinch:
                    if dragging and drag_src_idx is not None:
                        local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                        if local is not None:
                            lx, ly = local
                            idx2 = puzzle.get_index(lx, ly)
                            if idx2 is not None:
                                puzzle.swap(drag_src_idx, idx2)
                                if idx2 == drag_src_idx:
                                    sound.play("drop")
                                else:
                                    sound.play("swap")
                            else:
                                sound.play("drop")
                        else:
                            sound.play("drop")

                        puzzle.selected = None
                        drag_src_idx = None
                        dragging = False

                        if not solved and puzzle.is_solved(puzzle.original_tiles):
                            solved = True
                            end_time = time.time()
                            sound.play("solve")

            prev_pinch = pinch

            # ===== DRAW DRAG VISUALS =====
            gs = puzzle.grid_size
            cell_w = (sel_x2 - sel_x1) // gs
            cell_h = (sel_y2 - sel_y1) // gs

            # Highlight the drop-target cell when dragging
            if dragging and detected and sel_x1 is not None:
                local = to_local(cursor_nx, cursor_ny, sel_x1, sel_y1, sel_x2, sel_y2, w, h)
                if local is not None:
                    lx, ly = local
                    hover_idx = puzzle.get_index(lx, ly)
                    if hover_idx is not None and hover_idx != drag_src_idx:
                        hr = hover_idx // gs
                        hc = hover_idx % gs
                        hx1 = sel_x1 + hc * cell_w
                        hy1 = sel_y1 + hr * cell_h
                        hx2 = hx1 + cell_w
                        hy2 = hy1 + cell_h
                        # Semi-transparent highlight on drop target
                        overlay = output.copy()
                        cv2.rectangle(overlay, (hx1, hy1), (hx2, hy2), (254, 242, 0), -1)
                        cv2.addWeighted(overlay, 0.25, output, 0.75, 0, output)
                        cv2.rectangle(output, (hx1, hy1), (hx2, hy2), (254, 242, 0), 2)

            # Highlight the selected (source) tile
            if drag_src_idx is not None:
                sr = drag_src_idx // gs
                sc = drag_src_idx % gs
                sx1 = sel_x1 + sc * cell_w
                sy1 = sel_y1 + sr * cell_h
                sx2 = sx1 + cell_w
                sy2 = sy1 + cell_h
                cv2.rectangle(output, (sx1, sy1), (sx2, sy2), (127, 0, 255), 3)

                # Ghost tile preview following cursor
                tile_img = puzzle.tiles[drag_src_idx]
                ghost_w = cell_w // 2
                ghost_h = cell_h // 2
                ghost = cv2.resize(tile_img, (ghost_w, ghost_h))

                # Position ghost centered on cursor
                gx1 = cursor_x - ghost_w // 2
                gy1 = cursor_y - ghost_h // 2
                gx2 = gx1 + ghost_w
                gy2 = gy1 + ghost_h

                # Clamp to frame bounds
                src_x1 = max(0, -gx1)
                src_y1 = max(0, -gy1)
                dst_x1 = max(0, gx1)
                dst_y1 = max(0, gy1)
                dst_x2 = min(w, gx2)
                dst_y2 = min(h, gy2)
                src_x2 = src_x1 + (dst_x2 - dst_x1)
                src_y2 = src_y1 + (dst_y2 - dst_y1)

                if dst_x2 > dst_x1 and dst_y2 > dst_y1:
                    ghost_region = ghost[src_y1:src_y2, src_x1:src_x2]
                    frame_region = output[dst_y1:dst_y2, dst_x1:dst_x2]
                    blended = cv2.addWeighted(ghost_region, 0.7, frame_region, 0.3, 0)
                    output[dst_y1:dst_y2, dst_x1:dst_x2] = blended

            # ===== CURSOR =====
            if detected:
                if dragging:
                    # Pinching cursor: filled white + magenta ring
                    cv2.circle(output, (cursor_x, cursor_y), 10, (127, 0, 255), -1)
                    cv2.circle(output, (cursor_x, cursor_y), 12, (255, 255, 255), 2)
                else:
                    # Hover cursor: white dot + cyan ring
                    cv2.circle(output, (cursor_x, cursor_y), 7, (255, 255, 255), -1)
                    cv2.circle(output, (cursor_x, cursor_y), 9, (254, 242, 0), 2)

            # Draw sleek white border and header
            border_margin = 20
            cv2.rectangle(output, (border_margin, border_margin), (w - border_margin, h - border_margin), (255, 255, 255), 6)
            
            # Header Box Top Center
            title_w, title_h = 320, 60
            tx = w // 2 - title_w // 2
            ty = border_margin
            cv2.rectangle(output, (tx, ty), (tx + title_w, ty + title_h), (255, 255, 255), -1)
            output = draw_premium_text(output, "AeroPuzzle", (tx + 65, ty + 8), font_size=32, color=(15, 17, 26), bold=True)

            if start_time and not solved:
                elapsed = time.time() - start_time
                output = draw_premium_text(output, f"TIME: {elapsed:.2f}s", (w - 200, 38), font_size=20, color=(160, 245, 0), bold=True)

                draw_panel(output, w // 2 - 200, h - 60, 400, 40, bg_color=(20, 16, 13), opacity=0.8, border_color=(255, 255, 255), border_thickness=1)
                output = draw_premium_text(output, "Pinch to grab a tile. Move & release to swap.", (w // 2 - 170, h - 50), font_size=14, color=(220, 220, 220))

            if solved:
                final_time = end_time - start_time

                v_w, v_h = 420, 220
                v_x = w // 2 - v_w // 2
                v_y = h // 2 - v_h // 2

                draw_panel(output, v_x, v_y, v_w, v_h, bg_color=(15, 24, 16), opacity=0.85, border_color=(160, 245, 0), border_thickness=2)

                output = draw_premium_text(output, "PUZZLE SOLVED!", (v_x + 95, v_y + 40), font_size=32, color=(160, 245, 0), bold=True)
                output = draw_premium_text(output, f"Final Time: {final_time:.2f} seconds", (v_x + 90, v_y + 110), font_size=20, color=(255, 255, 255))

                time_left = max(0.0, 5.0 - (time.time() - end_time))
                output = draw_premium_text(output, f"Auto-closing in {time_left:.1f}s...", (v_x + 120, v_y + 165), font_size=14, color=(160, 160, 160))

                if time.time() - end_time > 5.0:
                    break

            cv2.imshow("Live Puzzle", output)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
