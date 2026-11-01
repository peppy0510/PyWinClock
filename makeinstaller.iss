; http://www.jrsoftware.org/ishelp/index.php

[Setup]
AppName="PyWinClock"
AppVerName="PyWinClock 0.1.0"
DefaultDirName="{autopf}\PyWinClock"
DefaultGroupName="PyWinClock"
AppVersion="0.1.0"
AppCopyright="Taehong Kim"
AppPublisher="Taehong Kim"
UninstallDisplayIcon="{app}\PyWinClock.exe"
Compression=lzma2/max
SolidCompression=yes
OutputDir=".dist"
OutputBaseFilename="PyWinClock-0.1.0-Setup"
; VersionInfoVersion="0.1.0"
VersionInfoProductVersion="0.1.0"
VersionInfoCompany="Taehong Kim"
VersionInfoCopyright="Taehong Kim"
ArchitecturesInstallIn64BitMode="x64compatible"

[Files]
Source: ".dist\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\PyWinClock"; Filename: "{app}\PyWinClock.exe"
Name: "{commondesktop}\PyWinClock"; Filename: "{app}\PyWinClock.exe"
