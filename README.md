# Tools

## 1) Screenshot sorter (`shixian.py`)

- Purpose: Watch a directory and sort images into date range folders like `YYYY.MM.DD-YYYY.MM.DD` based on ctime/mtime/EXIF.
- Requirements: `watchdog`, optional `Pillow` for EXIF.

Example:

```bash
python shixian.py --watch_dir F:\screenpicture --dst_dir F:\screenpicture --days 10 --origin 2025-05-01 --source ctime --process-existing
```

Args:
- `--watch_dir`: directory to watch
- `--dst_dir`: destination root
- `--days`: days per bucket (default 10)
- `--origin`: start date `YYYY-MM-DD`
- `--source`: `mtime` | `ctime` | `exif`
- `--process-existing`: re-sort current files at startup

## 2) Daily inspiration app (`daily_inspiration.py`)

- Purpose: Show a random inspiration and a random reflection from numbered text files, with encouragement, hotkeys, and optional auto reload.
- Requirements: `tkinter` (built-in on many systems). Optional `watchdog` for auto-reload.

Text format example for files (`my_inspirations.txt` / `my_daily_notes.txt`):

```
1. 第一条
多行会合并为同一条
2. 第二条
```

Run:

```bash
python daily_inspiration.py --notes my_daily_notes.txt --inspirations my_inspirations.txt --title "每日启发与打气" --width 520 --height 460 --topmost
```

Hotkeys:
- N: next
- Ctrl+C: copy all text
- Ctrl+O: open notes file
- Esc: close

If `watchdog` is installed, edits to the files will auto-refresh in the UI. Otherwise use the “刷新” button.

## Install optional deps

```bash
pip install watchdog pillow
```
