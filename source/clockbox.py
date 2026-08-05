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

# 문자판 위, 문자판과 시간 사이, 시간 아래. 이 셋은 창 크기와 상관없이 늘 같다.
# 창이 납작해지면 여백을 여기까지만 좁히고 그 다음부터 문자판을 줄인다.
MIN_GAP = 28
# 문자판이 창 좌우에 닿지 않게 두는 자리.
SIDE_GAP = 32
MIN_DIAMETER = 80
# 시간 아래 날짜 줄과, UTC 한 쌍 앞에 두는 자리.
DATE_GAP = 2
UTC_GAP = 12


class ClockCanvas(Canvas):

    now = None
    # 부모가 정해 주는 문자판 반지름. 위아래 여백을 같게 두려면 원이 캔버스에
    # 꼭 맞아야 하므로, 캔버스 크기에서 되짚지 않고 받아서 그린다.
    radius = 0

    NUMERAL_RATIO = 0.125
    RIM_WIDTH = 2

    def get_numeral_size(self, radius):
        # 문자판 숫자 크기. 아래 디지털 시계가 같은 크기를 쓰려고 꺼내 쓴다.
        return max(8, int(radius * self.NUMERAL_RATIO))

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        face = self.radius or min(width, height) / 2
        # 테두리 선은 반지름 위에 걸터앉아 절반이 밖으로 번진다. 그만큼 안으로
        # 들여 그려야 원이 캔버스 높이에 꼭 맞는다.
        radius = face - self.RIM_WIDTH / 2
        if radius < 30:
            return

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), self.RIM_WIDTH))
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

        gc.SetFont(get_font(self.get_numeral_size(face), bold=True),
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

    use_24h = True
    use_utc = False
    digital_size = 0
    digital_lead = 0
    # 마지막으로 배치에 옮긴 (지름, 여백). 같은 값이면 다시 재우지 않는다.
    placed = None

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

        # 아래 여백은 남는 자리 그대로다. 위 두 자리를 같은 값으로 두고 지름을
        # 거기에 맞춰 깎으므로, 마지막에 남는 높이가 곧 세 번째 여백이 된다.
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.head_gap = sizer.AddSpacer(0)
        sizer.Add(self.canvas, 0, wx.EXPAND)
        self.face_gap = sizer.AddSpacer(0)
        sizer.Add(self.digital, 0, wx.ALIGN_CENTER)
        sizer.Add(self.datetext, 0, wx.ALIGN_CENTER | wx.TOP, DATE_GAP)
        sizer.Add(self.utc_digital, 0, wx.ALIGN_CENTER | wx.TOP, UTC_GAP)
        sizer.Add(self.utc_datetext, 0, wx.ALIGN_CENTER | wx.TOP, DATE_GAP)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.apply_theme(theme)

    def on_size(self, event):
        self.update_layout()
        event.Skip()

    def measure_block(self, size):
        '''시간 글자 덩어리의 높이. 재려면 글꼴을 입혀 봐야 하므로 재는 김에
        입힌 채로 둔다. 숨긴 UTC 한 쌍은 사이저도 건너뛰니 여기서도 뺀다.'''
        if size != self.digital_size:
            self.digital_size = size
            font = get_font(size, bold=True)
            for text in (self.digital, self.utc_digital):
                text.SetFont(font)
            # 숫자는 글자 상자 위쪽 이만큼을 늘 비워 둔다. 상자끼리 맞추면 눈에는
            # 문자판과 시간 사이만 그만큼 벌어져 보이므로, 그 자리를 되돌려 준다.
            dc = wx.MemoryDC(wx.Bitmap(1, 1))
            dc.SetFont(font)
            self.digital_lead = dc.GetFontMetrics().internalLeading

        block = self.digital.GetBestSize()[1] + DATE_GAP + self.datetext.GetBestSize()[1]
        if self.use_utc:
            block += (UTC_GAP + self.utc_digital.GetBestSize()[1] +
                      DATE_GAP + self.utc_datetext.GetBestSize()[1])
        return block

    def update_layout(self):
        '''세 여백이 늘 같도록 문자판 지름과 글자 크기를 함께 정한다. 글자
        크기가 지름에서 나오고 지름이 다시 글자 높이에서 나오는 순환이라,
        배치에 옮기기 전에 여기서 값이 제자리에 설 때까지 굴린다. 창 크기만
        보고 답이 정해지므로 창을 끄는 동안 값이 진동하지 않는다.'''
        width, height = self.GetClientSize()
        if width <= 0 or height <= 0:
            return

        size = self.digital_size or 12
        for _ in range(6):
            # 글자 상자 위쪽 빈자리는 여백이 아니라 글자 몫으로 친다.
            block = self.measure_block(size) - self.digital_lead
            floor = max(MIN_GAP, self.digital_lead)
            diameter = max(MIN_DIAMETER, min(width - SIDE_GAP * 2,
                                             height - block - floor * 3))
            settled = self.canvas.get_numeral_size(diameter / 2)
            if settled == size:
                break
            size = settled

        # 남는 자리를 셋으로 똑 떨어지게 나누려고 나머지 1~2px 은 지름에서 뗀다.
        diameter -= -(height - block - diameter) % 3
        gap = max(0, (height - block - diameter) // 3)
        if self.placed == (diameter, gap):
            return

        self.placed = (diameter, gap)
        self.canvas.radius = diameter / 2
        self.canvas.SetMinSize(wx.Size(-1, diameter))
        self.head_gap.AssignSpacer(wx.Size(0, gap))
        self.face_gap.AssignSpacer(wx.Size(0, max(0, gap - self.digital_lead)))
        self.Layout()
        self.canvas.Refresh()

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
        # UTC 한 쌍이 드나들면 글자 덩어리 높이가 달라진다. 다시 재우게 한다.
        self.placed = None
        self.update_layout()
        self.tick()

    def format_time(self, now):
        if self.use_24h:
            return now.strftime('%H:%M:%S')
        meridiem = 'AM' if now.hour < 12 else 'PM'
        return '%d:%s %s' % ((now.hour % 12) or 12, now.strftime('%M:%S'), meridiem)

    def format_date(self, now, zone):
        return '%s (%s) · %s' % (
            now.strftime('%Y-%m-%d'), WEEKDAYS[now.weekday()], zone)

    def tick(self):
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
