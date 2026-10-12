# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import ctypes
import json
import math
import os
import winreg
import wx

from ctypes import wintypes


APP_NAME = 'PyWinClock'

# Stopwatch / Countdown 이 같은 크기를 쓰도록 여기서만 정의한다.
CONTROL_HEIGHT = 28
ROUND_SIZE = 46
CARD_HEIGHT = 54
CARD_RADIUS = 6
CONTROL_GAP = 4

# 시계 문자판과 카운트다운 고리가 자랄 수 있는 한계. 더 큰 창에서는 남는 자리를
# 그림에 주지 않고 바깥 여백으로 돌려, 덩어리가 통째로 가운데에 선다.
MAX_DIAL = 280
# 시간 글자가 커지는 한계. 카운트다운은 크기를 고리에서 뽑아 MAX_DIAL 에서 저절로
# 멈추므로, 스톱워치가 그와 나란히 서도록 그때의 값을 여기 적어 둔다.
MAX_TIME_SIZE = 27

# 직접 그리는 타이틀바의 높이. 캡션 버튼은 Windows 와 같은 46x32 로 둔다.
TITLEBAR_HEIGHT = 32
CAPTION_WIDTH = 46

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_CLIPSIBLINGS = 0x04000000

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35


THEMES = {
    'dark': {
        # 바탕은 형제 앱(PyWinAudio·PyWinAgent)과 같은 숯색.
        'bg': '#141517',
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
        # 일이 잘 안 됐음을 알리는 설명 글씨 (Start menu).
        'warn': '#ff9a3d',
        # 지도는 낮의 바다·육지를 깔고 그 위에 밤(map_night)을 map_night_alpha 만큼 덮는다.
        # 밤이 바다와 육지를 함께 덮어야 낮/밤 경계가 띠가 아니라 한 면으로 읽힌다.
        'map_sea': '#272a30',
        'map_land': '#4f555e',
        'map_night': '#0e0f12',
        'map_night_alpha': 0.62,
        'pin': '#f2f4f7',
        # 핀 둘레. 바다에서도 육지에서도 점이 떨어져 보이게 바탕과 반대 밝기로.
        'pin_edge': '#0e0f12',
        'close': '#c42b1c',
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
        'warn': '#b7791f',
        'map_sea': '#e6eaef',
        'map_land': '#b9c0c9',
        'map_night': '#5b6470',
        'map_night_alpha': 0.40,
        'pin': '#1d2126',
        'pin_edge': '#ffffff',
        'close': '#c42b1c',
        'titlebar_dark': False,
    },
}


class WindowRect(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


def get_colour_ref(colour):
    """DWM 은 COLORREF, 곧 0x00BBGGRR 을 받는다."""
    value = wx.Colour(colour)
    return (value.Blue() << 16) | (value.Green() << 8) | value.Red()


def apply_titlebar_theme(window, theme):
    """Win11 DWM 창틀. 이미 보이는 창은 프레임을 다시 계산시켜야 반영된다.

    캡션을 떼어낸 창에도 위쪽에는 크기 조절용 띠가 7px 남고 그 자리를 DWM 이
    캡션 색으로 칠한다. 배경색을 그대로 넣어야 우리가 그리는 헤더와 이어져 보인다."""
    try:
        handle = wintypes.HWND(window.GetHandle())
        value = ctypes.c_int(1 if theme['titlebar_dark'] else 0)
        for attribute in (DWMWA_USE_IMMERSIVE_DARK_MODE,
                          DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(value), ctypes.sizeof(value))

        value = ctypes.c_int(get_colour_ref(theme['bg']))
        for attribute in (DWMWA_CAPTION_COLOR, DWMWA_BORDER_COLOR):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        return

    if window.IsShown():
        width, height = window.GetSize()
        window.SetSize(width, height + 1)
        window.SetSize(width, height)


def apply_no_caption(window):
    """wxCAPTION 을 뺀 스타일로 만들어도 wxWidgets 3.3 부터는 WS_CAPTION 이 그대로
    붙는다(3.2 까지는 빠졌다). 시스템 캡션이 우리가 그리는 헤더 위에 한 줄 더 얹히고,
    두꺼워진 띠를 헤더가 제 높이로 착각해 글리프가 위로 잘린다. 떼고 나면 남는 것은
    위쪽 7px 짜리 크기 조절 띠뿐이다."""
    try:
        handle = wintypes.HWND(window.GetHandle())
        style = ctypes.windll.user32.GetWindowLongW(handle, GWL_STYLE)
        ctypes.windll.user32.SetWindowLongW(handle, GWL_STYLE, style & ~WS_CAPTION)
        ctypes.windll.user32.SetWindowPos(handle, 0, 0, 0, 0, 0,
                                          SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER |
                                          SWP_NOACTIVATE | SWP_FRAMECHANGED)
    except Exception:
        pass


def apply_clip_siblings(window):
    """wx 는 자식 창에 WS_CLIPSIBLINGS 를 주지 않는다. 그대로 두면 아래에 깔린
    형제가 다시 칠할 때마다 그 위에 띄운 창을 덮어 지운다. 이 스타일은 자손이
    그릴 때까지 함께 따라가므로 덮는 쪽의 뿌리 한 곳에만 주면 된다."""
    try:
        handle = wintypes.HWND(window.GetHandle())
        style = ctypes.windll.user32.GetWindowLongW(handle, GWL_STYLE)
        ctypes.windll.user32.SetWindowLongW(handle, GWL_STYLE, style | WS_CLIPSIBLINGS)
    except Exception:
        pass


def get_frame_margins(window):
    """창 사각형과 실제로 보이는 사각형의 차. 캡션을 뗀 창에도 좌·우·아래에는
    보이지 않는 크기 조절 여백이 남아, 최대화 자리를 잡을 때 그만큼 넓혀야
    보이는 가장자리가 작업 영역과 맞는다."""
    rect = WindowRect()
    try:
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(
                wintypes.HWND(window.GetHandle()), DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
            return (0, 0, 0, 0)
    except Exception:
        return (0, 0, 0, 0)

    outer = window.GetScreenRect()
    return (rect.left - outer.x, rect.top - outer.y,
            outer.x + outer.width - rect.right, outer.y + outer.height - rect.bottom)


def is_windows_dark():
    '''Windows 앱 테마. 못 읽으면 어둡다고 본다 (이 앱의 기본값).'''
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
        value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        winreg.CloseKey(key)
        return value == 0
    except OSError:
        return True


def get_asset_path(*parts):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'assets', *parts)


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
    return '.%02d' % (int(seconds * 100) % 100)


def format_timer(seconds):
    return format_hms(seconds) + format_hundredths(seconds)


def mix(colour, other, ratio):
    '''두 테마색 사이를 오간다. 밝기를 곱하는 shade 와 달리 어느 테마에서나
    같은 방향으로 움직여, 흰 바탕에서도 눈에 남는다.'''
    first, second = wx.Colour(colour), wx.Colour(other)
    return wx.Colour(*[round(a + (b - a) * ratio) for a, b in
                       ((first.Red(), second.Red()),
                        (first.Green(), second.Green()),
                        (first.Blue(), second.Blue()))])


def shade(colour, factor):
    base = wx.Colour(colour)
    return wx.Colour(min(255, int(base.Red() * factor)),
                     min(255, int(base.Green() * factor)),
                     min(255, int(base.Blue() * factor)))


def draw_card_rim(gc, colour, x, y, width, height, radius=CARD_RADIUS):
    '''카드 테두리. `gc` 의 펜으로 두르면 왼쪽과 위만 두 픽셀에 반씩 걸쳐
    오른쪽·아래보다 굵어 보인다. 바깥 모서리와 1px 안쪽 모서리 사이만 채워
    네 변을 같은 굵기로 세운다 — 겹치는 안쪽은 짝수라 비고 테두리만 남는다.'''
    path = gc.CreatePath()
    path.AddRoundedRectangle(x, y, width, height, radius)
    path.AddRoundedRectangle(x + 1, y + 1, width - 2, height - 2, max(0, radius - 1))
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(colour)))
    gc.FillPath(path, wx.ODDEVEN_RULE)


FONTS = {}


def get_font(size, bold=False):
    '''반 포인트 단위로 고른다. wxPython 4.3 의 wx.Font 생성자는 실수 크기를 거절해
    FontInfo 로 만든다.'''
    key = (size, bold)
    if key not in FONTS:
        info = wx.FontInfo(size).FaceName('Segoe UI')
        FONTS[key] = wx.Font(info.Bold() if bold else info)
    return FONTS[key]


INKS = {}
WIDTHS = {}


def get_luma(image, x, y):
    '''세 채널 평균. 글씨는 ClearType 이라 채널마다 1/3 칸씩 어긋나 한 채널만 보면 한쪽으로 쏠려 잰다.'''
    return (image.GetRed(x, y) + image.GetGreen(x, y) + image.GetBlue(x, y)) / 3.0


def get_ink(font):
    '''이 글꼴로 y=0 에 쓴 대문자 H 의 잉크 맨 윗줄과 맨 아랫줄(=기준선). 글자 상자는 위 여유와
    아래 내림 자리를 품어 상자로 가운데를 잡으면 글씨가 위아래로 치우친다. 잉크로 잡는다.'''
    key = font.GetNativeFontInfoDesc()
    if key not in INKS:
        bitmap = wx.Bitmap(80, 80, 24)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(font, wx.WHITE)
        gc.DrawText('H', 4, 0)
        del gc
        dc.SelectObject(wx.NullBitmap)
        image = bitmap.ConvertToImage()
        rows = [y for y in range(80) if any(get_luma(image, x, y) > 127 for x in range(80))]
        INKS[key] = (rows[0], rows[-1]) if rows else (0, 0)
    return INKS[key]


def get_text_width(font, text):
    '''그리는 것과 같은 GraphicsContext 로 잰 폭. DC 로 재면 1 px 어긋난다.'''
    key = (font.GetNativeFontInfoDesc(), text)
    if key not in WIDTHS:
        dc = wx.MemoryDC(wx.Bitmap(1, 1))
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(font, wx.BLACK)
        WIDTHS[key] = int(math.ceil(gc.GetTextExtent(text)[0]))
        del gc
        dc.SelectObject(wx.NullBitmap)
    return WIDTHS[key]


SPANS = {}


def get_ink_span(font, text, colour='#ffffff', back='#000000'):
    '''x=0 에 쓴 글씨의 잉크 왼쪽·오른쪽 끝. GDI+ 가 재 주는 글자 폭은 오른쪽에 여유를 더 얹어
    폭으로 가운데를 잡으면 글씨가 왼쪽으로 2~3 px 치우친다(실측). 가로 가운데는 잉크로 잡는다.
    ClearType 은 글씨·바탕 색에 따라 테두리가 달리 번져 실제 두 색으로 잰다.'''
    key = (font.GetNativeFontInfoDesc(), text, colour, back)
    if key not in SPANS:
        width = get_text_width(font, text) + 40
        fore, ground = wx.Colour(colour), wx.Colour(back)
        bitmap = wx.Bitmap(width, 60, 24)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.Brush(ground))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(font, fore)
        gc.DrawText(text, 20, 10)
        del gc
        dc.SelectObject(wx.NullBitmap)
        image = bitmap.ConvertToImage()
        base = (ground.Red() + ground.Green() + ground.Blue()) / 3.0
        limit = abs((fore.Red() + fore.Green() + fore.Blue()) / 3.0 - base) / 2.0
        columns = [x for x in range(width)
                   if any(abs(get_luma(image, x, y) - base) > limit for y in range(60))]
        SPANS[key] = (columns[0] - 20, columns[-1] - 20) if columns else (0, 0)
    return SPANS[key]


def get_text_top(font, top, height):
    '''top..top+height 칸의 세로 가운데에 대문자 잉크가 오게 하는 DrawText 의 y. 정수로 —
    반 칸에 걸리면 글씨가 번진다.'''
    ink_top, ink_bottom = get_ink(font)
    return int(round(top + (height - (ink_bottom - ink_top + 1)) / 2.0 - ink_top))


def draw_text_in(gc, text, rect, font, colour, align='center', back=None):
    '''rect 안에 글씨를 놓는다. 세로는 잉크 가운데, 가로는 가운데·왼쪽·오른쪽. back 은 글씨 뒤
    바탕색 (잉크를 그 색 위에서 잰다).'''
    gc.SetFont(font, wx.Colour(colour))
    width = get_text_width(font, text)
    if back is None:
        ink_left, ink_right = get_ink_span(font, text)
    else:
        ink_left, ink_right = get_ink_span(font, text, colour, back)
    if align == 'center':
        x = int(round(rect.x + (rect.width - (ink_right - ink_left + 1)) / 2.0 - ink_left))
    elif align == 'right':
        x = rect.x + rect.width - 1 - ink_right
    else:
        x = rect.x - ink_left
    gc.DrawText(text, x, get_text_top(font, rect.y, rect.height))
    return width


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

    def draw_backdrop(self, gc):
        '''반투명하게 비치거나 부모 그림 위에 떠 있으려면 뒤가 있어야 한다.
        자기 자리에 해당하는 부모 그림을 그대로 떠 온다. 부모는 자식 창을
        그리지 않으므로 되돌아오지 않는다.'''
        parent = self.GetParent()
        if not isinstance(parent, Canvas):
            return
        x, y = self.GetPosition()
        width, height = parent.GetClientSize()
        gc.PushState()
        gc.Translate(-x, -y)
        parent.draw(gc, width, height)
        gc.PopState()

    def fit_text(self, gc, text, limit):
        '''주어진 폭을 넘으면 말줄임으로 자른다. gc.Clip 은 쓰지 않는다. 배경을
        뜨느라 남의 그리기를 다시 부르는 자리가 있어, 그 안의 ResetClip 이
        바깥 클립까지 지워 버리기 때문이다.'''
        if gc.GetTextExtent(text)[0] <= limit:
            return text
        while text and gc.GetTextExtent(text + '…')[0] > limit:
            text = text[:-1]
        return text + '…'

    def draw_centered_text(self, gc, text, cx, y, font, colour):
        gc.SetFont(font, wx.Colour(colour))
        tw, th = gc.GetTextExtent(text)[:2]
        gc.DrawText(text, cx - tw / 2, y)
        return th


class TimerCanvas(Canvas):
    '''Stopwatch 와 Countdown 이 같은 폰트·배치로 시간을 그리도록 공유하는 베이스.
    00:00:00.00 을 한 줄로 그린다. 1/100 초도 크기와 색이 시·분·초와 같다.'''

    # 큰 숫자의 크기를 정하는 가로 폭 나눗수. 키우면 글자가 작아진다.
    WIDTH_DIVISOR = 13

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.seconds = 0.0

    def get_time_colour(self):
        return self.theme['text']

    def get_time_size(self, width, height):
        return max(14, min(int(width / self.WIDTH_DIVISOR), int(height / 2.9),
                           MAX_TIME_SIZE))

    def get_time_height(self, width, height):
        '''그려질 시간 글자의 높이. 캔버스를 글자에 맞춰 재울 때 쓴다.'''
        dc = wx.MemoryDC(wx.Bitmap(1, 1))
        dc.SetFont(get_font(self.get_time_size(width, height), bold=True))
        return dc.GetTextExtent(format_hms(0))[1]

    def draw(self, gc, width, height):
        self.draw_time(gc, width, height)

    def draw_time(self, gc, width, height, offset=0):
        '''시·분·초와 1/100 초는 글꼴도 색도 같다. 나눠 그릴 것 없이 한 줄이다.'''
        text = format_timer(self.seconds)
        gc.SetFont(get_font(self.get_time_size(width, height), bold=True),
                   wx.Colour(self.get_time_colour()))
        text_width, text_height = gc.GetTextExtent(text)[:2]

        # offset 은 시간 아래에 무언가를 더 쌓을 때 그만큼 위로 밀어, 쌓은
        # 덩어리 전체가 가운데에 오게 하려고 둔다.
        top = height / 2 - text_height / 2 + offset
        gc.DrawText(text, (width - text_width) / 2, top)
        return top + text_height
