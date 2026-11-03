# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import makeshortcut
import subprocess
import sys
import wx

from panels import AboutCard
from panels import ActionCard
from panels import ChoiceCard
from panels import LayoutCard
from panels import Panel
from panels import ScrollArea
from panels import SettingCard
from utilities import APP_AUTHOR
from utilities import APP_EMAIL
from utilities import APP_HOME
from utilities import APP_NAME
from utilities import APP_VERSION
from utilities import get_asset_path
from utilities import get_panel_theme


CLOCK_PRESETS = (('classic', 'Classic'), ('minimal', 'Minimal'))
THEMES = (('auto', 'Auto'), ('light', 'Light'), ('dark', 'Dark'))
ACCENTS = (('blue', 'Blue'), ('red', 'Red'))
OFFSETS = (('local', 'Local'), ('utc', 'UTC'))
# the clock page is always there
PAGES = (('world', 'World', 'Other cities and their time on a map'),
         ('weather', 'Weather', 'Forecast for the home city picked on World'),
         ('stopwatch', 'Stopwatch', 'Laps to a hundredth of a second'),
         ('countdown', 'Countdown', 'A timer that rings at zero'))
SHORTCUT_OFF = 'Put a shortcut in the Start menu'
SHORTCUT_ON = 'A shortcut is in the Start menu'
UPDATE_NOTE = 'Look for a new release on GitHub'
TRAY_NOTE = 'Also from the tray icon while the window is hidden'
TRAY_NOTE_OFF = 'Needs the tray icon, under Window'

DRAG_FRAME_MS = 16
DRAG_EASE = 0.35


class SettingsBox(ScrollArea):

    def __init__(self, parent, theme, settings, on_change, folds=None, on_fold=None,
                 on_check=None):
        theme = get_panel_theme(theme)
        super().__init__(parent, theme)
        self.folds = folds if folds is not None else set()
        self.on_folds = on_fold
        self.on_change = on_change
        board = self.content

        def toggle(label, description):
            return SettingCard(board, theme, label, description, on_change)

        self.use24h = toggle('24-hour clock', 'Show the time as 00-23')
        self.useutc = toggle('UTC', 'Offer UTC beside local time on the clock page')
        self.offset_choice = ChoiceCard(board, theme, 'Time difference',
                                        'On World, from the time here or from UTC', OFFSETS,
                                        on_change)
        self.pages = {key: LayoutCard(board, theme, label, note, on_change, self.on_drag)
                      for key, label, note in PAGES}
        self.drag = None
        self.drag_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_drag_frame, self.drag_timer)
        self.ontop = toggle('Always on top', 'Keep the window above others')
        self.tray = toggle('Tray icon', 'Show an icon in the notification area')
        self.close_to_tray = toggle('Close to tray',
                                    'Closing hides the window instead of quitting')
        self.autohide = toggle('Auto hide menu', 'Show the header only on hover')
        # a source run only: an installed exe has the installer's Start menu entry
        self.shortcut = None
        if not getattr(sys, 'frozen', False):
            self.shortcut = ActionCard(board, theme, 'Start menu', SHORTCUT_OFF, 'Create',
                                       self.on_shortcut)
            self.shortcut.set_captions('Remove')
            self.update_shortcut()
        self.preset = ChoiceCard(board, theme, 'Clock face', 'Pick how the dial is drawn',
                                 CLOCK_PRESETS, on_change)
        self.smooth = toggle('Smooth second hand', 'Sweep instead of stepping once a second')
        self.theme_choice = ChoiceCard(board, theme, 'Theme', 'Auto follows Windows', THEMES,
                                       on_change)
        self.accent_choice = ChoiceCard(board, theme, 'Accent',
                                        'Buttons on, the rings, the map and the menu', ACCENTS,
                                        on_change)
        self.check_updates = toggle('Check for updates', 'Once a day, a notice when one is out')
        self.tray_notice = toggle('Tray notification', TRAY_NOTE)
        self.check_now = ActionCard(board, theme, 'Latest release', UPDATE_NOTE, 'Check now',
                                    on_check)

        self.use24h.SetValue(settings.get('use_24h', True))
        self.useutc.SetValue(settings.get('use_utc', False))
        self.offset_choice.SetValue(settings.get('world_offset', 'local'))
        for key, card in self.pages.items():
            card.SetValue(settings.get(f'page_{key}', True))
        order = [key for key in settings.get('page_order', []) if key in self.pages]
        self.order = order + [key for key in self.pages if key not in order]
        self.ontop.SetValue(settings.get('on_top', False))
        self.tray.SetValue(settings.get('tray_icon', True))
        self.close_to_tray.SetValue(settings.get('close_to_tray', False))
        self.autohide.SetValue(settings.get('auto_hide_menu', True))
        self.preset.SetValue(settings.get('clock_preset', 'classic'))
        self.smooth.SetValue(settings.get('smooth_second', True))
        self.theme_choice.SetValue(settings.get('theme', 'dark'))
        self.accent_choice.SetValue(settings.get('accent', 'blue'))
        self.check_updates.SetValue(settings.get('update_check', True))
        self.tray_notice.SetValue(settings.get('update_tray', True))
        self.update_tray_note()

        self.pages_sizer = wx.BoxSizer(wx.VERTICAL)
        self.pages_panel = Panel(board, theme, 'settings.pages', 'Pages', (self.pages_sizer,),
                                 self.folds, self.on_fold, subtitle='Drag to reorder',
                                 rows=self.get_page_rows())
        self.fill_pages()
        self.set_panels([
            Panel(board, theme, 'settings.clock', 'Clock',
                  (self.use24h, self.useutc, self.offset_choice), self.folds, self.on_fold),
            self.pages_panel,
            Panel(board, theme, 'settings.window', 'Window',
                  tuple(card for card in (self.ontop, self.tray, self.close_to_tray,
                                          self.autohide, self.shortcut) if card),
                  self.folds, self.on_fold),
            Panel(board, theme, 'settings.appearance', 'Appearance',
                  (self.preset, self.smooth, self.theme_choice, self.accent_choice), self.folds,
                  self.on_fold),
            Panel(board, theme, 'settings.updates', 'Updates',
                  (self.check_updates, self.tray_notice, self.check_now), self.folds,
                  self.on_fold),
            Panel(board, theme, 'settings.about', 'About',
                  (AboutCard(board, theme, f'{APP_NAME} {APP_VERSION}',
                             (APP_AUTHOR, APP_EMAIL), 'GitHub', self.on_home,
                             wx.Image(get_asset_path('icon', 'muteklab.png'))),),
                  self.folds, self.on_fold),
        ])
        self.bind_children()
        self.apply_theme(theme)

    def update_tray_note(self):
        # the balloon pops up from the tray icon
        note = TRAY_NOTE if self.tray.GetValue() else TRAY_NOTE_OFF
        if note != self.tray_notice.description:
            self.tray_notice.description = note
            self.tray_notice.Refresh()

    def update_shortcut(self, note=None):
        present = makeshortcut.has_start_menu()
        self.shortcut.set_caption('Remove' if present else 'Create')
        self.shortcut.set_description(note or (SHORTCUT_ON if present else SHORTCUT_OFF))

    def on_shortcut(self):
        try:
            if makeshortcut.has_start_menu():
                makeshortcut.remove_start_menu()
                note = 'Shortcut removed'
            else:
                makeshortcut.create(makeshortcut.get_start_menu_paths()[0])
                note = 'Shortcut created'
        except Exception:
            self.shortcut.set_description('Could not change the shortcut')
            self.shortcut.set_tone('warn')
            return
        self.update_shortcut(note)
        self.shortcut.set_tone('plain')

    def on_home(self):
        # explorer hands the link to the shell, so the browser does not inherit elevation
        subprocess.Popen(['explorer', APP_HOME])

    def on_fold(self):
        self.relayout_panels()
        if self.on_folds:
            self.on_folds()

    def get_page_rows(self):
        return [self.pages[key] for key in self.order]

    def fill_pages(self):
        self.pages_sizer.Clear()
        for key in self.order:
            self.pages_sizer.Add(self.pages[key], 0, wx.EXPAND)
        self.pages_panel.set_rows(self.get_page_rows())
        self.pages_panel.apply_fold()

    def on_drag(self, card, phase, screen_y):
        key = next(name for name, value in self.pages.items() if value is card)
        if phase == 'start':
            slots = [self.pages[name].GetPosition().y for name in self.order]
            self.drag = {
                'key': key, 'order': list(self.order), 'slots': slots,
                'x': card.GetPosition().x,
                'grab': self.content.ScreenToClient(wx.Point(0, screen_y)).y - card.GetPosition().y,
                'y': {name: float(self.pages[name].GetPosition().y) for name in self.order},
                'mouse': screen_y, 'dropped': False,
            }
            card.Raise()
            self.drag_timer.Start(DRAG_FRAME_MS)
        elif phase == 'move' and self.drag:
            self.drag['mouse'] = screen_y
        elif phase == 'drop' and self.drag:
            self.drag['mouse'] = screen_y
            self.drag['dropped'] = True

    def on_drag_frame(self, event):
        drag = self.drag
        if not drag:
            self.drag_timer.Stop()
            return
        slots = drag['slots']
        stride = (slots[-1] - slots[0]) / float(len(slots) - 1) if len(slots) > 1 else 1
        key = drag['key']

        top = self.content.ScreenToClient(wx.Point(0, drag['mouse'])).y - drag['grab']
        top = min(max(top, slots[0]), slots[-1])
        index = int(round((top - slots[0]) / stride)) if stride else 0
        order = [name for name in drag['order'] if name != key]
        order.insert(index, key)

        settled = True
        for position, name in enumerate(order):
            if name == key and not drag['dropped']:
                drag['y'][name] = top
            else:
                target = slots[position]
                drag['y'][name] += (target - drag['y'][name]) * DRAG_EASE
                if abs(target - drag['y'][name]) < 0.5:
                    drag['y'][name] = target
                else:
                    settled = False
            self.pages[name].SetPosition(wx.Point(drag['x'], int(round(drag['y'][name]))))
        self.pages_panel.set_rows([self.pages[name] for name in order])

        if drag['dropped'] and settled:
            self.drag_timer.Stop()
            self.drag = None
            changed = order != self.order
            self.order = order
            self.fill_pages()
            self.content.Layout()
            self.fit()
            self.Refresh()
            if changed:
                self.on_change()

    def apply_theme(self, theme):
        theme = get_panel_theme(theme)
        self.set_theme(theme)
        for child in self.content.GetChildren():
            if hasattr(child, 'set_theme'):
                child.set_theme(theme)
        self.Refresh()

    def tick(self):
        pass
