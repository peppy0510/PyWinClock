# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import math
import wx


def get_pen(gc, colour, width):
    return gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(colour)).Width(width)
                        .Cap(wx.CAP_ROUND).Join(wx.JOIN_ROUND))


def draw_glyph(gc, name, cx, cy, size, colour, width=None):
    handler = HANDLERS.get(name)
    if handler is None:
        return
    width = width or max(1.0, size * 0.085)
    gc.SetPen(get_pen(gc, colour, width))
    gc.SetBrush(wx.TRANSPARENT_BRUSH)
    handler(gc, cx, cy, size, wx.Colour(colour), width)


def draw_clock(gc, cx, cy, size, colour, width):
    radius = size * 0.44
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
    gc.StrokeLine(cx, cy, cx, cy - radius * 0.56)
    gc.StrokeLine(cx, cy, cx + radius * 0.42, cy + radius * 0.26)


def draw_globe(gc, cx, cy, size, colour, width):
    radius = size * 0.44
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
    gc.StrokeLine(cx - radius, cy, cx + radius, cy)
    # one meridian, two blur at this size
    gc.DrawEllipse(cx - radius * 0.46, cy - radius, radius * 0.92, radius * 2)


def draw_stopwatch(gc, cx, cy, size, colour, width):
    radius = size * 0.38
    middle = cy + size * 0.08
    gc.DrawEllipse(cx - radius, middle - radius, radius * 2, radius * 2)
    gc.StrokeLine(cx, middle - radius, cx, cy - size * 0.40)
    gc.StrokeLine(cx - size * 0.17, cy - size * 0.44, cx + size * 0.17, cy - size * 0.44)
    gc.StrokeLine(cx, middle, cx, middle - radius * 0.52)


def draw_countdown(gc, cx, cy, size, colour, width):
    radius = size * 0.44
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
    path = gc.CreatePath()
    path.MoveToPoint(cx, cy)
    path.AddLineToPoint(cx, cy - radius)
    path.AddArc(cx, cy, radius, -math.pi / 2, 0, True)
    path.CloseSubpath()
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(colour))
    gc.FillPath(path)


def draw_settings(gc, cx, cy, size, colour, width):
    # a toothed outline, radial spokes read as a sun at this size
    outer, inner, hub = size * 0.48, size * 0.33, size * 0.15
    steps = 16

    path = gc.CreatePath()
    for step in range(steps):
        angle = math.radians(step * 360.0 / steps)
        radius = outer if step % 2 == 0 else inner
        x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        if step:
            path.AddLineToPoint(x, y)
        else:
            path.MoveToPoint(x, y)
    path.CloseSubpath()
    gc.StrokePath(path)
    gc.DrawEllipse(cx - hub, cy - hub, hub * 2, hub * 2)


def draw_menu(gc, cx, cy, size, colour, width):
    half = size * 0.42
    for offset in (-size * 0.30, 0.0, size * 0.30):
        gc.StrokeLine(cx - half, cy + offset, cx + half, cy + offset)


def draw_minimize(gc, cx, cy, size, colour, width):
    gc.StrokeLine(cx - size * 0.40, cy, cx + size * 0.40, cy)


def draw_maximize(gc, cx, cy, size, colour, width):
    span = size * 0.72
    gc.DrawRectangle(cx - span / 2, cy - span / 2, span, span)


def draw_restore(gc, cx, cy, size, colour, width):
    gc.DrawRectangle(cx - size * 0.38, cy - size * 0.22, size * 0.60, size * 0.60)
    path = gc.CreatePath()
    path.MoveToPoint(cx - size * 0.22, cy - size * 0.22)
    path.AddLineToPoint(cx - size * 0.22, cy - size * 0.38)
    path.AddLineToPoint(cx + size * 0.38, cy - size * 0.38)
    path.AddLineToPoint(cx + size * 0.38, cy + size * 0.22)
    path.AddLineToPoint(cx + size * 0.22, cy + size * 0.22)
    gc.StrokePath(path)


def draw_home(gc, cx, cy, size, colour, width):
    half = size * 0.46
    apex = cy - size * 0.42
    eaves = cy - size * 0.06
    base = cy + size * 0.40
    body = size * 0.30

    path = gc.CreatePath()
    path.MoveToPoint(cx - half, eaves)
    path.AddLineToPoint(cx, apex)
    path.AddLineToPoint(cx + half, eaves)
    gc.StrokePath(path)
    gc.DrawRectangle(cx - body, eaves, body * 2, base - eaves)


def get_meeting_angle(centre, radius, other, other_radius, upper=True):
    # where two circles cross, as an angle on the first; the upper crossing by default
    dx, dy = other[0] - centre[0], other[1] - centre[1]
    span = math.hypot(dx, dy)
    along = (radius ** 2 - other_radius ** 2 + span ** 2) / (2 * span)
    turn = math.acos(max(-1.0, min(1.0, along / radius)))
    base = math.atan2(dy, dx)
    first, second = base - turn, base + turn
    pick = first if math.sin(first) < math.sin(second) else second
    if not upper:
        pick = second if pick == first else first
    return pick


def add_cloud(path, cx, cy, size):
    # three bumps on a flat base, the outline only where no other bump covers it
    bumps = (((cx - size * 0.22, cy + size * 0.06), size * 0.16),
             ((cx + size * 0.02, cy - size * 0.04), size * 0.24),
             ((cx + size * 0.26, cy + size * 0.10), size * 0.12))
    base = cy + size * 0.22
    (left, r1), (top, r2), (right, r3) = bumps
    path.MoveToPoint(right[0], base)
    path.AddLineToPoint(left[0], base)
    path.AddArc(left[0], left[1], r1, math.pi / 2, get_meeting_angle(left, r1, top, r2), True)
    path.AddArc(top[0], top[1], r2, get_meeting_angle(top, r2, left, r1),
                get_meeting_angle(top, r2, right, r3), True)
    path.AddArc(right[0], right[1], r3, get_meeting_angle(right, r3, top, r2),
                math.pi / 2, True)
    path.CloseSubpath()


def draw_weather(gc, cx, cy, size, colour, width):
    # a sun behind a cloud: its rays only above and to the right
    sun = (cx + size * 0.14, cy - size * 0.16)
    radius = size * 0.15
    # outlines only, so the sun stops where the cloud would cover it
    arc = gc.CreatePath()
    arc.AddArc(sun[0], sun[1], radius, -math.pi * 0.95, math.pi * 0.2, True)
    gc.StrokePath(arc)
    for step in (-3, -2, -1, 0):
        angle = math.radians(step * 45)
        dx, dy = math.cos(angle), math.sin(angle)
        gc.StrokeLine(sun[0] + dx * size * 0.24, sun[1] + dy * size * 0.24,
                      sun[0] + dx * size * 0.32, sun[1] + dy * size * 0.32)
    path = gc.CreatePath()
    add_cloud(path, cx - size * 0.06, cy + size * 0.10, size * 0.92)
    gc.StrokePath(path)


def draw_close(gc, cx, cy, size, colour, width):
    arm = size * 0.36
    gc.StrokeLine(cx - arm, cy - arm, cx + arm, cy + arm)
    gc.StrokeLine(cx - arm, cy + arm, cx + arm, cy - arm)


HANDLERS = {
    'clock': draw_clock,
    'globe': draw_globe,
    'weather': draw_weather,
    'stopwatch': draw_stopwatch,
    'countdown': draw_countdown,
    'settings': draw_settings,
    'menu': draw_menu,
    'home': draw_home,
    'minimize': draw_minimize,
    'maximize': draw_maximize,
    'restore': draw_restore,
    'close': draw_close,
}
