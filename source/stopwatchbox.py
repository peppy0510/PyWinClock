# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import time
import wx

from controls import FlatButton
from utilities import Canvas
from utilities import get_font


def format_elapsed(value):
    total = int(value)
    return '%d:%02d:%02d' % (total // 3600, total % 3600 // 60, total % 60)


class StopwatchCanvas(Canvas):

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.elapsed = 0.0

    def draw(self, gc, width, height):
        theme = self.theme
        size = max(14, min(int(width / 8), int(height / 2.4)))
        top = height / 2 - size * 0.8
        height_used = self.draw_centered_text(
            gc, format_elapsed(self.elapsed), width / 2, top,
            get_font(size, bold=True), theme['text'])
        self.draw_centered_text(
            gc, '.%02d' % (int(self.elapsed * 100) % 100), width / 2, top + height_used,
            get_font(max(9, int(size * 0.5))), theme['second'])


class StopwatchBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.running = False
        self.elapsed = 0.0
        self.started_at = 0.0

        self.canvas = StopwatchCanvas(self, theme)
        self.start_button = FlatButton(self, theme, 'Start', self.on_start)
        self.lap_button = FlatButton(self, theme, 'Lap', self.on_lap)
        self.reset_button = FlatButton(self, theme, 'Reset', self.on_reset)
        self.laps = wx.ListBox(self, style=wx.NO_BORDER)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for button in (self.start_button, self.lap_button, self.reset_button):
            row.Add(button, 1, wx.EXPAND | wx.ALL, 4)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
        sizer.Add(self.laps, 1, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.laps.SetBackgroundColour(wx.Colour(theme['face']))
        self.laps.SetForegroundColour(wx.Colour(theme['text']))
        self.laps.SetFont(get_font(9))
        for button in (self.start_button, self.lap_button, self.reset_button):
            button.set_theme(theme)
        self.Refresh()

    def get_elapsed(self):
        if self.running:
            return self.elapsed + (time.perf_counter() - self.started_at)
        return self.elapsed

    def on_start(self):
        if self.running:
            self.elapsed = self.get_elapsed()
            self.running = False
            self.start_button.SetLabel('Start')
        else:
            self.started_at = time.perf_counter()
            self.running = True
            self.start_button.SetLabel('Stop')

    def on_lap(self):
        elapsed = self.get_elapsed()
        if elapsed <= 0:
            return
        self.laps.Insert('%2d.   %s.%02d' % (
            self.laps.GetCount() + 1, format_elapsed(elapsed),
            int(elapsed * 100) % 100), 0)

    def on_reset(self):
        self.running = False
        self.elapsed = 0.0
        self.start_button.SetLabel('Start')
        self.laps.Clear()
        self.tick()

    def tick(self):
        self.canvas.elapsed = self.get_elapsed()
        self.canvas.Refresh()
