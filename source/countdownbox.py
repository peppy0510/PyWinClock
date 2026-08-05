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
from utilities import get_font


# 입력창 양옆 버튼이 한 번에 옮기는 시간.
STEP_SECONDS = 60
# 99:59:59. 입력칸이 여덟 자리라 이보다 큰 값은 들어올 자리가 없다.
MAX_SECONDS = 359999
FIELD_CHARS = '0123456789:'
BLINK_INTERVAL = 0.5
WARN_SECONDS = 10
BUTTON_GAP = 10
# 고리 반지름은 가로 폭만 보고 정한다. 세로까지 보면 '높이 -> 반지름 -> 높이'
# 순환이 생겨 특정 창 크기에서 값이 수렴하지 않는다. 세로는 넘칠 때만 깎는다.
RING_RATIO = 0.38
# 고리 획 두께가 반지름 밖으로 반씩 나가므로 캔버스 높이에 그만큼 더 준다.
RING_PAD = 10
# 고리 캔버스가 제 둘레에 두는 여백.
CANVAS_MARGIN = 8
# 시간과 그 아래 입력칸 사이.
FIELD_GAP = 8
# 고리와 버튼 줄 사이. 고리는 아래로 둥글게 물러나므로 같은 값을 줘도 곧은
# 글자 밑동보다 더 붙어 보인다. 그만큼 한 뼘 더 둔다.
BUTTON_TOP_GAP = 14
# 창이 낮아 자리를 다 써야 할 때도 위아래로 남겨 두는 여백. 이게 없으면
# 버튼이 창 밑동에 딱 붙는다.
EDGE_GAP = 14


def format_duration(seconds):
    return '%02d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def parse_duration(text):
    '''적힌 만큼만 읽는다. 한 토막이면 초, 두 토막이면 분·초, 세 토막이면
    시·분·초다. 빈 토막은 0 으로 본다. `90` 도 `1:90` 도 받아 뒤에서 자리를
    옮겨 준다.'''
    parts = text.strip().split(':')
    if not parts or len(parts) > 3:
        return None
    try:
        values = [int(part) if part else 0 for part in parts]
    except ValueError:
        return None
    if any(value < 0 for value in values):
        return None
    while len(values) < 3:
        values.insert(0, 0)
    return min(MAX_SECONDS, values[0] * 3600 + values[1] * 60 + values[2])


class CountdownCanvas(TimerCanvas):

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.total = 0
        self.finished = False
        self.blink = False
        # 입력칸을 시간 바로 아래에 얹으려면 그 시간이 어디서 끝나는지 알아야 한다.
        # 글꼴 크기가 창을 따라 변하므로 그릴 때마다 적어 둔다.
        self.time_bottom = None
        # 시간 아래에 쌓이는 입력칸·버튼의 높이. 절반만큼 시간을 위로 밀어야
        # 쌓은 덩어리 전체가 고리 가운데에 온다.
        self.stack_space = 0

    def get_time_colour(self):
        if self.finished:
            return self.theme['second'] if self.blink else self.theme['dim']
        return self.theme['text']

    def get_sub_colour(self):
        return self.get_time_colour() if self.finished else self.theme['dim']

    def get_radius(self, width, height):
        return min(width * RING_RATIO, height / 2 - RING_PAD / 2)

    def get_time_size(self, width, height):
        '''글자는 고리 안에 들어가야 한다. 상자만 보고 잡으면 **창이 가로로 길
        때** 고리는 세로에 갇히는데 글자만 폭을 따라 커져 고리 밖으로 삐져나온다.
        고리가 폭을 다 쓰던 때의 비율(반지름 = 폭 x RING_RATIO, 글자 = 폭 /
        WIDTH_DIVISOR)을 그대로 반지름에 적용하면, 어느 쪽이 고리를 정하든
        글자와 고리의 크기 비가 늘 같다.'''
        return max(14, int(self.get_radius(width, height) /
                           (RING_RATIO * self.WIDTH_DIVISOR)))

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        radius = self.get_radius(width, height)
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

        self.time_bottom = self.draw_time(gc, width, height)

        if self.finished:
            size = self.get_time_size(width, height)
            self.draw_centered_text(gc, 'DONE', cx,
                                    self.time_bottom + self.stack_space + FIELD_GAP,
                                    get_font(max(9, int(size * 0.34)), bold=True),
                                    theme['second'])


class FieldBox(Canvas):
    '''둥근 판 하나에 시간 입력칸과 좌우 증감 버튼을 함께 담는다. 네이티브
    TextCtrl 은 모서리를 굴릴 수 없어, 판은 캔버스로 그리고 입력칸은 그 안쪽
    가운데에 앉힌다. 버튼은 판이 비쳐야 하므로 채움 없는 ghost 로 둔다.'''

    WIDTH = 148
    HEIGHT = 34
    PADDING = 3

    def __init__(self, parent, theme, make_step):
        super().__init__(parent, theme)
        size = self.HEIGHT - self.PADDING * 2
        self.minus = RoundButton(self, theme, 'minus', make_step(-STEP_SECONDS),
                                 tone='ghost', size=size)
        self.plus = RoundButton(self, theme, 'plus', make_step(STEP_SECONDS),
                                tone='ghost', size=size)
        self.field = wx.TextCtrl(self, value='00:05:00',
                                 style=wx.TE_PROCESS_ENTER | wx.NO_BORDER | wx.TE_CENTER)
        self.field.SetMaxLength(len('00:00:00'))
        self.field.Bind(wx.EVT_CHAR, self.on_char)
        self.buttons = (self.minus, self.plus)
        self.SetMinSize(wx.Size(self.WIDTH, self.HEIGHT))
        # 첫 그림이 끝나야 얹힐 자리를 알 수 있다. 그때까지 구석에 비치지 않게 숨긴다.
        self.Hide()
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_char(self, event):
        '''숫자와 자리 구분 콜론만 받는다. 지우기·이동 키와 단축키는 그대로 흘린다.'''
        code = event.GetKeyCode()
        if code >= wx.WXK_START or code < 32 or code == wx.WXK_DELETE:
            event.Skip()
        elif event.HasModifiers():
            event.Skip()
        elif chr(code) in FIELD_CHARS:
            event.Skip()

    def on_size(self, event):
        width, height = self.GetClientSize()
        size = height - self.PADDING * 2
        self.minus.SetSize(self.PADDING, self.PADDING, size, size)
        self.plus.SetSize(width - self.PADDING - size, self.PADDING, size, size)
        # 단일 라인 TextCtrl 은 높이를 키우면 글자가 위로 붙는다. 제 높이 그대로 두고
        # 두 버튼 사이 가운데에 앉힌다.
        left = self.PADDING + size
        text_height = self.field.GetBestSize()[1]
        self.field.SetSize(left, (height - text_height) // 2,
                           max(0, width - left * 2), text_height)
        event.Skip()

    def set_theme(self, theme):
        super().set_theme(theme)
        for button in self.buttons:
            button.set_theme(theme)
        self.field.SetBackgroundColour(wx.Colour(theme['control']))
        self.field.SetForegroundColour(wx.Colour(theme['text']))
        self.field.SetFont(get_font(10))

    def draw(self, gc, width, height):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(self.theme['control'])))
        gc.DrawRoundedRectangle(0, 0, width, height, height / 2)


class CountdownBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.total = 0
        self.remaining = 0
        self.running = False
        self.deadline = 0.0
        self.finished_at = 0.0

        self.canvas = CountdownCanvas(self, theme)
        # 사이저에 담지 않고 시간 바로 아래에 얹는다. 캔버스의 자식이라야
        # 고리를 다시 칠할 때 덧칠해 지워지지 않는다.
        self.fieldbox = FieldBox(self.canvas, theme, self.make_step)
        self.canvas.stack_space = FIELD_GAP + FieldBox.HEIGHT
        self.field = self.fieldbox.field
        self.field.Bind(wx.EVT_TEXT, lambda event: self.on_field())
        self.field.Bind(wx.EVT_TEXT_ENTER, lambda event: self.drop_focus())
        self.field.Bind(wx.EVT_KILL_FOCUS, self.on_field_done)
        # 입력칸 밖 아무 데나 누르면 손을 뗀다. 빈 바탕을 눌러도 wx 가 포커스를
        # 첫 입력칸으로 돌려주므로 페이지 자신에도 걸어 둔다.
        self.canvas.Bind(wx.EVT_LEFT_DOWN, lambda event: self.drop_focus())
        self.Bind(wx.EVT_LEFT_DOWN, lambda event: self.drop_focus())

        self.start_button = RoundButton(self, theme, 'play', self.on_start, tone='primary')
        self.reset_button = RoundButton(self, theme, 'reset', self.on_reset)
        self.buttons = (self.start_button, self.reset_button)

        control_row = wx.BoxSizer(wx.HORIZONTAL)
        control_row.AddStretchSpacer()
        control_row.Add(self.start_button, 0, wx.LEFT | wx.RIGHT, BUTTON_GAP)
        control_row.Add(self.reset_button, 0, wx.LEFT | wx.RIGHT, BUTTON_GAP)
        control_row.AddStretchSpacer()

        # 캔버스를 고리 높이에 딱 맞춰 둔다. 캔버스가 늘어나면 고리 아래에
        # 보이지 않는 여백이 생겨, 눈에는 버튼 위쪽만 넓어 보인다. 고리와 버튼
        # 줄 사이는 창 크기와 상관없이 고정하고, 남는 세로는 덩어리 위아래로
        # 똑같이 나눈다.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.canvas, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, CANVAS_MARGIN)
        sizer.AddSpacer(BUTTON_TOP_GAP)
        sizer.Add(control_row, 0, wx.EXPAND)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SHOW, self.on_show)

        self.apply_theme(theme)
        self.on_field()

    def drop_focus(self):
        '''입력칸에서 손을 뗀다. 포커스가 남아 있으면 깜빡이는 커서가 계속 보인다.
        패널 자신이 받아야 포커스가 다시 자식 입력칸으로 흘러가지 않는다.'''
        self.SetFocusIgnoringChildren()

    def on_show(self, event):
        # 페이지가 뜨면 wx 가 첫 입력칸에 포커스를 준다. 누르지도 않았는데
        # 커서가 깜빡이므로 곧바로 되돌린다.
        if event.IsShown():
            wx.CallAfter(self.drop_focus)
        event.Skip()

    def on_size(self, event):
        '''고리는 가로 폭이 정하므로 캔버스 높이도 거기서 나온다. 다만 그
        높이를 그대로 요구하면 **창이 가로로 길 때 캔버스가 세로를 다 먹어
        버튼 줄이 화면 밖으로 밀려난다.** 버튼 줄과 가장자리 여백이 쓸 자리를
        먼저 떼어 두고 남는 만큼만 준다. 페이지 높이는 창이 정하는 값이라
        여기에 되먹임 고리는 생기지 않는다.

        ★버튼 높이는 반드시 `GetMinSize`. 자리가 모자라면 사이저가 버튼을
        최소 크기 아래로 찌그러뜨리는데, 그 찌그러진 `GetSize` 를 보고 자리를
        다시 나누면 캔버스가 더 커지고 버튼은 더 찌그러진다 — 되먹임으로
        버튼이 순식간에 몇 픽셀까지 작아진다.'''
        width, height = self.GetClientSize()
        if width <= 0:
            return event.Skip()

        ring = int((width - CANVAS_MARGIN * 2) * RING_RATIO * 2) + RING_PAD
        room = (height - EDGE_GAP * 2 - BUTTON_TOP_GAP -
                self.start_button.GetMinSize()[1])
        target = max(0, min(ring, room))
        if self.canvas.GetMinSize()[1] != target:
            self.canvas.SetMinSize(wx.Size(-1, target))
            self.Layout()
        event.Skip()

    def apply_theme(self, theme):
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.canvas.set_theme(theme)
        self.fieldbox.set_theme(theme)
        for button in self.buttons:
            button.set_theme(theme)
        self.Refresh()

    def make_step(self, delta):
        def apply():
            # 먼저 멈춰야 on_field 가 값을 다시 읽는다. 0 아래로는 내려가지 않는다.
            seconds = min(MAX_SECONDS,
                          max(0, (parse_duration(self.field.GetValue()) or 0) + delta))
            self.stop()
            self.field.SetValue(format_duration(seconds))
            self.drop_focus()
        return apply

    def stop(self):
        self.running = False
        self.finished_at = 0.0
        self.start_button.set_icon('play')

    def on_field(self):
        if self.running:
            return
        seconds = parse_duration(self.field.GetValue())
        self.total = seconds or 0
        self.remaining = self.total
        self.tick()

    def on_field_done(self, event):
        '''손을 떼는 순간 적힌 것을 해석해 00:00:00 꼴로 다시 적는다.
        `90` 은 1 분 30 초로, `0:0` 은 0 으로 자리를 옮겨 준다.'''
        text = format_duration(parse_duration(self.field.GetValue()) or 0)
        if text != self.field.GetValue():
            # ChangeValue 는 EVT_TEXT 를 다시 일으키지 않으므로 직접 알린다.
            self.field.ChangeValue(text)
            self.on_field()
        event.Skip()

    def on_start(self):
        self.drop_focus()
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
        self.start_button.set_icon('pause')

    def on_reset(self):
        self.drop_focus()
        self.stop()
        self.on_field()

    def place_field(self):
        '''시간 글자 바로 아래, 가로 가운데. 글꼴이 창을 따라 커지므로
        지난 그림이 적어 둔 시간의 끝자리를 보고 따라간다.'''
        bottom = self.canvas.time_bottom
        if bottom is None:
            return
        width = self.canvas.GetClientSize()[0]
        size = self.fieldbox.GetMinSize()
        # 사이저 밖이라 자리와 크기를 직접 준다. 첫 그림 전에는 숨겨 두었다.
        rect = wx.Rect((width - size[0]) // 2, int(bottom) + FIELD_GAP, *size)
        if rect != self.fieldbox.GetRect():
            self.fieldbox.SetSize(rect)
        if not self.fieldbox.IsShown():
            self.fieldbox.Show()

    def tick(self):
        if self.running:
            self.remaining = max(0.0, self.deadline - time.perf_counter())
            if self.remaining <= 0:
                self.running = False
                self.finished_at = time.perf_counter()
                self.start_button.set_icon('play')
                wx.Bell()

        self.canvas.total = self.total
        self.canvas.seconds = self.remaining
        self.canvas.finished = bool(self.finished_at)
        if self.finished_at:
            elapsed = time.perf_counter() - self.finished_at
            self.canvas.blink = int(elapsed / BLINK_INTERVAL) % 2 == 0
        self.place_field()
        self.canvas.Refresh()
