# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import time
import wx

from controls import FlatButton
from utilities import BUTTON_SIZE
from utilities import CONTROL_GAP
from utilities import CONTROL_HEIGHT
from utilities import PRESET_SIZE
from utilities import TimerCanvas
from utilities import get_font


PRESETS = (60, 180, 300, 600, 1800)
BLINK_INTERVAL = 0.5
WARN_SECONDS = 10


def format_duration(seconds):
    return '%02d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def parse_duration(text):
    parts = text.strip().split(':')
    if not parts or len(parts) > 3:
        return None
    try:
        values = [int(part) for part in parts]
    except ValueError:
        return None
    if any(value < 0 for value in values):
        return None
    while len(values) < 3:
        values.insert(0, 0)
    return values[0] * 3600 + values[1] * 60 + values[2]


class CountdownCanvas(TimerCanvas):

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.total = 0
        self.finished = False
        self.blink = False

    def get_time_colour(self):
        if self.finished:
            return self.theme['second'] if self.blink else self.theme['dim']
        return self.theme['text']

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 16
        if radius < 24:
            return

        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 7))
        path = gc.CreatePath()
        path.AddArc(cx, cy, radius, 0, 6.2831853, True)
        gc.StrokePath(path)

        fraction = self.seconds / self.total if self.total > 0 else 0
        if fraction > 0:
            colour = theme['second'] if self.seconds <= WARN_SECONDS else theme['accent']
            gc.SetPen(wx.Pen(wx.Colour(colour), 7))
            path = gc.CreatePath()
            path.AddArc(cx, cy, radius, -1.5707963,
                        -1.5707963 + 6.2831853 * fraction, True)
            gc.StrokePath(path)

        bottom = self.draw_time(gc, width, height)

        if self.finished:
            size = self.get_time_size(width, height)
            self.draw_centered_text(gc, 'DONE', cx, bottom + size * 0.25,
                                    get_font(max(9, int(size * 0.34)), bold=True),
                                    theme['second'])


class CountdownBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.total = 0
        self.remaining = 0
        self.running = False
        self.deadline = 0.0
        self.finished_at = 0.0

        self.canvas = CountdownCanvas(self, theme)
        # 단일 라인 TextCtrl 은 MSW 에서 높이를 키우면 텍스트가 위로 붙는다.
        # 버튼과 같은 28px 박스를 패널로 만들고 그 안에서 세로 가운데에 둔다.
        self.fieldpanel = wx.Panel(self)
        self.fieldpanel.SetMinSize(wx.Size(-1, CONTROL_HEIGHT))
        self.field = wx.TextCtrl(self.fieldpanel, value='00:05:00',
                                 style=wx.TE_PROCESS_ENTER | wx.NO_BORDER | wx.TE_CENTER)
        self.field.Bind(wx.EVT_TEXT, lambda event: self.on_field())

        inner = wx.BoxSizer(wx.VERTICAL)
        inner.AddStretchSpacer()
        inner.Add(self.field, 0, wx.EXPAND)
        inner.AddStretchSpacer()
        self.fieldpanel.SetSizer(inner)

        self.presets = [FlatButton(self, theme, format_duration(seconds),
                                   self.make_preset(seconds), size=PRESET_SIZE)
                        for seconds in PRESETS]
        self.start_button = FlatButton(self, theme, 'Start', self.on_start, size=BUTTON_SIZE)
        self.reset_button = FlatButton(self, theme, 'Reset', self.on_reset, size=BUTTON_SIZE)
        self.buttons = self.presets + [self.start_button, self.reset_button]

        preset_row = wx.BoxSizer(wx.HORIZONTAL)
        for button in self.presets:
            preset_row.Add(button, 1, wx.EXPAND | wx.ALL, CONTROL_GAP)

        control_row = wx.BoxSizer(wx.HORIZONTAL)
        control_row.Add(self.start_button, 1, wx.EXPAND | wx.ALL, CONTROL_GAP)
        control_row.Add(self.reset_button, 1, wx.EXPAND | wx.ALL, CONTROL_GAP)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 8)
        # 버튼은 행 여백(CONTROL_GAP) 안에서 다시 CONTROL_GAP 을 갖는다.
        # 두 배를 주면 입력창 좌우 끝이 버튼 열과 정확히 맞는다.
        sizer.Add(self.fieldpanel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, CONTROL_GAP * 2)
        sizer.Add(preset_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, CONTROL_GAP)
        sizer.Add(control_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, CONTROL_GAP)
        self.SetSizer(sizer)

        self.apply_theme(theme)
        self.on_field()

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.fieldpanel.SetBackgroundColour(wx.Colour(theme['control']))
        self.field.SetBackgroundColour(wx.Colour(theme['control']))
        self.field.SetForegroundColour(wx.Colour(theme['text']))
        self.field.SetFont(get_font(10))
        for button in self.buttons:
            button.set_theme(theme)
        self.Refresh()

    def make_preset(self, seconds):
        def apply():
            self.field.SetValue(format_duration(seconds))
            self.stop()
        return apply

    def stop(self):
        self.running = False
        self.finished_at = 0.0
        self.start_button.SetLabel('Start')
        self.start_button.set_active(False)

    def on_field(self):
        if self.running:
            return
        seconds = parse_duration(self.field.GetValue())
        self.total = seconds or 0
        self.remaining = self.total
        self.tick()

    def on_start(self):
        if self.running:
            self.remaining = max(0.0, self.deadline - time.perf_counter())
            self.stop()
            return

        if self.remaining <= 0:
            self.on_field()
        if self.remaining <= 0:
            return

        self.deadline = time.perf_counter() + self.remaining
        self.running = True
        self.finished_at = 0.0
        self.start_button.SetLabel('Stop')
        self.start_button.set_active(True)

    def on_reset(self):
        self.stop()
        self.on_field()

    def tick(self):
        if self.running:
            self.remaining = max(0.0, self.deadline - time.perf_counter())
            if self.remaining <= 0:
                self.running = False
                self.finished_at = time.perf_counter()
                self.start_button.SetLabel('Start')
                self.start_button.set_active(False)
                wx.Bell()

        self.canvas.total = self.total
        self.canvas.seconds = self.remaining
        self.canvas.finished = bool(self.finished_at)
        if self.finished_at:
            elapsed = time.perf_counter() - self.finished_at
            self.canvas.blink = int(elapsed / BLINK_INTERVAL) % 2 == 0
        self.canvas.Refresh()
