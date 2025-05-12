#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时监控截图并按指定日期范围分类脚本

功能：
1. 每当到新的时间段（默认每10天）自动创建对应的文件夹。
2. 监控新增文件，按照创建/修改/EXIF时间自动分类。
3. 启动时处理现有所有图片，并重新分类。

Usage:
    python screen_auto_control.py WATCH_DIR DST_DIR [options]
Example:
    python screen_auto_control.py F:\\screenpicture F:\\screenpicture \
        --days 10 --origin 2025-05-01 --source ctime --process-existing
"""
import os
import shutil
import time
import argparse
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    EXIF_AVAILABLE = True
except ImportError:
    EXIF_AVAILABLE = False

# 全局参数，可由命令行覆盖
DAYS_PER_FOLDER = 10
ORIGIN_DATE = datetime(2025, 5, 1)


def get_exif_datetime(path: str) -> datetime | None:
    """
    从图片 EXIF 获取拍摄时间，失败返回 None
    """
    if not EXIF_AVAILABLE:
        return None
    try:
        img = Image.open(path)
        exif = img._getexif() or {}
        for tag, val in exif.items():
            name = TAGS.get(tag, tag)
            if name in ("DateTime", "DateTimeOriginal", "DateTimeDigitized"):
                return datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def pick_timestamp(path: str, source: str) -> datetime:
    """
    根据 source 选择时间戳：
      - mtime: 修改时间
      - ctime: 创建时间
      - exif: EXIF 时间（失败退回 mtime）
    """
    if source == "exif":
        dt = get_exif_datetime(path)
        if dt:
            return dt
    stat = os.stat(path)
    ts = stat.st_mtime if source != "ctime" else stat.st_ctime
    return datetime.fromtimestamp(ts)


def ensure_unique(dst: str) -> str:
    """
    如果目标已存在，同名文件后追加 _1、_2...避免覆盖
    """
    base, ext = os.path.splitext(dst)
    i = 1
    new_dst = dst
    while os.path.exists(new_dst):
        new_dst = f"{base}_{i}{ext}"
        i += 1
    return new_dst


def get_date_range_folder(dt: datetime, origin: datetime, days: int) -> str:
    """
    计算 dt 所属的时间段文件夹名，格式 YYYY.MM.DD-YYYY.MM.DD
    """
    delta = (dt.date() - origin.date()).days
    idx = delta // days
    start = origin.date() + timedelta(days=idx * days)
    end = start + timedelta(days=days - 1)
    return f"{start.strftime('%Y.%m.%d')}-{end.strftime('%Y.%m.%d')}"


def sort_file(path: str, dst_root: str, source: str, origin: datetime, days: int):
    """
    将单个文件移动到 dst_root/对应日期段/ 下
    """
    dt = pick_timestamp(path, source)
    folder_name = get_date_range_folder(dt, origin, days)
    target = os.path.join(dst_root, folder_name)
    os.makedirs(target, exist_ok=True)
    name = os.path.basename(path)
    dst = ensure_unique(os.path.join(target, name))
    shutil.move(path, dst)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Moved {name} → {folder_name}/")


def process_existing(watch_dir: str, dst_root: str, source: str, origin: datetime, days: int, exts: set[str]):
    """
    处理 watch_dir 下现有所有图片文件，重新分类
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing existing files...")
    for root, _, files in os.walk(watch_dir):
        for f in files:
            if f.lower().endswith(tuple(exts)):
                fp = os.path.join(root, f)
                # 跳过已归档目录
                if os.path.commonpath([fp, dst_root]) == dst_root:
                    continue
                sort_file(fp, dst_root, source, origin, days)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Existing done.")


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, dst_root: str, source: str, origin: datetime, days: int, exts: set[str]):
        self.dst = dst_root
        self.source = source
        self.origin = origin
        self.days = days
        self.exts = exts

    def on_created(self, event):
        if event.is_directory:
            return
        if not any(event.src_path.lower().endswith(e) for e in self.exts):
            return
        time.sleep(0.2)
        sort_file(event.src_path, self.dst, self.source, self.origin, self.days)


def main():
    parser = argparse.ArgumentParser(description="实时监控并按日期段分类截图")
    # 将 watch_dir 和 dst_dir 改为可选参数，添加默认值
    parser.add_argument('--watch_dir', default=r"F:\screenpicture", help='监控目录')
    parser.add_argument('--dst_dir', default=r"F:\screenpicture", help='目标目录')
    parser.add_argument('--days', '-d', type=int, default=DAYS_PER_FOLDER, help='每段天数')
    parser.add_argument('--origin', '-o', type=str, default=ORIGIN_DATE.strftime('%Y-%m-%d'), help='起始参考日期 YYYY-MM-DD')
    parser.add_argument('--source', '-s', choices=['mtime', 'ctime', 'exif'], default='ctime', help='时间源')
    parser.add_argument('--exts', '-e', default='png,jpg,jpeg', help='后缀列表')
    parser.add_argument('--process-existing', action='store_true', help='启动时处理现有文件')
    args = parser.parse_args()

    days = args.days
    origin = datetime.strptime(args.origin, '%Y-%m-%d')
    exts = {e.strip().lower() for e in args.exts.split(',')}
    os.makedirs(args.dst_dir, exist_ok=True)
    if args.source == 'exif' and not EXIF_AVAILABLE:
        print('Warning: Pillow missing, fallback to mtime.')

    if args.process_existing:
        process_existing(args.watch_dir, args.dst_dir, args.source, origin, days, exts)

    handler = ScreenshotHandler(args.dst_dir, args.source, origin, days, exts)
    observer = Observer()
    observer.schedule(handler, args.watch_dir, recursive=False)
    observer.start()
    print(f"Watching {args.watch_dir} → sorting into {args.dst_dir} every {days} days from {origin.date()}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
