# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import time
import wx

from controls import RoundButton
from utilities import Canvas
from utilities import TimerCanvas
from utilities import format_timer
from utilities import get_font


BUTTON_GAP = 10
# 캔버스와 랩 표가 창 가장자리에 두는 여백.
MARGIN = 8
# 버튼 줄 위아래로 똑같이 두는 자리.
ROW_GAP = 16
# 랩 표는 창 폭을 다 쓰지 않고 이만큼만 차지한 채 가운데에 선다.
TABLE_WIDTH = 300


class StopwatchCanvas(TimerCanvas):
    '''캔버스를 글자 높이에 맞춰 재우므로 글꼴은 가로 폭만 보고 정한다.
    세로까지 보면 '높이 -> 글꼴 -> 높이' 순환이 생겨 값이 수렴하지 않는다.'''

    def get_time_size(self, width, height):
        return max(14, int(width / self.WIDTH_DIVISOR))


class LapList(Canvas):
    '''Laps / Time / Total 세 열의 랩 표. wx.ListCtrl 은 Windows 에서
    배경색을 안 따르므로 여기서도 직접 그린다.'''

    HEADER_HEIGHT = 28
    ROW_HEIGHT = 24
    PADDING = 16
    TAG_OFFSET = 30

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.rows = []
        self.offset = 0
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)

    def clear(self):
        self.rows = []
        self.offset = 0
        self.Refresh()

    def set_totals(self, totals):
        splits = [total - (totals[index - 1] if index else 0)
                  for index, total in enumerate(totals)]
        # 랩이 하나뿐이거나 전부 같으면 최고·최저를 나눌 의미가 없다.
        fastest = splits.index(min(splits)) if splits else -1
        slowest = splits.index(max(splits)) if splits else -1
        if fastest == slowest:
            fastest = slowest = -1

        self.rows = []
        for index, total in enumerate(totals):
            tag = ''
            if index == fastest:
                tag = 'Fastest'
            elif index == slowest:
                tag = 'Slowest'
            self.rows.insert(0, ('%d' % (index + 1), tag,
                                 format_timer(splits[index]), format_timer(total)))
        self.offset = 0
        self.Refresh()

    def get_visible_count(self):
        height = self.GetClientSize()[1] - self.HEADER_HEIGHT
        return max(0, int(height // self.ROW_HEIGHT))

    def on_wheel(self, event):
        limit = max(0, len(self.rows) - self.get_visible_count())
        offset = min(limit, max(0, self.offset - (1 if event.GetWheelRotation() > 0 else -1)))
        if offset != self.offset:
            self.offset = offset
            self.Refresh()

    def get_columns(self, width):
        # 숫자 열은 오른쪽에 맞춘다. 마지막 열의 오른쪽 끝이 왼쪽 첫 열과 같은
        # 만큼 안으로 들어와야 한 줄의 좌우 여백이 같아 보인다.
        return (self.PADDING, self.PADDING + self.TAG_OFFSET,
                self.PADDING + (width - self.PADDING * 2) * 0.62,
                width - self.PADDING)

    def draw_right(self, gc, text, right, y):
        gc.DrawText(text, right - gc.GetTextExtent(text)[0], y)

    def draw(self, gc, width, height):
        theme = self.theme
        columns = self.get_columns(width)

        gc.SetFont(get_font(9), wx.Colour(theme['dim']))
        top = (self.HEADER_HEIGHT - gc.GetTextExtent('0')[1]) / 2
        gc.DrawText('Laps', columns[0], top)
        self.draw_right(gc, 'Time', columns[2], top)
        self.draw_right(gc, 'Total', columns[3], top)

        gc.SetPen(wx.Pen(wx.Colour(theme['rim']), 1))
        gc.StrokeLine(columns[0], self.HEADER_HEIGHT - 0.5,
                      columns[3], self.HEADER_HEIGHT - 0.5)

        top = self.HEADER_HEIGHT
        for row in self.rows[self.offset:]:
            if top + self.ROW_HEIGHT > height:
                break
            self.draw_row(gc, columns, row, top)
            top += self.ROW_HEIGHT

    def draw_row(self, gc, columns, row, top):
        theme = self.theme
        font = get_font(9)
        gc.SetFont(font, wx.Colour(theme['dim']))
        y = top + (self.ROW_HEIGHT - gc.GetTextExtent('0')[1]) / 2
        gc.DrawText(row[0], columns[0], y)
        gc.DrawText(row[1], columns[1], y)
        gc.SetFont(font, wx.Colour(theme['text']))
        self.draw_right(gc, row[2], columns[2], y)
        self.draw_right(gc, row[3], columns[3], y)


class StopwatchBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.running = False
        self.elapsed = 0.0
        self.started_at = 0.0
        self.totals = []

        self.canvas = StopwatchCanvas(self, theme)
        self.start_button = RoundButton(self, theme, 'play', self.on_start, tone='primary')
        self.lap_button = RoundButton(self, theme, 'flag', self.on_lap)
        self.reset_button = RoundButton(self, theme, 'reset', self.on_reset)
        self.buttons = (self.start_button, self.lap_button, self.reset_button)
        self.laps = LapList(self, theme)
        self.laps.SetMinSize(wx.Size(TABLE_WIDTH, -1))

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        for button in self.buttons:
            row.Add(button, 0, wx.LEFT | wx.RIGHT, BUTTON_GAP)
        row.AddStretchSpacer()

        # 캔버스를 글자 높이에 딱 맞춰 두어야 버튼 줄의 위 여백이 안 보이는
        # 빈자리까지 껴안지 않는다. 남는 세로는 위쪽과 랩 표가 나눠 갖는다.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.canvas, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, MARGIN)
        sizer.Add(row, 0, wx.EXPAND | wx.TOP, ROW_GAP)
        sizer.AddSpacer(ROW_GAP)
        lap_row = wx.BoxSizer(wx.HORIZONTAL)
        lap_row.AddStretchSpacer()
        lap_row.Add(self.laps, 0, wx.EXPAND)
        lap_row.AddStretchSpacer()
        sizer.Add(lap_row, 1, wx.EXPAND | wx.BOTTOM, MARGIN)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.apply_theme(theme)

    def on_size(self, event):
        width = self.GetClientSize()[0] - MARGIN * 2
        if width > 0:
            target = self.canvas.get_time_height(width, 0)
            if self.canvas.GetMinSize()[1] != target:
                self.canvas.SetMinSize(wx.Size(-1, target))
                self.Layout()
        event.Skip()

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.laps.set_theme(theme)
        for button in self.buttons:
            button.set_theme(theme)
        self.Refresh()

    def get_elapsed(self):
        if self.running:
            return self.elapsed + (time.perf_counter() - self.started_at)
        return self.elapsed

    def on_start(self):
        if self.running:
            self.elapsed = self.get_elapsed()
            self.running = False
            self.start_button.set_icon('play')
        else:
            self.started_at = time.perf_counter()
            self.running = True
            self.start_button.set_icon('pause')

    def on_lap(self):
        elapsed = self.get_elapsed()
        if elapsed <= 0:
            return
        self.totals.append(elapsed)
        self.laps.set_totals(self.totals)

    def on_reset(self):
        self.running = False
        self.elapsed = 0.0
        self.start_button.set_icon('play')
        self.totals = []
        self.laps.clear()
        self.tick()

    def tick(self):
        self.canvas.seconds = self.get_elapsed()
        self.canvas.Refresh()
