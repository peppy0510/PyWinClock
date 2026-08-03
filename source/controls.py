# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

네이티브 wx.Button / wx.CheckBox 는 Windows 에서 배경색을 따르지 않아
다크 테마에서 혼자 밝게 남는다. 캔버스로 직접 그려 대체한다.
'''


import wx

from utilities import Canvas
from utilities import get_font
from utilities import shade


class FlatButton(Canvas):

    def __init__(self, parent, theme, label, on_click, size=(88, 28)):
        super().__init__(parent, theme)
        self.label = label
        self.on_click = on_click
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
        if self.pressed:
            fill = theme['accent']
        elif self.hovered:
            fill = shade(theme['control'], 1.25)
        else:
            fill = theme['control']

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
        gc.SetBrush(wx.Brush(wx.Colour(fill)))
        gc.DrawRoundedRectangle(0.5, 0.5, width - 1, height - 1, 4)

        colour = '#ffffff' if self.pressed else theme['text']
        gc.SetFont(get_font(9), wx.Colour(colour))
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
