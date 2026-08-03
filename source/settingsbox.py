# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

탭 바에 노출되지 않는 페이지. 설정 아이콘으로만 들어온다.
'''


import wx

from controls import FlatCheckBox
from utilities import get_font


class SettingsBox(wx.Panel):

    def __init__(self, parent, theme, settings, on_change):
        super().__init__(parent)
        self.title = wx.StaticText(self, label='Settings')
        self.title.SetFont(get_font(15, bold=True))

        self.use24h = FlatCheckBox(self, theme, '24-hour clock', on_change)
        self.useutc = FlatCheckBox(self, theme, 'UTC', on_change)
        self.ontop = FlatCheckBox(self, theme, 'Always on Top', on_change)
        self.autohide = FlatCheckBox(self, theme, 'Auto hide menu', on_change)
        self.dark = FlatCheckBox(self, theme, 'Dark theme', on_change)
        self.checks = (self.use24h, self.useutc, self.ontop, self.autohide, self.dark)

        self.use24h.SetValue(settings.get('use_24h', True))
        self.useutc.SetValue(settings.get('use_utc', False))
        self.ontop.SetValue(settings.get('on_top', False))
        self.autohide.SetValue(settings.get('auto_hide_menu', True))
        self.dark.SetValue(settings.get('theme', 'dark') == 'dark')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, 0, wx.LEFT | wx.TOP, 22)
        sizer.AddSpacer(16)
        for check in self.checks:
            sizer.Add(check, 0, wx.LEFT | wx.BOTTOM, 22)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.title.SetForegroundColour(wx.Colour(theme['text']))
        for check in self.checks:
            check.set_theme(theme)
        self.Refresh()

    def tick(self):
        pass
