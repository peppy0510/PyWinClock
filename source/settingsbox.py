# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

탭 바에 노출되지 않는 페이지. 설정 아이콘으로만 들어온다.
Windows 11 설정처럼 그룹 제목 아래 카드를 쌓는다.
'''


import wx

from controls import SettingCard
from utilities import get_font


MARGIN = 16
# 카드 테두리는 선이지만 제목은 글자라, 같은 여백이면 제목이 왼쪽으로 삐져나와 보인다.
TITLE_INSET = 3
TITLE_GAP = 8
CARD_GAP = 4
GROUP_GAP = 14


class SettingsBox(wx.Panel):

    def __init__(self, parent, theme, settings, on_change):
        super().__init__(parent)
        self.use24h = SettingCard(self, theme, '24-hour clock',
                                  'Show the time as 00-23', on_change)
        self.useutc = SettingCard(self, theme, 'UTC',
                                  'Show UTC instead of local time', on_change)
        self.ontop = SettingCard(self, theme, 'Always on top',
                                 'Keep the window above others', on_change)
        self.autohide = SettingCard(self, theme, 'Auto hide menu',
                                    'Show the header only on hover', on_change)
        self.dark = SettingCard(self, theme, 'Dark theme',
                                'Use the dark colour scheme', on_change)
        self.cards = (self.use24h, self.useutc, self.ontop, self.autohide, self.dark)

        self.use24h.SetValue(settings.get('use_24h', True))
        self.useutc.SetValue(settings.get('use_utc', False))
        self.ontop.SetValue(settings.get('on_top', False))
        self.autohide.SetValue(settings.get('auto_hide_menu', True))
        self.dark.SetValue(settings.get('theme', 'dark') == 'dark')

        self.groups = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(MARGIN)
        for title, cards in (('Clock', (self.use24h, self.useutc)),
                             ('Window', (self.ontop, self.autohide)),
                             ('Appearance', (self.dark,))):
            label = wx.StaticText(self, label=title)
            label.SetFont(get_font(10, bold=True))
            self.groups.append(label)
            sizer.Add(label, 0, wx.LEFT, MARGIN + TITLE_INSET)
            sizer.AddSpacer(TITLE_GAP)
            for index, card in enumerate(cards):
                if index:
                    sizer.AddSpacer(CARD_GAP)
                sizer.Add(card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, MARGIN)
            sizer.AddSpacer(GROUP_GAP)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        for label in self.groups:
            label.SetForegroundColour(wx.Colour(theme['text']))
        for card in self.cards:
            card.set_theme(theme)
        self.Refresh()

    def tick(self):
        pass
