# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import os
import subprocess
import threading
import time
import wx
import wx.adv

from carousel import Carousel
from carousel import PageDots
from clockbox import ClockBox
from countdownbox import CountdownBox
from settingsbox import SettingsBox
from sidemenu import SideMenu
from stopwatchbox import StopwatchBox
from titlebar import TitleBar
from tray import TrayIcon
from updatebox import UpdateBox
from updater import Updater
from updater import restart_source
from weatherbox import WeatherBox
from worldbox import WorldBox
from utilities import APP_NAME
from utilities import THEMES
from utilities import apply_accent
from utilities import apply_clip_siblings
from utilities import apply_no_caption
from utilities import apply_titlebar_theme
from utilities import format_hms
from utilities import get_asset_path
from utilities import get_frame_margins
from utilities import is_windows_dark
from utilities import load_settings
from utilities import paint_now
from utilities import save_settings


TICK_INTERVAL = 50
# a running timer's hundredths: at 50 ms they stepped by 5, the last digit only ever two
RUNNING_INTERVAL = 16
DEFAULT_SIZE = (480, 720)
MIN_SIZE = (360, 480)
THEME_POLL = 2.0

# the carousel's pages; the clock leads, the rest are ordered and turned off in the settings
PAGES = {'clock': ('Clock', 'clock'), 'world': ('World', 'globe'),
         'weather': ('Weather', 'weather'), 'stopwatch': ('Stopwatch', 'stopwatch'),
         'countdown': ('Countdown', 'countdown')}
SETTINGS_ITEM = ('Settings', 'settings')

FRAME_STYLE = wx.DEFAULT_FRAME_STYLE & ~wx.CAPTION

MIN_VISIBLE_WIDTH = 120
MIN_VISIBLE_HEIGHT = 32


class Pacer(threading.Thread):
    # WM_TIMER starves while the mouse keeps moving; a thread keeps the beat

    def __init__(self, frame):
        super().__init__(name='tick-pacer', daemon=True)
        self.frame = frame
        self.running = True
        self.pending = False
        self.interval = TICK_INTERVAL / 1000

    def run(self):
        target = time.perf_counter()
        while self.running:
            target += self.interval
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                target = time.perf_counter()
            if not self.pending:
                self.pending = True
                try:
                    wx.CallAfter(self.frame.on_tick)
                except Exception:
                    return


class MainFrame(wx.Frame):

    stored_rect = None
    restore_bounds = None
    tray = None
    quitting = False

    def __init__(self):
        settings = load_settings()
        super().__init__(None, title=APP_NAME, size=wx.Size(*DEFAULT_SIZE),
                         style=FRAME_STYLE)
        apply_no_caption(self)
        self.SetMinSize(wx.Size(*MIN_SIZE))

        self.theme_name = self.resolve_theme(settings.get('theme', 'dark'))
        self.accent_name = settings.get('accent', 'blue')
        apply_accent(self.accent_name)
        self.theme_checked = time.monotonic()
        theme = THEMES[self.theme_name]

        self.set_icon()

        self.book = wx.Simplebook(self)
        self.clockbox = ClockBox(self.book, theme, self.on_clock_zone)
        # picked on the clock page, offered when the UTC setting is on
        self.clockbox.use_utc = settings.get(
            'clock_zone', 'utc' if settings.get('use_utc') else 'local') == 'utc'
        self.worldbox = WorldBox(self.book, theme, settings, self.store_settings)
        # the World page's home city
        self.weatherbox = WeatherBox(self.book, theme, lambda: self.worldbox.home)
        self.stopwatchbox = StopwatchBox(self.book, theme)
        self.countdownbox = CountdownBox(self.book, theme)
        self.settings_folds = set(settings.get('settings_folded', []))
        self.settingsbox = SettingsBox(self.book, theme, settings, self.on_settings,
                                       self.settings_folds, self.store_settings,
                                       self.on_check_updates)
        self.boxes = {'clock': self.clockbox, 'world': self.worldbox,
                      'weather': self.weatherbox, 'stopwatch': self.stopwatchbox,
                      'countdown': self.countdownbox}
        # filled by apply_pages from the settings
        self.shown_pages = []

        self.titlebar = TitleBar(self, theme, self.on_menu, self.toggle_maximize)
        # before the menu, which opens over it
        self.updatebox = UpdateBox(self, theme, self.on_update_action)
        self.updater = Updater(settings, self.on_update_checked)
        self.release = None
        self.sidemenu = SideMenu(self, theme, (SETTINGS_ITEM,), self.on_select)
        apply_clip_siblings(self.book)
        apply_clip_siblings(self.updatebox)
        self.dots = PageDots(self, theme, len(PAGES), self.on_dot)
        self.carousel = Carousel(self, self.book, len(PAGES), self.on_carousel, theme)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.titlebar, 0, wx.EXPAND)
        sizer.Add(self.updatebox, 0, wx.EXPAND)
        sizer.Add(self.book, 1, wx.EXPAND)
        sizer.Add(self.dots, 0, wx.EXPAND)
        self.SetSizer(sizer)

        self.apply_theme()
        self.on_settings()

        self.pacer = Pacer(self)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MAXIMIZE, self.on_maximize)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.pacer.start()
        self.on_tick()
        self.restore_rect(settings)

    def is_rect_visible(self, rect):
        for index in range(wx.Display.GetCount()):
            shared = wx.Display(index).GetClientArea().Intersect(rect)
            if shared.width >= MIN_VISIBLE_WIDTH and shared.height >= MIN_VISIBLE_HEIGHT:
                return True
        return False

    def centre_on_primary(self):
        primary = wx.Display(wx.Display.GetFromPoint(wx.Point(0, 0))).GetClientArea()
        width, height = self.GetSize()
        self.SetPosition(wx.Point(primary.x + (primary.width - width) // 2,
                                  primary.y + (primary.height - height) // 2))

    def restore_rect(self, settings):
        stored = settings.get('rect')
        if stored and len(stored) == 4:
            rect = wx.Rect(*stored)
            if self.is_rect_visible(rect):
                self.SetRect(rect)
                self.stored_rect = list(stored)
                return
            self.SetSize(rect.GetSize())
        else:
            size = settings.get('size')
            if size and len(size) == 2:
                self.SetSize(wx.Size(size[0], size[1]))

        self.centre_on_primary()
        self.stored_rect = list(self.GetRect())

    def set_icon(self):
        path = get_asset_path('icon', 'icon.ico')
        if os.path.exists(path):
            self.SetIcon(wx.Icon(path, wx.BITMAP_TYPE_ICO))

    def apply_theme(self):
        theme = THEMES[self.theme_name]
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.book.SetBackgroundColour(wx.Colour(theme['bg']))
        self.titlebar.set_theme(theme)
        self.sidemenu.set_theme(theme)
        self.updatebox.set_theme(theme)
        self.dots.set_theme(theme)
        self.carousel.set_theme(theme)

        self.clockbox.apply_theme(theme)
        self.worldbox.apply_theme(theme)
        self.weatherbox.apply_theme(theme)
        self.stopwatchbox.apply_theme(theme)
        self.countdownbox.apply_theme(theme)
        self.settingsbox.apply_theme(theme)

        apply_titlebar_theme(self, theme)
        self.Refresh()

    def on_menu(self):
        self.sidemenu.toggle()

    def on_select(self, index):
        # frozen as in the carousel: a page shown erases first
        self.Freeze()
        try:
            self.book.SetSelection(index)
            self.show_dots(index)
        finally:
            self.Thaw()
        self.on_tick()

    def on_dot(self, index):
        self.carousel.go_to(index)

    def on_carousel(self, index):
        self.sidemenu.set_selection(index)
        self.show_dots(index)
        self.on_tick()

    def show_dots(self, index):
        self.dots.set_current(index)
        shown = self.carousel.count > 1 and index < self.carousel.count
        if self.dots.IsShown() != shown:
            self.dots.Show(shown)
            self.Layout()

    def toggle_maximize(self):
        # a captionless window maximized by Windows overflows by its invisible border
        # and covers the taskbar, so fill the work area by hand
        if self.restore_bounds is not None:
            bounds, self.restore_bounds = self.restore_bounds, None
            self.SetRect(wx.Rect(*bounds))
        else:
            self.restore_bounds = list(self.GetRect())
            index = max(0, wx.Display.GetFromWindow(self))
            work = wx.Display(index).GetClientArea()
            left, top, right, bottom = get_frame_margins(self)
            self.SetRect(wx.Rect(work.x - left, work.y - top,
                                 work.width + left + right,
                                 work.height + top + bottom))
        self.titlebar.set_maximized(self.restore_bounds is not None)

    def on_maximize(self, event):
        if not self.IsMaximized():
            return
        self.Maximize(False)
        if self.restore_bounds is None:
            self.toggle_maximize()

    def on_char(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE and self.sidemenu.is_open():
            self.sidemenu.close()
            return
        event.Skip()

    def on_clock_zone(self, use_utc):
        self.store_settings()

    def is_page_on(self, name):
        return self.boxes[name] in self.shown_pages

    def apply_pages(self):
        cards = self.settingsbox.pages
        names = ['clock'] + [name for name in self.settingsbox.order if cards[name].GetValue()]
        pages = [self.boxes[name] for name in names] + [self.settingsbox]
        if pages == self.shown_pages:
            return
        current = self.book.GetCurrentPage()
        index = pages.index(current) if current in pages else 0
        self.shown_pages = pages
        count = len(names)
        self.Freeze()
        try:
            # a removed page stays a child of the book, shown unless hidden
            while self.book.GetPageCount():
                self.book.RemovePage(0)
            for page in pages + list(self.boxes.values()):
                page.Hide()
            for page in pages:
                self.book.AddPage(page, '')
            self.book.ChangeSelection(index)
            self.sidemenu.items = tuple(PAGES[name] for name in names) + (None, SETTINGS_ITEM)
            # past the separator for the settings
            self.sidemenu.set_selection(index if index < count else index + 1)
            self.sidemenu.place(TitleBar.HEIGHT)
            self.sidemenu.Refresh()
            self.dots.set_count(count)
            self.carousel.set_count(count)
            self.show_dots(index)
        finally:
            self.Thaw()

    def on_settings(self):
        self.apply_pages()
        self.clockbox.set_options(self.settingsbox.use24h.GetValue(),
                                  self.settingsbox.useutc.GetValue(),
                                  self.settingsbox.preset.GetValue(),
                                  self.settingsbox.smooth.GetValue())
        self.worldbox.set_options(self.settingsbox.use24h.GetValue(),
                                  self.settingsbox.offset_choice.GetValue())
        self.weatherbox.set_options(self.settingsbox.use24h.GetValue())

        style = self.GetWindowStyle()
        if self.settingsbox.ontop.GetValue():
            self.SetWindowStyle(style | wx.STAY_ON_TOP)
        else:
            self.SetWindowStyle(style & ~wx.STAY_ON_TOP)

        if self.settingsbox.tray.GetValue() and self.tray is None:
            self.tray = TrayIcon(self)
            self.tray.Bind(wx.adv.EVT_TASKBAR_BALLOON_CLICK, lambda event: self.show_window())
        elif not self.settingsbox.tray.GetValue() and self.tray is not None:
            self.remove_tray()
        self.settingsbox.update_sub_cards()

        self.update_theme()

    def remove_tray(self):
        self.tray.RemoveIcon()
        self.tray.Destroy()
        self.tray = None

    def quit(self):
        self.quitting = True
        self.Close(True)

    def show_window(self):
        if self.IsIconized():
            self.Iconize(False)
        self.Show()
        self.Raise()
        self.SetFocus()

    def hide_window(self):
        if self.restore_bounds is not None:
            self.stored_rect = list(self.restore_bounds)
        elif self.IsIconized() is False and self.IsMaximized() is False:
            self.stored_rect = list(self.GetRect())
        self.store_settings()
        # a second launch may have shown the window behind wx's back
        self.Show(True)
        self.Hide()

    def get_tray_items(self):
        stopwatch, countdown = self.stopwatchbox, self.countdownbox
        items = []
        if self.is_page_on('stopwatch'):
            items += [('Stop stopwatch' if stopwatch.running else 'Start stopwatch',
                       stopwatch.on_start),
                      ('Reset stopwatch',
                       stopwatch.on_reset if stopwatch.get_elapsed() > 0 else None)]
        if self.is_page_on('countdown') and countdown.running:
            items.append(('Pause countdown', countdown.on_start))
        return items

    def update_tray(self):
        lines = []
        if self.is_page_on('stopwatch') and self.stopwatchbox.running:
            lines.append(f'Stopwatch {format_hms(self.stopwatchbox.get_elapsed())}')
        if self.is_page_on('countdown') and self.countdownbox.running:
            remaining = max(0.0, self.countdownbox.deadline - time.perf_counter())
            lines.append(f'Countdown {format_hms(remaining)}')
        self.tray.set_tip('\n'.join(lines))

    def on_check_updates(self):
        self.settingsbox.check_now.set_tone('plain')
        self.settingsbox.check_now.set_description('Checking…')
        self.updater.check(forced=True)

    def get_checked_time(self):
        stamp = time.localtime(self.updater.checked_at)
        return time.strftime('%H:%M' if self.settingsbox.use24h.GetValue() else '%I:%M %p',
                             stamp)

    def on_update_checked(self, release, result, forced):
        # a queued call can arrive after close
        if not self:
            return
        card = self.settingsbox.check_now
        card.set_tone('warn' if result == 'error' else 'plain')
        if result == 'error':
            card.set_description('Could not reach GitHub')
            return
        self.store_settings()
        if result == 'found':
            card.set_description(f'{release["version"]} is available')
            self.show_update(release)
        elif result == 'skipped':
            card.set_description(f'{self.updater.skipped} skipped, '
                                 f'checked at {self.get_checked_time()}')
        else:
            card.set_description(f'Up to date, checked at {self.get_checked_time()}')

    def show_update(self, release):
        # a notice already updating stays as it is
        if self.updatebox.IsShown() and self.updatebox.state == 'busy':
            return
        self.release = release
        self.updatebox.show_release(release)
        if not self.updatebox.IsShown():
            self.updatebox.Show()
            self.Layout()
        if (self.tray is not None and self.settingsbox.tray_notice.enabled
                and self.settingsbox.tray_notice.GetValue() and not self.tray.is_window_shown()):
            self.tray.ShowBalloon(f'{APP_NAME} {release["version"]}',
                                  'A new version is available', 10000, wx.ICON_INFORMATION)

    def hide_update(self):
        self.updatebox.Hide()
        self.Layout()

    def on_update_action(self, key):
        release = self.release
        if key == 'skip':
            self.updater.skipped = release['version']
            self.store_settings()
            self.settingsbox.check_now.set_description(f'{release["version"]} skipped')
            self.hide_update()
        elif key == 'later':
            self.hide_update()
        elif key == 'cancel':
            self.updater.cancel()
        elif release['kind'] == 'page':
            # explorer hands the link to the shell, as the About card does
            subprocess.Popen(['explorer', release['page']])
            self.hide_update()
        else:
            if release['kind'] == 'installer':
                self.updatebox.set_busy('Downloading 0%', 0.0)
            else:
                self.updatebox.set_busy('Updating…')
            self.updater.update(release, self.on_update_progress, self.on_update_done)

    def on_update_progress(self, ratio):
        if not self or self.updatebox.state != 'busy':
            return
        message = f'Downloading {int(ratio * 100)}%'
        if message != self.updatebox.message:
            self.updatebox.set_busy(message, ratio)

    def on_update_done(self, error):
        if not self:
            return
        if error is not None:
            self.updatebox.set_failed(error)
            return
        if self.release['kind'] == 'git':
            try:
                restart_source()
            except OSError:
                self.updatebox.set_failed('Updated, start the app again to use it')
                return
        # the installer replaces the app's files once it is gone
        self.quit()

    @staticmethod
    def resolve_theme(choice):
        if choice == 'auto':
            return 'dark' if is_windows_dark() else 'light'
        return choice if choice in THEMES else 'dark'

    def update_theme(self):
        self.theme_checked = time.monotonic()
        theme_name = self.resolve_theme(self.settingsbox.theme_choice.GetValue())
        accent_name = self.settingsbox.accent_choice.GetValue()
        if theme_name != self.theme_name or accent_name != self.accent_name:
            self.theme_name = theme_name
            self.accent_name = accent_name
            apply_accent(accent_name)
            self.apply_theme()

    def on_size(self, event):
        self.sidemenu.place(TitleBar.HEIGHT)
        event.Skip()

    def on_tick(self):
        # a queued call can arrive after close; a destroyed window is falsy
        if not self:
            return
        self.pacer.pending = False
        page = self.book.GetCurrentPage()
        # covered by the slide: its repaint cost the slide a frame now and then
        if page is not None and not self.carousel.is_sliding():
            page.tick()
        running = getattr(page, 'running', False)
        self.pacer.interval = (RUNNING_INTERVAL if running else TICK_INTERVAL) / 1000

        if (self.settingsbox.theme_choice.GetValue() == 'auto' and
                time.monotonic() - self.theme_checked >= THEME_POLL):
            self.update_theme()

        visible = (not self.settingsbox.autohide.GetValue() or
                   page is self.settingsbox or
                   self.sidemenu.is_open() or
                   self.GetScreenRect().Contains(wx.GetMousePosition()))
        self.titlebar.set_visible(visible)
        self.titlebar.set_menu_open(self.sidemenu.is_open())
        if self.tray is not None:
            self.update_tray()
        self.updater.tick(self.settingsbox.check_updates.GetValue())
        paint_now(self)

    def store_settings(self):
        save_settings({
            'theme': self.settingsbox.theme_choice.GetValue(),
            'on_top': self.settingsbox.ontop.GetValue(),
            'use_24h': self.settingsbox.use24h.GetValue(),
            'use_utc': self.settingsbox.useutc.GetValue(),
            'world_offset': self.settingsbox.offset_choice.GetValue(),
            'clock_zone': 'utc' if self.clockbox.use_utc else 'local',
            'tray_icon': self.settingsbox.tray.GetValue(),
            'close_to_tray': self.settingsbox.close_to_tray.GetValue(),
            'auto_hide_menu': self.settingsbox.autohide.GetValue(),
            'clock_preset': self.settingsbox.preset.GetValue(),
            'smooth_second': self.settingsbox.smooth.GetValue(),
            **{f'page_{key}': card.GetValue() for key, card in self.settingsbox.pages.items()},
            'page_order': list(self.settingsbox.order),
            'accent': self.settingsbox.accent_choice.GetValue(),
            'update_check': self.settingsbox.check_updates.GetValue(),
            'update_tray': self.settingsbox.tray_notice.GetValue(),
            'update_checked_at': self.updater.checked_at,
            'update_skipped': self.updater.skipped,
            'cities': list(self.worldbox.names),
            'home_city': self.worldbox.home,
            'settings_folded': sorted(self.settings_folds),
            'rect': self.stored_rect,
        })

    def on_close(self, event):
        if (self.tray is not None and self.settingsbox.close_to_tray.GetValue()
                and not self.quitting and event.CanVeto()):
            event.Veto()
            self.hide_window()
            return
        self.pacer.running = False
        self.updater.cancel()
        # its filter sees every event: removed before the windows go
        self.carousel.close()
        # close() releases the mouse capture but starts the slide timer, which would
        # fire into the destroyed window (0xc0000374)
        self.sidemenu.close()
        self.sidemenu.timer.Stop()
        # the weather list's scroll bar fades on a timer of its own, the same crash
        self.weatherbox.timer.Stop()
        if self.restore_bounds is not None:
            self.stored_rect = list(self.restore_bounds)
        elif self.IsIconized() is False and self.IsMaximized() is False:
            self.stored_rect = list(self.GetRect())
        self.store_settings()
        # a live tray icon keeps the app running after the frame is gone
        if self.tray is not None:
            self.remove_tray()
        event.Skip()


def launch_mainapp():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    apply_titlebar_theme(frame, THEMES[frame.theme_name])
    app.MainLoop()
