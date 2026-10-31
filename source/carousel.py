# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import ctypes
import threading
import time
import wx

from ctypes import wintypes

from utilities import Canvas
from utilities import paint_now


DRAG_START = 12
FLING_SPEED = 900.0
SLIDE_SECONDS = 0.2
SLIDE_LONGEST = 0.35
FRAME_MS = 8
DOTS_HEIGHT = 22
DOTS_RAISE = 3
DOT = 6
DOT_GAP = 10

WM_PRINT = 0x0317
PRF_NONCLIENT = 0x0002
PRF_CLIENT = 0x0004
PRF_ERASEBKGND = 0x0008
# a private user32: its argtypes not shared with other callers
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM


def capture(window):
    # what DWM keeps, covered or off-screen too; PrintWindow repaints it all (25-50 ms)
    width, height = window.GetClientSize()
    bitmap = wx.Bitmap(max(width, 1), max(height, 1))
    dc = wx.MemoryDC(bitmap)
    dc.Blit(0, 0, width, height, wx.ClientDC(window), 0, 0)
    dc.SelectObject(wx.NullBitmap)
    return bitmap


def print_native(window):
    # WM_PRINT draws a hidden control too; None when it drew nothing
    width, height = window.GetClientSize()
    if width <= 0 or height <= 0:
        return None
    ground = window.GetBackgroundColour()
    bitmap = wx.Bitmap(width, height)
    dc = wx.MemoryDC(bitmap)
    dc.SetBackground(wx.Brush(ground))
    dc.Clear()
    try:
        user32.SendMessageW(window.GetHandle(), WM_PRINT, dc.GetHDC(),
                            PRF_CLIENT | PRF_NONCLIENT | PRF_ERASEBKGND)
    except Exception:
        dc.SelectObject(wx.NullBitmap)
        return None
    dc.SelectObject(wx.NullBitmap)
    image = bitmap.ConvertToImage()
    data = bytes(image.GetData())
    plain = bytes((ground.Red(), ground.Green(), ground.Blue())) * (width * height)
    return bitmap if data != plain else None


def draw_native_text(window, gc, width, height):
    text = window.GetLabel() if isinstance(window, wx.StaticText) else window.GetValue()
    gc.SetFont(window.GetFont(), window.GetForegroundColour())
    tw, th = gc.GetTextExtent(text)[:2]
    style = window.GetWindowStyle()
    if style & (wx.TE_CENTER | wx.ALIGN_CENTER_HORIZONTAL):
        x = (width - tw) / 2.0
    elif style & (wx.TE_RIGHT | wx.ALIGN_RIGHT):
        x = width - tw
    else:
        x = 0
    y = (height - th) / 2.0 if isinstance(window, wx.TextCtrl) else 0
    gc.DrawText(text, x, y)


def render(window):
    '''the window and its children as on the screen, each in a picture of its own size
    (drawn on one, a child's draw_backdrop painted its parent over its siblings)'''
    width, height = window.GetClientSize()
    bitmap = wx.Bitmap(max(width, 1), max(height, 1))
    dc = wx.MemoryDC(bitmap)
    ground = wx.Colour(window.theme['bg']) if isinstance(window, Canvas) else \
        window.GetBackgroundColour()
    dc.SetBackground(wx.Brush(ground))
    dc.Clear()
    gc = wx.GraphicsContext.Create(dc)
    if isinstance(window, Canvas):
        background = window.get_background(width, height) if width > 0 and height > 0 else None
        if background is not None:
            gc.DrawBitmap(background, 0, 0, width, height)
        window.draw_scaled(gc, width, height)
    elif isinstance(window, (wx.StaticText, wx.TextCtrl)):
        picture = print_native(window)
        if picture is not None:
            gc.DrawBitmap(picture, 0, 0, width, height)
        else:
            draw_native_text(window, gc, width, height)
    for child in window.GetChildren():
        if child.IsTopLevel() or not child.IsShown():
            continue
        x, y = child.GetPosition()
        if isinstance(child, wx.StaticText):
            # GDI's ClearType as on the screen; its own ground is white, the parent's shows
            picture = print_native(child)
            if picture is not None:
                gc.DrawBitmap(picture, x, y, *child.GetClientSize())
                continue
            gc.PushState()
            gc.Translate(x, y)
            draw_native_text(child, gc, *child.GetClientSize())
            gc.PopState()
            continue
        gc.DrawBitmap(render(child), x, y, *child.GetClientSize())
    del gc
    dc.SelectObject(wx.NullBitmap)
    return bitmap


def leave(window):
    # the slide takes the mouse, so nothing under it would hear the pointer go
    for child in window.GetChildren():
        leave(child)
    event = wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW)
    event.SetEventObject(window)
    window.GetEventHandler().ProcessEvent(event)


def ease_out(share):
    return 1.0 - (1.0 - share) ** 3


class FramePacer(threading.Thread):

    '''wx.Timer rounds to 15.6 ms ticks: frames 10 and 20 ms apart by turns, now and then
    a 60 Hz screen frame without a move; DwmFlush skipped every other screen frame.
    Twice a screen frame instead, each placed by the clock'''

    def __init__(self, on_frame):
        super().__init__(name='slide-pacer', daemon=True)
        self.on_frame = on_frame
        self.running = True
        self.pending = False

    def run(self):
        while self.running:
            time.sleep(FRAME_MS / 1000)
            if self.running and not self.pending:
                self.pending = True
                try:
                    wx.CallAfter(self.beat)
                except Exception:
                    return

    def beat(self):
        self.pending = False
        if self.running:
            self.on_frame(None)


class Slide(Canvas):

    '''the pages' pictures side by side over the book while a page is dragged or slides in'''

    def __init__(self, parent, theme):
        super().__init__(parent, theme)
        self.pictures = {}
        self.offset = 0.0
        self.Hide()

    def on_paint(self, event):
        # GDI blits: GraphicsContext.DrawBitmap converts all three pictures' pixels a frame
        dc = wx.AutoBufferedPaintDC(self)
        width, height = self.GetClientSize()
        dc.SetBackground(wx.Brush(wx.Colour(self.theme['bg'])))
        dc.Clear()
        for step, bitmap in self.pictures.items():
            dc.DrawBitmap(bitmap, round(self.offset + step * width), 0)


class PageDots(Canvas):

    '''a dot a page; one pressed slides to its page'''

    def __init__(self, parent, theme, count, on_pick):
        super().__init__(parent, theme)
        self.count = count
        self.on_pick = on_pick
        self.current = 0
        self.hovered = -1
        self.SetMinSize(wx.Size(-1, DOTS_HEIGHT))
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda event: self.set_hovered(-1))

    def set_current(self, index):
        if index != self.current:
            self.current = index
            self.Refresh()

    def set_hovered(self, index):
        if index != self.hovered:
            self.hovered = index
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND if index >= 0 else wx.CURSOR_ARROW))
            self.Refresh()

    def get_centres(self, width, height):
        span = self.count * DOT + (self.count - 1) * DOT_GAP
        left = (width - span) / 2.0 + DOT / 2.0
        return [(left + k * (DOT + DOT_GAP), height / 2.0 - DOTS_RAISE) for k in range(self.count)]

    def hit(self, point):
        width, height = self.GetClientSize()
        for k, (cx, cy) in enumerate(self.get_centres(width, height)):
            if abs(point.x - cx) <= (DOT + DOT_GAP) / 2.0 and abs(point.y - cy) <= height / 2.0:
                return k
        return -1

    def on_motion(self, event):
        self.set_hovered(self.hit(event.GetPosition()))

    def on_down(self, event):
        index = self.hit(event.GetPosition())
        if index >= 0:
            self.on_pick(index)

    def draw(self, gc, width, height):
        theme = self.theme
        gc.SetPen(wx.TRANSPARENT_PEN)
        for k, (cx, cy) in enumerate(self.get_centres(width, height)):
            colour = theme['accent'] if k == self.current else \
                theme['dim'] if k == self.hovered else theme['rim']
            gc.SetBrush(wx.Brush(wx.Colour(colour)))
            gc.DrawEllipse(cx - DOT / 2.0, cy - DOT / 2.0, DOT, DOT)


class Carousel(wx.EventFilter):

    '''on_show(index) when the carousel shows another page'''

    def __init__(self, frame, book, count, on_show, theme):
        super().__init__()
        self.frame = frame
        self.book = book
        self.count = count
        self.on_show = on_show
        self.theme = theme
        self.slide = Slide(frame, theme)
        self.press = None
        self.dragging = False
        self.motion = []
        self.target = None
        self.animation = None
        self.drawn = set()
        self.pacer = None
        self.slide.Bind(wx.EVT_MOTION, self.on_drag)
        self.slide.Bind(wx.EVT_LEFT_UP, self.on_release)
        self.slide.Bind(wx.EVT_MOUSE_CAPTURE_LOST, lambda event: self.on_release(None))
        wx.EvtHandler.AddFilter(self)

    def close(self):
        wx.EvtHandler.RemoveFilter(self)
        self.stop_pacer()

    def set_theme(self, theme):
        self.theme = theme
        self.drawn.clear()
        self.slide.set_theme(theme)

    def current(self):
        return self.book.GetSelection()

    def is_sliding(self):
        return self.dragging or self.animation is not None

    def stop_pacer(self):
        if self.pacer is not None:
            self.pacer.running = False
            self.pacer = None

    def is_page(self, window):
        # not a text field: a drag there selects text
        page = self.book.GetCurrentPage()
        if self.current() >= self.count or isinstance(window, wx.TextCtrl):
            return False
        while window is not None:
            if window is page:
                return True
            window = window.GetParent()
        return False

    def FilterEvent(self, event):
        kind = event.GetEventType()
        if kind not in (wx.wxEVT_LEFT_DOWN, wx.wxEVT_MOTION, wx.wxEVT_LEFT_UP):
            return self.Event_Skip
        if self.dragging or self.animation is not None:
            return self.Event_Skip
        window = event.GetEventObject()
        if kind == wx.wxEVT_LEFT_DOWN:
            self.press = wx.GetMousePosition() if isinstance(window, wx.Window) and \
                self.is_page(window) else None
        elif kind == wx.wxEVT_LEFT_UP:
            self.press = None
        elif self.press is not None and wx.GetMouseState().LeftIsDown():
            point = wx.GetMousePosition()
            dx, dy = point.x - self.press.x, point.y - self.press.y
            if abs(dx) >= DRAG_START and abs(dx) > abs(dy) * 1.5:
                wx.CallAfter(self.begin_drag, self.press)
                self.press = None
                return self.Event_Processed
        return self.Event_Skip

    def get_neighbour(self, step):
        return (self.current() + step) % self.count

    def take(self, index):
        page = self.book.GetPage(index)
        width, height = self.book.GetClientSize()
        if tuple(page.GetSize()) != (width, height):
            page.SetSize(0, 0, width, height)
            page.Layout()
        if index == self.current():
            return capture(page)
        tick = getattr(page, 'tick', None)
        # a hidden page's first drawing at a size sets what its tick places by
        first = (index, width, height) not in self.drawn
        self.drawn.add((index, width, height))
        for _ in range(2 if tick is not None and first else 1):
            if tick is not None:
                try:
                    tick()
                except Exception:
                    pass
            bitmap = render(page)
        return bitmap

    def show_slide(self, steps):
        self.slide.pictures = {step: self.take(self.get_neighbour(step)) for step in steps}
        rect = self.book.GetRect()
        self.slide.SetSize(rect)
        self.slide.offset = 0.0
        self.slide.Show()
        self.slide.Raise()
        self.slide.Refresh()
        self.slide.Update()

    def begin_drag(self, origin):
        if not wx.GetMouseState().LeftIsDown() or self.current() >= self.count:
            return
        self.dragging = True
        self.origin = origin
        self.motion = [(time.monotonic(), wx.GetMousePosition().x)]
        page = self.book.GetCurrentPage()
        leave(page)
        page.Update()
        self.show_slide((-1, 0, 1))
        self.slide.CaptureMouse()
        self.on_drag(None)

    def on_drag(self, event):
        if not self.dragging:
            return
        x = wx.GetMousePosition().x
        self.motion = (self.motion + [(time.monotonic(), x)])[-6:]
        self.slide.offset = float(x - self.origin.x)
        self.slide.Refresh()
        self.slide.Update()

    def on_release(self, event):
        if not self.dragging:
            return
        self.dragging = False
        if self.slide.HasCapture():
            self.slide.ReleaseMouse()
        width = self.book.GetClientSize().width
        speed = 0.0
        if len(self.motion) >= 2:
            (t0, x0), (t1, x1) = self.motion[0], self.motion[-1]
            speed = (x1 - x0) / max(t1 - t0, 1e-3)
        offset = self.slide.offset
        step = 0
        if offset <= -width / 4.0 or speed <= -FLING_SPEED:
            step = 1
        elif offset >= width / 4.0 or speed >= FLING_SPEED:
            step = -1
        if step:
            # taken as the drag began, a clock in it would jump to the time when it lands
            self.slide.pictures[step] = self.take(self.get_neighbour(step))
        end = -step * width
        # ease_out sets off at 3x its mean speed: as fast as the hand, not a kick past it
        toward = speed if end > offset else -speed
        seconds = SLIDE_SECONDS
        if toward > 0:
            seconds = min(max(3.0 * abs(end - offset) / toward, SLIDE_SECONDS), SLIDE_LONGEST)
        self.animate(offset, end, step, seconds=seconds)

    def go_to(self, index):
        current = self.current()
        if index == current or current >= self.count or self.animation is not None:
            return
        step = 1 if (index - current) % self.count <= self.count // 2 else -1
        self.slide.pictures = {0: self.take(current), step: self.take(index)}
        rect = self.book.GetRect()
        self.slide.SetSize(rect)
        self.slide.offset = 0.0
        self.slide.Show()
        self.slide.Raise()
        self.animate(0.0, -step * rect.width, step, index)

    def animate(self, start, end, step, index=None, seconds=SLIDE_SECONDS):
        self.target = self.get_neighbour(step) if index is None else index
        self.animation = (time.monotonic(), start, end, seconds)
        self.stop_pacer()
        self.pacer = FramePacer(self.on_frame)
        self.pacer.start()
        self.on_frame(None)

    def on_frame(self, event):
        if self.animation is None:
            return
        began, start, end, seconds = self.animation
        share = min((time.monotonic() - began) / seconds, 1.0)
        self.slide.offset = start + (end - start) * ease_out(share)
        self.slide.Refresh()
        self.slide.Update()
        if share < 1.0:
            return
        self.stop_pacer()
        self.animation = None
        # frozen until the new page is whole: a page shown or uncovered erases first
        self.frame.Freeze()
        try:
            self.slide.Hide()
            self.slide.pictures = {}
            if self.target != self.current():
                self.book.SetSelection(self.target)
                self.on_show(self.target)
            else:
                # its ticks were skipped while covered
                tick = getattr(self.book.GetCurrentPage(), 'tick', None)
                if tick is not None:
                    tick()
        finally:
            self.frame.Thaw()
        paint_now(self.frame)
