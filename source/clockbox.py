# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import datetime
import math
import wx

from controls import FlatCheckBox
from utilities import Canvas
from utilities import get_font


WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')


class ClockCanvas(Canvas):

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 12
        if radius < 30:
            return

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
        gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        for index in range(60):
            major = index % 5 == 0
            angle = math.radians(index * 6)
            outer = radius * 0.94
            inner = radius * (0.84 if major else 0.90)
            colour = theme['tick_major'] if major else theme['tick']
            gc.SetPen(wx.Pen(wx.Colour(colour), 3 if major else 1))
            gc.StrokeLine(cx + outer * math.sin(angle), cy - outer * math.cos(angle),
                          cx + inner * math.sin(angle), cy - inner * math.cos(angle))

        gc.SetFont(get_font(max(8, int(radius * 0.15)), bold=True), wx.Colour(theme['numeral']))
        for hour in range(1, 13):
            angle = math.radians(hour * 30)
            label = str(hour)
            tw, th = gc.GetTextExtent(label)[:2]
            gc.DrawText(label,
                        cx + radius * 0.70 * math.sin(angle) - tw / 2,
                        cy - radius * 0.70 * math.cos(angle) - th / 2)

        now = datetime.datetime.now()
        seconds = now.second + now.microsecond / 1000000
        minutes = now.minute + seconds / 60
        hours = now.hour % 12 + minutes / 60

        self.draw_hand(gc, cx, cy, hours / 12, radius * 0.50, 7, theme['hand'])
        self.draw_hand(gc, cx, cy, minutes / 60, radius * 0.74, 5, theme['hand'])
        self.draw_hand(gc, cx, cy, seconds / 60, radius * 0.84, 2, theme['second'])

        gc.SetPen(wx.Pen(wx.Colour(theme['face']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['second'])))
        gc.DrawEllipse(cx - 5, cy - 5, 10, 10)

    def draw_hand(self, gc, cx, cy, fraction, length, width, colour):
        angle = math.radians(fraction * 360)
        tail = length * 0.16
        gc.SetPen(wx.Pen(wx.Colour(colour), width))
        gc.StrokeLine(cx - tail * math.sin(angle), cy + tail * math.cos(angle),
                      cx + length * math.sin(angle), cy - length * math.cos(angle))


class ClockBox(wx.Panel):

    def __init__(self, parent, theme, settings):
        super().__init__(parent)
        self.canvas = ClockCanvas(self, theme)
        self.digital = wx.StaticText(self, label='')
        self.datetext = wx.StaticText(self, label='')
        self.use24h = FlatCheckBox(self, theme, '24-hour clock', self.tick)
        self.use24h.SetValue(settings.get('use_24h', True))

        self.digital.SetFont(get_font(30, bold=True))
        self.datetext.SetFont(get_font(11))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.digital, 0, wx.ALIGN_CENTER)
        sizer.Add(self.datetext, 0, wx.ALIGN_CENTER | wx.TOP, 2)
        sizer.Add(self.use24h, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        self.SetSizer(sizer)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.digital.SetForegroundColour(wx.Colour(theme['text']))
        self.datetext.SetForegroundColour(wx.Colour(theme['dim']))
        self.use24h.set_theme(theme)
        self.Refresh()

    def tick(self):
        now = datetime.datetime.now()
        if self.use24h.GetValue():
            self.digital.SetLabel(now.strftime('%H:%M:%S'))
        else:
            meridiem = 'AM' if now.hour < 12 else 'PM'
            self.digital.SetLabel('%d:%s %s' % (
                (now.hour % 12) or 12, now.strftime('%M:%S'), meridiem))
        self.datetext.SetLabel('%s, %s %d, %d' % (
            WEEKDAYS[now.weekday()], MONTHS[now.month - 1], now.day, now.year))
        self.Layout()
        self.canvas.Refresh()
