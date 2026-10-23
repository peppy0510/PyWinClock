# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import ctypes
import os
import psutil
import sys

from pathlib import Path


SW_SHOW = 5
SW_RESTORE = 9


def has_process_authority(p):
    try:
        p.cwd()
        p.name()
    except Exception:
        return False
    return True


def get_current_process():
    pid = int(os.getpid())
    for p in psutil.process_iter():
        if p.pid == pid and has_process_authority(p):
            return p


def get_source_path():
    return str(Path(__file__).resolve().parent)


def has_running_instance():
    pid = int(os.getpid())
    source = get_source_path()
    # a venv launches through Scripts\python.exe, which shares our name and cwd
    ancestors = {p.pid for p in psutil.Process(pid).parents()}

    for p in psutil.process_iter():
        if p.pid == pid or p.pid in ancestors or not has_process_authority(p):
            continue

        if hasattr(sys, '_MEIPASS'):
            cp = get_current_process()
            if cp is not None and cp.name() == p.name():
                return True
            continue

        if p.name().lower() not in ('python.exe', 'pythonw.exe',):
            continue

        try:
            cmdline = p.cmdline()
        except Exception:
            continue

        if [True for v in cmdline if v.startswith(source)]:
            return True

    return False


def show_running_window(title):
    # the running copy may sit hidden in the tray; bring it back instead of doing nothing
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW('wxWindowNR', title)
    if not hwnd:
        return
    user32.ShowWindow(hwnd, SW_RESTORE if user32.IsIconic(hwnd) else SW_SHOW)
    user32.SetForegroundWindow(hwnd)
