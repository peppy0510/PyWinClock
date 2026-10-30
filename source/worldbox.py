# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import json
import math
import os
import time
import wx

from datetime import datetime
from datetime import timezone
from zoneinfo import ZoneInfo

from cities import CITIES
from cities import CITY_BY_NAME
from controls import RoundButton
from icons import draw_glyph
from utilities import CARD_RADIUS
from utilities import Canvas
from utilities import draw_card_rim
from utilities import draw_text_in
from utilities import get_font
from utilities import get_ink
from utilities import shade


DEFAULT_CITIES = ('Honolulu', 'Los Angeles', 'New York', 'UTC', 'Dubai')
LOCAL = 'Local time'

LAT_TOP = 78.0
LAT_BOTTOM = -56.0
ASPECT = 360.0 / (LAT_TOP - LAT_BOTTOM)

ROW_HEIGHT = 52
ROW_GAP = 0
ROW_STRIDE = ROW_HEIGHT + ROW_GAP
MARGIN = 14
# the map and the list stop growing here and stay centred, as the other pages' dial
COLUMN_WIDTH = 400
ADD_SIZE = 36
PHASE_WIDTH = 24
NAME_GAP = 12
LINE_GAP = 6

TWILIGHT = 16.0
TOOLBOX_INSET = 8
ROW_INSET = 4


def get_land():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'assets', 'map', 'land.json')
    try:
        with open(path, encoding='utf-8') as file:
            data = json.load(file)
    except Exception:
        return []

    scale = float(data.get('scale', 1))
    return [[(ring[index] / scale, ring[index + 1] / scale)
             for index in range(0, len(ring), 2)] for ring in data.get('rings', ())]


def get_sun_position(moment):
    # low-precision solar position, plenty for a display that changes once a minute
    day = moment.timetuple().tm_yday + moment.hour / 24.0
    angle = math.radians(360.0 / 365.24 * (day + 10))
    declination = -math.asin(0.39779 * math.cos(angle))
    seconds = moment.hour * 3600 + moment.minute * 60 + moment.second
    longitude = 180.0 - seconds / 240.0
    return math.degrees(declination), (longitude + 180) % 360 - 180


def get_sun_elevation(latitude, longitude, declination, sun_longitude):
    hour_angle = math.radians(longitude - sun_longitude)
    return (math.sin(math.radians(latitude)) * math.sin(math.radians(declination)) +
            math.cos(math.radians(latitude)) * math.cos(math.radians(declination)) *
            math.cos(hour_angle))


def is_daylight(latitude, longitude, declination, sun_longitude):
    return get_sun_elevation(latitude, longitude, declination, sun_longitude) > 0


def draw_city_text(gc, theme, row, left, right, top, height, fill, time_size, colour=None):
    colour = colour or theme['text']
    time_font = get_font(time_size, bold=True)
    # the digits' ClearType fringe ran a pixel past the dividers
    draw_text_in(gc, row['time'], wx.Rect(0, int(top), right - 1, height), time_font, colour,
                 align='right', back=fill)
    gc.SetFont(time_font, wx.Colour(colour))
    time_width = gc.GetTextExtent(row['time'])[0]

    limit = max(0, right - time_width - NAME_GAP - left)
    name_font, note_font = get_font(10), get_font(8)
    name_ink, note_ink = get_ink(name_font), get_ink(note_font)
    name_height = name_ink[1] - name_ink[0] + 1
    note_height = note_ink[1] - note_ink[0] + 1
    block_top = int(round(top + (height - name_height - LINE_GAP - note_height) / 2))
    gc.SetFont(name_font, wx.Colour(colour))
    gc.DrawText(fit_text(gc, row['label'], limit), left, block_top - name_ink[0])
    gc.SetFont(note_font, wx.Colour(theme['dim']))
    gc.DrawText(fit_text(gc, row['detail'], limit), left,
                block_top + name_height + LINE_GAP - note_ink[0])


def fit_text(gc, text, limit):
    if gc.GetTextExtent(text)[0] <= limit:
        return text
    while text and gc.GetTextExtent(text + '\u2026')[0] > limit:
        text = text[:-1]
    return text + '\u2026'


def draw_row_divider(gc, theme, width, top):
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(theme['rim'])))
    gc.DrawRectangle(MARGIN, top, width - MARGIN * 2, 1)


def draw_row_light(gc, theme, width, top, height):
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(theme['control'])))
    gc.DrawRoundedRectangle(ROW_INSET, top + ROW_INSET, width - ROW_INSET * 2,
                            height - ROW_INSET * 2, CARD_RADIUS - 2)
    return theme['control']


class WorldMap(Canvas):

    GRID = 128
    PIN_RADIUS = 3.5
    PIN_REACH = 12

    def __init__(self, parent, theme, on_hover=None, on_reveal=None):
        super().__init__(parent, theme)
        self.land = get_land()
        self.pins = []
        self.moment = datetime.now(timezone.utc)
        self.base = None
        self.base_key = None
        self.on_hover = on_hover
        self.on_reveal = on_reveal
        self.hovered = -1
        self.active = -1
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)

    def set_pins(self, pins):
        self.pins = pins
        self.Refresh()

    def set_active(self, index):
        if index != self.active:
            self.active = index
            self.Refresh()

    def hit_test(self, x, y):
        width, height = self.GetClientSize()
        found, nearest = -1, self.PIN_REACH
        for longitude, latitude, row in self.pins:
            px, py = self.project(longitude, latitude, width, height)
            span = math.hypot(px - x, py - y)
            if span < nearest:
                found, nearest = row, span
        return found

    def on_motion(self, event):
        self.report(self.hit_test(*event.GetPosition()))

    def on_leave(self, event):
        self.report(-1)

    def on_dclick(self, event):
        index = self.hit_test(*event.GetPosition())
        if index >= 0 and self.on_reveal:
            self.on_reveal(index)

    def report(self, index):
        if index == self.hovered:
            return
        self.hovered = index
        self.Refresh()
        if self.on_hover:
            self.on_hover(index)

    def project(self, longitude, latitude, width, height):
        return ((longitude + 180) / 360.0 * width,
                (LAT_TOP - latitude) / (LAT_TOP - LAT_BOTTOM) * height)

    def draw(self, gc, width, height):
        if width <= 0 or height <= 0:
            return
        gc.DrawBitmap(self.get_base(width, height), 0, 0, width, height)

        lit = [pin for pin in self.pins if pin[2] in (self.hovered, self.active)]
        for longitude, latitude, row in [pin for pin in self.pins if pin not in lit] + lit:
            x, y = self.project(longitude, latitude, width, height)
            self.draw_pin(gc, x, y, row in (self.hovered, self.active))

        self.draw_card_edge(gc, width, height)

    def draw_card_edge(self, gc, width, height):
        theme = self.theme
        path = gc.CreatePath()
        path.AddRectangle(0, 0, width, height)
        path.AddRoundedRectangle(0, 0, width, height, CARD_RADIUS)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['bg'])))
        gc.FillPath(path, wx.ODDEVEN_RULE)

        draw_card_rim(gc, theme['rim'], 0, 0, width, height)

    def get_base(self, width, height):
        theme = self.theme
        key = (width, height, self.moment, theme['map_sea'], theme['map_land'],
               theme['map_night'], theme['map_night_alpha'])
        if self.base_key != key:
            bitmap = wx.Bitmap(width, height, 24)
            dc = wx.MemoryDC(bitmap)
            dc.SetBackground(wx.Brush(wx.Colour(theme['bg'])))
            dc.Clear()
            gc = wx.GraphicsContext.Create(dc)
            gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(theme['map_sea'])))
            gc.DrawRectangle(0, 0, width, height)

            gc.SetBrush(wx.Brush(wx.Colour(theme['map_land'])))
            for ring in self.land:
                path = gc.CreatePath()
                for index, (longitude, latitude) in enumerate(ring):
                    x, y = self.project(longitude, latitude, width, height)
                    if index:
                        path.AddLineToPoint(x, y)
                    else:
                        path.MoveToPoint(x, y)
                path.CloseSubpath()
                gc.FillPath(path)

            gc.DrawBitmap(self.make_night(width, height), 0, 0, width, height)
            del gc
            dc.SelectObject(wx.NullBitmap)
            self.base_key, self.base = key, bitmap
        return self.base

    def make_night(self, width, height):
        columns = self.GRID
        rows = max(2, round(columns / ASPECT))
        declination, sun_longitude = get_sun_position(self.moment)
        limit = math.sin(math.radians(TWILIGHT))
        strength = self.theme['map_night_alpha']

        alpha = bytearray(columns * rows)
        for row in range(rows):
            latitude = LAT_TOP - (row + 0.5) / rows * (LAT_TOP - LAT_BOTTOM)
            for column in range(columns):
                longitude = (column + 0.5) / columns * 360.0 - 180.0
                elevation = get_sun_elevation(latitude, longitude, declination, sun_longitude)
                ratio = min(1.0, max(0.0, (elevation + limit) / (limit * 2)))
                day = ratio * ratio * (3 - 2 * ratio)
                alpha[row * columns + column] = int(255 * strength * (1 - day))

        glow = wx.Colour(self.theme['map_night'])
        image = wx.Image(columns, rows)
        image.SetData(bytes((glow.Red(), glow.Green(), glow.Blue())) * (columns * rows))
        image.SetAlpha(bytes(alpha))
        image.Rescale(max(1, width), max(1, height), wx.IMAGE_QUALITY_BILINEAR)
        return image.ConvertToBitmap()

    def draw_pin(self, gc, x, y, active):
        theme = self.theme
        radius = self.PIN_RADIUS
        gc.SetPen(wx.TRANSPARENT_PEN)
        if active:
            ring = wx.Colour(theme['accent'])
            gc.SetBrush(wx.Brush(wx.Colour(ring.Red(), ring.Green(), ring.Blue(), 90)))
            gc.DrawEllipse(x - radius * 3, y - radius * 3, radius * 6, radius * 6)
        edge = radius + 1.5
        gc.SetBrush(wx.Brush(wx.Colour(theme['pin_edge'])))
        gc.DrawEllipse(x - edge, y - edge, edge * 2, edge * 2)
        gc.SetBrush(wx.Brush(wx.Colour(theme['accent'] if active else theme['pin'])))
        gc.DrawEllipse(x - radius, y - radius, radius * 2, radius * 2)


class CityList(Canvas):

    CLOSE_SIZE = 22
    BUTTON_SIZE = 24
    BUTTON_RADIUS = 6

    STEP = 16
    SCROLL_EASING = 0.28
    HOLD = 0.7
    FADE_EASING = 0.22

    def __init__(self, parent, theme, on_remove, on_home=None, on_hover=None):
        super().__init__(parent, theme)
        self.on_remove = on_remove
        self.on_home = on_home
        self.on_hover = on_hover
        self.rows = []
        self.offset = 0
        self.scroll = 0.0
        self.fade = 0.0
        self.hold_until = 0.0
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_animate)
        self.hovered = -1
        self.active = -1
        self.on_button = -1
        self.editing = False
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def set_rows(self, rows):
        self.rows = rows
        self.offset = min(self.offset, max(0, len(rows) - self.get_visible_count()))
        if not self.timer.IsRunning():
            self.scroll = float(self.offset * ROW_STRIDE)
        self.Refresh()

    def on_size(self, event):
        # grown taller, rows scrolled away while it was small fit again
        limit = max(0, len(self.rows) - self.get_visible_count())
        if self.offset > limit:
            self.offset = limit
            self.scroll = float(limit * ROW_STRIDE)
        event.Skip()

    def set_editing(self, editing):
        if editing != self.editing:
            self.editing = editing
            self.Refresh()

    def set_active(self, index):
        if index != self.active:
            self.active = index
            self.Refresh()

    def get_view_height(self):
        height = self.GetClientSize()[1]
        total = len(self.rows) * ROW_STRIDE
        if total <= height:
            return total
        return max(1, height // ROW_STRIDE) * ROW_STRIDE

    def get_visible_count(self):
        return max(1, self.get_view_height() // ROW_STRIDE)

    def get_row_top(self, index):
        return index * ROW_STRIDE - self.scroll

    def hit_test(self, y):
        if not 0 <= y < self.get_view_height():
            return -1
        index = int((y + self.scroll) // ROW_STRIDE)
        return index if 0 <= index < len(self.rows) else -1

    def get_button_rect(self, width, top):
        size = self.BUTTON_SIZE
        return wx.Rect(round(width - MARGIN + 4 - size),
                       round(top + (ROW_HEIGHT - size) / 2), size, size)

    def hit_button(self, x, y):
        index = self.hit_test(y)
        if index < 0 or not self.editing:
            return -1
        rect = self.get_button_rect(self.GetClientSize()[0], self.get_row_top(index))
        return index if rect.Contains(wx.Point(x, y)) else -1

    def on_wheel(self, event):
        limit = max(0, len(self.rows) - self.get_visible_count())
        offset = min(limit, max(0, self.offset - (1 if event.GetWheelRotation() > 0 else -1)))
        if offset != self.offset:
            self.offset = offset
            self.show_scrollbar()

    def reveal(self, index):
        if not 0 <= index < len(self.rows):
            return
        count = self.get_visible_count()
        offset = self.offset
        if index < offset:
            offset = index
        elif index >= offset + count:
            offset = index - count + 1
        offset = min(max(0, len(self.rows) - count), max(0, offset))
        if offset != self.offset:
            self.offset = offset
            self.show_scrollbar()

    def show_scrollbar(self):
        self.fade = 1.0
        self.hold_until = time.monotonic() + self.HOLD
        if not self.timer.IsRunning():
            self.timer.Start(self.STEP)
        self.Refresh()

    def on_animate(self, event):
        target = self.offset * ROW_STRIDE
        if abs(target - self.scroll) > 0.5:
            self.scroll += (target - self.scroll) * self.SCROLL_EASING
        else:
            self.scroll = float(target)

        if self.fade and time.monotonic() >= self.hold_until:
            self.fade -= self.fade * self.FADE_EASING
            if self.fade < 0.02:
                self.fade = 0.0

        if self.scroll == target and not self.fade:
            self.timer.Stop()
        self.Refresh()

    def on_motion(self, event):
        x, y = event.GetPosition()
        button = self.hit_button(x, y)
        if button != self.on_button:
            self.on_button = button
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND if button >= 0 else wx.CURSOR_ARROW))
            self.Refresh()
        self.report(self.hit_test(y))

    def on_leave(self, event):
        if self.on_button != -1:
            self.on_button = -1
            self.Refresh()
        self.report(-1)

    def report(self, index):
        if index == self.hovered:
            return
        self.hovered = index
        self.Refresh()
        if self.on_hover:
            self.on_hover(index)

    def on_up(self, event):
        index = self.hit_button(*event.GetPosition())
        if index < 0:
            return
        if self.rows[index]['fixed']:
            if self.on_home:
                self.on_home()
        else:
            self.on_remove(self.rows[index]['name'])

    def draw(self, gc, width, height):
        theme = self.theme
        view = self.get_view_height()
        if not view:
            return
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
        gc.DrawRoundedRectangle(0, 0, width, view, CARD_RADIUS)

        gc.Clip(0, 0, width, view)
        for index in range(len(self.rows)):
            top = self.get_row_top(index)
            if top >= view:
                break
            if top + ROW_HEIGHT > 0:
                self.draw_row(gc, self.rows[index], index, width, top)
        gc.ResetClip()

        draw_card_rim(gc, theme['rim'], 0, 0, width, view)
        if self.fade and self.get_content_height() > view:
            self.draw_scrollbar(gc, width, view)

    def get_content_height(self):
        return max(0, len(self.rows) * ROW_STRIDE - ROW_GAP)

    def draw_scrollbar(self, gc, width, height):
        total = self.get_content_height()
        span = max(20, height * height / total)
        top = (height - span) * min(1.0, max(0.0, self.scroll / (total - height)))
        rim = wx.Colour(self.theme['rim'])
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(rim.Red(), rim.Green(), rim.Blue(),
                                       round(255 * self.fade))))
        gc.DrawRoundedRectangle(width - 6, top, 3, span, 1.5)

    def draw_row(self, gc, row, index, width, top):
        theme = self.theme
        fill = theme['face']
        if index:
            draw_row_divider(gc, theme, width, top)
        if index in (self.hovered, self.active):
            fill = draw_row_light(gc, theme, width, top, ROW_HEIGHT)

        middle = top + ROW_HEIGHT / 2
        self.draw_phase(gc, MARGIN + PHASE_WIDTH / 2, middle, row['daylight'], fill)

        right = width - MARGIN
        if self.editing:
            right = self.get_button_rect(width, top).x - NAME_GAP
        draw_city_text(gc, theme, row, MARGIN + PHASE_WIDTH + NAME_GAP, right, top, ROW_HEIGHT,
                       fill, 15)

        if self.editing:
            self.draw_button(gc, row, index, width, top)

    def draw_button(self, gc, row, index, width, top):
        theme = self.theme
        rect = self.get_button_rect(width, top)
        if index == self.on_button:
            grey = wx.Colour(theme['tick'])
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(grey.Red(), grey.Green(), grey.Blue(), 64)))
            gc.DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height,
                                    self.BUTTON_RADIUS)

        cx, cy = rect.x + rect.width / 2, rect.y + rect.height / 2
        colour = theme['text'] if index == self.on_button else theme['dim']
        if row['fixed']:
            draw_glyph(gc, 'home', cx, cy, 13, colour, 1.6)
        else:
            self.draw_close(gc, cx, cy, colour, 4.5)

    def draw_phase(self, gc, cx, cy, daylight, fill):
        theme = self.theme
        colour = wx.Colour(theme['text'] if daylight else theme['dim'])
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(colour))

        if daylight:
            gc.DrawEllipse(cx - 5, cy - 5, 10, 10)
            gc.SetPen(wx.Pen(colour, 1))
            for step in range(8):
                angle = math.radians(step * 45)
                dx, dy = math.cos(angle), math.sin(angle)
                gc.StrokeLine(cx + dx * 7.5, cy + dy * 7.5, cx + dx * 10, cy + dy * 10)
            return

        gc.DrawEllipse(cx - 8, cy - 8, 16, 16)
        gc.SetBrush(wx.Brush(wx.Colour(fill)))
        gc.DrawEllipse(cx - 4.5, cy - 9.5, 15, 15)

    def draw_close(self, gc, cx, cy, colour, size=5):
        gc.SetPen(wx.Pen(wx.Colour(colour), 2))
        gc.StrokeLine(cx - size, cy - size, cx + size, cy + size)
        gc.StrokeLine(cx - size, cy + size, cx + size, cy - size)


class Toolbox(Canvas):

    BUTTON = 28
    PADDING = 4
    GAP = 2
    RADIUS = 9

    @staticmethod
    def get_plate(theme):
        return shade(theme['face'], 1.18)

    def __init__(self, parent, theme, on_edit, on_add):
        super().__init__(parent, theme)
        plate = self.get_plate(theme)
        self.edit_button = RoundButton(self, theme, 'pencil', on_edit, tone='ghost',
                                       size=self.BUTTON, square=True, backdrop=plate)
        self.add_button = RoundButton(self, theme, 'plus', on_add, tone='ghost',
                                      size=self.BUTTON, square=True, backdrop=plate)
        self.buttons = (self.edit_button, self.add_button)
        self.edit_button.icon_shift = 1
        # outside a sizer SetMinSize alone leaves the 20x20 default size
        for index, button in enumerate(self.buttons):
            button.SetSize(self.PADDING + index * (self.BUTTON + self.GAP),
                           self.PADDING, self.BUTTON, self.BUTTON)

    @classmethod
    def get_extent(cls):
        return (cls.PADDING * 2 + cls.BUTTON * 2 + cls.GAP, cls.PADDING * 2 + cls.BUTTON)

    def set_theme(self, theme):
        super().set_theme(theme)
        for button in self.buttons:
            button.set_theme(theme)
            button.set_backdrop(self.get_plate(theme))

    def set_editing(self, editing):
        self.edit_button.set_tone('plain' if editing else 'ghost')

    def draw(self, gc, width, height):
        self.draw_backdrop(gc)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(self.get_plate(self.theme)))
        gc.DrawRoundedRectangle(0, 0, width, height, self.RADIUS)
        draw_card_rim(gc, self.theme['rim'], 0, 0, width, height, self.RADIUS)


class SearchBox(Canvas):

    HEIGHT = 36
    PADDING = 4
    GAP = 4

    def __init__(self, parent, theme, on_back):
        super().__init__(parent, theme)
        size = self.HEIGHT - self.PADDING * 2
        # no solid backdrop, its square corners would poke out of the rounded card
        self.back_button = RoundButton(self, theme, 'back', on_back, tone='ghost',
                                       size=size)
        self.field = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.NO_BORDER)
        self.field.SetHint('Search a city')
        self.SetMinSize(wx.Size(-1, self.HEIGHT))
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, event):
        width, height = self.GetClientSize()
        size = height - self.PADDING * 2
        self.back_button.SetSize(self.PADDING, self.PADDING, size, size)
        # a taller single-line TextCtrl pins its text to the top, keep its own height
        left = self.PADDING + size + self.GAP
        text_height = self.field.GetBestSize()[1]
        self.field.SetSize(left, (height - text_height) // 2,
                           max(0, width - left - self.PADDING - self.GAP), text_height)
        event.Skip()

    def set_theme(self, theme):
        super().set_theme(theme)
        self.back_button.set_theme(theme)
        self.field.SetBackgroundColour(wx.Colour(theme['face']))
        self.field.SetForegroundColour(wx.Colour(theme['text']))
        self.field.SetFont(get_font(10))

    def draw(self, gc, width, height):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(self.theme['face'])))
        gc.DrawRoundedRectangle(0, 0, width, height, CARD_RADIUS)
        draw_card_rim(gc, self.theme['rim'], 0, 0, width, height)


class CityPicker(Canvas):

    ROW = 46

    def __init__(self, parent, theme, on_pick):
        super().__init__(parent, theme)
        self.on_pick = on_pick
        self.rows = []
        self.offset = 0
        self.hovered = -1
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def set_rows(self, rows):
        self.rows = rows
        self.offset = 0
        self.Refresh()

    def on_size(self, event):
        self.offset = min(self.offset, max(0, len(self.rows) - self.get_visible_count()))
        event.Skip()

    def get_visible_count(self):
        return max(1, self.GetClientSize()[1] // self.ROW)

    def get_view_height(self):
        return min(len(self.rows), self.get_visible_count()) * self.ROW

    def hit_test(self, y):
        if not 0 <= y < self.get_view_height():
            return -1
        index = int(y // self.ROW) + self.offset
        return index if 0 <= index < len(self.rows) else -1

    def on_wheel(self, event):
        limit = max(0, len(self.rows) - self.get_visible_count())
        offset = min(limit, max(0, self.offset - (2 if event.GetWheelRotation() > 0 else -2)))
        if offset != self.offset:
            self.offset = offset
            self.Refresh()

    def on_motion(self, event):
        index = self.hit_test(event.GetY())
        if index != self.hovered:
            self.hovered = index
            pickable = index >= 0 and not self.rows[index]['taken']
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND if pickable else wx.CURSOR_ARROW))
            self.Refresh()

    def on_leave(self, event):
        if self.hovered != -1:
            self.hovered = -1
            self.Refresh()

    def on_up(self, event):
        index = self.hit_test(event.GetY())
        if index >= 0 and not self.rows[index]['taken']:
            self.on_pick(self.rows[index]['name'])

    def draw(self, gc, width, height):
        theme = self.theme
        view = self.get_view_height()
        if not view:
            return
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
        gc.DrawRoundedRectangle(0, 0, width, view, CARD_RADIUS)

        for slot in range(view // self.ROW):
            index = self.offset + slot
            row = self.rows[index]
            top = slot * self.ROW
            fill = theme['face']
            if slot:
                draw_row_divider(gc, theme, width, top)
            if index == self.hovered and not row['taken']:
                fill = draw_row_light(gc, theme, width, top, self.ROW)
            draw_city_text(gc, theme, row, MARGIN, width - MARGIN, top, self.ROW, fill, 11,
                           theme['dim'] if row['taken'] else None)

        draw_card_rim(gc, theme['rim'], 0, 0, width, view)


class WorldBox(wx.Panel):

    def __init__(self, parent, theme, settings, on_change):
        super().__init__(parent)
        self.on_change = on_change
        self.names = [name for name in settings.get('cities', DEFAULT_CITIES)
                      if name in CITY_BY_NAME]
        # a UTC offset cannot tell Seoul from Tokyo, so the home city is picked by hand
        self.home = settings.get('home_city')
        if self.home not in CITY_BY_NAME:
            self.home = None
        self.use24h = True
        self.editing = False
        self.picking_home = False
        self.stamp = None

        self.book = wx.Simplebook(self)
        self.browse = self.build_browse(theme)
        self.picker = self.build_picker(theme)
        self.book.AddPage(self.browse, '')
        self.book.AddPage(self.picker, '')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.book, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.apply_theme(theme)
        self.refresh_rows()

    def build_browse(self, theme):
        panel = wx.Panel(self.book)
        self.map = WorldMap(panel, theme, self.on_map_hover, self.on_map_reveal)
        self.list = CityList(panel, theme, self.on_remove,
                             on_home=self.on_pick_home, on_hover=self.on_list_hover)
        # a child of the map, as a sibling the map repaint would cover it
        self.toolbox = Toolbox(self.map, theme, self.on_edit, self.on_add)
        self.map.Bind(wx.EVT_SIZE, self.on_map_size)

        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.map, 0, wx.EXPAND)
        column.AddSpacer(MARGIN)
        column.Add(self.list, 0, wx.EXPAND)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(column)
        row.AddStretchSpacer()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, MARGIN)
        sizer.AddStretchSpacer()
        panel.SetSizer(sizer)
        return panel

    def build_picker(self, theme):
        panel = wx.Panel(self.book)
        self.search = SearchBox(panel, theme, self.on_back)
        self.field = self.search.field
        self.field.Bind(wx.EVT_TEXT, lambda event: self.refresh_picker())
        self.results = CityPicker(panel, theme, self.on_pick)

        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.search, 0, wx.EXPAND | wx.BOTTOM, MARGIN)
        column.Add(self.results, 1, wx.EXPAND)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(column, 0, wx.EXPAND)
        row.AddStretchSpacer()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(row, 1, wx.EXPAND | wx.ALL, MARGIN)
        panel.SetSizer(sizer)
        return panel

    def apply_theme(self, theme):
        for panel in (self, self.browse, self.picker, self.book):
            panel.SetBackgroundColour(wx.Colour(theme['bg']))
        for control in (self.map, self.list, self.results, self.toolbox, self.search):
            control.set_theme(theme)
        self.Refresh()

    def on_size(self, event):
        self.fit_column()
        event.Skip()

    def fit_column(self):
        width, height = self.GetClientSize()
        width = min(COLUMN_WIDTH, width - MARGIN * 2)
        if width <= 0:
            return
        map_height = int(width / ASPECT)
        # as tall as its rows, whole rows when the window is shorter
        room = (height - MARGIN * 3 - map_height) // ROW_STRIDE * ROW_STRIDE
        list_height = max(ROW_STRIDE, min(len(self.list.rows) * ROW_STRIDE, room))
        sizes = (wx.Size(width, map_height), wx.Size(width, list_height), wx.Size(width, -1))
        if sizes == (self.map.GetMinSize(), self.list.GetMinSize(), self.results.GetMinSize()):
            return
        self.map.SetMinSize(sizes[0])
        self.list.SetMinSize(sizes[1])
        self.results.SetMinSize(sizes[2])
        self.browse.Layout()
        self.picker.Layout()

    def on_map_size(self, event):
        height = self.map.GetClientSize()[1]
        extent = Toolbox.get_extent()
        self.toolbox.SetSize(TOOLBOX_INSET, height - extent[1] - TOOLBOX_INSET, *extent)
        event.Skip()

    def on_map_hover(self, index):
        self.list.set_active(index)

    def on_map_reveal(self, index):
        self.list.reveal(index)

    def on_list_hover(self, index):
        self.map.set_active(index)

    def on_edit(self):
        self.editing = not self.editing
        self.list.set_editing(self.editing)
        self.toolbox.set_editing(self.editing)

    def on_add(self):
        self.open_picker(False)

    def on_pick_home(self):
        self.open_picker(True)

    def open_picker(self, picking_home):
        self.picking_home = picking_home
        self.field.SetValue('')
        self.book.SetSelection(1)
        self.refresh_picker()
        self.field.SetFocus()

    def on_back(self):
        self.book.SetSelection(0)

    def on_pick(self, name):
        if self.picking_home:
            self.home = name
            self.refresh_rows()
            self.on_change()
        elif name not in self.names:
            self.names.append(name)
            self.refresh_rows()
            self.on_change()
        self.book.SetSelection(0)

    def on_remove(self, name):
        if name in self.names:
            self.names.remove(name)
            self.refresh_rows()
            self.on_change()

    def set_options(self, use24h):
        if use24h != self.use24h:
            self.use24h = use24h
            self.refresh_rows()

    def get_time_text(self, moment):
        # %#H and %#I drop the leading zero (MSVC strftime)
        if self.use24h:
            return moment.strftime('%#H:%M')
        return moment.strftime('%#I:%M %p').lower()

    def get_day_text(self, moment, local):
        days = (moment.date() - local.date()).days
        return {0: 'Today', -1: 'Yesterday', 1: 'Tomorrow'}.get(days, moment.strftime('%b %d'))

    def get_shift_text(self, minutes, unit=''):
        sign = '-' if minutes < 0 else '+'
        hours, rest = divmod(abs(minutes), 60)
        rest = f' {int(rest):02d}m' if rest else ''
        return f'{unit}{sign}{int(hours)}h{rest}'

    def get_detail_text(self, moment, local, home=False):
        if home:
            minutes = round(moment.utcoffset().total_seconds() / 60)
            parts = [self.get_shift_text(minutes, 'UTC')]
        else:
            minutes = round((moment.utcoffset() - local.utcoffset()).total_seconds() / 60)
            parts = [self.get_day_text(moment, local),
                     self.get_shift_text(minutes) if minutes else 'Same time']
        # zones without an abbreviation report an offset like +04, which repeats the shift
        abbreviation = moment.tzname() or ''
        if abbreviation[:1].isalpha() and abbreviation != 'UTC':
            parts.append(abbreviation)
        return ' \u00b7 '.join(parts)

    def refresh_rows(self):
        now = datetime.now(timezone.utc)
        local = now.astimezone()
        declination, sun_longitude = get_sun_position(now)

        rows = []
        pins = []
        for name in self.names:
            _, zone, latitude, longitude = CITY_BY_NAME[name]
            moment = now.astimezone(ZoneInfo(zone))
            rows.append({
                'name': name,
                'label': name,
                'time': self.get_time_text(moment),
                'detail': self.get_detail_text(moment, local),
                'daylight': is_daylight(latitude, longitude, declination, sun_longitude),
                'fixed': False,
            })
            if zone != 'UTC':
                pins.append((longitude, latitude, len(rows) - 1))

        daylight = 6 <= local.hour < 18
        label = LOCAL
        detail = 'Local time \u00b7 ' + self.get_shift_text(
            round(local.utcoffset().total_seconds() / 60), 'UTC')
        if self.home:
            _, zone, latitude, longitude = CITY_BY_NAME[self.home]
            moment = now.astimezone(ZoneInfo(zone))
            daylight = is_daylight(latitude, longitude, declination, sun_longitude)
            label = self.home
            detail = 'Local time \u00b7 ' + self.get_detail_text(moment, local, True)
            pins.append((longitude, latitude, len(rows)))

        rows.append({
            'name': LOCAL,
            'label': label,
            'time': self.get_time_text(local),
            'detail': detail,
            'daylight': daylight,
            'fixed': True,
        })

        self.map.moment = now
        self.map.set_pins(pins)
        self.list.set_rows(rows)
        self.fit_column()

    def refresh_picker(self):
        now = datetime.now(timezone.utc)
        local = now.astimezone()
        query = self.field.GetValue().strip().lower()
        rows = []
        for name, zone, _, _ in CITIES:
            if query and query not in name.lower() and query not in zone.lower():
                continue
            moment = now.astimezone(ZoneInfo(zone))
            detail = self.get_detail_text(moment, local)
            if zone != 'UTC':
                detail += ' \u00b7 ' + zone.replace('_', ' ')
            rows.append({
                'name': name,
                'label': name,
                'time': self.get_time_text(moment),
                'detail': detail,
                'taken': not self.picking_home and name in self.names,
            })
        self.results.set_rows(rows)

    def tick(self):
        stamp = int(time.time() // 60)
        if stamp == self.stamp:
            return
        self.stamp = stamp
        self.refresh_rows()
        if self.book.GetSelection() == 1:
            self.refresh_picker()
