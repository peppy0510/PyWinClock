# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import ctypes
import json
import os
import wx


APP_NAME = 'PyWinClock'

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19

THEMES = {
    'dark': {
        'bg': '#1b1d21',
        'face': '#25282d',
        'rim': '#3a3f46',
        'tick': '#6b727c',
        'tick_major': '#c8cdd4',
        'numeral': '#e6e9ed',
        'hand': '#e6e9ed',
        'second': '#e5484d',
        'text': '#e6e9ed',
        'dim': '#8b929b',
        'accent': '#4c9aff',
        'control': '#2f333a',
        'titlebar_dark': True,
    },
    'light': {
        'bg': '#f4f5f7',
        'face': '#ffffff',
        'rim': '#d5d9df',
        'tick': '#9aa1aa',
        'tick_major': '#3d434b',
        'numeral': '#1d2126',
        'hand': '#1d2126',
        'second': '#d93036',
        'text': '#1d2126',
        'dim': '#6b727c',
        'accent': '#2b6cb0',
        'control': '#e8eaee',
        'titlebar_dark': False,
    },
}


def apply_titlebar_theme(window, dark):
    """Win11 DWM 다크 타이틀바. 이미 보이는 창은 프레임을 다시 계산시켜야 반영된다."""
    try:
        handle = window.GetHandle()
        value = ctypes.c_int(1 if dark else 0)
        for attribute in (DWMWA_USE_IMMERSIVE_DARK_MODE,
                          DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        return

    if window.IsShown():
        width, height = window.GetSize()
        window.SetSize(width, height + 1)
        window.SetSize(width, height)


def get_settings_path():
    return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                        APP_NAME, 'settings.json')


def load_settings():
    try:
        with open(get_settings_path(), encoding='utf-8') as file:
            return json.load(file)
    except Exception:
        return {}


def save_settings(settings):
    try:
        path = get_settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(settings, file, ensure_ascii=False, indent=2)
    except Exception:
        pass


def shade(colour, factor):
    base = wx.Colour(colour)
    return wx.Colour(min(255, int(base.Red() * factor)),
                     min(255, int(base.Green() * factor)),
                     min(255, int(base.Blue() * factor)))


def get_font(size, bold=False):
    weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                   weight, faceName='Segoe UI')


class Canvas(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent, style=wx.FULL_REPAINT_ON_RESIZE)
        self.theme = theme
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetDoubleBuffered(True)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda event: None)

    def set_theme(self, theme):
        self.theme = theme
        self.Refresh()

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(self.theme['bg'])))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if gc is None:
            return
        gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
        width, height = self.GetClientSize()
        self.draw(gc, width, height)

    def draw(self, gc, width, height):
        pass

    def draw_centered_text(self, gc, text, cx, y, font, colour):
        gc.SetFont(font, wx.Colour(colour))
        tw, th = gc.GetTextExtent(text)[:2]
        gc.DrawText(text, cx - tw / 2, y)
        return th
