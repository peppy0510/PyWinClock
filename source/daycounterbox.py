# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com

네이티브 wx.adv.DatePickerCtrl 은 Windows 에서 다크 배경을 따르지 않는다.
다크로 칠할 수 있는 wx.TextCtrl 에 YYYY-MM-DD 를 직접 입력받는다.
'''


import datetime
import wx

from controls import FlatButton
from utilities import get_font


DATE_FORMAT = '%Y-%m-%d'


class DayCounterBox(wx.Panel):

    def __init__(self, parent, theme):
        super().__init__(parent)
        today = datetime.date.today()

        self.result = wx.StaticText(self, label='')
        self.detail = wx.StaticText(self, label='')
        self.result.SetFont(get_font(26, bold=True))
        self.detail.SetFont(get_font(10))

        self.labels = [wx.StaticText(self, label='From'), wx.StaticText(self, label='To')]
        self.base = wx.TextCtrl(self, value=today.strftime(DATE_FORMAT),
                                style=wx.TE_PROCESS_ENTER | wx.NO_BORDER)
        self.target = wx.TextCtrl(self, value=today.strftime(DATE_FORMAT),
                                  style=wx.TE_PROCESS_ENTER | wx.NO_BORDER)
        self.buttons = [
            FlatButton(self, theme, 'Today', self.on_base_today, size=(64, 26)),
            FlatButton(self, theme, 'Today', self.on_target_today, size=(64, 26)),
        ]

        for field in (self.base, self.target):
            field.Bind(wx.EVT_TEXT, lambda event: self.recalculate())

        grid = wx.FlexGridSizer(2, 3, 8, 10)
        grid.Add(self.labels[0], 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.base, 1, wx.EXPAND)
        grid.Add(self.buttons[0], 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.labels[1], 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.target, 1, wx.EXPAND)
        grid.Add(self.buttons[1], 0, wx.ALIGN_CENTER_VERTICAL)
        grid.AddGrowableCol(1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.result, 0, wx.ALIGN_CENTER)
        sizer.Add(self.detail, 0, wx.ALIGN_CENTER | wx.TOP, 6)
        sizer.AddStretchSpacer()
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 18)
        self.SetSizer(sizer)
        self.apply_theme(theme)
        self.recalculate()

    def apply_theme(self, theme):
        self.theme = theme
        self.SetBackgroundColour(wx.Colour(theme['bg']))
        self.result.SetForegroundColour(wx.Colour(theme['text']))
        self.detail.SetForegroundColour(wx.Colour(theme['dim']))
        for label in self.labels:
            label.SetForegroundColour(wx.Colour(theme['dim']))
            label.SetBackgroundColour(wx.Colour(theme['bg']))
            label.SetFont(get_font(9))
        for field in (self.base, self.target):
            field.SetBackgroundColour(wx.Colour(theme['control']))
            field.SetForegroundColour(wx.Colour(theme['text']))
            field.SetFont(get_font(10))
        for button in self.buttons:
            button.set_theme(theme)
        self.Refresh()

    def get_date(self, field):
        try:
            return datetime.datetime.strptime(field.GetValue().strip(), DATE_FORMAT).date()
        except ValueError:
            return None

    def on_base_today(self):
        self.base.SetValue(datetime.date.today().strftime(DATE_FORMAT))

    def on_target_today(self):
        self.target.SetValue(datetime.date.today().strftime(DATE_FORMAT))

    def recalculate(self):
        base = self.get_date(self.base)
        target = self.get_date(self.target)
        if base is None or target is None:
            self.result.SetLabel('--')
            self.detail.SetLabel('enter dates as YYYY-MM-DD')
            self.Layout()
            return

        days = (target - base).days
        if days == 0:
            self.result.SetLabel('D-Day')
        elif days > 0:
            self.result.SetLabel('D-%d' % days)
        else:
            self.result.SetLabel('D+%d' % -days)
        self.detail.SetLabel('%s  →  %s      %d days  (%dw %dd)' % (
            base.strftime(DATE_FORMAT), target.strftime(DATE_FORMAT),
            days, abs(days) // 7, abs(days) % 7))
        self.Layout()

    def tick(self):
        pass
