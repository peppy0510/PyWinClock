# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

세계 시각. 위에는 낮/밤이 드리운 세계지도와 도시 핀, 아래에는 도시별 시각을 둔다.
지도는 assets/map/land.json 의 육지 폴리곤을 등간투영으로 직접 그린다 (makemap.py 참고).
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

# 남극은 잘라내고 사람 사는 위도만 남긴다. 지도 칸의 세로:가로 비율이 여기서 나온다.
LAT_TOP = 78.0
LAT_BOTTOM = -56.0
ASPECT = 360.0 / (LAT_TOP - LAT_BOTTOM)

# 도시 줄은 한 카드 안에 틈 없이 쌓고 줄 사이에 안쪽으로 들인 1 px 금을 긋는다.
ROW_HEIGHT = 52
ROW_GAP = 0
ROW_STRIDE = ROW_HEIGHT + ROW_GAP
MARGIN = 14
ADD_SIZE = 36
# 줄 왼쪽의 해·달 자리와 이름 사이.
PHASE_WIDTH = 24
NAME_GAP = 12
# 이름 줄과 설명 줄 사이 (이름 기준선에서 설명 대문자 윗줄까지).
LINE_GAP = 6

# 낮에서 밤으로 넘어가는 띠의 폭(태양 고도 ±도). 넓을수록 경계가 은은해진다.
TWILIGHT = 16.0
# 지도 카드 모서리에서 도구 상자까지.
TOOLBOX_INSET = 8
# 가리킨 줄의 밝힘을 카드 테두리 안쪽으로 이만큼 들인다.
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
    '''태양이 머리 위에 오는 지점. 분 단위 표시에는 이 정도 근사로 충분하다.'''
    day = moment.timetuple().tm_yday + moment.hour / 24.0
    angle = math.radians(360.0 / 365.24 * (day + 10))
    declination = -math.asin(0.39779 * math.cos(angle))
    seconds = moment.hour * 3600 + moment.minute * 60 + moment.second
    longitude = 180.0 - seconds / 240.0
    return math.degrees(declination), (longitude + 180) % 360 - 180


def get_sun_elevation(latitude, longitude, declination, sun_longitude):
    '''태양 고도의 사인값. 0 이 지평선, 1 이 머리 위다.'''
    hour_angle = math.radians(longitude - sun_longitude)
    return (math.sin(math.radians(latitude)) * math.sin(math.radians(declination)) +
            math.cos(math.radians(latitude)) * math.cos(math.radians(declination)) *
            math.cos(hour_angle))


def is_daylight(latitude, longitude, declination, sun_longitude):
    return get_sun_elevation(latitude, longitude, declination, sun_longitude) > 0


def draw_city_text(gc, theme, row, left, right, top, height, fill, time_size, colour=None):
    '''도시 한 줄의 글자. 시각은 right 에 붙여 세우고, 이름과 설명 두 줄은 대문자 잉크로 재서
    줄의 세로 가운데에 놓는다 (설정 카드와 같다). 도시 목록과 도시 고르기가 함께 쓴다.'''
    colour = colour or theme['text']
    time_font = get_font(time_size, bold=True)
    draw_text_in(gc, row['time'], wx.Rect(0, int(top), right, height), time_font, colour,
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
    '''한 카드 안 줄 사이의 금. 양옆을 MARGIN 만큼 들인다.'''
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(theme['rim'])))
    gc.DrawRectangle(MARGIN, top, width - MARGIN * 2, 1)


def draw_row_light(gc, theme, width, top, height):
    '''가리킨 줄. 카드 테두리와 금을 덮지 않게 안쪽으로 들인 둥근 네모로 칠하고 그 색을 돌려준다.'''
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(theme['control'])))
    gc.DrawRoundedRectangle(ROW_INSET, top + ROW_INSET, width - ROW_INSET * 2,
                            height - ROW_INSET * 2, CARD_RADIUS - 2)
    return theme['control']


class WorldMap(Canvas):
    '''등간투영 세계지도. 낮의 바다와 육지를 깔고 그 위에 밤을 부드럽게 덮는다.
    핀은 (경도, 위도, 줄 번호) 다. 자리가 없는 줄(UTC)은 핀이 없어 둘의 차례가 다를 수 있다.'''

    # 낮의 농도를 계산할 가로 표본 수. 이 격자를 지도 크기로 늘려 부드럽게 만든다.
    GRID = 128
    PIN_RADIUS = 3.5
    # 이 거리 안이면 그 핀을 가리킨 것으로 본다.
    PIN_REACH = 12

    def __init__(self, parent, theme, on_hover=None, on_reveal=None):
        super().__init__(parent, theme)
        self.land = get_land()
        self.pins = []
        self.moment = datetime.now(timezone.utc)
        self.daylight = None
        self.daylight_key = None
        self.on_hover = on_hover
        self.on_reveal = on_reveal
        # hovered 는 지도에서 직접 가리킨 핀, active 는 목록 쪽에서 알려 온 핀이다.
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
        '''핀을 두 번 누르면 그 도시 줄을 목록에서 찾아 보여 준다. 줄이 넘쳐
        접혀 있으면 지도에서 짚어도 아무 일도 안 일어나는 것처럼 보인다.'''
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
        theme = self.theme
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['map_sea'])))
        gc.DrawRectangle(0, 0, width, height)

        gc.SetPen(wx.TRANSPARENT_PEN)
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

        # 밤은 바다와 육지를 함께 덮는다. 바다에만 칠하면 대륙 사이로 세로 띠만 남는다.
        gc.DrawBitmap(self.get_night(width, height), 0, 0, width, height)

        # 가리킨 핀은 맨 위에 오도록 나중에 그린다.
        lit = [pin for pin in self.pins if pin[2] in (self.hovered, self.active)]
        for longitude, latitude, row in [pin for pin in self.pins if pin not in lit] + lit:
            x, y = self.project(longitude, latitude, width, height)
            self.draw_pin(gc, x, y, row in (self.hovered, self.active))

        self.draw_card_edge(gc, width, height)

    def draw_card_edge(self, gc, width, height):
        '''아래 도시 줄과 같은 카드로 보이게 다 그린 뒤 네 귀퉁이를 페이지
        바탕색으로 도려내고 테두리를 두른다. 지도는 사각형에 그려야 투영이
        맞으므로, 둥글게 그리는 것보다 도려내는 편이 간단하다.'''
        theme = self.theme
        path = gc.CreatePath()
        path.AddRectangle(0, 0, width, height)
        path.AddRoundedRectangle(0, 0, width, height, CARD_RADIUS)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['bg'])))
        # 두 도형이 겹치는 안쪽은 짝수라 비고, 귀퉁이 조각만 칠해진다.
        gc.FillPath(path, wx.ODDEVEN_RULE)

        draw_card_rim(gc, theme['rim'], 0, 0, width, height)

    def get_night(self, width, height):
        key = (width, height, self.moment, self.theme['map_night'])
        if self.daylight_key != key:
            self.daylight_key = key
            self.daylight = self.make_night(width, height)
        return self.daylight

    def make_night(self, width, height):
        '''칸마다 태양 고도를 재어 밤일수록 진한 알파를 둔 뒤, 지도 크기로 늘린다.'''
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
                # 낮과 밤의 경계를 부드럽게 잇는 smoothstep.
                day = ratio * ratio * (3 - 2 * ratio)
                alpha[row * columns + column] = int(255 * strength * (1 - day))

        glow = wx.Colour(self.theme['map_night'])
        image = wx.Image(columns, rows)
        image.SetData(bytes((glow.Red(), glow.Green(), glow.Blue())) * (columns * rows))
        image.SetAlpha(bytes(alpha))
        image.Rescale(max(1, width), max(1, height), wx.IMAGE_QUALITY_BILINEAR)
        return image.ConvertToBitmap()

    def draw_pin(self, gc, x, y, active):
        '''점 하나로 끝낸다. 바다에서도 육지에서도 읽히도록 pin_edge 테를 채워 두른다
        (펜으로 두르면 반 칸에 걸려 테가 번진다). 가리킨 핀은 강조색 고리를 더한다.'''
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
    '''도시별 시각 카드. 도구 상자의 연필을 누른 동안에만 제거 표시를 띄운다.'''

    CLOSE_SIZE = 22
    # 줄 오른쪽 끝 버튼. 도구 상자와 같은 모서리 굴린 네모로 둔다.
    BUTTON_SIZE = 24
    BUTTON_RADIUS = 6

    # 타이머 하나가 두 가지를 움직인다. 줄은 목표 자리까지 남은 거리의
    # SCROLL_EASING 씩 좁혀 가고, 스크롤바는 마지막 움직임에서 HOLD 초를 버틴
    # 뒤 남은 진하기의 FADE_EASING 씩 덜어 내며 사라진다.
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
        # offset 은 맨 위에 둘 줄, scroll 은 실제로 그려지는 픽셀 자리다.
        # 둘이 벌어져 있는 동안이 애니메이션이다.
        self.offset = 0
        self.scroll = 0.0
        self.fade = 0.0
        self.hold_until = 0.0
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_animate)
        # hovered 는 목록에서 직접 가리킨 줄, active 는 지도 쪽에서 알려 온 줄이다.
        self.hovered = -1
        self.active = -1
        # 오른쪽 끝 버튼 위에 손이 올라간 줄.
        self.on_button = -1
        self.editing = False
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)

    def set_rows(self, rows):
        self.rows = rows
        self.offset = min(self.offset, max(0, len(rows) - self.get_visible_count()))
        # 줄이 줄어 목표가 당겨졌다면, 움직이는 중이 아닐 때는 곧바로 맞춘다.
        if not self.timer.IsRunning():
            self.scroll = float(self.offset * ROW_STRIDE)
        self.Refresh()

    def set_editing(self, editing):
        if editing != self.editing:
            self.editing = editing
            self.Refresh()

    def set_active(self, index):
        if index != self.active:
            self.active = index
            self.Refresh()

    def get_view_height(self):
        '''카드의 키. 줄이 넘치면 반쯤 걸친 줄 없이 딱 떨어지는 줄 수만큼만 보인다.
        나머지는 굴려서 본다.'''
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
        '''지도에서 짚어 준 줄이 접혀 있으면 보이는 자리까지 끌어 온다.
        이미 보이는 줄이면 목록을 흔들지 않는다.'''
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
        # 붙박이 줄(로컬)은 지울 수 없다. 대신 어느 도시인지 고르게 한다.
        if self.rows[index]['fixed']:
            if self.on_home:
                self.on_home()
        else:
            self.on_remove(self.rows[index]['name'])

    def draw(self, gc, width, height):
        # 줄 전체가 한 카드다. 줄은 카드 안에서 굴러가고 카드 밖으로는 안 나간다.
        theme = self.theme
        view = self.get_view_height()
        if not view:
            return
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['face'])))
        gc.DrawRoundedRectangle(0, 0, width, view, CARD_RADIUS)

        # 움직이는 중에는 위아래로 반쯤 걸친 줄이 있다. 카드 안으로 자른다.
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
        # 줄이 넘칠 때만, 휠로 더 볼 수 있다는 표시로 얇게 둔다. 움직이는 동안만
        # 떠 있다가 사라지므로 평소에는 카드 위에 아무것도 얹히지 않는다.
        total = self.get_content_height()
        span = max(20, height * height / total)
        top = (height - span) * min(1.0, max(0.0, self.scroll / (total - height)))
        rim = wx.Colour(self.theme['rim'])
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(rim.Red(), rim.Green(), rim.Blue(),
                                       round(255 * self.fade))))
        # 카드 테두리 안쪽에 둔다.
        gc.DrawRoundedRectangle(width - 6, top, 3, span, 1.5)

    def draw_row(self, gc, row, index, width, top):
        theme = self.theme
        fill = theme['face']
        if index:
            draw_row_divider(gc, theme, width, top)
        # 지도에서 짚어 준 줄도 목록에서 직접 짚은 줄과 같은 색으로만 밝힌다.
        if index in (self.hovered, self.active):
            fill = draw_row_light(gc, theme, width, top, ROW_HEIGHT)

        middle = top + ROW_HEIGHT / 2
        self.draw_phase(gc, MARGIN + PHASE_WIDTH / 2, middle, row['daylight'], fill)

        # 시각은 오른쪽 끝에 세운다. 고치는 동안은 줄 끝 버튼에 자리를 내준다.
        right = width - MARGIN
        if self.editing:
            right = self.get_button_rect(width, top).x - NAME_GAP
        draw_city_text(gc, theme, row, MARGIN + PHASE_WIDTH + NAME_GAP, right, top, ROW_HEIGHT,
                       fill, 15)

        if self.editing:
            self.draw_button(gc, row, index, width, top)

    def draw_button(self, gc, row, index, width, top):
        '''줄 오른쪽 끝의 지우기·내 도시 버튼. 평소엔 아이콘만 두고 손이 올라간
        동안만 회색을 비추는, 도구 상자 ghost 버튼과 같은 말씨다.'''
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

        # 초승달은 원을 하나 그리고 카드 색 원으로 한 입 베어내 만든다.
        gc.DrawEllipse(cx - 8, cy - 8, 16, 16)
        gc.SetBrush(wx.Brush(wx.Colour(fill)))
        gc.DrawEllipse(cx - 4.5, cy - 9.5, 15, 15)

    def draw_close(self, gc, cx, cy, colour, size=5):
        gc.SetPen(wx.Pen(wx.Colour(colour), 2))
        gc.StrokeLine(cx - size, cy - size, cx + size, cy + size)
        gc.StrokeLine(cx - size, cy + size, cx + size, cy - size)


class Toolbox(Canvas):
    '''지도 왼쪽 아래에 떠 있는 도구 상자. 둥근 판 위에 모서리를 굴린 네모
    아이콘 버튼을 늘어놓는다. 버튼은 판이 비쳐야 하므로 ghost 로 둔다.'''

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
        # 사이저에 담지 않으므로 최소 크기만으로는 20x20 기본값에 머문다. 자리와
        # 크기를 여기서 직접 준다.
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
        # 켜졌다는 표시는 사이드 메뉴의 고른 줄, 타이틀바의 열린 햄버거와 같은
        # 관례를 따른다. 액센트로 칠하지 않고 control 바탕에 아이콘만 밝힌다.
        self.edit_button.set_tone('plain' if editing else 'ghost')

    def draw(self, gc, width, height):
        self.draw_backdrop(gc)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(self.get_plate(self.theme)))
        gc.DrawRoundedRectangle(0, 0, width, height, self.RADIUS)
        draw_card_rim(gc, self.theme['rim'], 0, 0, width, height, self.RADIUS)


class SearchBox(Canvas):
    '''카드 하나에 되돌아가기와 검색칸을 함께 담는다 (지도·도시 목록과 같은 카드). 네이티브
    TextCtrl 은 모서리를 굴릴 수 없어, 판은 캔버스로 그리고 그 안에 앉힌다.'''

    HEIGHT = 36
    PADDING = 4
    GAP = 4

    def __init__(self, parent, theme, on_back):
        super().__init__(parent, theme)
        size = self.HEIGHT - self.PADDING * 2
        # 동그라미 단추. 바탕을 한 색으로 깔면 네모 귀퉁이가 카드 둥근 모서리 밖으로
        # 튀어나오므로 판 그림을 그대로 떠 온다.
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
        # 단일 라인 TextCtrl 은 높이를 키우면 글자가 위로 붙는다. 제 높이 그대로
        # 두고 세로 가운데에 앉힌다.
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
    '''검색어에 걸린 도시를 도시 목록과 같은 카드의 줄로 보여 준다. 이미 담은 도시는
    흐리게 두고 지나친다.'''

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

    def set_rows(self, rows):
        self.rows = rows
        self.offset = 0
        self.Refresh()

    def get_visible_count(self):
        return max(1, self.GetClientSize()[1] // self.ROW)

    def get_view_height(self):
        '''카드의 키. 반쯤 걸친 줄 없이 보이는 줄 수만큼.'''
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
        # 로컬이 어느 도시인지는 시간대만으로 가릴 수 없다(+09:00 에 Seoul 도
        # Tokyo 도 있다). 직접 골라 둔 도시가 있어야 지도에 찍을 수 있다.
        self.home = settings.get('home_city')
        if self.home not in CITY_BY_NAME:
            self.home = None
        self.use24h = True
        self.editing = False
        self.picking_home = False
        self.stamp = None
        self.map_height = 0

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
        # 지도 카드 왼쪽 아래(남태평양, 도시가 없는 자리)에 띄운다. 목록 위에 띄우면 넘친 줄의
        # 시각을 덮고, 오른쪽 위는 좁은 창에서 서울 핀에 걸린다. 형제로
        # 두면 지도가 다시 칠할 때마다 덧칠해 지워지므로 지도의 자식으로 만들어 부모가 클립하게 한다.
        self.toolbox = Toolbox(self.map, theme, self.on_edit, self.on_add)
        self.map.Bind(wx.EVT_SIZE, self.on_map_size)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.map, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, MARGIN)
        sizer.AddSpacer(MARGIN)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, MARGIN)
        panel.SetSizer(sizer)
        return panel

    def build_picker(self, theme):
        panel = wx.Panel(self.book)
        # 되돌아가기는 검색칸 안 왼쪽에 얹는다. 검색칸이 목록과 같은 폭을 갖는다.
        self.search = SearchBox(panel, theme, self.on_back)
        self.field = self.search.field
        self.field.Bind(wx.EVT_TEXT, lambda event: self.refresh_picker())
        self.results = CityPicker(panel, theme, self.on_pick)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, MARGIN)
        sizer.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, MARGIN)
        panel.SetSizer(sizer)
        return panel

    def apply_theme(self, theme):
        for panel in (self, self.browse, self.picker, self.book):
            panel.SetBackgroundColour(wx.Colour(theme['bg']))
        for control in (self.map, self.list, self.results, self.toolbox, self.search):
            control.set_theme(theme)
        self.Refresh()

    def on_size(self, event):
        # 지도 카드도 좌우 여백만큼 좁아졌다. 그 폭으로 높이를 잡아야 투영이
        # 늘어나지 않는다.
        width = max(0, self.GetClientSize()[0] - MARGIN * 2)
        height = int(width / ASPECT)
        if width > 0 and height != self.map_height:
            self.map_height = height
            self.map.SetMinSize(wx.Size(-1, height))
            self.browse.Layout()
        event.Skip()

    def on_map_size(self, event):
        # 사이저에 담지 않았으므로 지도 안에서의 자리를 여기서 직접 준다.
        height = self.map.GetClientSize()[1]
        extent = Toolbox.get_extent()
        self.toolbox.SetSize(TOOLBOX_INSET, height - extent[1] - TOOLBOX_INSET, *extent)
        event.Skip()

    def on_map_hover(self, index):
        # 핀과 줄은 차례가 같다. 마지막 Local time 줄만 짝이 없어 그냥 비켜 간다.
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
        # %#H / %#I 는 MSVC 확장이다. 앞자리 0 을 떼어 Windows 시계와 같게 둔다.
        if self.use24h:
            return moment.strftime('%#H:%M')
        return moment.strftime('%#I:%M %p').lower()

    def get_day_text(self, moment, local):
        '''로컬 날짜와 견준 날. 날짜를 다 적으면 줄마다 같은 글자가 되풀이된다.'''
        days = (moment.date() - local.date()).days
        return {0: 'Today', -1: 'Yesterday', 1: 'Tomorrow'}.get(days, moment.strftime('%b %d'))

    def get_shift_text(self, minutes, unit=''):
        '''+9h, -3h 30m. 30 분·45 분짜리 지역이 있어 시간만으로는 모자라다.'''
        sign = '-' if minutes < 0 else '+'
        hours, rest = divmod(abs(minutes), 60)
        return '%s%s%dh%s' % (unit, sign, hours, ' %02dm' % rest if rest else '')

    def get_detail_text(self, moment, local, home=False):
        '''도시 이름 아래 줄. 날, 시차, 시간대 약칭. 약칭이 없는 지역은 zoneinfo 가 +04 처럼
        오프셋을 돌려주는데 시차와 겹치므로 뺀다. 로컬 줄의 시차는 늘 0 이라 UTC 와의 시차를 적는다.'''
        if home:
            minutes = round(moment.utcoffset().total_seconds() / 60)
            parts = [self.get_shift_text(minutes, 'UTC')]
        else:
            minutes = round((moment.utcoffset() - local.utcoffset()).total_seconds() / 60)
            parts = [self.get_day_text(moment, local),
                     self.get_shift_text(minutes) if minutes else 'Same time']
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
            # 자리가 없는 줄(UTC)은 지도에 찍지 않는다. 0,0 은 기니만 바다다.
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

    def refresh_picker(self):
        now = datetime.now(timezone.utc)
        local = now.astimezone()
        query = self.field.GetValue().strip().lower()
        rows = []
        for name, zone, _, _ in CITIES:
            if query and query not in name.lower() and query not in zone.lower():
                continue
            moment = now.astimezone(ZoneInfo(zone))
            # 검색은 시간대 이름으로도 걸리므로 설명 줄 끝에 그 이름을 둔다.
            detail = self.get_detail_text(moment, local)
            if zone != 'UTC':
                detail += ' \u00b7 ' + zone.replace('_', ' ')
            rows.append({
                'name': name,
                'label': name,
                'time': self.get_time_text(moment),
                'detail': detail,
                # 내 도시를 고르는 중에는 이미 담은 도시도 다시 고를 수 있다.
                'taken': not self.picking_home and name in self.names,
            })
        self.results.set_rows(rows)

    def tick(self):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
        if stamp == self.stamp:
            return
        self.stamp = stamp
        self.refresh_rows()
        if self.book.GetSelection() == 1:
            self.refresh_picker()
