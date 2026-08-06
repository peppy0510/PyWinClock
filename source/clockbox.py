# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import datetime
import math
import wx

from utilities import MAX_DIAL
from utilities import Canvas
from utilities import get_font


WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

# 문자판 위와, 문자판과 시간 사이. 창이 커져도 이보다 벌어지지 않고, 납작해지면
# 여기까지만 좁힌 다음 문자판을 줄인다.
GAP = 28
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
    # 문자판 프리셋. classic 은 원과 숫자가 있는 원래 시계, minimal 은
    # 눈금과 가는 바늘만 배경 위에 남긴다.
    preset = 'classic'
    # 초침이 흐르는지, 한 칸씩 딸깍이는지.
    smooth = True

    NUMERAL_RATIO = 0.125
    RIM_WIDTH = 2

    # minimal 의 눈금. 셋 다 바깥 끝을 맞추고 안쪽 끝만 다르게 둔다.
    TICK_OUTER = 0.97
    TICK_INNER = 0.90
    MAJOR_INNER = 0.83

    def get_numeral_size(self, radius):
        # 문자판 숫자 크기. 아래 디지털 시계가 같은 크기를 쓰려고 꺼내 쓴다.
        # minimal 에는 숫자가 없지만 그래도 이 값을 쓴다 — 프리셋을 바꿔도
        # 아래 글자와 여백이 그대로여야 화면이 흔들리지 않는다.
        return max(8, int(radius * self.NUMERAL_RATIO))

    def set_preset(self, preset, smooth):
        if (preset, smooth) != (self.preset, self.smooth):
            self.preset, self.smooth = preset, smooth
            self.Refresh()

    def get_fractions(self):
        '''세 바늘이 도는 자리. 모두 0~1 이고 아래 자리의 진행이 위로 이어진다.
        딸깍이는 시계는 1/1000 초를 버리기만 하면 된다 — 분·시침도 여기서
        나오므로 초침이 멈춰 있는 동안 함께 멈춘다. 진짜 쿼츠와 같다.'''
        now = self.now or datetime.datetime.now()
        seconds = now.second + (now.microsecond / 1000000 if self.smooth else 0)
        minutes = now.minute + seconds / 60
        hours = now.hour % 12 + minutes / 60
        return hours / 12, minutes / 60, seconds / 60

    def draw(self, gc, width, height):
        cx, cy = width / 2, height / 2
        face = self.radius or min(width, height) / 2
        if self.preset == 'minimal':
            self.draw_minimal(gc, cx, cy, face)
        else:
            self.draw_classic(gc, cx, cy, face)

    def draw_classic(self, gc, cx, cy, face):
        theme = self.theme
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

        hours, minutes, seconds = self.get_fractions()
        self.draw_hand(gc, cx, cy, hours, radius * 0.50, 7, theme['hand'])
        self.draw_hand(gc, cx, cy, minutes, radius * 0.74, 5, theme['hand'])
        self.draw_hand(gc, cx, cy, seconds, radius * 0.84, 2, theme['second'])

        gc.SetPen(wx.Pen(wx.Colour(theme['face']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['second'])))
        gc.DrawEllipse(cx - 5, cy - 5, 10, 10)

    def draw_minimal(self, gc, cx, cy, radius):
        '''문자판도 테두리도 숫자도 없다. 눈금과 굵기가 고른 바늘만 배경 위에
        뜨므로 어느 자리에도 색을 채우지 않는다. 굵기는 모두 반지름에서 뽑는다
        — 창을 줄였을 때 획만 남아 그림이 뭉개지지 않게.'''
        theme = self.theme
        if radius < 30:
            return

        major_width = max(2, round(radius * 0.021))
        for index in range(60):
            major = index % 5 == 0
            angle = math.radians(index * 6)
            outer = radius * self.TICK_OUTER
            inner = radius * (self.MAJOR_INNER if major else self.TICK_INNER)
            gc.SetPen(wx.Pen(wx.Colour(theme['tick_major'] if major else theme['tick']),
                             major_width if major else 1))
            gc.StrokeLine(cx + outer * math.sin(angle), cy - outer * math.cos(angle),
                          cx + inner * math.sin(angle), cy - inner * math.cos(angle))

        hours, minutes, seconds = self.get_fractions()
        # 시·분은 눈금보다 어둡게 둔다. 초침은 1px 이라 안티에일리어싱에 절반을
        # 먹히니, 같은 무게로 보이려면 눈금과 같은 밝기를 줘야 한다.
        self.draw_hand(gc, cx, cy, hours, radius * 0.52,
                       max(2, round(radius * 0.017)), theme['dim'])
        self.draw_hand(gc, cx, cy, minutes, radius * 0.82,
                       max(2, round(radius * 0.014)), theme['dim'])
        self.draw_hand(gc, cx, cy, seconds, radius * 0.70, 1, theme['tick_major'])

        knob = max(3, round(radius * 0.035))
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['numeral'])))
        gc.DrawEllipse(cx - knob, cy - knob, knob * 2, knob * 2)

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
        '''문자판 지름과 글자 크기를 함께 정한다. 글자 크기가 지름에서 나오고
        지름이 다시 글자 높이에서 나오는 순환이라, 배치에 옮기기 전에 여기서
        값이 제자리에 설 때까지 굴린다. 창 크기만 보고 답이 정해지므로 창을
        끄는 동안 값이 진동하지 않는다.

        자리가 모자랄 때와 남을 때가 다르다. 모자라면 세 여백을 똑같이 나눠
        쓰고 문자판을 깎는다. 남으면 문자판도 여백도 더는 키우지 않고, 남는
        만큼을 위아래 바깥 여백으로 돌려 덩어리를 가운데에 세운다.'''
        width, height = self.GetClientSize()
        if width <= 0 or height <= 0:
            return

        size = self.digital_size or 12
        for _ in range(6):
            # 글자 상자 위쪽 빈자리는 여백이 아니라 글자 몫으로 친다.
            block = self.measure_block(size) - self.digital_lead
            floor = max(GAP, self.digital_lead)
            diameter = max(MIN_DIAMETER, min(MAX_DIAL, width - SIDE_GAP * 2,
                                             height - block - floor * 3))
            settled = self.canvas.get_numeral_size(diameter / 2)
            if settled == size:
                break
            size = settled

        room = height - block - diameter
        if room < floor * 3:
            # 남는 자리를 셋으로 똑 떨어지게 나누려고 나머지 1~2px 은 지름에서 뗀다.
            diameter -= -room % 3
            room = height - block - diameter
        gap = max(0, min(floor, room // 3))
        head = gap + max(0, room - gap * 3) // 2
        if self.placed == (diameter, gap, head):
            return

        self.placed = (diameter, gap, head)
        self.canvas.radius = diameter / 2
        self.canvas.SetMinSize(wx.Size(-1, diameter))
        self.head_gap.AssignSpacer(wx.Size(0, head))
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

    def set_options(self, use_24h, use_utc, preset, smooth):
        self.use_24h = use_24h
        self.use_utc = use_utc
        self.canvas.set_preset(preset, smooth)
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
