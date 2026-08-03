# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import time
import wx

from controls import FlatButton
from utilities import BUTTON_SIZE
from utilities import CONTROL_GAP
from utilities import TimerCanvas
from utilities import format_hms
from utilities import format_hundredths
from utilities import get_font


class StopwatchBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.running = False
        self.elapsed = 0.0
        self.started_at = 0.0

        self.canvas = TimerCanvas(self, theme)
        self.start_button = FlatButton(self, theme, 'Start', self.on_start,
                                       size=BUTTON_SIZE, kind='primary')
        self.lap_button = FlatButton(self, theme, 'Lap', self.on_lap, size=BUTTON_SIZE)
        self.reset_button = FlatButton(self, theme, 'Reset', self.on_reset, size=BUTTON_SIZE)
        self.buttons = (self.start_button, self.lap_button, self.reset_button)
        self.laps = wx.ListBox(self, style=wx.NO_BORDER)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for button in self.buttons:
            row.Add(button, 1, wx.EXPAND | wx.ALL, CONTROL_GAP)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, CONTROL_GAP)
        sizer.Add(self.laps, 1, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.laps.SetBackgroundColour(wx.Colour(theme['face']))
        self.laps.SetForegroundColour(wx.Colour(theme['text']))
        self.laps.SetFont(get_font(10))
        for button in self.buttons:
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
            self.start_button.set_kind('primary')
        else:
            self.started_at = time.perf_counter()
            self.running = True
            self.start_button.SetLabel('Stop')
            self.start_button.set_kind('danger')

    def on_lap(self):
        elapsed = self.get_elapsed()
        if elapsed <= 0:
            return
        # 한 줄에 이어 붙으므로 여기서는 구분자가 필요하다.
        self.laps.Insert('%2d.   %s.%s' % (
            self.laps.GetCount() + 1, format_hms(elapsed), format_hundredths(elapsed)), 0)

    def on_reset(self):
        self.running = False
        self.elapsed = 0.0
        self.start_button.SetLabel('Start')
        self.start_button.set_kind('primary')
        self.laps.Clear()
        self.tick()

    def tick(self):
        self.canvas.seconds = self.get_elapsed()
        self.canvas.Refresh()
