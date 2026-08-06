# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

네이티브 wx.Button / wx.CheckBox 는 Windows 에서 배경색을 따르지 않아
다크 테마에서 혼자 밝게 남는다. 캔버스로 직접 그려 대체한다.
'''


import math
import wx

from utilities import CARD_HEIGHT
from utilities import CARD_RADIUS
from utilities import ROUND_SIZE
from utilities import Canvas
from utilities import draw_card_rim
from utilities import get_font
from utilities import mix
from utilities import shade


class Pressable(Canvas):
    '''캔버스 버튼들이 공유하는 hover / press 상태.'''

    def __init__(self, parent, theme, on_click):
        super().__init__(parent, theme)
        self.on_click = on_click
        self.hovered = False
        self.pressed = False
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)

    def on_down(self, event):
        self.pressed = True
        self.Refresh()

    def on_up(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self.Refresh()
        if was_pressed and self.hovered and self.on_click:
            self.on_click()

    def on_enter(self, event):
        self.hovered = True
        self.Refresh()

    def on_leave(self, event):
        self.hovered = False
        self.pressed = False
        self.Refresh()


class RoundButton(Pressable):
    '''Windows 시계와 같은 원형 아이콘 버튼. 글자 대신 아이콘을 그린다.
    tone 은 원의 채움색과 아이콘 색을 고르는 이름이다. 지도처럼 그림 위에 얹히는
    자리에는 평소엔 아이콘만 두고 호버 때만 회색이 비치는 ghost 를 쓴다.'''

    TONES = {
        'plain': ('control', 'text'),
        'primary': ('accent', '#ffffff'),
        'ghost': (None, 'dim'),
    }

    # 모서리를 굴린 네모로 그리고 싶을 때 쓰는 반지름. None 이면 동그라미다.
    CORNER = 9

    def __init__(self, parent, theme, icon, on_click, tone='plain', size=ROUND_SIZE,
                 square=False, backdrop=None):
        super().__init__(parent, theme, on_click)
        self.icon = icon
        self.tone = tone
        self.square = square
        # 뒤가 한 색으로 덮인 판 위라면 그 색만 깔면 된다. 부모 그림을 다시
        # 부르는 draw_backdrop 은 그리기 상태가 얽혀 화면이 깨지기 쉽다.
        self.backdrop = backdrop
        self.SetMinSize(wx.Size(size, size))

    def set_backdrop(self, colour):
        self.backdrop = colour
        self.Refresh()

    def set_icon(self, icon):
        if icon != self.icon:
            self.icon = icon
            self.Refresh()

    def set_tone(self, tone):
        if tone != self.tone:
            self.tone = tone
            self.Refresh()

    def draw(self, gc, width, height):
        theme = self.theme
        radius = min(width, height) / 2 - 1
        cx, cy = width / 2, height / 2

        key, mark = self.TONES[self.tone]
        # 채운 톤이라도 굴린 모서리 바깥은 비어 있다. 그 자리를 채워 두지 않으면
        # 페이지 배경색이 그대로 드러나 네모난 검은 자국이 남는다.
        if self.backdrop is not None:
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(self.backdrop)))
            gc.DrawRectangle(0, 0, width, height)
        else:
            self.draw_backdrop(gc)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(self.get_fill(key)))
        if self.square:
            gc.DrawRoundedRectangle(cx - radius, cy - radius,
                                    radius * 2, radius * 2, self.CORNER)
        else:
            gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # 아이콘 색은 테마의 이름일 수도, 테마를 타지 않는 색 자체일 수도 있다.
        self.draw_icon(gc, cx, cy, radius, wx.Colour(theme.get(mark, mark)))

    def get_fill(self, key):
        if key is None:
            # 채움색이 없으면 평소엔 비워 두고 호버·눌림에만 회색을 비친다.
            grey = wx.Colour(self.theme['tick'])
            alpha = 96 if self.pressed else 64 if self.hovered else 0
            return wx.Colour(grey.Red(), grey.Green(), grey.Blue(), alpha)

        fill = self.theme[key]
        if self.pressed:
            fill = shade(fill, 0.85)
        elif self.hovered:
            fill = shade(fill, 1.16)
        return wx.Colour(fill)

    def draw_icon(self, gc, cx, cy, radius, colour):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(colour))

        if self.icon == 'play':
            path = gc.CreatePath()
            # 삼각형은 무게 중심이 왼쪽으로 쏠려 보여 조금 오른쪽으로 민다.
            path.MoveToPoint(cx - radius * 0.19, cy - radius * 0.40)
            path.AddLineToPoint(cx + radius * 0.44, cy)
            path.AddLineToPoint(cx - radius * 0.19, cy + radius * 0.40)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'pause':
            for sign in (-1, 1):
                gc.DrawRectangle(cx + sign * radius * 0.24 - radius * 0.08,
                                 cy - radius * 0.38, radius * 0.16, radius * 0.76)

        elif self.icon == 'flag':
            gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.11))))
            gc.StrokeLine(cx - radius * 0.28, cy - radius * 0.44,
                          cx - radius * 0.28, cy + radius * 0.46)
            gc.SetPen(wx.TRANSPARENT_PEN)
            path = gc.CreatePath()
            path.MoveToPoint(cx - radius * 0.28, cy - radius * 0.40)
            path.AddLineToPoint(cx + radius * 0.40, cy - radius * 0.14)
            path.AddLineToPoint(cx - radius * 0.28, cy + radius * 0.12)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon in ('plus', 'minus'):
            # 가로획이 상자 한가운데를 지나면 아래로 처져 보인다. 한 픽셀 올린다.
            cy -= 1
            arm = radius * 0.44
            gc.SetPen(wx.Pen(colour, max(1, round(radius * 0.13))))
            gc.StrokeLine(cx - arm, cy, cx + arm, cy)
            if self.icon == 'plus':
                gc.StrokeLine(cx, cy - arm, cx, cy + arm)
            gc.SetPen(wx.TRANSPARENT_PEN)

        elif self.icon == 'pencil':
            # 왼쪽 아래 촉에서 오른쪽 위 꼭지까지 기울어진 몸통 하나로 그린다.
            length = radius * 0.60
            half = radius * 0.15
            neck = radius * 0.26
            dx, dy = math.cos(math.radians(-45)), math.sin(math.radians(-45))
            px, py = -dy, dx
            tip = (cx - dx * length, cy - dy * length)
            end = (cx + dx * length, cy + dy * length)

            path = gc.CreatePath()
            path.MoveToPoint(tip[0], tip[1])
            path.AddLineToPoint(tip[0] + dx * neck + px * half,
                                tip[1] + dy * neck + py * half)
            path.AddLineToPoint(end[0] + px * half, end[1] + py * half)
            path.AddLineToPoint(end[0] - px * half, end[1] - py * half)
            path.AddLineToPoint(tip[0] + dx * neck - px * half,
                                tip[1] + dy * neck - py * half)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'back':
            gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.12))))
            gc.StrokeLine(cx - radius * 0.36, cy, cx + radius * 0.38, cy)
            gc.SetPen(wx.TRANSPARENT_PEN)
            path = gc.CreatePath()
            path.MoveToPoint(cx - radius * 0.44, cy)
            path.AddLineToPoint(cx - radius * 0.06, cy - radius * 0.28)
            path.AddLineToPoint(cx - radius * 0.06, cy + radius * 0.28)
            path.CloseSubpath()
            gc.FillPath(path)

        elif self.icon == 'reset':
            self.draw_reset(gc, cx, cy, radius, colour)

    def draw_reset(self, gc, cx, cy, radius, colour):
        ring = radius * 0.40
        # 위쪽을 터놓은 원호에 반시계 방향 화살촉을 붙인다.
        path = gc.CreatePath()
        path.AddArc(cx, cy, ring, math.radians(300), math.radians(240), True)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(wx.Pen(colour, max(2, int(radius * 0.12))))
        gc.StrokePath(path)

        angle = math.radians(300)
        x, y = cx + ring * math.cos(angle), cy + ring * math.sin(angle)
        dx, dy = math.sin(angle), -math.cos(angle)
        size = radius * 0.24
        path = gc.CreatePath()
        path.MoveToPoint(x + dx * size, y + dy * size)
        path.AddLineToPoint(x - dy * size * 0.8, y + dx * size * 0.8)
        path.AddLineToPoint(x + dy * size * 0.8, y - dx * size * 0.8)
        path.CloseSubpath()
        gc.SetBrush(wx.Brush(colour))
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.FillPath(path)


class CardBase(Pressable):
    '''Windows 11 설정과 같은 카드 한 줄. 바탕과 제목·설명은 여기서 그리고,
    오른쪽 끝의 조작부만 자식이 채운다. 조작부가 자리를 먼저 잡고 남는 왼쪽을
    글자가 쓰므로, 제목은 조작부가 넓어지는 만큼 말없이 잘린다.'''

    PADDING = 14
    # 제목이 조작부에 닿지 않게 두는 자리.
    LABEL_GAP = 12

    def __init__(self, parent, theme, label, description, on_change=None):
        super().__init__(parent, theme, self.activate)
        self.label = label
        self.description = description
        self.on_change = on_change
        self.SetMinSize(wx.Size(-1, CARD_HEIGHT))

    def activate(self):
        '''카드를 눌렀을 때 값을 바꾸는 자리.'''

    def notify(self):
        self.Refresh()
        if self.on_change:
            self.on_change()

    def draw(self, gc, width, height):
        theme = self.theme
        fill = theme['face']
        if self.pressed:
            fill = shade(fill, 0.94)
        elif self.hovered:
            fill = shade(fill, 1.12)

        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(fill)))
        gc.DrawRoundedRectangle(0, 0, width, height, CARD_RADIUS)
        draw_card_rim(gc, theme['rim'], 0, 0, width, height)

        label_right = self.draw_control(gc, width, height) - self.LABEL_GAP
        gc.SetFont(get_font(10), wx.Colour(theme['text']))
        title_height = gc.GetTextExtent(self.label)[1]
        top = (height - title_height - 15) / 2
        gc.Clip(self.PADDING, 0, max(0, label_right - self.PADDING), height)
        gc.DrawText(self.label, self.PADDING, top)
        gc.SetFont(get_font(8), wx.Colour(theme['dim']))
        gc.DrawText(self.description, self.PADDING, top + title_height + 1)
        gc.ResetClip()

    def draw_control(self, gc, width, height):
        '''오른쪽 끝에서부터 조작부를 그리고 그 왼쪽 끝 x 를 돌려준다.'''
        return width - self.PADDING


class SettingCard(CardBase):
    '''오른쪽 끝에 On/Off 토글을 둔 카드. 카드 어디를 눌러도 토글된다.'''

    TRACK_WIDTH = 38
    TRACK_HEIGHT = 20

    value = False

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = bool(value)
        self.Refresh()

    def activate(self):
        self.value = not self.value
        self.notify()

    def draw_control(self, gc, width, height):
        theme = self.theme
        switch_left = width - self.PADDING - self.TRACK_WIDTH
        state = 'On' if self.value else 'Off'
        gc.SetFont(get_font(9), wx.Colour(theme['dim']))
        state_width, state_height = gc.GetTextExtent(state)[:2]
        gc.DrawText(state, switch_left - state_width - 8, (height - state_height) / 2)
        # 세로 자리는 반 칸 없이 딱 떨어져야 알약 위아래가 흐려지지 않는다.
        self.draw_switch(gc, switch_left, round((height - self.TRACK_HEIGHT) / 2))
        return switch_left - state_width - 8

    def draw_switch(self, gc, left, top):
        theme = self.theme
        radius = self.TRACK_HEIGHT / 2
        gc.SetPen(wx.TRANSPARENT_PEN)

        # 선을 두르면 1px 획이 화소 경계에 반씩 걸려 아래쪽 곡선이 각져 보이고
        # 핸들과도 반 칸 어긋난다. 채운 알약 위에 한 칸 작은 알약을 겹쳐 테를 만든다.
        if self.value:
            gc.SetBrush(wx.Brush(wx.Colour(theme['accent'])))
            gc.FillPath(self.get_track(gc, left, top, 0))
        else:
            gc.SetBrush(wx.Brush(wx.Colour(theme['dim'])))
            gc.FillPath(self.get_track(gc, left, top, 0))
            gc.SetBrush(wx.Brush(wx.Colour(theme['bg'])))
            gc.FillPath(self.get_track(gc, left, top, 1))

        knob = radius - 4
        x = left + (self.TRACK_WIDTH - radius if self.value else radius)
        gc.SetBrush(wx.Brush(wx.Colour('#ffffff' if self.value else theme['text'])))
        gc.DrawEllipse(x - knob, top + radius - knob, knob * 2, knob * 2)

    def get_track(self, gc, left, top, inset):
        '''반원 둘을 직선으로 이은 알약. 둥근 사각형은 반지름이 높이의 절반일 때
        호와 직선이 만나는 자리가 각져 보인다.

        밑동 좌우가 위보다 살짝 각져 보이는 것은 이 경로 탓이 아니다. 원 둘 +
        네모로 다시 그려 봐도 화소가 한 점 다르지 않았다 — GDI+ 가 맨 윗줄과
        맨 아랫줄의 안티에일리어싱을 다르게 얹는다(실측: 꽉 찬 구간이 위 18px,
        아래 22px, 윤곽선 자체는 대칭). 모양을 바꿔서는 못 없앤다.'''
        left, top = left + inset, top + inset
        width, height = self.TRACK_WIDTH - inset * 2, self.TRACK_HEIGHT - inset * 2
        radius = height / 2

        path = gc.CreatePath()
        path.MoveToPoint(left + radius, top)
        path.AddLineToPoint(left + width - radius, top)
        path.AddArc(left + width - radius, top + radius, radius,
                    -math.pi / 2, math.pi / 2, True)
        path.AddLineToPoint(left + radius, top + height)
        path.AddArc(left + radius, top + radius, radius, math.pi / 2, -math.pi / 2, True)
        path.CloseSubpath()
        return path


class ChoiceCard(CardBase):
    '''고를 것이 몇 되지 않으면 목록을 펼칠 것 없이 칸을 나란히 붙인다. 토글과
    달리 카드 바탕을 눌러서는 값이 바뀌지 않는다 — 어느 칸을 고르는지 눌러서
    알릴 길이 없기 때문이다.'''

    SEGMENT_HEIGHT = 26
    SEGMENT_PADDING = 14
    SEGMENT_RADIUS = 5
    # 칸끼리 붙여 두면 어디까지가 한 칸인지 눈에 안 들어온다. 사이를 띄운다.
    SEGMENT_GAP = 6

    # 마우스가 얹힌 칸. 카드 밖으로 나가면 지운다.
    marked = -1

    def __init__(self, parent, theme, label, description, options, on_change=None):
        super().__init__(parent, theme, label, description, on_change)
        # (저장할 값, 보일 이름) 의 나열.
        self.options = options
        self.value = options[0][0]
        # 칸 폭은 글꼴이 정하니 한 번만 재 둔다. 누른 자리를 따지는 데도 쓴다.
        dc = wx.MemoryDC(wx.Bitmap(1, 1))
        dc.SetFont(get_font(9))
        self.segment = (max(dc.GetTextExtent(name)[0] for _, name in options) +
                        self.SEGMENT_PADDING * 2)
        self.Bind(wx.EVT_MOTION, self.on_motion)

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        if value in [option[0] for option in self.options]:
            self.value = value
            self.Refresh()

    def get_stride(self):
        return self.segment + self.SEGMENT_GAP

    def get_left(self, width):
        return (width - self.PADDING - self.get_stride() * len(self.options) +
                self.SEGMENT_GAP)

    def get_index(self, position):
        width, height = self.GetClientSize()
        left = self.get_left(width)
        top = (height - self.SEGMENT_HEIGHT) / 2
        if not top <= position.y < top + self.SEGMENT_HEIGHT:
            return -1
        if not left <= position.x < width - self.PADDING:
            return -1
        # 칸 사이 빈자리는 어느 쪽도 아니다. 넘겨짚어 고르면 눌린 적 없는 값이 선다.
        index, offset = divmod(int(position.x - left), self.get_stride())
        return index if offset < self.segment else -1

    def on_motion(self, event):
        self.mark(self.get_index(event.GetPosition()))
        event.Skip()

    def on_leave(self, event):
        self.mark(-1)
        super().on_leave(event)

    def mark(self, index):
        if index != self.marked:
            self.marked = index
            self.Refresh()

    def activate(self):
        index = self.get_index(self.ScreenToClient(wx.GetMousePosition()))
        if index < 0 or self.options[index][0] == self.value:
            return
        self.value = self.options[index][0]
        self.notify()

    def draw_control(self, gc, width, height):
        theme = self.theme
        left = self.get_left(width)
        top = round((height - self.SEGMENT_HEIGHT) / 2)
        gc.SetPen(wx.TRANSPARENT_PEN)

        for index, (value, name) in enumerate(self.options):
            x = left + self.get_stride() * index
            chosen = value == self.value
            if chosen:
                fill = wx.Colour(theme['accent'])
            elif index == self.marked:
                fill = mix(theme['control'], theme['text'], 0.14)
            else:
                fill = wx.Colour(theme['control'])
            gc.SetBrush(wx.Brush(fill))
            gc.DrawRoundedRectangle(x, top, self.segment, self.SEGMENT_HEIGHT,
                                    self.SEGMENT_RADIUS)
            gc.SetFont(get_font(9), wx.Colour('#ffffff' if chosen else theme['dim']))
            text_width, text_height = gc.GetTextExtent(name)[:2]
            gc.DrawText(name, x + (self.segment - text_width) / 2,
                        top + (self.SEGMENT_HEIGHT - text_height) / 2)
        return left
