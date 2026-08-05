# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

햄버거로 여닫는 왼쪽 서랍. 탭 바를 대신해 페이지를 고른다.
사이저에 담지 않고 페이지 위에 띄워 두었다가 왼쪽에서 밀어 넣는다.

열려 있는 동안 마우스를 잡아 둔다. 바깥을 누르면 닫히고, 그 누름은
아래로 넘기지 않는다. 햄버거를 다시 누르는 것도 바깥 누름이라 그대로 닫힌다.
'''


import wx

from icons import draw_glyph
from utilities import Canvas
from utilities import get_font
from utilities import mix


class SideMenu(Canvas):

    WIDTH = 240
    ITEM_HEIGHT = 40
    MARGIN = 6
    RADIUS = 5
    ICON_SIZE = 17
    LABEL_LEFT = 48

    # 밀려 들어오는 속도. 남은 거리의 일정 비율씩 좁혀 끝에서 부드럽게 선다.
    STEP = 12
    EASING = 0.34

    def __init__(self, parent, theme, items, on_select, bottom=1):
        super().__init__(parent, theme)
        self.items = items
        self.on_select = on_select
        self.bottom = bottom
        self.selected = 0
        self.hovered = -1
        self.opened = False
        self.shift = float(self.WIDTH)
        self.top = 0

        self.timer = wx.Timer(self)
        self.Hide()
        self.Bind(wx.EVT_TIMER, self.on_slide)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_capture_lost)

    def place(self, top, height):
        self.top = top
        self.SetSize(-round(self.shift), top, self.WIDTH, height)

    def is_open(self):
        return self.opened

    def toggle(self):
        self.close() if self.opened else self.open()

    def open(self):
        if self.opened:
            return
        self.opened = True
        self.Show()
        self.Raise()
        if not self.HasCapture():
            self.CaptureMouse()
        self.timer.Start(self.STEP)

    def close(self):
        if not self.opened:
            return
        self.opened = False
        self.hovered = -1
        if self.HasCapture():
            self.ReleaseMouse()
        self.timer.Start(self.STEP)

    def set_selection(self, index):
        if index != self.selected:
            self.selected = index
            self.Refresh()

    def on_slide(self, event):
        target = 0.0 if self.opened else float(self.WIDTH)
        self.shift += (target - self.shift) * self.EASING
        if abs(target - self.shift) < 1:
            self.shift = target
            self.timer.Stop()
            if not self.opened:
                self.Hide()
        self.SetPosition(wx.Point(-round(self.shift), self.top))

    def contains(self, position):
        width, height = self.GetClientSize()
        return 0 <= position.x < width and 0 <= position.y < height

    def get_item_rect(self, index):
        width, height = self.GetClientSize()
        if index >= len(self.items) - self.bottom:
            top = height - self.MARGIN - (len(self.items) - index) * self.ITEM_HEIGHT
        else:
            top = self.MARGIN + index * self.ITEM_HEIGHT
        return wx.Rect(self.MARGIN, top, width - self.MARGIN * 2, self.ITEM_HEIGHT)

    def hit_test(self, position):
        if not self.contains(position):
            return -1
        for index in range(len(self.items)):
            if self.get_item_rect(index).Contains(position):
                return index
        return -1

    def on_down(self, event):
        if not self.contains(event.GetPosition()):
            self.close()

    def on_up(self, event):
        index = self.hit_test(event.GetPosition())
        if index < 0:
            return
        self.set_selection(index)
        self.close()
        self.on_select(index)

    def on_motion(self, event):
        index = self.hit_test(event.GetPosition())
        if index != self.hovered:
            self.hovered = index
            self.Refresh()

    def on_leave(self, event):
        if self.hovered != -1:
            self.hovered = -1
            self.Refresh()

    def on_capture_lost(self, event):
        # 이미 놓친 캡처를 다시 놓으면 assertion 이 뜬다. 상태만 되돌린다.
        if self.opened:
            self.opened = False
            self.hovered = -1
            self.timer.Start(self.STEP)

    def draw(self, gc, width, height):
        theme = self.theme
        # 페이지와 같은 바탕이라 오른쪽 테두리 한 줄이 서랍의 경계를 알리는 전부다.
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['bg'])))
        gc.DrawRectangle(0, 0, width, height)
        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
        gc.StrokeLine(width - 0.5, 0, width - 0.5, height)

        for index, (label, glyph) in enumerate(self.items):
            self.draw_item(gc, index, label, glyph)

    def draw_item(self, gc, index, label, glyph):
        theme = self.theme
        rect = self.get_item_rect(index)
        active = index == self.selected

        if active:
            fill = theme['control']
        elif index == self.hovered:
            fill = mix(theme['bg'], theme['control'], 0.55)
        else:
            fill = None

        if fill:
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(fill)))
            gc.DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height, self.RADIUS)

        if active:
            # 고른 줄을 알리는 왼쪽 짧은 막대. Windows 11 탐색 창과 같은 표시다.
            bar = rect.height * 0.40
            gc.SetBrush(wx.Brush(wx.Colour(theme['accent'])))
            gc.DrawRoundedRectangle(rect.x + 2, rect.y + (rect.height - bar) / 2,
                                    3, bar, 1.5)

        colour = theme['text'] if active or index == self.hovered else theme['dim']
        draw_glyph(gc, glyph, rect.x + 26, rect.y + rect.height / 2,
                   self.ICON_SIZE, colour)

        gc.SetFont(get_font(10, bold=active), wx.Colour(colour))
        text_height = gc.GetTextExtent(label)[1]
        gc.DrawText(label, rect.x + self.LABEL_LEFT,
                    rect.y + (rect.height - text_height) / 2)
