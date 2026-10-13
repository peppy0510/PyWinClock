# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import math
import time
import wx

from utilities import CARD_HEIGHT
from utilities import CARD_RADIUS
from utilities import ROUND_SIZE
from utilities import Canvas
from utilities import apply_clip_siblings
from utilities import draw_card_rim
from utilities import get_font
from utilities import mix
from utilities import shade


class Pressable(Canvas):

    def __init__(self, parent, theme, on_click):
        super().__init__(parent, theme)
        self.on_click = on_click
        self.hovered = False
        self.pressed = False
        self.holding = False
        self.up_position = wx.Point(-1, -1)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_MOTION, self.on_track)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_lost)

    def get_hit(self):
        return None

    def hits(self, position):
        rect = self.get_hit()
        return rect is None or rect.Contains(position)

    def set_hovered(self, hovered):
        if hovered != self.hovered:
            self.hovered = hovered
            self.update_cursor()
            self.Refresh()

    def update_cursor(self):
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND if self.hovered else wx.CURSOR_ARROW))

    def on_track(self, event):
        inside = self.hits(event.GetPosition())
        self.set_hovered(inside)
        if self.holding and inside != self.pressed:
            self.pressed = inside
            self.Refresh()
        event.Skip()

    def on_down(self, event):
        if not self.hits(event.GetPosition()):
            event.Skip()
            return
        self.holding = True
        self.pressed = True
        if not self.HasCapture():
            self.CaptureMouse()
        self.Refresh()

    def on_dclick(self, event):
        self.on_down(event)

    def on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        # keep the event position, re-reading the cursor can disagree with the event
        self.up_position = event.GetPosition()
        clicked = self.holding and self.hits(self.up_position)
        self.holding = False
        self.pressed = False
        self.Refresh()
        if clicked and self.on_click:
            self.on_click()

    def on_lost(self, event):
        self.holding = False
        self.pressed = False
        self.Refresh()

    def on_enter(self, event):
        self.set_hovered(self.hits(event.GetPosition()))

    def on_leave(self, event):
        if self.holding:
            if self.pressed:
                self.pressed = False
                self.Refresh()
            self.set_hovered(False)
            return
        self.set_hovered(False)


class RoundButton(Pressable):

    TONES = {
        'plain': ('control', 'text'),
        'primary': ('accent', '#ffffff'),
        'ghost': (None, 'dim'),
    }

    CORNER = 9

    def __init__(self, parent, theme, icon, on_click, tone='plain', size=ROUND_SIZE,
                 square=False, backdrop=None):
        super().__init__(parent, theme, on_click)
        self.icon = icon
        self.tone = tone
        self.square = square
        # a solid colour behind, draw_backdrop re-enters the parent's drawing state
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
        # fill outside the rounded shape too, else a dark square shows behind it
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

        self.draw_icon(gc, cx, cy, radius, wx.Colour(theme.get(mark, mark)))

    def get_fill(self, key):
        if key is None:
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
            # shifted right, a triangle's weight reads left of centre
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
            # a stroke through the exact centre reads low
            cy -= 1
            arm = radius * 0.44
            gc.SetPen(wx.Pen(colour, max(1, round(radius * 0.13))))
            gc.StrokeLine(cx - arm, cy, cx + arm, cy)
            if self.icon == 'plus':
                gc.StrokeLine(cx, cy - arm, cx, cy + arm)
            gc.SetPen(wx.TRANSPARENT_PEN)

        elif self.icon == 'pencil':
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

    PADDING = 14
    LABEL_GAP = 12
    tone = 'dim'

    def __init__(self, parent, theme, label, description, on_change=None):
        super().__init__(parent, theme, self.activate)
        self.label = label
        self.description = description
        self.on_change = on_change
        self.SetMinSize(wx.Size(-1, CARD_HEIGHT))

    def activate(self):
        pass

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
        gc.SetFont(get_font(8), wx.Colour(theme[self.tone]))
        gc.DrawText(self.description, self.PADDING, top + title_height + 1)
        gc.ResetClip()

    def draw_control(self, gc, width, height):
        return width - self.PADDING


class SettingCard(CardBase):

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
        self.draw_switch(gc, switch_left, round((height - self.TRACK_HEIGHT) / 2))
        return switch_left - state_width - 8

    def draw_switch(self, gc, left, top):
        theme = self.theme
        radius = self.TRACK_HEIGHT / 2
        gc.SetPen(wx.TRANSPARENT_PEN)

        # a 1px stroke straddles pixels, stack a filled pill and an inset one instead
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
        # the flatter bottom edge is GDI+ antialiasing, not this path (checked)
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

    SEGMENT_HEIGHT = 26
    SEGMENT_PADDING = 14
    SEGMENT_RADIUS = 5
    SEGMENT_GAP = 6

    marked = -1

    def __init__(self, parent, theme, label, description, options, on_change=None):
        super().__init__(parent, theme, label, description, on_change)
        self.options = options
        self.value = options[0][0]
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
        # a gap belongs to neither segment, guessing would pick a value never pressed
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
        index = self.get_index(self.up_position)
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


class ButtonCard(CardBase):

    BUTTON_HEIGHT = 26
    BUTTON_PADDING = 16
    BUTTON_RADIUS = 5

    def __init__(self, parent, theme, label, description, caption, on_click):
        super().__init__(parent, theme, label, description)
        self.action = on_click
        self.caption = caption
        dc = wx.MemoryDC(wx.Bitmap(1, 1))
        dc.SetFont(get_font(9))
        self.button = dc.GetTextExtent(caption)[0] + self.BUTTON_PADDING * 2

    def set_description(self, description, tone='dim'):
        self.description = description
        self.tone = tone
        self.Refresh()

    def get_button_rect(self):
        width, height = self.GetClientSize()
        return wx.Rect(width - self.PADDING - self.button,
                       round((height - self.BUTTON_HEIGHT) / 2),
                       self.button, self.BUTTON_HEIGHT)

    def get_hit(self):
        return self.get_button_rect()

    def activate(self):
        self.action()

    def draw(self, gc, width, height):
        # only the button reacts, so the card body is drawn unpressed
        pressed, hovered = self.pressed, self.hovered
        self.pressed = self.hovered = False
        super().draw(gc, width, height)
        self.pressed, self.hovered = pressed, hovered
        self.draw_button(gc)

    def draw_control(self, gc, width, height):
        return self.get_button_rect().x

    def draw_button(self, gc):
        theme = self.theme
        rect = self.get_button_rect()
        fill = theme['control']
        if self.pressed:
            fill = shade(fill, 0.90)
        elif self.hovered:
            fill = mix(theme['control'], theme['text'], 0.14)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(fill)))
        gc.DrawRoundedRectangle(rect.x, rect.y, rect.width, rect.height, self.BUTTON_RADIUS)
        gc.SetFont(get_font(9), wx.Colour(theme['text']))
        text_width, text_height = gc.GetTextExtent(self.caption)[:2]
        gc.DrawText(self.caption, rect.x + (rect.width - text_width) / 2,
                    rect.y + (rect.height - text_height) / 2)


class ScrollBar(Canvas):

    WIDTH = 4
    INSET = 2
    RADIUS = 2
    HOLD = 700
    FADE_MS = 400
    STEP = 16

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.fade = 0.0
        self.span = 0.0
        self.ratio = 1.0
        self.shown_at = 0.0
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_fade)

    def set_span(self, ratio, span):
        self.ratio = min(1.0, max(0.0, ratio))
        self.span = min(1.0, max(0.0, span))
        self.Refresh()

    def show(self):
        self.fade = 1.0
        self.shown_at = time.monotonic()
        if not self.timer.IsRunning():
            self.timer.Start(self.STEP)
        self.Refresh()

    def on_fade(self, event):
        elapsed = (time.monotonic() - self.shown_at) * 1000 - self.HOLD
        if elapsed <= 0:
            return
        progress = min(1.0, elapsed / self.FADE_MS)
        self.fade = (1.0 - progress) ** 2
        if progress >= 1.0:
            self.fade = 0.0
            self.timer.Stop()
        self.Refresh()

    def draw(self, gc, width, height):
        if self.fade <= 0 or self.ratio >= 1.0:
            return
        colour = wx.Colour(self.theme['rim'])
        colour = wx.Colour(colour.Red(), colour.Green(), colour.Blue(),
                           int(255 * self.fade))
        thumb = max(24, height * self.ratio)
        top = (height - thumb) * self.span
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(colour))
        gc.DrawRoundedRectangle(self.INSET, top, self.WIDTH, thumb, self.RADIUS)


class ScrollArea(wx.Panel):

    LINE = 42

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme
        self.offset = 0
        # a moving content panel, wx.ScrolledWindow's native bar ignores the dark theme
        self.content = wx.Panel(self)
        self.content.SetDoubleBuffered(True)
        self.bar = ScrollBar(self, theme)
        apply_clip_siblings(self.content)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.bind_wheel(self)

    def set_theme(self, theme):
        self.theme = theme
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.content.SetBackgroundColour(wx.Colour(theme['bg']))
        self.bar.set_theme(theme)

    def bind_wheel(self, window):
        window.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)

    def bind_children(self):
        # wheel events do not climb to the parent in wx, bind every child
        def walk(window):
            for child in window.GetChildren():
                if child is not self.bar:
                    self.bind_wheel(child)
                    walk(child)
        walk(self.content)

    TWO_COLUMNS = 820
    THREE_COLUMNS = 1240

    groups = None
    columns = 0
    column_gap = 0
    wide_columns = True

    def set_groups(self, top, groups, side=0, bottom=0):
        self.groups = list(groups)
        self.root = wx.BoxSizer(wx.VERTICAL)
        self.root.AddSpacer(top)
        self.row = wx.BoxSizer(wx.HORIZONTAL)
        self.root.Add(self.row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, side)
        if bottom:
            self.root.AddSpacer(bottom)
        self.content.SetSizer(self.root)
        self.columns = 0
        self.arrange()

    def set_wide(self, wide):
        if wide != self.wide_columns:
            self.wide_columns = wide
            self.arrange()

    def get_column_count(self):
        width = self.GetClientSize()[0]
        if not self.wide_columns or width < self.TWO_COLUMNS:
            return 1
        return 3 if width >= self.THREE_COLUMNS else 2

    @staticmethod
    def split_columns(heights, count):
        prefix = [0]
        for height in heights:
            prefix.append(prefix[-1] + height)
        n = len(heights)
        best = {1: prefix[:]}
        cut = {1: [0] * (n + 1)}
        for c in range(2, count + 1):
            best[c], cut[c] = [], []
            for i in range(n + 1):
                # ties cut late so an empty column ends up last
                choice = min(range(i, -1, -1),
                             key=lambda j: max(best[c - 1][j], prefix[i] - prefix[j]))
                best[c].append(max(best[c - 1][choice], prefix[i] - prefix[choice]))
                cut[c].append(choice)
        starts, end = [], n
        for c in range(count, 0, -1):
            starts.insert(0, cut[c][end])
            end = cut[c][end]
        return starts

    def arrange(self, force=False):
        if not self.groups:
            return
        count = self.get_column_count()
        if count == self.columns and not force:
            return
        self.columns = count
        self.Freeze()
        try:
            self.arrange_columns(count)
        finally:
            self.Thaw()
        self.Refresh()

    def arrange_columns(self, count):
        # heights depend on the column width, so place, re-measure and re-split until stable
        starts = None
        for _ in range(3):
            heights = [group.CalcMin()[1] for group in self.groups]
            fresh = self.split_columns(heights, count)
            if fresh == starts:
                break
            starts = fresh
            self.fill_columns(starts, count)
            self.content.SetSize(self.GetClientSize()[0], self.content.GetSize()[1])
            self.content.Layout()
        self.fit()

    def fill_columns(self, starts, count):
        # detach first, Clear deletes the sizers it holds
        for item in list(self.row.GetChildren()):
            column = item.GetSizer()
            if column:
                for group in self.groups:
                    column.Detach(group)
        self.row.Clear(delete_windows=False)
        columns = []
        for index in range(count):
            if index and self.column_gap:
                self.row.AddSpacer(self.column_gap)
            column = wx.BoxSizer(wx.VERTICAL)
            self.row.Add(column, 1, wx.EXPAND)
            columns.append(column)
        for index, group in enumerate(self.groups):
            column = max(c for c, start in enumerate(starts) if index >= start)
            columns[column].Add(group, 0, wx.EXPAND)

    def get_extent(self):
        sizer = self.content.GetSizer()
        return sizer.GetMinSize()[1] if sizer else 0

    def get_limit(self):
        return max(0, self.get_extent() - self.GetClientSize()[1])

    def scroll_to(self, offset):
        offset = min(self.get_limit(), max(0, offset))
        if offset == self.offset:
            return False
        self.offset = offset
        self.content.SetPosition(wx.Point(0, -offset))
        return True

    def on_wheel(self, event):
        limit = self.get_limit()
        if limit <= 0:
            return
        lines = event.GetWheelRotation() / float(event.GetWheelDelta())
        self.scroll_to(self.offset - int(round(lines)) * self.LINE)
        self.update_bar()
        self.bar.show()

    def update_bar(self):
        extent, height = self.get_extent(), self.GetClientSize()[1]
        limit = self.get_limit()
        self.bar.set_span(height / float(extent) if extent else 1.0,
                          self.offset / float(limit) if limit else 0.0)

    def fit(self):
        width, height = self.GetClientSize()
        self.content.SetSize(0, -self.offset, width, max(height, self.get_extent()))
        self.scroll_to(self.offset)
        self.update_bar()

    def on_size(self, event):
        width, height = self.GetClientSize()
        bar_width = ScrollBar.WIDTH + ScrollBar.INSET * 2
        self.arrange()
        self.fit()
        self.bar.SetSize(width - bar_width, 0, bar_width, height)
        self.bar.Raise()
        event.Skip()
