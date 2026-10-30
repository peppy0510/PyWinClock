# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import subprocess
import wx

from panels import AboutCard
from panels import ActionCard
from panels import ChoiceCard
from panels import Panel
from panels import ScrollArea
from panels import SettingCard
from utilities import APP_AUTHOR
from utilities import APP_EMAIL
from utilities import APP_HOME
from utilities import APP_NAME
from utilities import APP_VERSION
from utilities import get_asset_path


CLOCK_PRESETS = (('classic', 'Classic'), ('minimal', 'Minimal'))
THEMES = (('auto', 'Auto'), ('light', 'Light'), ('dark', 'Dark'))
ACCENTS = (('blue', 'Blue'), ('red', 'Red'))
SHORTCUT_NOTE = 'Put a shortcut in the Start menu'


class SettingsBox(ScrollArea):

    def __init__(self, parent, theme, settings, on_change, folds=None, on_fold=None):
        super().__init__(parent, theme)
        self.folds = folds if folds is not None else set()
        self.on_folds = on_fold
        board = self.content

        def toggle(label, description):
            return SettingCard(board, theme, label, description, on_change)

        self.use24h = toggle('24-hour clock', 'Show the time as 00-23')
        self.useutc = toggle('UTC', 'Offer UTC beside local time on the clock page')
        self.ontop = toggle('Always on top', 'Keep the window above others')
        self.tray = toggle('Tray icon', 'Show an icon in the notification area')
        self.close_to_tray = toggle('Close to tray',
                                    'Closing hides the window instead of quitting')
        self.autohide = toggle('Auto hide menu', 'Show the header only on hover')
        self.shortcut = ActionCard(board, theme, 'Start menu', SHORTCUT_NOTE, 'Create',
                                   self.on_shortcut)
        self.preset = ChoiceCard(board, theme, 'Clock face', 'Pick how the dial is drawn',
                                 CLOCK_PRESETS, on_change)
        self.smooth = toggle('Smooth second hand', 'Sweep instead of stepping once a second')
        self.theme_choice = ChoiceCard(board, theme, 'Theme', 'Auto follows Windows', THEMES,
                                       on_change)
        self.accent_choice = ChoiceCard(board, theme, 'Accent',
                                        'Buttons on, the rings, the map and the menu', ACCENTS,
                                        on_change)

        self.use24h.SetValue(settings.get('use_24h', True))
        self.useutc.SetValue(settings.get('use_utc', False))
        self.ontop.SetValue(settings.get('on_top', False))
        self.tray.SetValue(settings.get('tray_icon', True))
        self.close_to_tray.SetValue(settings.get('close_to_tray', False))
        self.autohide.SetValue(settings.get('auto_hide_menu', True))
        self.preset.SetValue(settings.get('clock_preset', 'classic'))
        self.smooth.SetValue(settings.get('smooth_second', True))
        self.theme_choice.SetValue(settings.get('theme', 'dark'))
        self.accent_choice.SetValue(settings.get('accent', 'blue'))

        self.set_panels([
            Panel(board, theme, 'settings.clock', 'Clock', (self.use24h, self.useutc),
                  self.folds, self.on_fold),
            Panel(board, theme, 'settings.window', 'Window',
                  (self.ontop, self.tray, self.close_to_tray, self.autohide, self.shortcut),
                  self.folds, self.on_fold),
            Panel(board, theme, 'settings.appearance', 'Appearance',
                  (self.preset, self.smooth, self.theme_choice, self.accent_choice), self.folds,
                  self.on_fold),
            Panel(board, theme, 'settings.about', 'About',
                  (AboutCard(board, theme, f'{APP_NAME} {APP_VERSION}',
                             (APP_AUTHOR, APP_EMAIL), 'GitHub', self.on_home,
                             wx.Image(get_asset_path('icon', 'muteklab.png'))),),
                  self.folds, self.on_fold),
        ])
        self.bind_children()
        self.apply_theme(theme)

    def on_shortcut(self):
        # win32com costs about 7 MB, load it only when asked
        import makeshortcut
        from shortcut import ShortCut
        try:
            makeshortcut.create(ShortCut.get_user_startmenu_path(APP_NAME))
        except Exception:
            self.shortcut.set_description('Could not create the shortcut')
            self.shortcut.set_tone('warn')
            return
        self.shortcut.set_description('Shortcut created')
        self.shortcut.set_tone('plain')

    def on_home(self):
        # explorer hands the link to the shell, so the browser does not inherit elevation
        subprocess.Popen(['explorer', APP_HOME])

    def on_fold(self):
        self.relayout_panels()
        if self.on_folds:
            self.on_folds()

    def apply_theme(self, theme):
        self.set_theme(theme)
        for child in self.content.GetChildren():
            if hasattr(child, 'set_theme'):
                child.set_theme(theme)
        self.Refresh()

    def tick(self):
        pass
