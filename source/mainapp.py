# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import os
import wx

from clockbox import ClockBox
from controls import SettingsButton
from countdownbox import CountdownBox
from settingsbox import SettingsBox
from stopwatchbox import StopwatchBox
from tabbar import TabBar
from utilities import APP_NAME
from utilities import THEMES
from utilities import apply_titlebar_theme
from utilities import load_settings
from utilities import save_settings


TICK_INTERVAL = 50
TABS = ('Clock', 'Stopwatch', 'Countdown')


class MainFrame(wx.Frame):

    def __init__(self):
        settings = load_settings()
        width, height = settings.get('size', [380, 580])
        super().__init__(None, title=APP_NAME, size=wx.Size(width, height))

        self.theme_name = settings.get('theme', 'dark')
        theme = THEMES[self.theme_name]

        self.set_icon()

        self.tab_index = 0
        self.book = wx.Simplebook(self)
        self.clockbox = ClockBox(self.book, theme)
        self.stopwatchbox = StopwatchBox(self.book, theme)
        self.countdownbox = CountdownBox(self.book, theme)
        self.settingsbox = SettingsBox(self.book, theme, settings, self.on_settings)
        for page in (self.clockbox, self.stopwatchbox,
                     self.countdownbox, self.settingsbox):
            self.book.AddPage(page, '')

        self.tabbar = TabBar(self, theme, TABS, self.on_tab)
        self.settings_button = SettingsButton(self, theme, self.on_settings_button)

        header = wx.BoxSizer(wx.HORIZONTAL)
        header.Add(self.tabbar, 1, wx.EXPAND)
        header.Add(self.settings_button, 0, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(header, 0, wx.EXPAND)
        sizer.Add(self.book, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.apply_theme()
        self.on_settings()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_tick)
        self.Bind(wx.EVT_SIZE, self.on_size)
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
        self.settings_button.set_theme(theme)

        self.clockbox.apply_theme(theme)
        self.stopwatchbox.apply_theme(theme)
        self.countdownbox.apply_theme(theme)
        self.settingsbox.apply_theme(theme)

        apply_titlebar_theme(self, theme['titlebar_dark'])
        self.Refresh()

    def on_tab(self, index):
        self.tab_index = index
        self.book.SetSelection(index)
        self.settings_button.set_active(False)
        self.on_tick(None)

    def on_settings_button(self):
        if self.book.GetCurrentPage() is self.settingsbox:
            self.tabbar.set_selection(self.tab_index)
            self.book.SetSelection(self.tab_index)
            self.settings_button.set_active(False)
        else:
            self.tabbar.set_selection(-1)
            self.book.SetSelection(len(TABS))
            self.settings_button.set_active(True)
        self.on_tick(None)

    def on_settings(self):
        self.clockbox.set_options(self.settingsbox.use24h.GetValue(),
                                  self.settingsbox.useutc.GetValue())

        style = self.GetWindowStyle()
        if self.settingsbox.ontop.GetValue():
            self.SetWindowStyle(style | wx.STAY_ON_TOP)
        else:
            self.SetWindowStyle(style & ~wx.STAY_ON_TOP)

        theme_name = 'dark' if self.settingsbox.dark.GetValue() else 'light'
        if theme_name != self.theme_name:
            self.theme_name = theme_name
            self.apply_theme()

    def on_size(self, event):
        width = self.GetClientSize()[0]
        if width > 0 and self.settings_button.set_width(width // (len(TABS) + 1)):
            self.Layout()
        event.Skip()

    def on_tick(self, event):
        page = self.book.GetCurrentPage()
        if page is not None:
            page.tick()

        # Auto hide menu 가 켜져 있으면 창에 마우스가 올라와 있을 때만 헤더를
        # 보여준다. 설정 페이지에 머무는 동안은 돌아갈 길을 남겨두려고 계속 보인다.
        visible = (not self.settingsbox.autohide.GetValue() or
                   page is self.settingsbox or
                   self.GetScreenRect().Contains(wx.GetMousePosition()))
        self.tabbar.set_visible(visible)
        self.settings_button.set_visible(visible)

    def on_close(self, event):
        self.timer.Stop()
        width, height = self.GetSize()
        save_settings({
            'theme': self.theme_name,
            'on_top': self.settingsbox.ontop.GetValue(),
            'use_24h': self.settingsbox.use24h.GetValue(),
            'use_utc': self.settingsbox.useutc.GetValue(),
            'auto_hide_menu': self.settingsbox.autohide.GetValue(),
            'size': [width, height],
        })
        event.Skip()


def launch_mainapp():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    apply_titlebar_theme(frame, THEMES[frame.theme_name]['titlebar_dark'])
    app.MainLoop()
