# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import datetime
import math
import wx

from utilities import Canvas
from utilities import get_font


WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

# 맨 아래 날짜 줄이 창 밑동에 붙지 않게 두는 자리.
BOTTOM_GAP = 40
# 문자판이 헤더에 바로 붙지 않게 위에 두는 자리.
TOP_GAP = 16


class ClockCanvas(Canvas):

    now = None

    NUMERAL_RATIO = 0.135

    def get_numeral_size(self, radius=None):
        # 문자판 숫자 크기. 아래 디지털 시계가 같은 크기를 쓰려고 꺼내 쓴다.
        if radius is None:
            width, height = self.GetClientSize()
            radius = min(width, height) / 2 - 12
        return max(8, int(radius * self.NUMERAL_RATIO))

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 12
        if radius < 30:
            return

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
        gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        for index in range(60):
            major = index % 5 == 0
            angle = math.radians(index * 6)
            outer = radius * 0.94
            inner = radius * (0.84 if major else 0.90)
            colour = theme['tick_major'] if major else theme['tick']
            gc.SetPen(wx.Pen(wx.Colour(colour), 3 if major else 1))
            gc.StrokeLine(cx + outer * math.sin(angle), cy - outer * math.cos(angle),
                          cx + inner * math.sin(angle), cy - inner * math.cos(angle))

        gc.SetFont(get_font(self.get_numeral_size(radius), bold=True),
                   wx.Colour(theme['numeral']))
        for hour in range(1, 13):
            angle = math.radians(hour * 30)
            label = str(hour)
            tw, th = gc.GetTextExtent(label)[:2]
            gc.DrawText(label,
                        cx + radius * 0.70 * math.sin(angle) - tw / 2,
                        cy - radius * 0.70 * math.cos(angle) - th / 2)

        now = self.now or datetime.datetime.now()
        seconds = now.second + now.microsecond / 1000000
        minutes = now.minute + seconds / 60
        hours = now.hour % 12 + minutes / 60

        self.draw_hand(gc, cx, cy, hours / 12, radius * 0.50, 7, theme['hand'])
        self.draw_hand(gc, cx, cy, minutes / 60, radius * 0.74, 5, theme['hand'])
        self.draw_hand(gc, cx, cy, seconds / 60, radius * 0.84, 2, theme['second'])

        gc.SetPen(wx.Pen(wx.Colour(theme['face']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['second'])))
        gc.DrawEllipse(cx - 5, cy - 5, 10, 10)

    def draw_hand(self, gc, cx, cy, fraction, length, width, colour):
        angle = math.radians(fraction * 360)
        tail = length * 0.16
        gc.SetPen(wx.Pen(wx.Colour(colour), width))
        gc.StrokeLine(cx - tail * math.sin(angle), cy + tail * math.cos(angle),
                      cx + length * math.sin(angle), cy - length * math.cos(angle))


class ClockBox(wx.Panel):

    # 캔버스 높이를 패널 높이의 고정 비율로 잡는다. 남은 공간을 캔버스가
    # 먹게 두면 '폰트 -> 텍스트 높이 -> 캔버스 높이 -> 숫자 크기 -> 폰트'
    # 순환이 생겨 특정 창 크기에서 값이 수렴하지 않고 진동한다.
    CANVAS_RATIO = 0.74
    CANVAS_RATIO_UTC = 0.62

    use_24h = True
    use_utc = False
    digital_size = 0

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.canvas = ClockCanvas(self, theme)
        self.digital = wx.StaticText(self, label='')
        self.datetext = wx.StaticText(self, label='')
        self.utc_digital = wx.StaticText(self, label='')
        self.utc_datetext = wx.StaticText(self, label='')

        for text in (self.datetext, self.utc_datetext):
            text.SetFont(get_font(10))
        self.utc_digital.Hide()
        self.utc_datetext.Hide()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(TOP_GAP)
        sizer.Add(self.canvas, 0, wx.EXPAND | wx.ALL, 8)
        sizer.AddStretchSpacer()
        sizer.Add(self.digital, 0, wx.ALIGN_CENTER)
        sizer.Add(self.datetext, 0, wx.ALIGN_CENTER | wx.TOP, 2)
        sizer.Add(self.utc_digital, 0, wx.ALIGN_CENTER | wx.TOP, 12)
        sizer.Add(self.utc_datetext, 0, wx.ALIGN_CENTER | wx.TOP, 2)
        sizer.AddSpacer(BOTTOM_GAP)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.apply_theme(theme)

    def on_size(self, event):
        self.update_canvas_height()
        event.Skip()

    def update_canvas_height(self):
        height = self.GetClientSize()[1]
        if height <= 0:
            return
        ratio = self.CANVAS_RATIO_UTC if self.use_utc else self.CANVAS_RATIO
        target = max(60, int(height * ratio))
        if self.canvas.GetMinSize()[1] != target:
            self.canvas.SetMinSize(wx.Size(-1, target))
            self.Layout()

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        for text in (self.digital, self.utc_digital):
            text.SetForegroundColour(wx.Colour(theme['text']))
        for text in (self.datetext, self.utc_datetext):
            text.SetForegroundColour(wx.Colour(theme['dim']))
        self.Refresh()

    def set_options(self, use_24h, use_utc):
        self.use_24h = use_24h
        self.use_utc = use_utc
        self.utc_digital.Show(use_utc)
        self.utc_datetext.Show(use_utc)
        self.update_canvas_height()
        self.tick()

    def update_digital_font(self):
        # 문자판 숫자와 같은 크기를 쓴다. 창 크기가 바뀌면 따라 움직인다.
        size = self.canvas.get_numeral_size()
        if size == self.digital_size:
            return
        self.digital_size = size
        for text in (self.digital, self.utc_digital):
            text.SetFont(get_font(size, bold=True))

    def format_time(self, now):
        if self.use_24h:
            return now.strftime('%H:%M:%S')
        meridiem = 'AM' if now.hour < 12 else 'PM'
        return '%d:%s %s' % ((now.hour % 12) or 12, now.strftime('%M:%S'), meridiem)

    def format_date(self, now, zone):
        return '%s (%s) · %s' % (
            now.strftime('%Y-%m-%d'), WEEKDAYS[now.weekday()], zone)

    def tick(self):
        self.update_digital_font()
        utc = datetime.datetime.now(datetime.timezone.utc)
        local = utc.astimezone()
        offset = local.strftime('%z')

        self.digital.SetLabel(self.format_time(local))
        self.datetext.SetLabel(
            self.format_date(local, 'UTC%s:%s' % (offset[:3], offset[3:])))

        # UTC 는 로컬을 대체하지 않고 한 쌍을 더 붙인다. 시계바늘은 로컬을 따른다.
        if self.use_utc:
            self.utc_digital.SetLabel(self.format_time(utc))
            self.utc_datetext.SetLabel(self.format_date(utc, 'UTC'))

        self.canvas.now = local
        self.Layout()
        self.canvas.Refresh()
