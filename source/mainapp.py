# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import os
import wx

from clockbox import ClockBox
from countdownbox import CountdownBox
from settingsbox import SettingsBox
from sidemenu import SideMenu
from stopwatchbox import StopwatchBox
from titlebar import TitleBar
from worldbox import WorldBox
from utilities import APP_NAME
from utilities import THEMES
from utilities import apply_clip_siblings
from utilities import apply_no_caption
from utilities import apply_titlebar_theme
from utilities import get_asset_path
from utilities import get_frame_margins
from utilities import load_settings
from utilities import save_settings


TICK_INTERVAL = 50
DEFAULT_SIZE = (440, 640)

# 사이드 메뉴의 차례가 곧 페이지의 차례다. None 은 구분선이라 페이지가 없다.
MENU_ITEMS = (('Clock', 'clock'), ('World', 'globe'), ('Stopwatch', 'stopwatch'),
              ('Countdown', 'countdown'), None, ('Settings', 'settings'))

# 캡션을 떼고 그 자리를 직접 그린다. 크기 조절과 스냅은 그대로 남는다.
FRAME_STYLE = wx.DEFAULT_FRAME_STYLE & ~wx.CAPTION

# 기억된 위치가 이만큼도 화면에 안 걸리면 사라진 모니터로 본다.
MIN_VISIBLE_WIDTH = 120
MIN_VISIBLE_HEIGHT = 32


class MainFrame(wx.Frame):

    stored_rect = None
    # 흉내 낸 최대화 이전의 자리. None 이면 최대화 상태가 아니다.
    restore_bounds = None

    def __init__(self):
        settings = load_settings()
        super().__init__(None, title=APP_NAME, size=wx.Size(*DEFAULT_SIZE),
                         style=FRAME_STYLE)
        apply_no_caption(self)

        self.theme_name = settings.get('theme', 'dark')
        theme = THEMES[self.theme_name]

        self.set_icon()

        self.book = wx.Simplebook(self)
        self.clockbox = ClockBox(self.book, theme)
        self.worldbox = WorldBox(self.book, theme, settings, self.store_settings)
        self.stopwatchbox = StopwatchBox(self.book, theme)
        self.countdownbox = CountdownBox(self.book, theme)
        self.settingsbox = SettingsBox(self.book, theme, settings, self.on_settings)
        for page in (self.clockbox, self.worldbox, self.stopwatchbox,
                     self.countdownbox, self.settingsbox):
            self.book.AddPage(page, '')

        self.titlebar = TitleBar(self, theme, self.on_menu, self.toggle_maximize)
        self.sidemenu = SideMenu(self, theme, MENU_ITEMS, self.on_select)
        # 서랍은 페이지 위에 떠 있다. 페이지 쪽이 형제를 클립해 주어야 살아남는다.
        apply_clip_siblings(self.book)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.titlebar, 0, wx.EXPAND)
        sizer.Add(self.book, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.apply_theme()
        self.on_settings()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_tick)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MAXIMIZE, self.on_maximize)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.timer.Start(TICK_INTERVAL)
        self.on_tick(None)
        self.restore_rect(settings)

    def is_rect_visible(self, rect):
        # 모니터 구성이 바뀌면 기억된 좌표가 아무 화면에도 안 걸릴 수 있다.
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
            # rect 이전 버전은 크기만 저장했다. 그 값이라도 살려 쓴다.
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
        self.book.SetSelection(index)
        self.on_tick(None)

    def toggle_maximize(self):
        '''캡션이 없는 창을 Windows 가 최대화하면 보이지 않는 여백만큼 화면
        밖으로 넘치고 작업 표시줄까지 덮는다. 작업 영역에 맞춰 직접 채운다.'''
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
        # 화면 위로 던지거나 Win+Up 을 눌러도 같은 자리에 오도록 되돌려 잡는다.
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

        theme_name = 'dark' if self.settingsbox.dark.GetValue() else 'light'
        if theme_name != self.theme_name:
            self.theme_name = theme_name
            self.apply_theme()

    def on_size(self, event):
        self.sidemenu.place(TitleBar.HEIGHT)
        event.Skip()

    def on_tick(self, event):
        page = self.book.GetCurrentPage()
        if page is not None:
            page.tick()

        # Auto hide menu 가 켜져 있으면 창에 마우스가 올라와 있을 때만 타이틀바를
        # 보여준다. 설정 페이지와 서랍이 열린 동안은 돌아갈 길을 남겨두려고 계속 보인다.
        visible = (not self.settingsbox.autohide.GetValue() or
                   page is self.settingsbox or
                   self.sidemenu.is_open() or
                   self.GetScreenRect().Contains(wx.GetMousePosition()))
        self.titlebar.set_visible(visible)
        self.titlebar.set_menu_open(self.sidemenu.is_open())

    def store_settings(self):
        save_settings({
            'theme': self.theme_name,
            'on_top': self.settingsbox.ontop.GetValue(),
            'use_24h': self.settingsbox.use24h.GetValue(),
            'use_utc': self.settingsbox.useutc.GetValue(),
            'auto_hide_menu': self.settingsbox.autohide.GetValue(),
            'clock_preset': self.settingsbox.preset.GetValue(),
            'smooth_second': self.settingsbox.smooth.GetValue(),
            'cities': list(self.worldbox.names),
            'home_city': self.worldbox.home,
            'rect': self.stored_rect,
        })

    def on_close(self, event):
        self.timer.Stop()
        # 마우스를 잡은 채로 창이 사라지면 나중에 죽는다. 먼저 놓게 한다.
        self.sidemenu.close()
        # 최소화/최대화 상태의 좌표를 저장하면 다음 실행이 이상해진다.
        if self.restore_bounds is not None:
            self.stored_rect = list(self.restore_bounds)
        elif self.IsIconized() is False and self.IsMaximized() is False:
            self.stored_rect = list(self.GetRect())
        self.store_settings()
        event.Skip()


def launch_mainapp():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    apply_titlebar_theme(frame, THEMES[frame.theme_name])
    app.MainLoop()
