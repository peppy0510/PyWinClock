# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import datetime
import math
import wx

from controls import Pressable
from panels import draw_button
from panels import get_button_width
from utilities import BUTTON_GAP
from utilities import BUTTON_HEIGHT
from utilities import MAX_DIAL
from utilities import Canvas
from utilities import get_font


WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

GAP = 28
SIDE_GAP = 32
MIN_DIAMETER = 80
DATE_GAP = 2
SWITCH_GAP = 14


class ClockCanvas(Canvas):

    now = None
    radius = 0
    preset = 'classic'
    smooth = True
    face_key = None
    face_bitmap = None

    NUMERAL_RATIO = 0.125
    RIM_WIDTH = 2

    TICK_OUTER = 0.97
    TICK_INNER = 0.90
    MAJOR_INNER = 0.83

    def get_numeral_size(self, radius):
        # minimal draws no numerals but keeps this size so the text below does not jump
        return max(8, int(radius * self.NUMERAL_RATIO))

    def set_theme(self, theme):
        self.face_key = None
        super().set_theme(theme)

    def set_preset(self, preset, smooth):
        if (preset, smooth) != (self.preset, self.smooth):
            self.preset, self.smooth = preset, smooth
            self.face_key = None
            self.Refresh()

    def get_fractions(self):
        now = self.now or datetime.datetime.now()
        seconds = now.second + (now.microsecond / 1000000 if self.smooth else 0)
        minutes = now.minute + seconds / 60
        hours = now.hour % 12 + minutes / 60
        return hours / 12, minutes / 60, seconds / 60

    def get_background(self, width, height):
        face = self.radius or min(width, height) / 2
        if not self.has_face(face) or width <= 0 or height <= 0:
            return None
        key = (width, height, face)
        if key != self.face_key:
            cx, cy = width / 2, height / 2
            bitmap = wx.Bitmap(width, height, 24)
            dc = wx.MemoryDC(bitmap)
            dc.SetBackground(wx.Brush(wx.Colour(self.theme['bg'])))
            dc.Clear()
            gc = wx.GraphicsContext.Create(dc)
            gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
            if self.preset == 'minimal':
                self.draw_minimal_dial(gc, cx, cy, face)
            else:
                self.draw_classic_dial(gc, cx, cy, face)
            del gc
            dc.SelectObject(wx.NullBitmap)
            self.face_key, self.face_bitmap = key, bitmap
        return self.face_bitmap

    def has_face(self, face):
        if self.preset == 'minimal':
            return face >= 30
        return face - self.RIM_WIDTH / 2 >= 30

    def draw(self, gc, width, height):
        cx, cy = width / 2, height / 2
        face = self.radius or min(width, height) / 2
        if not self.has_face(face):
            return
        if self.preset == 'minimal':
            self.draw_minimal_hands(gc, cx, cy, face)
        else:
            self.draw_classic_hands(gc, cx, cy, face)

    def draw_classic_dial(self, gc, cx, cy, face):
        theme = self.theme
        # the rim pen straddles the radius, inset it so the circle fits the canvas height
        radius = face - self.RIM_WIDTH / 2

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

    def draw_classic_hands(self, gc, cx, cy, face):
        theme = self.theme
        radius = face - self.RIM_WIDTH / 2
        hours, minutes, seconds = self.get_fractions()
        self.draw_hand(gc, cx, cy, hours, radius * 0.50, 7, theme['hand'])
        self.draw_hand(gc, cx, cy, minutes, radius * 0.74, 5, theme['hand'])
        self.draw_hand(gc, cx, cy, seconds, radius * 0.84, 2, theme['second'])

        gc.SetPen(wx.Pen(wx.Colour(theme['face']), 2))
        gc.SetBrush(wx.Brush(wx.Colour(theme['second'])))
        gc.DrawEllipse(cx - 5, cy - 5, 10, 10)

    def draw_minimal_dial(self, gc, cx, cy, radius):
        theme = self.theme
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

    def draw_minimal_hands(self, gc, cx, cy, radius):
        theme = self.theme
        hours, minutes, seconds = self.get_fractions()
        self.draw_hand(gc, cx, cy, hours, radius * 0.52,
                       max(2, round(radius * 0.017)), theme['dim'])
        self.draw_hand(gc, cx, cy, minutes, radius * 0.82,
                       max(2, round(radius * 0.014)), theme['dim'])
        # a 1px diagonal loses half its weight to antialiasing, so it gets the tick colour
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


class ZoneSwitch(Pressable):

    '''Local or UTC, the time the page shows'''

    OPTIONS = (('local', 'Local'), ('utc', 'UTC'))

    def __init__(self, parent, theme, on_change):
        super().__init__(parent, theme, self.activate)
        self.on_change = on_change
        self.value = 'local'
        self.marked = -1
        self.down_index = -1
        self.segment = max(get_button_width(name) for _, name in self.OPTIONS)
        count = len(self.OPTIONS)
        self.SetMinSize(wx.Size(self.segment * count + BUTTON_GAP * (count - 1), BUTTON_HEIGHT))

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        if value != self.value:
            self.value = value
            self.Refresh()

    def get_cell(self, index):
        return wx.Rect((self.segment + BUTTON_GAP) * index, 0, self.segment, BUTTON_HEIGHT)

    def get_index(self, position):
        for index in range(len(self.OPTIONS)):
            if self.get_cell(index).Contains(position):
                return index
        return -1

    def hits(self, position):
        return self.get_index(position) >= 0

    def on_track(self, event):
        index = self.get_index(event.GetPosition())
        if index != self.marked:
            self.marked = index
            self.Refresh()
        super().on_track(event)

    def on_down(self, event):
        self.down_index = self.get_index(event.GetPosition())
        super().on_down(event)

    def on_leave(self, event):
        if self.marked != -1:
            self.marked = -1
            self.Refresh()
        super().on_leave(event)

    def activate(self):
        index = self.get_index(self.up_position)
        if index < 0 or index != self.down_index or self.OPTIONS[index][0] == self.value:
            return
        self.value = self.OPTIONS[index][0]
        self.Refresh()
        self.on_change()

    def draw(self, gc, width, height):
        for index, (value, name) in enumerate(self.OPTIONS):
            if value == self.value:
                state = 'lit'
            elif self.pressed and index == self.down_index and index == self.marked:
                state = 'down'
            elif index == self.marked:
                state = 'hover'
            else:
                state = 'plain'
            draw_button(gc, self.theme, self.get_cell(index), name, state)


class ClockBox(wx.Panel):

    use_24h = True
    # use_utc: the switch's pick; utc_offered: the setting that shows the switch at all
    use_utc = False
    utc_offered = False
    digital_size = 0
    digital_lead = 0
    placed = None

    def __init__(self, parent, theme, on_zone=None):
        super().__init__(parent)
        self.on_zone = on_zone
        self.canvas = ClockCanvas(self, theme)
        self.digital = wx.StaticText(self, label='')
        self.datetext = wx.StaticText(self, label='')
        self.datetext.SetFont(get_font(10))
        self.zone = ZoneSwitch(self, theme, self.on_switch)

        # the dial, one time under it and its zone picked below, centred on the page as one
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.head_gap = sizer.AddSpacer(0)
        sizer.Add(self.canvas, 0, wx.EXPAND)
        self.face_gap = sizer.AddSpacer(0)
        sizer.Add(self.digital, 0, wx.ALIGN_CENTER)
        sizer.Add(self.datetext, 0, wx.ALIGN_CENTER | wx.TOP, DATE_GAP)
        sizer.Add(self.zone, 0, wx.ALIGN_CENTER | wx.TOP, SWITCH_GAP)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.apply_theme(theme)

    def on_size(self, event):
        self.update_layout()
        event.Skip()

    def on_switch(self):
        self.use_utc = self.zone.GetValue() == 'utc'
        self.tick()
        if self.on_zone:
            self.on_zone(self.use_utc)

    def measure_block(self, size):
        if size != self.digital_size:
            self.digital_size = size
            self.digital.SetFont(get_font(size, bold=True))
            dc = wx.MemoryDC(wx.Bitmap(1, 1))
            dc.SetFont(get_font(size, bold=True))
            self.digital_lead = dc.GetFontMetrics().internalLeading
        block = self.digital.GetBestSize()[1] + DATE_GAP + self.datetext.GetBestSize()[1]
        if self.utc_offered:
            block += SWITCH_GAP + self.zone.GetMinSize()[1]
        return block

    def update_layout(self):
        # numeral size follows the diameter and the diameter follows the text height,
        # so iterate until it settles instead of letting the sizer oscillate
        width, height = self.GetClientSize()
        if width <= 0 or height <= 0:
            return

        size = self.digital_size or 12
        for _ in range(6):
            block = self.measure_block(size) - self.digital_lead
            floor = max(GAP, self.digital_lead)
            diameter = max(MIN_DIAMETER, min(MAX_DIAL, width - SIDE_GAP * 2,
                                             height - block - floor * 3))
            settled = self.canvas.get_numeral_size(diameter / 2)
            if settled == size:
                break
            size = settled

        gap = max(0, min(floor, (height - diameter - block) // 3))
        head = max(0, (height - diameter - gap - block) // 2)
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
        self.zone.set_theme(theme)
        self.digital.SetForegroundColour(wx.Colour(theme['text']))
        self.datetext.SetForegroundColour(wx.Colour(theme['dim']))
        self.Refresh()

    def set_options(self, use_24h, utc_offered, preset, smooth):
        self.use_24h = use_24h
        self.utc_offered = utc_offered
        self.canvas.set_preset(preset, smooth)
        self.zone.SetValue('utc' if self.use_utc else 'local')
        self.zone.Show(utc_offered)
        self.placed = None
        self.update_layout()
        self.tick()

    def format_time(self, now):
        if self.use_24h:
            return now.strftime('%H:%M:%S')
        meridiem = 'AM' if now.hour < 12 else 'PM'
        return f'{int((now.hour % 12) or 12)}:{now.strftime("%M:%S")} {meridiem}'

    def format_date(self, now, zone):
        return f'{now.strftime("%Y-%m-%d")} ({WEEKDAYS[now.weekday()]}) · {zone}'

    def tick(self):
        if self.GetTopLevelParent().IsIconized():
            return
        utc = datetime.datetime.now(datetime.timezone.utc)
        local = utc.astimezone()
        offset = local.strftime('%z')

        shows_utc = self.use_utc and self.utc_offered
        now = utc if shows_utc else local
        zone = 'UTC' if shows_utc else f'UTC{offset[:3]}:{offset[3:]}'
        labels = [(self.digital, self.format_time(now)),
                  (self.datetext, self.format_date(now, zone))]

        changed = False
        for text, label in labels:
            if text.GetLabel() != label:
                text.SetLabel(label)
                changed = True

        self.canvas.now = now
        if changed:
            self.Layout()
        if changed or self.canvas.smooth:
            self.canvas.Refresh()
