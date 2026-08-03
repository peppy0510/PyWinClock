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

# Stopwatch / Countdown 이 같은 크기를 쓰도록 여기서만 정의한다.
CONTROL_HEIGHT = 28
BUTTON_SIZE = (88, CONTROL_HEIGHT)
PRESET_SIZE = (58, CONTROL_HEIGHT)
CONTROL_GAP = 4

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


def format_hms(seconds):
    total = int(seconds)
    return '%02d:%02d:%02d' % (total // 3600, total % 3600 // 60, total % 60)


def format_hundredths(seconds):
    return '%02d' % (int(seconds * 100) % 100)


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


class TimerCanvas(Canvas):
    '''Stopwatch 와 Countdown 이 같은 폰트·배치로 시간을 그리도록 공유하는 베이스.'''

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.seconds = 0.0

    def get_time_colour(self):
        return self.theme['text']

    def get_time_size(self, width, height):
        return max(14, min(int(width / 9), int(height / 3.2)))

    def draw(self, gc, width, height):
        self.draw_time(gc, width, height)

    def draw_time(self, gc, width, height):
        size = self.get_time_size(width, height)
        top = height / 2 - size * 0.78
        used = self.draw_centered_text(gc, format_hms(self.seconds), width / 2, top,
                                       get_font(size, bold=True), self.get_time_colour())

        # 큰 숫자의 디센더 여백만큼 끌어올려 두 줄 사이 간격을 좁힌다.
        sub_top = top + used - size * 0.24
        sub_used = self.draw_centered_text(
            gc, format_hundredths(self.seconds), width / 2, sub_top,
            get_font(max(9, int(size * 0.38))), self.theme['dim'])
        return sub_top + sub_used
