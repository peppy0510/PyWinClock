# PyWinClock

A Windows clock app drawn entirely on a wxPython canvas. Written as a replacement for
TimeKit, a UWP clock app that has been delisted from the Microsoft Store.

On a PC with Smart App Control enabled, a sideloaded MSIX cannot run without a trusted
signature. Running local sources directly through `pythonw.exe` is not subject to that
restriction, so this app is deliberately **not** packaged into a distributable build.

![Clock](assets/images/screenshot-001.png)
![Stopwatch](assets/images/screenshot-002.png)
![Countdown](assets/images/screenshot-003.png)

## Features

- **Clock** — analog dial rendered with `wx.GraphicsContext` (smooth sweeping second hand),
  digital readout, `2026-08-03 (Monday) · UTC+09:00` date line
- **Stopwatch** — start/stop, lap records, hundredths of a second
- **Countdown** — progress ring, `HH:MM:SS` entry with 1m/3m/5m/10m/30m presets,
  start/pause/reset, and a blinking `DONE` with a beep at zero
- **Settings** — 12/24-hour, local/UTC (the dial follows it too), always on top, dark theme.
  Sits at the right end of the header and returns to the previous tab when clicked again.

The whole header stays hidden until the pointer is over the window, so the clock face is
uninterrupted while idle. It keeps its space rather than collapsing, so nothing shifts when
it appears. Every header item is the same width. The header stays visible on the Settings
page so there is always a way back.

Dark and light themes cover the window title bar too, via DWM immersive dark mode. Window
size and settings persist automatically, and only one instance runs at a time
(`wininstance.has_running_instance`).

Settings are stored in `%APPDATA%\PyWinClock\settings.json`.

Every control is drawn on canvas rather than using native widgets. Native `wx.Button`,
`wx.CheckBox` and `wx.adv.DatePickerCtrl` ignore background colours on Windows and stay
light in a dark theme, so they are replaced by `controls.FlatButton`, `controls.FlatCheckBox`
and plain `wx.TextCtrl` fields.

## Requirements

Python 3.13 with `wxPython`, `psutil` and `pywin32`.

## Run

```
pythonw source\main.pyw
```

## Start menu entry

```
python source\makeicon.py
python source\makeshortcut.py
```

`makeshortcut.py` creates `Start Menu\Programs\PyWinClock.lnk` pointing at
`pythonw.exe "source\main.pyw"`. Remove that `.lnk` to uninstall.

## Layout

| File | Role |
| --- | --- |
| `source/main.pyw` | Entry point. Checks for a running instance, then calls `mainapp` |
| `source/mainapp.py` | `MainFrame`, tab wiring, timer, theme and settings |
| `source/clockbox.py` | Analog clock canvas and clock tab |
| `source/stopwatchbox.py` | Stopwatch canvas and stopwatch tab |
| `source/countdownbox.py` | Countdown ring canvas and countdown tab |
| `source/settingsbox.py` | Settings page, opened from the header |
| `source/tabbar.py` | Canvas-drawn tab header, hidden until hover |
| `source/controls.py` | Canvas-drawn button, checkbox and settings item |
| `source/utilities.py` | `Canvas` base class, themes, fonts, settings, dark title bar |
| `source/wininstance.py` | Single instance check |
| `source/shortcut.py` | Shortcut helper |
| `source/makeshortcut.py` | Creates the start menu link |
| `source/makeicon.py` | Generates `assets/icon/icon.ico` |
