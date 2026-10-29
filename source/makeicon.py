# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import math
import os
import wx


SIZE = 128
DISC = '#4a4f57'
DIAL = '#f2f3f5'
TICK = '#5b616a'
HAND = '#22262b'
SECOND = '#8b929b'


def draw_icon(gc, size):
    cx = cy = size / 2
    radius = size / 2 - 2

    gc.SetPen(wx.Pen(wx.Colour(DISC), 1))
    gc.SetBrush(wx.Brush(wx.Colour(DISC)))
    gc.DrawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

    inner = radius * 0.86
    gc.SetBrush(wx.Brush(wx.Colour(DIAL)))
    gc.DrawEllipse(cx - inner, cy - inner, inner * 2, inner * 2)

    gc.SetPen(wx.Pen(wx.Colour(TICK), max(2, int(size / 32))))
    for index in range(12):
        angle = math.radians(index * 30)
        outer = inner * 0.88
        length = inner * (0.72 if index % 3 == 0 else 0.80)
        gc.StrokeLine(cx + outer * math.sin(angle), cy - outer * math.cos(angle),
                      cx + length * math.sin(angle), cy - length * math.cos(angle))

    def hand(fraction, length, width, colour):
        angle = math.radians(fraction * 360)
        gc.SetPen(wx.Pen(wx.Colour(colour), width, wx.PENSTYLE_SOLID))
        gc.StrokeLine(cx, cy, cx + length * math.sin(angle), cy - length * math.cos(angle))

    hand(10 / 12 + (10 / 60) / 12, inner * 0.46, max(3, int(size / 20)), HAND)
    hand(10 / 60, inner * 0.68, max(3, int(size / 24)), HAND)
    hand(0, inner * 0.74, max(2, int(size / 48)), SECOND)

    gc.SetPen(wx.Pen(wx.Colour(DIAL), 1))
    gc.SetBrush(wx.Brush(wx.Colour(HAND)))
    cap = max(2, size / 32)
    gc.DrawEllipse(cx - cap, cy - cap, cap * 2, cap * 2)


def main():
    app = wx.App(False)  # noqa
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, 'assets', 'icon')
    os.makedirs(path, exist_ok=True)

    bitmap = wx.Bitmap(SIZE, SIZE)
    dc = wx.MemoryDC(bitmap)
    dc.SetBackground(wx.Brush(wx.Colour(DISC)))
    dc.Clear()
    gc = wx.GraphicsContext.Create(dc)
    gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
    draw_icon(gc, SIZE)
    del gc
    dc.SelectObject(wx.NullBitmap)

    bitmap.SaveFile(os.path.join(path, 'icon.png'), wx.BITMAP_TYPE_PNG)
    bitmap.SaveFile(os.path.join(path, 'icon.ico'), wx.BITMAP_TYPE_ICO)
    print(f'[ ICON CREATED ] [ {os.path.join(path, "icon.ico")} ]')


if __name__ == '__main__':
    main()
