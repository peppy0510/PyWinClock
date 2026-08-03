# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

네이티브 wx.Notebook 은 탭 헤더 배경색을 따르지 않는다.
다크 테마를 온전히 적용하려고 탭 바를 캔버스로 직접 그린다.
'''


import wx

from utilities import Canvas
from utilities import get_font


class TabBar(Canvas):

    HEIGHT = 38

    def __init__(self, parent, theme, labels, on_select):
        super().__init__(parent, theme)
        self.labels = labels
        self.on_select = on_select
        self.selected = 0
        self.hovered = -1
        self.SetMinSize(wx.Size(-1, self.HEIGHT))
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)

    def get_tab_width(self):
        return self.GetClientSize()[0] / max(1, len(self.labels))

    def hit_test(self, x):
        index = int(x // self.get_tab_width())
        return index if 0 <= index < len(self.labels) else -1

    def set_selection(self, index):
        if index != self.selected:
            self.selected = index
            self.Refresh()

    def on_click(self, event):
        index = self.hit_test(event.GetX())
        if index >= 0 and index != self.selected:
            self.selected = index
            self.Refresh()
            self.on_select(index)

    def on_motion(self, event):
        index = self.hit_test(event.GetX())
        if index != self.hovered:
            self.hovered = index
            self.Refresh()

    def on_leave(self, event):
        if self.hovered != -1:
            self.hovered = -1
            self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        tab_width = self.get_tab_width()

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
        gc.StrokeLine(0, height - 1, width, height - 1)

        for index, label in enumerate(self.labels):
            left = tab_width * index
            active = index == self.selected

            if active:
                gc.SetPen(wx.Pen(wx.Colour(theme['face']), 1))
                gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
                gc.DrawRectangle(left, 0, tab_width, height - 1)
            elif index == self.hovered:
                gc.SetPen(wx.Pen(wx.Colour(theme['control']), 1))
                gc.SetBrush(wx.Brush(wx.Colour(theme['control'])))
                gc.DrawRectangle(left, 0, tab_width, height - 1)

            font = get_font(10, bold=active)
            colour = theme['text'] if active or index == self.hovered else theme['dim']
            gc.SetFont(font, wx.Colour(colour))
            tw, th = gc.GetTextExtent(label)[:2]
            gc.DrawText(label, left + (tab_width - tw) / 2, (height - th) / 2 - 1)

            if active:
                gc.SetPen(wx.Pen(wx.Colour(theme['accent']), 3))
                gc.StrokeLine(left + 12, height - 2, left + tab_width - 12, height - 2)
