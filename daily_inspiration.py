#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日启发与打气 - 优化版

改进点：
- 启动时只解析文件一次，后续“下一条”直接使用缓存，避免重复 IO
- 智能避免连续重复（支持退避多次尝试）
- 更稳健的错误处理与提示
- 快捷键支持：
  - Ctrl+N / n：下一条
  - Ctrl+R / F5 / r：重新加载文件
  - Ctrl+1：打开主笔记文件
  - Ctrl+2：打开启发文件
  - Ctrl+C：复制主内容
  - Ctrl+Shift+C：复制主内容+打气话
  - Esc / Ctrl+Q：关闭窗口
- 额外按钮：复制内容、重新加载
- 可选命令行参数覆盖文件路径、窗口大小、是否置顶
"""

from __future__ import annotations

import argparse
import os
import random
import re
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import font, ttk, messagebox
from typing import List, Tuple

# --- 默认配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NOTES_PATH = os.path.join(BASE_DIR, 'my_daily_notes.txt')
DEFAULT_INSPIRATIONS_PATH = os.path.join(BASE_DIR, 'my_inspirations.txt')
APP_TITLE = "每日启发与打气"

# 笔记/启发条目起始判断：形如 "1. ..."、"23. ..."
NOTE_START_PATTERN = re.compile(r"^\d+\.\s*")

# --- 预设打气话（可自行增删） ---
ENCOURAGEMENT_PHRASES = [
    "今天也要元气满满！",
    "加油，你最棒！",
    "不要放弃，成绩就在下一步！",
    "相信自己，你可以的！",
    "努力的你，未来可期！",
    "坚持就是胜利！",
    "把每一天都当作新的开始！",
    "向着目标，再冲一把！",
    "每一次努力都算数！",
    "享受过程，结果自然来！",
    "你比你想象的更强大！",
]


def parse_items_from_file(file_path: str, pattern: re.Pattern[str]) -> List[str]:
    """从文本文件中解析分条内容。

    条目以匹配 pattern 的新行作为开头，后续非空行归并到当前条目。
    """
    items: List[str] = []
    current_item: List[str] = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if pattern.match(stripped):
                if current_item:
                    items.append('\n'.join(current_item).strip())
                current_item = [stripped]
            else:
                current_item.append(stripped)
        if current_item:
            items.append('\n'.join(current_item).strip())

    return [item for item in items if item]


@dataclass
class ParsedFilesCache:
    notes_path: str
    inspirations_path: str
    pattern: re.Pattern[str]

    _notes_cache: Tuple[float, List[str]] | None = None
    _ins_cache: Tuple[float, List[str]] | None = None

    def _read_with_mtime(self, path: str) -> Tuple[float, List[str]]:
        mtime = os.path.getmtime(path)
        items = parse_items_from_file(path, self.pattern)
        return mtime, items

    def get_notes(self) -> List[str]:
        if not os.path.exists(self.notes_path):
            raise FileNotFoundError(f"文件不存在：{self.notes_path}")
        mtime = os.path.getmtime(self.notes_path)
        if self._notes_cache is None or self._notes_cache[0] != mtime:
            self._notes_cache = self._read_with_mtime(self.notes_path)
        return self._notes_cache[1]

    def get_inspirations(self) -> List[str]:
        if not os.path.exists(self.inspirations_path):
            raise FileNotFoundError(f"文件不存在：{self.inspirations_path}")
        mtime = os.path.getmtime(self.inspirations_path)
        if self._ins_cache is None or self._ins_cache[0] != mtime:
            self._ins_cache = self._read_with_mtime(self.inspirations_path)
        return self._ins_cache[1]

    def invalidate(self) -> None:
        self._notes_cache = None
        self._ins_cache = None


class DailyInspirationApp:
    def __init__(
        self,
        notes_path: str = DEFAULT_NOTES_PATH,
        inspirations_path: str = DEFAULT_INSPIRATIONS_PATH,
        title: str = APP_TITLE,
        width: int = 480,
        height: int = 420,
        always_on_top: bool = True,
        random_seed: int | None = None,
    ) -> None:
        if random_seed is not None:
            random.seed(random_seed)

        self.notes_path = notes_path
        self.inspirations_path = inspirations_path
        self.title = title
        self.window_width = width
        self.window_height = height
        self.always_on_top = always_on_top

        self.cache = ParsedFilesCache(notes_path, inspirations_path, NOTE_START_PATTERN)

        self.last_note: str | None = None
        self.last_inspiration: str | None = None
        self.last_encouragement: str | None = None

        self.root = tk.Tk()
        self._build_ui()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        root = self.root
        root.title(self.title)

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_pos = (screen_width // 2) - (self.window_width // 2)
        y_pos = (screen_height // 2) - (self.window_height // 2)
        root.geometry(f"{self.window_width}x{self.window_height}+{x_pos}+{y_pos}")
        root.resizable(True, True)

        if self.always_on_top:
            root.attributes('-topmost', True)
        root.lift()
        root.focus_force()

        # 顶部：打气话
        bold_font = font.Font(family="Arial", size=14, weight="bold")
        self.encouragement_label = tk.Label(root, text="", font=bold_font, fg="blue", wraplength=self.window_width - 40)
        self.encouragement_label.pack(pady=(15, 10), padx=10)

        ttk.Separator(root, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # 主文本 + 滚动条
        text_frame = tk.Frame(root)
        text_frame.pack(pady=(10, 5), padx=10, fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        try:
            text_font = font.nametofont("TkFixedFont")
        except tk.TclError:
            text_font = ("Consolas", 10)

        self.text_widget = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=text_font,
            height=10,
        )
        self.text_widget.config(state="disabled")
        self.text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_widget.yview)

        # 底部：按钮组
        button_frame = tk.Frame(root)
        button_frame.pack(pady=(5, 12))

        self.next_button = tk.Button(
            button_frame,
            text="下一条",
            command=self.show_next,
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.next_button.pack(side="left", padx=8)

        self.copy_button = tk.Button(
            button_frame,
            text="复制内容",
            command=self.copy_content,
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.copy_button.pack(side="left", padx=8)

        self.reload_button = tk.Button(
            button_frame,
            text="重新加载",
            command=self.reload_files,
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.reload_button.pack(side="left", padx=8)

        self.open_notes_button = tk.Button(
            button_frame,
            text="打开主笔记文件",
            command=lambda: self.open_file(self.notes_path),
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.open_notes_button.pack(side="left", padx=8)

        self.open_insp_button = tk.Button(
            button_frame,
            text="打开今日推荐文件",
            command=lambda: self.open_file(self.inspirations_path),
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.open_insp_button.pack(side="left", padx=8)

        self.close_button = tk.Button(
            button_frame,
            text="关闭",
            command=root.destroy,
            font=("Arial", 10),
            bd=2,
            relief="raised",
        )
        self.close_button.pack(side="left", padx=8)

        # 绑定快捷键
        self._bind_hotkeys()

        # 初始展示
        self.show_next(initial=True)

    def _bind_hotkeys(self) -> None:
        root = self.root
        # 下一条
        root.bind('<Control-n>', lambda e: self.show_next())
        root.bind('n', lambda e: self.show_next())
        # 重新加载
        root.bind('<Control-r>', lambda e: self.reload_files())
        root.bind('<F5>', lambda e: self.reload_files())
        root.bind('r', lambda e: self.reload_files())
        # 打开文件
        root.bind('<Control-Key-1>', lambda e: self.open_file(self.notes_path))
        root.bind('<Control-Key-2>', lambda e: self.open_file(self.inspirations_path))
        # 复制
        root.bind('<Control-c>', lambda e: self.copy_content(include_encouragement=False))
        root.bind('<Control-C>', lambda e: self.copy_content(include_encouragement=True))
        # 关闭
        root.bind('<Escape>', lambda e: root.destroy())
        root.bind('<Control-q>', lambda e: root.destroy())

    # ---------- 业务逻辑 ----------
    @staticmethod
    def open_file(file_path: str) -> None:
        if not os.path.exists(file_path):
            messagebox.showerror("文件不存在", f"文件 '{file_path}' 不存在，请检查路径。")
            return
        try:
            if sys.platform.startswith('win'):
                os.startfile(file_path)  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("打开文件失败", f"无法打开文件 '{file_path}'：{e}")

    def _pick_non_repeating(self, items: List[str], last_item: str | None) -> str:
        if not items:
            raise ValueError("条目列表为空")
        if len(items) == 1:
            return items[0]
        # 尝试多次避免重复
        for _ in range(10):
            candidate = random.choice(items)
            if candidate != last_item:
                return candidate
        # 多次尝试仍重复，则直接返回
        return random.choice(items)

    def _compose_main_content(self, inspiration: str, note: str) -> str:
        return (
            f"--- 💡 每日启发 💡 ---\n"
            f"{inspiration}\n\n"
            f"{'=' * 30}\n\n"
            f"--- 📝 今日反思 📝 ---\n"
            f"{note}"
        )

    def _update_text(self, content: str) -> None:
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", content)
        self.text_widget.config(state="disabled")

    def show_next(self, initial: bool = False) -> None:
        try:
            notes = self.cache.get_notes()
            inspirations = self.cache.get_inspirations()
        except FileNotFoundError as e:
            self._update_text(str(e))
            self.encouragement_label.config(text="")
            if initial:
                messagebox.showerror("内容加载失败", str(e))
            return
        except Exception as e:  # noqa: BLE001
            self._update_text(f"读取文件时发生错误：{e}")
            self.encouragement_label.config(text="")
            if initial:
                messagebox.showerror("内容加载失败", f"读取文件时发生错误：{e}")
            return

        if not notes:
            self._update_text("错误：主笔记文件为空或未按编号格式编写。")
            self.encouragement_label.config(text="")
            if initial:
                messagebox.showerror("内容加载失败", "无法加载主笔记条目。")
            return
        if not inspirations:
            self._update_text("错误：启发语录文件为空或未按编号格式编写。")
            self.encouragement_label.config(text="")
            if initial:
                messagebox.showerror("内容加载失败", "无法加载启发语录条目。")
            return

        selected_note = self._pick_non_repeating(notes, self.last_note)
        selected_inspiration = self._pick_non_repeating(inspirations, self.last_inspiration)
        available_encouragements = ENCOURAGEMENT_PHRASES
        selected_encouragement = self._pick_non_repeating(available_encouragements, self.last_encouragement)

        self.last_note = selected_note
        self.last_inspiration = selected_inspiration
        self.last_encouragement = selected_encouragement

        main_content = self._compose_main_content(selected_inspiration, selected_note)
        self._update_text(main_content)
        self.encouragement_label.config(text=selected_encouragement)

    def copy_content(self, include_encouragement: bool = False) -> None:
        try:
            main_content = self.text_widget.get("1.0", tk.END).strip()
            if not main_content:
                return
            text_to_copy = main_content
            if include_encouragement:
                enc_text = self.encouragement_label.cget("text").strip()
                if enc_text:
                    text_to_copy = f"{enc_text}\n\n{main_content}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
        except Exception:
            pass

    def reload_files(self) -> None:
        self.cache.invalidate()
        self.show_next()

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日启发与打气（优化版）")
    parser.add_argument('--notes', default=DEFAULT_NOTES_PATH, help='主笔记文件路径，默认当前目录 my_daily_notes.txt')
    parser.add_argument('--inspirations', default=DEFAULT_INSPIRATIONS_PATH, help='启发语录文件路径，默认当前目录 my_inspirations.txt')
    parser.add_argument('--title', default=APP_TITLE, help='窗口标题')
    parser.add_argument('--width', type=int, default=480, help='窗口宽度')
    parser.add_argument('--height', type=int, default=420, help='窗口高度')
    parser.add_argument('--no-topmost', action='store_true', help='取消窗口置顶')
    parser.add_argument('--seed', type=int, default=None, help='随机数种子（可复现选择）')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    app = DailyInspirationApp(
        notes_path=args.notes,
        inspirations_path=args.inspirations,
        title=args.title,
        width=args.width,
        height=args.height,
        always_on_top=(not args.no_topmost),
        random_seed=args.seed,
    )
    app.run()