# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import math
import wx

from utilities import ROUND_SIZE
from utilities import Canvas
from utilities import shade


class Pressable(Canvas):

    def __init__(self, parent, theme, on_click):
        super().__init__(parent, theme)
        self.on_click = on_click
        self.hovered = False
        self.pressed = False
        self.holding = False
        self.up_position = wx.Point(-1, -1)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_MOTION, self.on_track)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_lost)

    def get_hit(self):
        return None

    def hits(self, position):
        rect = self.get_hit()
        return rect is None or rect.Contains(position)

    def set_hovered(self, hovered):
        if hovered != self.hovered:
            self.hovered = hovered
            self.update_cursor()
            self.Refresh()

    def update_cursor(self):
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND if self.hovered else wx.CURSOR_ARROW))

    def on_track(self, event):
        inside = self.hits(event.GetPosition())
        self.set_hovered(inside)
        if self.holding and inside != self.pressed:
            self.pressed = inside
            self.Refresh()
        event.Skip()

    def on_down(self, event):
        if not self.hits(event.GetPosition()):
            event.Skip()
            return
        self.holding = True
        self.pressed = True
        if not self.HasCapture():
            self.CaptureMouse()
        self.Refresh()

    def on_dclick(self, event):
        self.on_down(event)

    def on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        # keep the event position, re-reading the cursor can disagree with the event
        self.up_position = event.GetPosition()
        clicked = self.holding and self.hits(self.up_position)
        self.holding = False
        self.pressed = False
        self.Refresh()
        if clicked and self.on_click:
            self.on_click()

    def on_lost(self, event):
        self.holding = False
        self.pressed = False
        self.Refresh()

    def on_enter(self, event):
        self.set_hovered(self.hits(event.GetPosition()))

    def on_leave(self, event):
        if self.holding:
            if self.pressed:
                self.pressed = False
                self.Refresh()
            self.set_hovered(False)
            return
        self.set_hovered(False)


class RoundButton(Pressable):

    TONES = {
        'plain': ('control', 'text'),
        'primary': ('accent', '#ffffff'),
        'ghost': (None, 'dim'),
    }

    CORNER = 9
    icon_shift = 0

    def __init__(self, parent, theme, icon, on_click, tone='plain', size=ROUND_SIZE,
                 square=False, backdrop=None):
        super().__init__(parent, theme, on_click)
        self.icon = icon
        self.tone = tone
        self.square = square
        # a solid colour behind, draw_backdrop re-enters the parent's drawing state
        self.backdrop = backdrop
        self.SetMinSize(wx.Size(size, size))

    def set_backdrop(self, colour):
        self.backdrop = colour
        self.Refresh()

    def set_icon(self, icon):
        if icon != self.icon:
            self.icon = icon
            self.Refresh()

    def set_tone(self, tone):
        if tone != self.tone:
            self.tone = tone
            self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        radius = min(width, height) / 2 - 1
        cx, cy = width / 2, height / 2

        key, mark = self.TONES[self.tone]
        # fill outside the rounded shape too, else a dark square shows behind it
        if self.backdrop is not None:
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(self.backdrop)))
            gc.DrawRectangle(0, 0, width, height)
        else:
            self.draw_backdrop(gc)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(self.get_fill(key)))
        if self.square:
            gc.DrawRoundedRectangle(cx - radius, cy - radius,
                                    radius * 2, radius * 2, self.CORNER)
        else:
            gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        self.draw_icon(gc, cx, cy + self.icon_shift, radius, wx.Colour(theme.get(mark, mark)))

    def get_fill(self, key):
        if key is None:
            grey = wx.Colour(self.theme['tick'])
            alpha = 96 if self.pressed else 64 if self.hovered else 0
            return wx.Colour(grey.Red(), grey.Green(), grey.Blue(), alpha)

        fill = self.theme[key]
        if self.pressed:
            fill = shade(fill, 0.85)
        elif self.hovered:
            fill = shade(fill, 1.16)
        return wx.Colour(fill)

    def draw_icon(self, gc, cx, cy, radius, colour):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(colour))

        if self.icon == 'play':
            path = gc.CreatePath()
            # shifted right, a triangle's weight reads left of centre
            path.MoveToPoint(cx - radius * 0.19, cy - radius * 0.40)
            path.AddLineToPoint(cx + radius * 0.44, cy)
            path.AddLineToPoint(cx - radius * 0.19, cy + radius * 0.40)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'pause':
            for sign in (-1, 1):
                gc.DrawRectangle(cx + sign * radius * 0.24 - radius * 0.08,
                                 cy - radius * 0.38, radius * 0.16, radius * 0.76)

        elif self.icon == 'flag':
            gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.11))))
            gc.StrokeLine(cx - radius * 0.28, cy - radius * 0.44,
                          cx - radius * 0.28, cy + radius * 0.46)
            gc.SetPen(wx.TRANSPARENT_PEN)
            path = gc.CreatePath()
            path.MoveToPoint(cx - radius * 0.28, cy - radius * 0.40)
            path.AddLineToPoint(cx + radius * 0.40, cy - radius * 0.14)
            path.AddLineToPoint(cx - radius * 0.28, cy + radius * 0.12)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon in ('plus', 'minus'):
            arm = radius * 0.44
            gc.SetPen(wx.Pen(colour, max(1, round(radius * 0.13))))
            gc.StrokeLine(cx - arm, cy, cx + arm, cy)
            if self.icon == 'plus':
                gc.StrokeLine(cx, cy - arm, cx, cy + arm)
            gc.SetPen(wx.TRANSPARENT_PEN)

        elif self.icon == 'pencil':
            # measured: its ink a pixel right of and half a pixel under the plus's
            cx -= 1
            cy -= 0.5
            length = radius * 0.60
            half = radius * 0.15
            neck = radius * 0.26
            dx, dy = math.cos(math.radians(-45)), math.sin(math.radians(-45))
            px, py = -dy, dx
            tip = (cx - dx * length, cy - dy * length)
            end = (cx + dx * length, cy + dy * length)

            path = gc.CreatePath()
            path.MoveToPoint(tip[0], tip[1])
            path.AddLineToPoint(tip[0] + dx * neck + px * half,
                                tip[1] + dy * neck + py * half)
            path.AddLineToPoint(end[0] + px * half, end[1] + py * half)
            path.AddLineToPoint(end[0] - px * half, end[1] - py * half)
            path.AddLineToPoint(tip[0] + dx * neck - px * half,
                                tip[1] + dy * neck - py * half)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'back':
            gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.12))))
            gc.StrokeLine(cx - radius * 0.36, cy, cx + radius * 0.38, cy)
            gc.SetPen(wx.TRANSPARENT_PEN)
            path = gc.CreatePath()
            path.MoveToPoint(cx - radius * 0.44, cy)
            path.AddLineToPoint(cx - radius * 0.06, cy - radius * 0.28)
            path.AddLineToPoint(cx - radius * 0.06, cy + radius * 0.28)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'reset':
            self.draw_reset(gc, cx, cy, radius, colour)

    def draw_reset(self, gc, cx, cy, radius, colour):
        ring = radius * 0.40
        path = gc.CreatePath()
        path.AddArc(cx, cy, ring, math.radians(300), math.radians(240), True)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.12))))
        gc.StrokePath(path)

        angle = math.radians(300)
        x, y = cx + ring * math.cos(angle), cy + ring * math.sin(angle)
        dx, dy = math.sin(angle), -math.cos(angle)
        size = radius * 0.24
        path = gc.CreatePath()
        path.MoveToPoint(x + dx * size, y + dy * size)
        path.AddLineToPoint(x - dy * size * 0.8, y + dx * size * 0.8)
        path.AddLineToPoint(x + dy * size * 0.8, y - dx * size * 0.8)
        path.CloseSubpath()
        gc.SetBrush(wx.Brush(colour))
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.FillPath(path)
