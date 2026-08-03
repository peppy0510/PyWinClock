# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

네이티브 wx.Button / wx.CheckBox 는 Windows 에서 배경색을 따르지 않아
다크 테마에서 혼자 밝게 남는다. 캔버스로 직접 그려 대체한다.
'''


import wx

from utilities import BUTTON_SIZE
from utilities import Canvas
from utilities import get_font
from utilities import shade


class FlatButton(Canvas):
    '''kind 로 위계를 준다. primary/danger 는 채운 버튼, ghost 는 테두리만.'''

    RADIUS = 6

    # kind: (채움 색 키, 글자 색 키). 채움 키가 없으면 평소에는 비워 둔다.
    PALETTE = {
        'default': ('control', 'text'),
        'primary': ('accent', None),
        'danger': ('second', None),
        'ghost': (None, 'dim'),
    }

    def __init__(self, parent, theme, label, on_click, size=BUTTON_SIZE, kind='default'):
        super().__init__(parent, theme)
        self.label = label
        self.on_click = on_click
        self.kind = kind
        self.hovered = False
        self.pressed = False
        self.SetMinSize(wx.Size(size[0], size[1]))
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)

    def SetLabel(self, label):
        self.label = label
        self.Refresh()

    def set_kind(self, kind):
        if kind != self.kind:
            self.kind = kind
            self.Refresh()

    def on_down(self, event):
        self.pressed = True
        self.Refresh()

    def on_up(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self.Refresh()
        if was_pressed and self.hovered:
            self.on_click()

    def on_enter(self, event):
        self.hovered = True
        self.Refresh()

    def on_leave(self, event):
        self.hovered = False
        self.pressed = False
        self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        fill_key, text_key = self.PALETTE[self.kind]
        base = theme[fill_key] if fill_key else theme['control']
        filled = fill_key is not None

        if self.pressed:
            fill, filled = shade(base, 0.84), True
        elif self.hovered:
            fill, filled = shade(base, 1.22), True
        else:
            fill = base

        if filled:
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(fill)))
            gc.DrawRoundedRectangle(0, 0, width, height, self.RADIUS)
        else:
            gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawRoundedRectangle(0.5, 0.5, width - 1, height - 1, self.RADIUS)

        if text_key is None:
            colour = '#ffffff'
        elif self.hovered or self.pressed:
            colour = theme['text']
        else:
            colour = theme[text_key]

        gc.SetFont(get_font(9, bold=self.kind in ('primary', 'danger')), wx.Colour(colour))
        tw, th = gc.GetTextExtent(self.label)[:2]
        gc.DrawText(self.label, (width - tw) / 2, (height - th) / 2)


class FlatCheckBox(Canvas):

    BOX = 15

    def __init__(self, parent, theme, label, on_toggle=None):
        super().__init__(parent, theme)
        self.label = label
        self.on_toggle = on_toggle
        self.value = False
        self.hovered = False
        self.Bind(wx.EVT_LEFT_UP, self.on_click)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.fit()

    def fit(self):
        dc = wx.ClientDC(self)
        dc.SetFont(get_font(9))
        tw, th = dc.GetTextExtent(self.label)
        self.SetMinSize(wx.Size(self.BOX + 8 + tw, max(self.BOX, th) + 6))

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = bool(value)
        self.Refresh()

    def on_click(self, event):
        self.value = not self.value
        self.Refresh()
        if self.on_toggle:
            self.on_toggle()

    def on_enter(self, event):
        self.hovered = True
        self.Refresh()

    def on_leave(self, event):
        self.hovered = False
        self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        top = (height - self.BOX) / 2

        if self.value:
            gc.SetPen(wx.Pen(wx.Colour(theme['accent']), 1))
            gc.SetBrush(wx.Brush(wx.Colour(theme['accent'])))
        else:
            border = shade(theme['rim'], 1.3) if self.hovered else theme['rim']
            gc.SetPen(wx.Pen(wx.Colour(border), 1))
            gc.SetBrush(wx.Brush(wx.Colour(theme['control'])))
        gc.DrawRoundedRectangle(0.5, top, self.BOX, self.BOX, 3)

        if self.value:
            path = gc.CreatePath()
            path.MoveToPoint(4, top + self.BOX * 0.52)
            path.AddLineToPoint(self.BOX * 0.44, top + self.BOX - 4.5)
            path.AddLineToPoint(self.BOX - 3, top + 4)
            gc.SetPen(wx.Pen(wx.Colour('#ffffff'), 2))
            gc.StrokePath(path)

        colour = theme['text'] if self.hovered else theme['dim']
        gc.SetFont(get_font(9), wx.Colour(colour))
        tw, th = gc.GetTextExtent(self.label)[:2]
        gc.DrawText(self.label, self.BOX + 8, (height - th) / 2)


class SettingsButton(Canvas):
    '''탭 바 오른쪽 끝의 Settings 항목. 창에 마우스가 올라와 있을 때만 그린다.'''

    HEIGHT = 38
    LABEL = 'Settings'

    def __init__(self, parent, theme, on_click):
        super().__init__(parent, theme)
        self.on_click = on_click
        self.visible = False
        self.active = False
        self.hovered = False
        self.SetMinSize(wx.Size(96, self.HEIGHT))
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)

    def set_width(self, width):
        # 탭과 같은 폭으로 맞춘다. 남은 폭을 탭들이 균등 분할하므로
        # 헤더 항목 전체가 같은 넓이가 된다.
        if self.GetMinSize()[0] != width:
            self.SetMinSize(wx.Size(width, self.HEIGHT))
            return True
        return False

    def set_visible(self, visible):
        if visible != self.visible:
            self.visible = visible
            self.Refresh()

    def set_active(self, active):
        if active != self.active:
            self.active = active
            self.Refresh()

    def on_up(self, event):
        if self.visible:
            self.on_click()

    def on_enter(self, event):
        self.hovered = True
        self.Refresh()

    def on_leave(self, event):
        self.hovered = False
        self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        if not self.visible:
            return

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
        gc.StrokeLine(0, height - 1, width, height - 1)

        if self.active:
            fill = theme['face']
        elif self.hovered:
            fill = theme['control']
        else:
            fill = None

        if fill:
            gc.SetPen(wx.Pen(wx.Colour(fill), 1))
            gc.SetBrush(wx.Brush(wx.Colour(fill)))
            gc.DrawRectangle(0, 0, width, height - 1)

        colour = theme['text'] if self.active or self.hovered else theme['dim']
        gc.SetFont(get_font(10, bold=self.active), wx.Colour(colour))
        tw, th = gc.GetTextExtent(self.LABEL)[:2]
        gc.DrawText(self.LABEL, (width - tw) / 2, (height - th) / 2 - 1)
