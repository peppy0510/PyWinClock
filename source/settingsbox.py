# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import wx

from controls import ButtonCard
from controls import ChoiceCard
from controls import ScrollArea
from controls import SettingCard
from utilities import APP_NAME
from utilities import get_font


CLOCK_PRESETS = (('classic', 'Classic'), ('minimal', 'Minimal'))

THEMES = (('auto', 'Auto'), ('light', 'Light'), ('dark', 'Dark'))

SHORTCUT_NOTE = 'Put a shortcut in the Start menu'

MARGIN = 16
# text aligned to a card's rim line looks outdented
TITLE_INSET = 3
TITLE_GAP = 8
CARD_GAP = 4
GROUP_GAP = 14


class SettingsBox(ScrollArea):

    def __init__(self, parent, theme, settings, on_change):
        super().__init__(parent, theme)
        board = self.content
        self.use24h = SettingCard(board, theme, '24-hour clock',
                                  'Show the time as 00-23', on_change)
        self.useutc = SettingCard(board, theme, 'UTC',
                                  'Show UTC instead of local time', on_change)
        self.ontop = SettingCard(board, theme, 'Always on top',
                                 'Keep the window above others', on_change)
        self.autohide = SettingCard(board, theme, 'Auto hide menu',
                                    'Show the header only on hover', on_change)
        self.shortcut = ButtonCard(board, theme, 'Start menu', SHORTCUT_NOTE, 'Create',
                                   self.on_shortcut)
        self.preset = ChoiceCard(board, theme, 'Clock face',
                                 'Pick how the dial is drawn', CLOCK_PRESETS, on_change)
        self.smooth = SettingCard(board, theme, 'Smooth second hand',
                                  'Sweep instead of stepping once a second', on_change)
        self.theme_choice = ChoiceCard(board, theme, 'Theme', 'Auto follows Windows',
                                       THEMES, on_change)
        self.cards = (self.use24h, self.useutc, self.ontop, self.autohide, self.shortcut,
                      self.preset, self.smooth, self.theme_choice)

        self.use24h.SetValue(settings.get('use_24h', True))
        self.useutc.SetValue(settings.get('use_utc', False))
        self.ontop.SetValue(settings.get('on_top', False))
        self.autohide.SetValue(settings.get('auto_hide_menu', True))
        self.preset.SetValue(settings.get('clock_preset', 'classic'))
        self.smooth.SetValue(settings.get('smooth_second', True))
        self.theme_choice.SetValue(settings.get('theme', 'dark'))

        self.titles = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(MARGIN)
        for title, cards in (('Clock', (self.use24h, self.useutc)),
                             ('Window', (self.ontop, self.autohide, self.shortcut)),
                             ('Appearance', (self.preset, self.smooth, self.theme_choice))):
            label = wx.StaticText(board, label=title)
            label.SetFont(get_font(10, bold=True))
            self.titles.append(label)
            sizer.Add(label, 0, wx.LEFT, MARGIN + TITLE_INSET)
            sizer.AddSpacer(TITLE_GAP)
            for index, card in enumerate(cards):
                if index:
                    sizer.AddSpacer(CARD_GAP)
                sizer.Add(card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, MARGIN)
            sizer.AddSpacer(GROUP_GAP)
        board.SetSizer(sizer)
        self.bind_children()
        self.apply_theme(theme)

    def on_shortcut(self):
        # win32com costs about 7 MB, load it only when asked
        import makeshortcut
        from shortcut import ShortCut
        try:
            makeshortcut.create(ShortCut.get_user_startmenu_path(APP_NAME))
        except Exception:
            self.shortcut.set_description('Could not create the shortcut', 'warn')
            return
        self.shortcut.set_description('Shortcut created')

    def apply_theme(self, theme):
        self.set_theme(theme)
        for label in self.titles:
            label.SetBackgroundColour(wx.Colour(theme['bg']))
            label.SetForegroundColour(wx.Colour(theme['text']))
        for card in self.cards:
            card.set_theme(theme)
        self.Refresh()

    def tick(self):
        pass
