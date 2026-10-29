# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import os
import threading
import time
import wx

from carousel import Carousel
from carousel import PageDots
from clockbox import ClockBox
from countdownbox import CountdownBox
from settingsbox import SettingsBox
from sidemenu import SideMenu
from stopwatchbox import StopwatchBox
from titlebar import TitleBar
from tray import TrayIcon
from worldbox import WorldBox
from utilities import APP_NAME
from utilities import THEMES
from utilities import apply_clip_siblings
from utilities import apply_no_caption
from utilities import apply_titlebar_theme
from utilities import get_asset_path
from utilities import get_frame_margins
from utilities import is_windows_dark
from utilities import load_settings
from utilities import paint_now
from utilities import save_settings


TICK_INTERVAL = 50
DEFAULT_SIZE = (440, 640)
THEME_POLL = 2.0

MENU_ITEMS = (('Clock', 'clock'), ('World', 'globe'), ('Stopwatch', 'stopwatch'),
              ('Countdown', 'countdown'), None, ('Settings', 'settings'))

FRAME_STYLE = wx.DEFAULT_FRAME_STYLE & ~wx.CAPTION

CAROUSEL_PAGES = 4

MIN_VISIBLE_WIDTH = 120
MIN_VISIBLE_HEIGHT = 32


class Pacer(threading.Thread):
    # WM_TIMER starves while the mouse keeps moving; a thread keeps the beat

    def __init__(self, frame):
        super().__init__(name='tick-pacer', daemon=True)
        self.frame = frame
        self.running = True
        self.pending = False

    def run(self):
        interval = TICK_INTERVAL / 1000
        target = time.perf_counter()
        while self.running:
            target += interval
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

        self.theme_name = self.resolve_theme(settings.get('theme', 'dark'))
        self.theme_checked = time.monotonic()
        theme = THEMES[self.theme_name]

        self.set_icon()

        self.book = wx.Simplebook(self)
        self.clockbox = ClockBox(self.book, theme)
        self.worldbox = WorldBox(self.book, theme, settings, self.store_settings)
        self.stopwatchbox = StopwatchBox(self.book, theme)
        self.countdownbox = CountdownBox(self.book, theme)
        self.settings_folds = set(settings.get('settings_folded', []))
        self.settingsbox = SettingsBox(self.book, theme, settings, self.on_settings,
                                       self.settings_folds, self.store_settings)
        for page in (self.clockbox, self.worldbox, self.stopwatchbox,
                     self.countdownbox, self.settingsbox):
            self.book.AddPage(page, '')

        self.titlebar = TitleBar(self, theme, self.on_menu, self.toggle_maximize)
        self.sidemenu = SideMenu(self, theme, MENU_ITEMS, self.on_select)
        apply_clip_siblings(self.book)
        self.dots = PageDots(self, theme, CAROUSEL_PAGES, self.on_dot)
        self.carousel = Carousel(self, self.book, CAROUSEL_PAGES, self.on_carousel, theme)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.titlebar, 0, wx.EXPAND)
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
        self.dots.set_theme(theme)
        self.carousel.set_theme(theme)

        self.clockbox.apply_theme(theme)
        self.worldbox.apply_theme(theme)
        self.stopwatchbox.apply_theme(theme)
        self.countdownbox.apply_theme(theme)
        self.settingsbox.apply_theme(theme)

        apply_titlebar_theme(self, theme)
        self.Refresh()

    def on_menu(self):
        self.sidemenu.toggle()

    def on_select(self, index):
        # frozen as in the carousel: unfrozen, the new page showed blank first (9 switches in 16)
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
        shown = index < CAROUSEL_PAGES
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

    def on_settings(self):
        self.clockbox.set_options(self.settingsbox.use24h.GetValue(),
                                  self.settingsbox.useutc.GetValue(),
                                  self.settingsbox.preset.GetValue(),
                                  self.settingsbox.smooth.GetValue())
        self.worldbox.set_options(self.settingsbox.use24h.GetValue())

        style = self.GetWindowStyle()
        if self.settingsbox.ontop.GetValue():
            self.SetWindowStyle(style | wx.STAY_ON_TOP)
        else:
            self.SetWindowStyle(style & ~wx.STAY_ON_TOP)

        if self.settingsbox.tray.GetValue() and self.tray is None:
            self.tray = TrayIcon(self)
        elif not self.settingsbox.tray.GetValue() and self.tray is not None:
            self.remove_tray()

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

    @staticmethod
    def resolve_theme(choice):
        if choice == 'auto':
            return 'dark' if is_windows_dark() else 'light'
        return choice if choice in THEMES else 'dark'

    def update_theme(self):
        self.theme_checked = time.monotonic()
        theme_name = self.resolve_theme(self.settingsbox.theme_choice.GetValue())
        if theme_name != self.theme_name:
            self.theme_name = theme_name
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
        if page is not None:
            page.tick()

        if (self.settingsbox.theme_choice.GetValue() == 'auto' and
                time.monotonic() - self.theme_checked >= THEME_POLL):
            self.update_theme()

        visible = (not self.settingsbox.autohide.GetValue() or
                   page is self.settingsbox or
                   self.sidemenu.is_open() or
                   self.GetScreenRect().Contains(wx.GetMousePosition()))
        self.titlebar.set_visible(visible)
        self.titlebar.set_menu_open(self.sidemenu.is_open())
        paint_now(self)

    def store_settings(self):
        save_settings({
            'theme': self.settingsbox.theme_choice.GetValue(),
            'on_top': self.settingsbox.ontop.GetValue(),
            'use_24h': self.settingsbox.use24h.GetValue(),
            'use_utc': self.settingsbox.useutc.GetValue(),
            'tray_icon': self.settingsbox.tray.GetValue(),
            'close_to_tray': self.settingsbox.close_to_tray.GetValue(),
            'auto_hide_menu': self.settingsbox.autohide.GetValue(),
            'clock_preset': self.settingsbox.preset.GetValue(),
            'smooth_second': self.settingsbox.smooth.GetValue(),
            'cities': list(self.worldbox.names),
            'home_city': self.worldbox.home,
            'settings_folded': sorted(self.settings_folds),
            'rect': self.stored_rect,
        })

    def on_close(self, event):
        if (self.tray is not None and self.settingsbox.close_to_tray.GetValue()
                and not self.quitting and event.CanVeto()):
            event.Veto()
            if self.restore_bounds is not None:
                self.stored_rect = list(self.restore_bounds)
            elif self.IsIconized() is False and self.IsMaximized() is False:
                self.stored_rect = list(self.GetRect())
            self.store_settings()
            # a second launch may have shown the window behind wx's back
            self.Show(True)
            self.Hide()
            return
        self.pacer.running = False
        # its filter sees every event: removed before the windows go
        self.carousel.close()
        # close() releases the mouse capture but starts the slide timer, which would
        # fire into the destroyed window (0xc0000374)
        self.sidemenu.close()
        self.sidemenu.timer.Stop()
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
