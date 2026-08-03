# PyWinClock

A Windows clock app drawn entirely on a wxPython canvas. Written as a replacement for
TimeKit, a UWP clock app that has been delisted from the Microsoft Store.

On a PC with Smart App Control enabled, a sideloaded MSIX cannot run without a trusted
signature. Running local sources directly through `pythonw.exe` is not subject to that
restriction, so this app is deliberately **not** packaged into a distributable build.

![Clock](assets/images/screenshot-001.png)
![Stopwatch](assets/images/screenshot-002.png)
![Date](assets/images/screenshot-003.png)

## Features

- **Clock** — analog dial rendered with `wx.GraphicsContext` (smooth sweeping second hand),
  digital readout, 12/24-hour toggle
- **Stopwatch** — start/stop, lap records, hundredths of a second
- **Date** — D-Day counter with elapsed/remaining days and week breakdown
- Dark and light themes, including the window title bar (DWM immersive dark mode)
  and a canvas-drawn tab header
- Always on top, window size and settings persisted automatically
- Single instance (`wininstance.has_running_instance`)

Settings are stored in `%APPDATA%\PyWinClock\settings.json`.

Every control is drawn on canvas rather than using native widgets. Native `wx.Button`,
`wx.CheckBox` and `wx.adv.DatePickerCtrl` ignore background colours on Windows and stay
light in a dark theme, so they are replaced by `controls.FlatButton`, `controls.FlatCheckBox`
and a plain `wx.TextCtrl` date field.

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
| `source/daycounterbox.py` | Date tab |
| `source/tabbar.py` | Canvas-drawn tab header |
| `source/controls.py` | Canvas-drawn button and checkbox |
| `source/utilities.py` | `Canvas` base class, themes, fonts, settings, dark title bar |
| `source/wininstance.py` | Single instance check |
| `source/shortcut.py` | Shortcut helper |
| `source/makeshortcut.py` | Creates the start menu link |
| `source/makeicon.py` | Generates `assets/icon/icon.ico` |
