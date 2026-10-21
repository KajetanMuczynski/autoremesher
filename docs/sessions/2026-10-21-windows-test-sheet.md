# 2026-10-21 · Claude (cloud thread) · Windows test sheet
- Repos/commits: core 9648bb6 (master)
- Did: wrote `docs/windows-test/README.md` (Windows test sheet: CI artifact download, install by hand
  and by script, folders, Defender/SmartScreen, test plan with Linux references, what to report) and
  `docs/windows-test/quadami-update.ps1` (Windows twin of the Linux `quadami-update.sh`: dry run,
  `-Apply`, `-AllVersions`, asks Blender for its extensions folder, installs with
  `blender.exe --command extension install-file -r user_default -e`, prints the build id).
- Found: the Windows CI log confirms the extensions path
  `%APPDATA%\Blender Foundation\Blender\<X.Y>\extensions\user_default\quadami` and that `blender.exe`
  prints to the console. Same commit, same 128×64 sphere at 2000: Linux 2010 quads (Blender 4.2),
  Windows 1998 (Blender 5.2), so Windows numbers are close to, not equal to, Linux ones.
- Measured: script run with PowerShell 7.4 on Linux against a fake Blender (dry run, wrapper and
  Linux zip refused, prompt, deletions, install, non-ASCII user folder). Not run on Windows or in
  Windows PowerShell 5.1.
- Next: Kajetan's (or a helper's) first Windows run with the sheet.
