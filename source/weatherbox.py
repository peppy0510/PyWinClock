# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
import wx

from datetime import datetime
from zoneinfo import ZoneInfo

from cities import CITY_BY_NAME
from icons import add_cloud
from utilities import CARD_RADIUS
from utilities import PAGE_COLUMN
from utilities import APP_NAME
from utilities import Canvas
from utilities import get_font
from utilities import get_ink
from utilities import get_ink_span
from utilities import get_page_scale
from utilities import get_settings_path
from utilities import get_text_top
from utilities import draw_card_rim
from utilities import fill_rounded
from utilities import mix


FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
PAST_DAYS = 3
FORECAST_DAYS = 7
# a forecast changes slowly; asked again only this often, and later after a failure
FRESH_SECONDS = 30 * 60
RETRY_SECONDS = 5 * 60
TIMEOUT = 10

# the cards as laid out at the window's first size; a larger window scales the page as one
COLUMN_WIDTH = PAGE_COLUMN
# around and between the cards, as the World page's
MARGIN = 14
GAP = 14
# the card for now: three columns, each centred on its middle; the cards' ink, cap tops
# to baselines, keeps 14 px from their edges above and below, as their text does at the sides
NOW_HEIGHT = 77
NOW_ICON = 32
NOW_TEMPERATURE = 18
NOW_GAP = 10
NOW_WORD_GAP = 8
HOURLY_HEIGHT = 143
HOURLY_TOP = 2
# rows as the World page's: their height, a name over a note; the list scrolls when the
# window has no room for them all
DAY_HEIGHT = 52
DAY_INSET = 4
DAY_ICON = 22
DAY_TEXT = 50
DAY_LINE_GAP = 6
# the list's scroll bar shows while it scrolls or the pointer comes on, then fades as World's
SCROLL_HOLD = 0.7
SCROLL_EASING = 0.22
SCROLL_STEP = 16
HOURS = 24
HOUR_STEPS = (2, 3)
# the room a label needs: '12°', '65%' and '11pm' side by side without touching
HOUR_ROOM = 28
SHOWERS = 20

# cold to warm runs blue to orange, never green against red
COLD = {True: '#5aa7ff', False: '#2b6cb0'}
RAIN = COLD

# WMO weather codes as Open-Meteo reports them
CONDITIONS = {
    0: ('Clear', 'clear'),
    1: ('Mainly clear', 'clear'),
    2: ('Partly cloudy', 'partly'),
    3: ('Overcast', 'cloud'),
    45: ('Fog', 'fog'),
    48: ('Rime fog', 'fog'),
    51: ('Light drizzle', 'drizzle'),
    53: ('Drizzle', 'drizzle'),
    55: ('Heavy drizzle', 'drizzle'),
    56: ('Freezing drizzle', 'drizzle'),
    57: ('Freezing drizzle', 'drizzle'),
    61: ('Light rain', 'rain'),
    63: ('Rain', 'rain'),
    65: ('Heavy rain', 'rain'),
    66: ('Freezing rain', 'rain'),
    67: ('Freezing rain', 'rain'),
    71: ('Light snow', 'snow'),
    73: ('Snow', 'snow'),
    75: ('Heavy snow', 'snow'),
    77: ('Snow grains', 'snow'),
    80: ('Light showers', 'rain'),
    81: ('Showers', 'rain'),
    82: ('Heavy showers', 'rain'),
    85: ('Snow showers', 'snow'),
    86: ('Heavy snow showers', 'snow'),
    95: ('Thunderstorm', 'thunder'),
    96: ('Thunderstorm, hail', 'thunder'),
    99: ('Thunderstorm, hail', 'thunder'),
}


def get_condition(code):
    return CONDITIONS.get(code, ('Unknown', 'cloud'))


def get_cache_path():
    return os.path.join(os.path.dirname(get_settings_path()), 'weather.json')


def load_cache():
    try:
        with open(get_cache_path(), encoding='utf-8') as file:
            return json.load(file)
    except Exception:
        return None


def save_cache(cache):
    try:
        path = get_cache_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(cache, file)
    except Exception:
        pass


def fetch_forecast(latitude, longitude, zone):
    query = urllib.parse.urlencode({
        'latitude': latitude,
        'longitude': longitude,
        'timezone': zone,
        'past_days': PAST_DAYS,
        'forecast_days': FORECAST_DAYS,
        'current': 'temperature_2m,apparent_temperature,weather_code,'
                   'relative_humidity_2m,wind_speed_10m,is_day',
        'hourly': 'temperature_2m,weather_code,precipitation_probability,is_day',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,'
                 'precipitation_probability_max',
    })
    request = urllib.request.Request(f'{FORECAST_URL}?{query}',
                                     headers={'User-Agent': APP_NAME})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def format_degrees(value):
    return '–' if value is None else f'{round(value)}°'


def draw_sun(gc, cx, cy, size, colour):
    radius = size * 0.22
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(colour)))
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
    gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(colour)).Width(max(1.0, size * 0.07))
                           .Cap(wx.CAP_ROUND)))
    for step in range(8):
        angle = math.radians(step * 45)
        dx, dy = math.cos(angle), math.sin(angle)
        gc.StrokeLine(cx + dx * size * 0.32, cy + dy * size * 0.32,
                      cx + dx * size * 0.45, cy + dy * size * 0.45)


def draw_moon(gc, cx, cy, size, colour, back):
    radius = size * 0.30
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(colour)))
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
    # the card's own colour bites the crescent out
    gc.SetBrush(wx.Brush(wx.Colour(back)))
    bite = radius * 0.86
    centre = (cx + radius * 0.40, cy - radius * 0.45)
    gc.DrawEllipse(centre[0] - bite, centre[1] - bite, bite * 2, bite * 2)


def fill_cloud(gc, cx, cy, size, colour):
    path = gc.CreatePath()
    add_cloud(path, cx, cy, size)
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(wx.Colour(colour)))
    gc.FillPath(path)


def draw_weather_icon(gc, kind, cx, cy, size, theme, back, day=True):
    '''the shapes alone tell the kinds apart, colour only helps'''
    dark = theme['titlebar_dark']
    cloud = mix(theme['dim'], theme['text'], 0.35)
    sun = theme['warn']
    moon = theme['tick_major']
    if kind == 'clear':
        if day:
            draw_sun(gc, cx, cy, size, sun)
        else:
            draw_moon(gc, cx, cy, size, moon, back)
        return
    if kind == 'partly':
        if day:
            draw_sun(gc, cx - size * 0.14, cy - size * 0.14, size * 0.78, sun)
        else:
            draw_moon(gc, cx - size * 0.14, cy - size * 0.16, size * 0.78, moon, back)
        fill_cloud(gc, cx + size * 0.06, cy + size * 0.08, size * 0.82, cloud)
        return
    if kind == 'fog':
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(cloud).Width(max(1.5, size * 0.09))
                               .Cap(wx.CAP_ROUND)))
        for row, (left, right) in enumerate(((-0.40, 0.30), (-0.30, 0.40), (-0.40, 0.24))):
            y = cy - size * 0.22 + row * size * 0.22
            gc.StrokeLine(cx + size * left, y, cx + size * right, y)
        return

    lifted = kind in ('rain', 'drizzle', 'snow', 'thunder')
    fill_cloud(gc, cx, cy - (size * 0.14 if lifted else 0), size, cloud)
    below = cy + size * 0.20
    if kind in ('rain', 'drizzle'):
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(RAIN[dark]))
                               .Width(max(1.2, size * 0.07)).Cap(wx.CAP_ROUND)))
        reach = size * (0.18 if kind == 'rain' else 0.07)
        for step in (-1, 0, 1):
            x = cx + step * size * 0.20
            gc.StrokeLine(x, below, x - reach * 0.4, below + reach)
    elif kind == 'snow':
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(theme['text'])))
        dot = max(1.2, size * 0.06)
        for step, drop in ((-1, 0.04), (0, 0.16), (1, 0.04)):
            x, y = cx + step * size * 0.20, below + size * drop
            gc.DrawEllipse(x - dot, y - dot, dot * 2, dot * 2)
    elif kind == 'thunder':
        path = gc.CreatePath()
        path.MoveToPoint(cx + size * 0.04, below - size * 0.06)
        path.AddLineToPoint(cx - size * 0.10, below + size * 0.12)
        path.AddLineToPoint(cx + size * 0.02, below + size * 0.12)
        path.AddLineToPoint(cx - size * 0.06, below + size * 0.28)
        path.AddLineToPoint(cx + size * 0.14, below + size * 0.06)
        path.AddLineToPoint(cx + size * 0.02, below + size * 0.06)
        path.CloseSubpath()
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(sun)))
        gc.FillPath(path)


ICON_SPANS = {}


def get_icon_span(kind, day, size, theme):
    '''how far an icon's ink reaches left and right of its centre; a crescent or a sun
    behind a cloud sits off its box's middle'''
    key = (kind, day, size, theme['face'], theme['text'])
    if key not in ICON_SPANS:
        side = int(size * 2)
        bitmap = wx.Bitmap(side, side, 24)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.Brush(wx.Colour(theme['face'])))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        draw_weather_icon(gc, kind, side / 2, side / 2, size, theme, theme['face'], day)
        del gc
        dc.SelectObject(wx.NullBitmap)
        image = bitmap.ConvertToImage()
        data = image.GetData()
        ground = wx.Colour(theme['face'])
        base = (ground.Red(), ground.Green(), ground.Blue())
        columns = [x for x in range(side) if any(
            sum(abs(data[(y * side + x) * 3 + c] - base[c]) for c in range(3)) > 48
            for y in range(side))]
        ICON_SPANS[key] = (side / 2 - columns[0], columns[-1] + 1 - side / 2) if columns \
            else (size / 2, size / 2)
    return ICON_SPANS[key]


class Forecast:

    '''the reply, read once into what the page draws'''

    def __init__(self, data, zone):
        self.zone = ZoneInfo(zone)
        current = data.get('current', {})
        self.temperature = current.get('temperature_2m')
        self.feels = current.get('apparent_temperature')
        self.code = current.get('weather_code')
        self.humidity = current.get('relative_humidity_2m')
        self.wind = current.get('wind_speed_10m')
        self.day = bool(current.get('is_day', 1))

        hourly = data.get('hourly', {})
        self.hours = [datetime.fromisoformat(stamp) for stamp in hourly.get('time', [])]
        self.hour_temperatures = hourly.get('temperature_2m', [])
        self.hour_codes = hourly.get('weather_code', [])
        self.hour_rain = hourly.get('precipitation_probability', [])
        self.hour_day = hourly.get('is_day', [])

        daily = data.get('daily', {})
        self.days = [datetime.fromisoformat(stamp).date() for stamp in daily.get('time', [])]
        self.day_codes = daily.get('weather_code', [])
        self.highs = daily.get('temperature_2m_max', [])
        self.lows = daily.get('temperature_2m_min', [])
        self.day_rain = daily.get('precipitation_probability_max', [])

    def get_now(self):
        return datetime.now(self.zone).replace(tzinfo=None)

    def get_hour_index(self):
        hour = self.get_now().replace(minute=0, second=0, microsecond=0)
        try:
            return self.hours.index(hour)
        except ValueError:
            return -1

    def get_today_index(self):
        try:
            return self.days.index(self.get_now().date())
        except ValueError:
            return -1


class WeatherFeed:

    '''the forecast of one place, asked for off the GUI thread and kept on disk'''

    def __init__(self, on_result):
        self.on_result = on_result
        self.place = None
        self.data = None
        self.fetched = 0.0
        self.failed = 0.0
        self.busy = False
        self.error = False
        cache = load_cache()
        if cache:
            self.place = cache.get('place')
            self.data = cache.get('data')
            self.fetched = cache.get('fetched', 0.0)

    def set_place(self, name):
        if name == self.place:
            return
        self.place = name
        self.data = None
        self.fetched = 0.0
        self.failed = 0.0
        self.error = False

    def is_due(self):
        if self.busy or self.place not in CITY_BY_NAME:
            return False
        now = time.time()
        if now - self.failed < RETRY_SECONDS:
            return False
        return now - self.fetched >= FRESH_SECONDS

    def refresh(self):
        if not self.is_due():
            return
        self.busy = True
        _, zone, latitude, longitude = CITY_BY_NAME[self.place]
        threading.Thread(target=self.run, args=(self.place, latitude, longitude, zone),
                         name='weather-fetch', daemon=True).start()

    def run(self, place, latitude, longitude, zone):
        try:
            data = fetch_forecast(latitude, longitude, zone)
        except Exception:
            data = None
        try:
            wx.CallAfter(self.take, place, data)
        except Exception:
            pass

    def take(self, place, data):
        self.busy = False
        if place != self.place:
            return
        if data is None:
            self.failed = time.time()
            self.error = True
        else:
            self.data = data
            self.fetched = time.time()
            self.error = False
            save_cache({'place': place, 'fetched': self.fetched, 'data': data})
        self.on_result()


class WeatherBox(Canvas):

    '''the home city's weather: now, the next hours, the days around today'''

    def __init__(self, parent, theme, get_place):
        super().__init__(parent, theme)
        self.get_place = get_place
        self.use24h = True
        self.feed = WeatherFeed(self.on_result)
        self.forecast = None
        self.stamp = None
        # the day the hourly card shows, None for today
        self.picked = None
        self.hovered = None
        self.pressed = None
        self.day_rects = []
        # the first row in sight, None until the list is first laid out
        self.day_offset = None
        self.day_count = 0
        self.day_visible = 0
        self.day_card = wx.Rect()
        self.fade = 0.0
        self.hold_until = 0.0
        self.over_days = False
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_fade, self.timer)
        self.read_forecast()
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, event):
        # the same scale as the other pages, so they grow together
        self.set_scale(get_page_scale(*self.GetClientSize()))
        event.Skip()

    def on_leave(self, event):
        self.over_days = False
        self.set_hovered(None)

    def get_point(self, position):
        return self.locate(position)

    def show_scrollbar(self):
        if self.day_count <= self.day_visible:
            return
        self.fade = 1.0
        self.hold_until = time.monotonic() + SCROLL_HOLD
        if not self.timer.IsRunning():
            self.timer.Start(SCROLL_STEP)
        self.Refresh()

    def on_fade(self, event):
        # a beat can land after the window is gone
        if not self:
            return
        if time.monotonic() >= self.hold_until:
            self.fade -= self.fade * SCROLL_EASING
            if self.fade < 0.02:
                self.fade = 0.0
                self.timer.Stop()
        self.Refresh()

    def on_wheel(self, event):
        if not self.day_card.Contains(self.get_point(event.GetPosition())):
            return
        self.show_scrollbar()
        limit = max(0, self.day_count - self.day_visible)
        step = -1 if event.GetWheelRotation() > 0 else 1
        offset = min(limit, max(0, (self.day_offset or 0) + step))
        if offset != self.day_offset:
            self.day_offset = offset
            self.Refresh()
            # the rows moved under a still pointer
            self.Update()
            self.set_hovered(self.hit_day(event.GetPosition()))

    def hit_day(self, position):
        point = self.get_point(position)
        for rect, day in self.day_rects:
            if rect.Contains(point):
                return day
        return None

    def set_hovered(self, day):
        if day != self.hovered:
            self.hovered = day
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND if day else wx.CURSOR_ARROW))
            self.Refresh()

    def on_motion(self, event):
        over = self.day_card.Contains(self.get_point(event.GetPosition()))
        if over and not self.over_days:
            self.show_scrollbar()
        self.over_days = over
        self.set_hovered(self.hit_day(event.GetPosition()))

    def on_down(self, event):
        self.pressed = self.hit_day(event.GetPosition())
        event.Skip()

    def on_up(self, event):
        day = self.hit_day(event.GetPosition())
        if day is not None and day == self.pressed and self.forecast is not None:
            # the day shown again goes back to today
            today = self.forecast.get_now().date()
            self.picked = None if day in (today, self.picked) else day
            self.Refresh()
        self.pressed = None
        event.Skip()

    def apply_theme(self, theme):
        self.set_theme(theme)

    def set_options(self, use24h):
        if use24h != self.use24h:
            self.use24h = use24h
            self.Refresh()

    def read_forecast(self):
        self.forecast = None
        if self.feed.data and self.feed.place in CITY_BY_NAME:
            zone = CITY_BY_NAME[self.feed.place][1]
            try:
                self.forecast = Forecast(self.feed.data, zone)
            except Exception:
                self.forecast = None

    def on_result(self):
        # a reply can land after the window is gone
        if not self:
            return
        self.read_forecast()
        self.Refresh()

    def tick(self):
        place = self.get_place()
        if place != self.feed.place:
            self.feed.set_place(place)
            self.read_forecast()
            self.Refresh()
        self.feed.refresh()
        # the mark of now moves along the hours; a pixel takes a few minutes
        stamp = int(time.time() // 300)
        if stamp != self.stamp:
            self.stamp = stamp
            self.Refresh()

    def get_hour_text(self, moment):
        if self.use24h:
            return moment.strftime('%H')
        return moment.strftime('%#I%p').lower()

    def get_clock_text(self, moment):
        if self.use24h:
            return moment.strftime('%H:%M')
        return moment.strftime('%#I:%M %p').lower()

    def get_day_text(self, day, today):
        days = (day - today).days
        return {0: 'Today', -1: 'Yesterday', 1: 'Tomorrow'}.get(days, day.strftime('%a'))

    def fill_card(self, gc, x, y, width, height, colour=None):
        fill_rounded(gc, colour or self.theme['face'], x, y, width, height)
        draw_card_rim(gc, self.theme['rim'], x, y, width, height)

    def draw_text(self, gc, text, x, y, size, colour, bold=False, align='left', middle=False):
        '''middle: y is the line's centre, met by the ink as the triangles meet it'''
        font = get_font(size, bold)
        gc.SetFont(font, wx.Colour(colour))
        text_width, text_height = gc.GetTextExtent(text)[:2]
        if middle:
            y = get_text_top(font, round(y) - 20, 40)
        if align == 'right':
            x -= text_width
        elif align == 'center':
            x -= text_width / 2
        gc.DrawText(text, x, y)
        return text_width, text_height

    def draw_message(self, gc, width, height, lines):
        top = height / 2 - len(lines) * 11
        for index, (text, colour) in enumerate(lines):
            self.draw_text(gc, text, width / 2, top + index * 22, 10, colour, align='center')

    def place_days(self, forecast, visible):
        # yesterday on top at first; kept where it was scrolled to after that
        count = len(forecast.days)
        limit = max(0, count - visible)
        if self.day_offset is None:
            today = forecast.get_today_index()
            self.day_offset = max(0, today - 1) if today >= 0 else 0
        self.day_offset = min(limit, self.day_offset)
        self.day_count, self.day_visible = count, visible
        return self.day_offset, self.day_offset + visible

    def draw(self, gc, width, height):
        theme = self.theme
        column = min(COLUMN_WIDTH, width - MARGIN * 2)
        if column <= 0:
            return
        place = self.feed.place
        forecast = self.forecast
        if place not in CITY_BY_NAME:
            self.draw_message(gc, width, height, (
                ('Pick a home city on the World page', theme['text']),
                ('to see its weather here', theme['dim'])))
            return
        if forecast is None:
            if self.feed.error:
                lines = (('Weather unavailable', theme['text']),
                         ('Trying again in a few minutes', theme['dim']))
            else:
                lines = ((f'Loading the weather for {place}', theme['dim']),)
            self.draw_message(gc, width, height, lines)
            return

        fixed = NOW_HEIGHT + GAP + HOURLY_HEIGHT + GAP
        spare = height - MARGIN * 2 - fixed
        visible = min(len(forecast.days), max(1, int(spare // DAY_HEIGHT)))
        first, last = self.place_days(forecast, visible)
        if self.picked not in forecast.days:
            self.picked = None
        total = fixed + visible * DAY_HEIGHT
        # whole pixels, so the rows' triangles land on the pixel grid
        x = round((width - column) / 2)
        y = max(MARGIN, round((height - total) / 2))

        self.draw_now(gc, forecast, place, x, y, column)
        y += NOW_HEIGHT + GAP
        self.draw_hours(gc, forecast, x, y, column)
        y += HOURLY_HEIGHT + GAP
        self.draw_days(gc, forecast, x, y, column, first, last)

    def get_update_lines(self):
        fetched = datetime.fromtimestamp(self.feed.fetched)
        when = self.get_clock_text(fetched)
        if fetched.date() != datetime.now().date():
            when = f'{fetched.strftime("%b %d")} {when}'
        # GDI+ fits 8 pt type to the pixels and loses the colon; hair spaces keep it in sight
        when = when.replace(':', '\u200a:\u200a')
        lines = [f'Updated {when}']
        if self.feed.error:
            lines.append('Offline')
        return lines

    def get_centred_top(self, lines, middle):
        '''the top for lines of (font, offset) whose ink, cap top of the first to the
        baseline of the last, is centred on middle'''
        first, first_offset = lines[0]
        last, last_offset = lines[-1]
        ink_top = first_offset + get_ink(first)[0]
        ink_bottom = last_offset + get_ink(last)[1]
        return round(middle - (ink_top + ink_bottom + 1) / 2)

    def measure(self, gc, text, size, bold=False):
        gc.SetFont(get_font(size, bold), wx.BLACK)
        return gc.GetTextExtent(text)[:2]

    def draw_now(self, gc, forecast, place, x, y, width):
        '''the place and its update time, the weather now, its details; a line for yesterday'''
        theme = self.theme
        self.fill_card(gc, x, y, width, NOW_HEIGHT)
        # the middle of the rows inside the rim, caps to baselines centred on it
        middle = y + NOW_HEIGHT / 2

        # the details on the left, the place and its update time on the right, each
        # aligned on its margin by ink; text extents pad the right side
        # the World page's type: names and readings 10, notes 8 and dim
        title, detail, note = get_font(11, True), get_font(10), get_font(8)
        details = []
        if forecast.feels is not None:
            details.append(f'Feels like {format_degrees(forecast.feels)}')
        if forecast.humidity is not None:
            details.append(f'Humidity {round(forecast.humidity)}%')
        if forecast.wind is not None:
            details.append(f'Wind {round(forecast.wind)} km/h')
        spans = [get_ink_span(detail, text) for text in details]
        left_end = x + 14 + max((right - left + 1 for left, right in spans), default=0)
        # each column's ink centred on the body's middle, as the icon is
        top = self.get_centred_top([(detail, index * 20) for index in range(len(details))]
                                   or [(detail, 0)], middle)
        gc.SetFont(detail, wx.Colour(theme['dim']))
        for index, (text, (left, _)) in enumerate(zip(details, spans)):
            gc.DrawText(text, x + 14 - left, top + index * 20)

        _, place_height = self.measure(gc, place, 11, bold=True)
        lines = [(place, title, theme['text'], 0)]
        for index, text in enumerate(self.get_update_lines()):
            lines.append((text, note, theme['dim'], place_height + 2 + index * 17))
        top = self.get_centred_top([(font, offset) for _, font, _, offset in lines], middle)
        lines = [(text, font, colour, top + offset) for text, font, colour, offset in lines]
        spans = [get_ink_span(font, text) for text, font, _, _ in lines]
        edge = x + width - 14
        right_start = edge - max(right - left + 1 for left, right in spans)
        for (text, font, colour, top), (_, right) in zip(lines, spans):
            gc.SetFont(font, wx.Colour(colour))
            gc.DrawText(text, edge - 1 - right, top)

        # the icon, the temperature and the weather in one line, its ink centred on the card
        label, kind = get_condition(forecast.code)
        temperature = format_degrees(forecast.temperature)
        big, small = get_font(NOW_TEMPERATURE, True), get_font(10)
        reach_left, reach_right = get_icon_span(kind, forecast.day, NOW_ICON, theme)
        temperature_ink = get_ink_span(big, temperature)
        label_ink = get_ink_span(small, label)
        block = (reach_left + reach_right + NOW_GAP +
                 temperature_ink[1] - temperature_ink[0] + 1 + NOW_WORD_GAP +
                 label_ink[1] - label_ink[0] + 1)
        left = round(x + (width - block) / 2)
        # clear of the columns in a narrow window
        left = max(left_end + 12, min(left, right_start - 12 - block))
        centre = left + reach_left
        draw_weather_icon(gc, kind, centre, middle, NOW_ICON, theme, theme['face'],
                          forecast.day)
        text_left = centre + reach_right + NOW_GAP - temperature_ink[0]
        top = self.get_centred_top([(big, 0)], middle)
        self.draw_text(gc, temperature, text_left, top, NOW_TEMPERATURE, theme['text'],
                       bold=True)
        # the weather on the temperature's baseline
        label_left = text_left + temperature_ink[1] + 1 + NOW_WORD_GAP - label_ink[0]
        self.draw_text(gc, label, label_left, top + get_ink(big)[1] - get_ink(small)[1], 10,
                       theme['text'])

    def get_hour_start(self, forecast, day):
        try:
            return forecast.hours.index(datetime(day.year, day.month, day.day))
        except ValueError:
            return -1

    def draw_hours(self, gc, forecast, x, y, width):
        '''the shown day from 00 to 24; today marks the time now and dims the hours gone'''
        theme = self.theme
        self.fill_card(gc, x, y, width, HOURLY_HEIGHT)
        # the rows below placed from here, so the ink sits as far from the top as the bottom
        y += HOURLY_TOP
        moment = forecast.get_now()
        today = moment.date()
        shown = self.picked or today
        # a note in the pages' type, its caps where the 9 pt title's were
        lead, _ = self.draw_text(gc, 'Hourly \u00b7 ', x + 14, y + 9, 8, theme['dim'])
        # the date in a column as wide as its widest digits, so the day after it holds still
        gc.SetFont(get_font(8), wx.Colour(theme['dim']))
        slot = max(gc.GetTextExtent(f'{digit}{digit}')[0] for digit in range(10))
        self.draw_text(gc, shown.strftime('%d'), x + 14 + lead + slot, y + 9, 8, theme['dim'],
                       align='right')
        self.draw_text(gc, self.get_day_text(shown, today), x + 14 + lead + slot + 4, y + 9, 8,
                       theme['dim'])
        start = self.get_hour_start(forecast, shown)
        if start < 0:
            self.draw_text(gc, 'No hourly forecast for this day', x + width / 2, y + 64, 9,
                           theme['dim'], align='center')
            return
        end = min(len(forecast.hours), start + HOURS + 1)
        temperatures = [value for value in forecast.hour_temperatures[start:end]
                        if value is not None]
        if not temperatures:
            return
        low, high = min(temperatures), max(temperatures)
        spread = max(high - low, 4.0)
        middle = (high + low) / 2
        inner = width - 28
        # every 2 hours, every 3 in a narrow window
        step = next((step for step in HOUR_STEPS
                     if inner / (HOURS // step + 1) >= HOUR_ROOM), HOUR_STEPS[-1])
        left = x + 14 + inner / ((HOURS // step + 1) * 2)
        span = inner - (left - x - 14) * 2
        # the highest label clear of the title above it
        band_top, band_bottom = y + 52, y + 72
        # hours into the shown day: past its end for a day gone, before it for one to come
        hour_now = (moment - datetime(shown.year, shown.month, shown.day)).total_seconds() / 3600
        marker = left + span * hour_now / HOURS if 0 <= hour_now <= end - start - 1 else None

        def get_height(value):
            share = (value - middle) / spread + 0.5
            return band_bottom - share * (band_bottom - band_top)

        def place(index):
            return (left + span * index / HOURS,
                    get_height(forecast.hour_temperatures[start + index]))

        points = [(index, *place(index)) for index in range(end - start)
                  if forecast.hour_temperatures[start + index] is not None]
        for gone in (True, False):
            # the hours gone drawn fainter than the ones to come
            path = gc.CreatePath()
            drawn = False
            for (_, px, py), (index, qx, qy) in zip(points, points[1:]):
                if (index <= hour_now) != gone:
                    continue
                if not drawn:
                    path.MoveToPoint(px, py)
                    drawn = True
                path.AddLineToPoint(qx, qy)
            if drawn:
                colour = theme['rim'] if gone else theme['dim']
                gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(colour)).Width(1.6)
                                       .Join(wx.JOIN_ROUND).Cap(wx.CAP_ROUND)))
                gc.StrokePath(path)

        for index in range(0, end - start, step):
            value = forecast.hour_temperatures[start + index]
            if value is None:
                continue
            px, py = place(index)
            gone = index < hour_now - 1
            ink = theme['dim'] if gone else theme['text']
            # an hour's dot under the mark of now would show as a notch in it
            if marker is None or abs(px - marker) >= 7:
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.SetBrush(wx.Brush(wx.Colour(ink)))
                gc.DrawEllipse(px - 2.5, py - 2.5, 5, 5)
            self.draw_text(gc, format_degrees(value), px, py - 21, 10, ink, align='center')
            code = forecast.hour_codes[start + index]
            day = bool(forecast.hour_day[start + index]) if forecast.hour_day else True
            draw_weather_icon(gc, get_condition(code)[1], px, y + 90, 18, theme,
                              theme['face'], day)
            rain = forecast.hour_rain[start + index] if forecast.hour_rain else None
            if rain is not None and rain >= SHOWERS:
                self.draw_text(gc, f'{round(rain)}%', px, y + 101, 8,
                               RAIN[theme['titlebar_dark']], align='center')
            text = self.get_hour_text(forecast.hours[start + index])
            if index == HOURS:
                text = '24' if self.use24h else '12am'
            self.draw_text(gc, text, px, y + 116, 8, theme['dim'], align='center')

        if marker is not None:
            # now, between two hours on the line
            before = int(hour_now)
            after = min(before + 1, end - start - 1)
            first = forecast.hour_temperatures[start + before]
            second = forecast.hour_temperatures[start + after]
            if first is not None and second is not None:
                value = first + (second - first) * (hour_now - before)
                py = get_height(value)
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.SetBrush(wx.Brush(wx.Colour(theme['accent'])))
                gc.DrawEllipse(marker - 4.5, py - 4.5, 9, 9)

    def draw_days(self, gc, forecast, x, y, width, first, last):
        theme = self.theme
        tall = DAY_HEIGHT
        height = (last - first) * tall
        self.fill_card(gc, x, y, width, height)
        self.day_card = wx.Rect(x, y, width, height)
        today = forecast.get_now().date()
        # every day's range, so the bars hold still as the list scrolls
        values = [value for value in forecast.lows + forecast.highs if value is not None]
        if not values:
            return
        coldest, warmest = min(values), max(values)
        spread = max(warmest - coldest, 1.0)
        # the high just after the bar, in a column as wide as '-00°' that ends on the margin
        gc.SetFont(get_font(10), wx.BLACK)
        high_slot = gc.GetTextExtent('-00\u00b0')[0]
        bar_left, bar_right = x + 196, x + width - 14 - high_slot - 8
        gc.SetFont(get_font(10, True), wx.BLACK)
        date_slot = max(gc.GetTextExtent(f'{digit}{digit}')[0] for digit in range(10))
        name_ink, note_ink = get_ink(get_font(10)), get_ink(get_font(8))
        dark = theme['titlebar_dark']
        shown = self.picked or today
        self.day_rects = []

        for row, index in enumerate(range(first, last)):
            top = y + row * tall
            # the divider, or the card's rim on the first row, takes the top pixel;
            # the highlight and the text's middle are placed in what is left
            cy = top + 1 + (tall - 1) // 2
            day = forecast.days[index]
            past = day < today
            # divided as the World page's rows, lit 4 px inside the row
            if row:
                fill_rounded(gc, theme['rim'], x + 14, top, width - 28, 1, 0)
            rect = wx.Rect(x + DAY_INSET, top + 1 + DAY_INSET, width - DAY_INSET * 2,
                           tall - 1 - DAY_INSET * 2)
            self.day_rects.append((rect, day))
            # the day the hourly card shows tinged as a picked choice, as Local or UTC
            fill = theme['tint'] if day == shown else theme['control_hover'] \
                if day == self.hovered else theme['control'] if day == today else None
            if fill is not None:
                fill_rounded(gc, fill, rect.x, rect.y, rect.width, rect.height,
                             CARD_RADIUS - 2)
            colour = theme['dim'] if past else theme['text']
            code = forecast.day_codes[index] if index < len(forecast.day_codes) else None
            draw_weather_icon(gc, get_condition(code)[1], x + 26, cy, DAY_ICON, theme,
                              fill or theme['face'])

            rain = forecast.day_rain[index] if index < len(forecast.day_rain) else None
            note = f'Rain {round(rain)}%' if rain is not None and rain >= SHOWERS else ''
            # a name over its note, their ink centred on the row as the World page's;
            # the name alone in the middle on a day with no note
            name_height = name_ink[1] - name_ink[0] + 1
            name_top = cy - (name_height + DAY_LINE_GAP + note_ink[1] - note_ink[0] + 1) // 2 \
                if note else cy - name_height // 2
            note_top = name_top + name_height + DAY_LINE_GAP
            left = x + DAY_TEXT
            gc.SetFont(get_font(10, True), wx.Colour(colour))
            digits = day.strftime('%d')
            # the date's digits right-aligned in a column of their own
            gc.DrawText(digits, left + date_slot - gc.GetTextExtent(digits)[0],
                        name_top - name_ink[0])
            gc.SetFont(get_font(10, day == today), wx.Colour(colour))
            gc.DrawText(self.get_day_text(day, today), left + date_slot + 5,
                        name_top - name_ink[0])
            if note:
                gc.SetFont(get_font(8), wx.Colour(theme['dim']))
                gc.DrawText(note, left, note_top - note_ink[0])

            low, high = forecast.lows[index], forecast.highs[index]
            self.draw_text(gc, format_degrees(high), bar_right + 8, cy, 10, colour, middle=True)
            # the low as the high: dim marks a day gone, not a lesser reading
            self.draw_text(gc, format_degrees(low), bar_left - 8, cy, 10, colour,
                           align='right', middle=True)
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(theme['rim'])))
            gc.DrawRoundedRectangle(bar_left, cy - 2, bar_right - bar_left, 4, 2)
            if low is not None and high is not None:
                start = bar_left + (bar_right - bar_left) * (low - coldest) / spread
                end = bar_left + (bar_right - bar_left) * (high - coldest) / spread
                end = max(end, start + 4)
                warm = mix(COLD[dark], theme['warn'], (high - coldest) / spread)
                cool = mix(COLD[dark], theme['warn'], (low - coldest) / spread)
                gc.SetBrush(gc.CreateLinearGradientBrush(start, cy, end, cy, cool, warm))
                gc.DrawRoundedRectangle(start, cy - 2, end - start, 4, 2)

        if self.fade and self.day_count > self.day_visible:
            # where the rows in sight sit among all the days
            track = height - DAY_INSET * 2
            thumb = max(12, round(track * self.day_visible / self.day_count))
            share = self.day_offset / (self.day_count - self.day_visible)
            rim = wx.Colour(theme['rim'])
            colour = wx.Colour(rim.Red(), rim.Green(), rim.Blue(), round(255 * self.fade))
            fill_rounded(gc, colour, x + width - 6, y + DAY_INSET + round((track - thumb) *
                         share), 3, thumb, 1)
