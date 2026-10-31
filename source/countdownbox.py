# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import math
import time
import wx

from controls import RoundButton
from controls import set_start
from utilities import MAX_DIAL
from utilities import ROUND_SIZE
from utilities import Canvas
from utilities import fill_rounded
from utilities import TimerCanvas
from utilities import get_font
from utilities import get_page_scale
from utilities import mix


STEP_SECONDS = 60
# 99:59:59
MAX_SECONDS = 359999
FIELD_CHARS = '0123456789:'
BLINK_INTERVAL = 0.5
WARN_SECONDS = 10
BUTTON_GAP = 10
# radius from the width only, height -> radius -> height never settles
RING_RATIO = 0.38
RING_PAD = 10
RING_WIDTH = 7
CANVAS_MARGIN = 8
# field, time and buttons stacked inside the ring this far apart; DONE sits in the lower gap
STACK_GAP = 18
# the field faded toward the page until the mouse is over it or it is being typed in
FIELD_FADE = 0.6
# the buttons keep this clear of the ring's inner edge, shrinking to SMALLEST_BUTTON
RING_CLEARANCE = 10
SMALLEST_BUTTON = 30
EDGE_GAP = 14


def format_duration(seconds):
    return f'{int(seconds // 3600):02d}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}'


def parse_duration(text):
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
        self.time_bottom = None
        self.ring_key = None
        self.ring_bitmap = None

    def get_time_colour(self):
        if self.finished:
            return self.theme['alert'] if self.blink else self.theme['dim']
        return self.theme['text']

    def get_radius(self, width, height):
        pad = RING_PAD * self.zoom
        return min(width * RING_RATIO, height / 2 - pad / 2, (MAX_DIAL * self.zoom - pad) / 2)

    def get_time_size(self, width, height):
        # scale from the ring so the text stays inside it when the window is wide
        return max(14, int(self.get_radius(width, height) /
                           (RING_RATIO * self.WIDTH_DIVISOR)))

    def set_theme(self, theme):
        self.ring_key = None
        super().set_theme(theme)

    def get_background(self, width, height):
        radius = self.get_radius(width, height)
        if radius < 24 or width <= 0 or height <= 0:
            return None
        if (width, height, self.zoom) != self.ring_key:
            bitmap = wx.Bitmap(width, height, 24)
            dc = wx.MemoryDC(bitmap)
            dc.SetBackground(wx.Brush(wx.Colour(self.theme['bg'])))
            dc.Clear()
            gc = wx.GraphicsContext.Create(dc)
            gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.SetPen(wx.Pen(wx.Colour(self.theme['rim']), round(RING_WIDTH * self.zoom)))
            path = gc.CreatePath()
            path.AddArc(width / 2, height / 2, radius, 0, 6.2831853, True)
            gc.StrokePath(path)
            del gc
            dc.SelectObject(wx.NullBitmap)
            self.ring_key, self.ring_bitmap = (width, height, self.zoom), bitmap
        return self.ring_bitmap

    def draw(self, gc, width, height):
        theme = self.theme
        cx, cy = width / 2, height / 2
        radius = self.get_radius(width, height)
        if radius < 24:
            return

        fraction = self.seconds / self.total if self.total > 0 else 0
        if fraction > 0:
            colour = theme['alert'] if self.seconds <= WARN_SECONDS else theme['accent']
            gc.SetPen(wx.Pen(wx.Colour(colour), round(RING_WIDTH * self.zoom)))
            path = gc.CreatePath()
            path.AddArc(cx, cy, radius, -1.5707963,
                        -1.5707963 + 6.2831853 * fraction, True)
            gc.StrokePath(path)

        self.time_bottom = self.draw_time(gc, width, height)

        if self.finished:
            font = get_font(max(9, int(self.get_time_size(width, height) * 0.34)), bold=True)
            gc.SetFont(font, wx.Colour(theme['alert']))
            done_height = gc.GetTextExtent('DONE')[1]
            self.draw_centered_text(gc, 'DONE', cx,
                                    self.time_bottom + (STACK_GAP * self.zoom - done_height) / 2,
                                    font,
                                    theme['alert'])


class FieldBox(Canvas):

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
        self.lit = False
        self.buttons = (self.minus, self.plus)
        self.zoom = 1.0
        self.SetMinSize(wx.Size(self.WIDTH, self.HEIGHT))
        # hidden until the first paint tells where the time text ends
        self.Hide()
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_char(self, event):
        code = event.GetKeyCode()
        if code >= wx.WXK_START or code < 32 or code == wx.WXK_DELETE:
            event.Skip()
        elif event.HasModifiers():
            event.Skip()
        elif chr(code) in FIELD_CHARS:
            event.Skip()

    def set_zoom(self, zoom):
        if zoom != self.zoom:
            self.zoom = zoom
            self.field.SetFont(get_font(round(10 * zoom * 2) / 2))
            self.SetMinSize(wx.Size(round(self.WIDTH * zoom), round(self.HEIGHT * zoom)))

    def on_size(self, event):
        width, height = self.GetClientSize()
        padding = round(self.PADDING * self.zoom)
        size = height - padding * 2
        self.minus.SetSize(padding, padding, size, size)
        self.plus.SetSize(width - padding - size, padding, size, size)
        # a taller single-line TextCtrl pins its text to the top, keep its own height
        left = padding + size
        text_height = self.field.GetBestSize()[1]
        self.field.SetSize(left, (height - text_height) // 2,
                           max(0, width - left * 2), text_height)
        event.Skip()

    def set_theme(self, theme):
        super().set_theme(theme)
        for button in self.buttons:
            button.set_theme(theme)
        self.field.SetFont(get_font(round(10 * self.zoom * 2) / 2))
        self.apply_lit()

    def set_lit(self, lit):
        if lit != self.lit:
            self.lit = lit
            self.apply_lit()
            self.Refresh()

    def apply_lit(self):
        self.field.SetBackgroundColour(self.get_fill())
        self.field.SetForegroundColour(wx.Colour(self.theme['text' if self.lit else 'tick']))
        self.field.Refresh()
        for button in self.buttons:
            button.set_tone('ghost' if self.lit else 'faint')

    def get_fill(self):
        fill = self.theme['control']
        return wx.Colour(fill) if self.lit else mix(fill, self.theme['bg'], FIELD_FADE)

    def draw(self, gc, width, height):
        fill_rounded(gc, self.get_fill(), 0, 0, width, height, height // 2)


def place(window, rect):
    if rect != window.GetRect():
        window.SetSize(rect)
    if not window.IsShown():
        window.Show()


class CountdownBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.total = 0
        self.remaining = 0
        self.running = False
        self.deadline = 0.0
        self.finished_at = 0.0

        self.canvas = CountdownCanvas(self, theme)
        # a child of the canvas, as a sibling the ring repaint would cover it
        self.fieldbox = FieldBox(self.canvas, theme, self.make_step)
        self.field = self.fieldbox.field
        self.field.Bind(wx.EVT_TEXT, lambda event: self.on_field())
        self.field.Bind(wx.EVT_TEXT_ENTER, lambda event: self.drop_focus())
        self.field.Bind(wx.EVT_KILL_FOCUS, self.on_field_done)
        # wx hands focus back to the first field when the empty page is clicked
        self.canvas.Bind(wx.EVT_LEFT_DOWN, lambda event: self.drop_focus())
        self.Bind(wx.EVT_LEFT_DOWN, lambda event: self.drop_focus())

        # inside the ring under the time, placed as the field is
        self.start_button = RoundButton(self.canvas, theme, 'play', self.on_start,
                                        backdrop=theme['bg'])
        self.reset_button = RoundButton(self.canvas, theme, 'reset', self.on_reset,
                                        backdrop=theme['bg'])
        self.buttons = (self.start_button, self.reset_button)
        for button in self.buttons:
            button.Hide()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.canvas, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, CANVAS_MARGIN)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SHOW, self.on_show)

        self.apply_theme(theme)
        self.on_field()

    def drop_focus(self):
        self.SetFocusIgnoringChildren()

    def on_show(self, event):
        # wx focuses the first field whenever the page is shown
        if event.IsShown():
            wx.CallAfter(self.drop_focus)
        event.Skip()

    def on_size(self, event):
        # GetMinSize, not GetSize: a squeezed button would shrink itself further on every pass
        width, height = self.GetClientSize()
        if width <= 0:
            return event.Skip()

        # the carousel pages' shared scale: the ring's limit, the field, the keys and gaps
        zoom = get_page_scale(width, height)
        if zoom != self.canvas.zoom:
            self.canvas.zoom = zoom
            self.fieldbox.set_zoom(zoom)
            self.canvas.Refresh()
        ring = min(round(MAX_DIAL * zoom),
                   int((width - CANVAS_MARGIN * 2) * RING_RATIO * 2) + round(RING_PAD * zoom))
        target = max(0, min(ring, height - EDGE_GAP * 2))
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
            button.set_backdrop(theme['bg'])
        self.Refresh()

    def make_step(self, delta):
        def apply():
            seconds = min(MAX_SECONDS,
                          max(0, (parse_duration(self.field.GetValue()) or 0) + delta))
            # stop first, on_field ignores the field while running
            self.stop()
            self.field.SetValue(format_duration(seconds))
            self.drop_focus()
        return apply

    def stop(self):
        self.running = False
        self.finished_at = 0.0
        set_start(self.start_button, False)

    def on_field(self):
        if self.running:
            return
        seconds = parse_duration(self.field.GetValue())
        self.total = seconds or 0
        self.remaining = self.total
        self.tick()

    def on_field_done(self, event):
        text = format_duration(parse_duration(self.field.GetValue()) or 0)
        if text != self.field.GetValue():
            # ChangeValue sends no EVT_TEXT
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
        set_start(self.start_button, True)

    def on_reset(self):
        self.drop_focus()
        self.stop()
        self.on_field()

    def place_controls(self):
        # the field above the time, the buttons under it; known once a paint placed the time
        bottom = self.canvas.time_bottom
        if bottom is None:
            return
        width, height = self.canvas.GetClientSize()
        cx, cy = width / 2, height / 2
        top = height - bottom
        zoom = self.canvas.zoom
        stack, gap = round(STACK_GAP * zoom), round(BUTTON_GAP * zoom)
        size = self.fieldbox.GetMinSize()
        place(self.fieldbox, wx.Rect((width - size[0]) // 2,
                                     int(top) - stack - size[1], *size))

        # as large as the ring's width under the time allows
        inner = self.canvas.get_radius(width, height) - RING_CLEARANCE * zoom
        y = int(bottom) + stack
        side = round(ROUND_SIZE * zoom)
        while side > SMALLEST_BUTTON * zoom and (
                y + side - cy >= inner or
                gap + side > math.sqrt(inner ** 2 - (y + side - cy) ** 2)):
            side -= 1
        place(self.start_button, wx.Rect(int(cx - gap - side), y, side, side))
        place(self.reset_button, wx.Rect(int(cx + gap), y, side, side))

    def tick(self):
        if self.running:
            self.remaining = max(0.0, self.deadline - time.perf_counter())
            if self.remaining <= 0:
                self.running = False
                self.finished_at = time.perf_counter()
                set_start(self.start_button, False)
                wx.Bell()

        canvas = self.canvas
        blink = canvas.blink
        if self.finished_at:
            elapsed = time.perf_counter() - self.finished_at
            blink = int(elapsed / BLINK_INTERVAL) % 2 == 0
        state = (self.total, self.remaining, bool(self.finished_at), blink)
        self.place_controls()
        box = self.fieldbox
        box.set_lit(box.GetClientRect().Contains(box.ScreenToClient(wx.GetMousePosition()))
                    or self.field.HasFocus())
        if state != (canvas.total, canvas.seconds, canvas.finished, canvas.blink):
            canvas.total, canvas.seconds, canvas.finished, canvas.blink = state
            self.refresh_canvas()

    def refresh_canvas(self):
        # leave the field box out, repainting its native TextCtrl costs more than the ring
        if not self.fieldbox.IsShown():
            self.canvas.Refresh()
            return
        width, height = self.canvas.GetClientSize()
        box = self.fieldbox.GetRect()
        right, bottom = box.x + box.width, box.y + box.height
        self.canvas.RefreshRect(wx.Rect(0, 0, width, box.y))
        self.canvas.RefreshRect(wx.Rect(0, bottom, width, height - bottom))
        self.canvas.RefreshRect(wx.Rect(0, box.y, box.x, box.height))
        self.canvas.RefreshRect(wx.Rect(right, box.y, width - right, box.height))
