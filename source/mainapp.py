# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import os
import wx

from clockbox import ClockBox
from controls import FlatButton
from controls import FlatCheckBox
from daycounterbox import DayCounterBox
from stopwatchbox import StopwatchBox
from tabbar import TabBar
from utilities import APP_NAME
from utilities import THEMES
from utilities import apply_titlebar_theme
from utilities import load_settings
from utilities import save_settings


TICK_INTERVAL = 50
TABS = ('Clock', 'Stopwatch', 'Date')


class MainFrame(wx.Frame):

    def __init__(self):
        settings = load_settings()
        width, height = settings.get('size', [380, 580])
        super().__init__(None, title=APP_NAME, size=wx.Size(width, height))

        self.theme_name = settings.get('theme', 'dark')
        theme = THEMES[self.theme_name]

        self.set_icon()

        self.book = wx.Simplebook(self)
        self.clockbox = ClockBox(self.book, theme, settings)
        self.stopwatchbox = StopwatchBox(self.book, theme)
        self.daycounterbox = DayCounterBox(self.book, theme)
        for page in (self.clockbox, self.stopwatchbox, self.daycounterbox):
            self.book.AddPage(page, '')

        self.tabbar = TabBar(self, theme, TABS, self.on_tab)
        self.theme_button = FlatButton(self, theme, 'Theme', self.on_theme)
        self.ontop_check = FlatCheckBox(self, theme, 'Always on Top', self.on_ontop)
        self.ontop_check.SetValue(settings.get('on_top', False))

        bar = wx.BoxSizer(wx.HORIZONTAL)
        bar.Add(self.ontop_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        bar.AddStretchSpacer()
        bar.Add(self.theme_button, 0, wx.RIGHT, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tabbar, 0, wx.EXPAND)
        sizer.Add(self.book, 1, wx.EXPAND)
        sizer.Add(bar, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        self.SetSizer(sizer)

        self.apply_theme()
        self.on_ontop()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_tick)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.timer.Start(TICK_INTERVAL)
        self.on_tick(None)
        self.Centre()

    def set_icon(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'assets', 'icon', 'icon.ico')
        if os.path.exists(path):
            self.SetIcon(wx.Icon(path, wx.BITMAP_TYPE_ICO))

    def apply_theme(self):
        theme = THEMES[self.theme_name]
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.book.SetBackgroundColour(wx.Colour(theme['bg']))
        self.tabbar.set_theme(theme)

        self.ontop_check.set_theme(theme)
        self.theme_button.set_theme(theme)

        self.clockbox.apply_theme(theme)
        self.stopwatchbox.apply_theme(theme)
        self.daycounterbox.apply_theme(theme)

        apply_titlebar_theme(self, theme['titlebar_dark'])
        self.Refresh()

    def on_tab(self, index):
        self.book.SetSelection(index)
        self.on_tick(None)

    def on_theme(self):
        self.theme_name = 'light' if self.theme_name == 'dark' else 'dark'
        self.apply_theme()

    def on_ontop(self):
        style = self.GetWindowStyle()
        if self.ontop_check.GetValue():
            self.SetWindowStyle(style | wx.STAY_ON_TOP)
        else:
            self.SetWindowStyle(style & ~wx.STAY_ON_TOP)

    def on_tick(self, event):
        page = self.book.GetCurrentPage()
        if page is not None:
            page.tick()

    def on_close(self, event):
        self.timer.Stop()
        width, height = self.GetSize()
        save_settings({
            'theme': self.theme_name,
            'on_top': self.ontop_check.GetValue(),
            'use_24h': self.clockbox.use24h.GetValue(),
            'size': [width, height],
        })
        event.Skip()


def launch_mainapp():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    apply_titlebar_theme(frame, THEMES[frame.theme_name]['titlebar_dark'])
    app.MainLoop()
