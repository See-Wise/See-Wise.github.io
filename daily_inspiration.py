#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日启发与打气 - 增强版

改进点：
- 更清晰的结构：面向对象封装，职责更清晰
- 解析更健壮：跳过空行、支持跨行条目、编号匹配更宽松
- 避免重复：同一会话内避免重复，并将上次选择持久化到本地 JSON，跨会话也尽量避免立即重复
- 可选自动热更新：若安装 watchdog，则文件修改后自动刷新内容（否则手动“刷新”即可）
- 快捷键：N 下一条，Ctrl+C 复制，Ctrl+O 打开文件，Esc 关闭
- 细节：状态栏显示条目数量，复制按钮，窗口大小/置顶可通过 CLI 配置

用法示例：
  python daily_inspiration.py \
      --notes my_daily_notes.txt \
      --inspirations my_inspirations.txt \
      --title "每日启发与打气" --width 520 --height 460 --topmost

文本格式：
- 每条以“数字+点+空格”开始，如：
  1. 今天做了哪些事
     这里是多行内容
  2. 下一条
- 多行会自动合并到同一条目；空行会被忽略
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import font, ttk, messagebox

# 可选依赖：watchdog 用于自动文件变更刷新
try:
    from watchdog.observers import Observer  # type: ignore
    from watchdog.events import FileSystemEventHandler  # type: ignore
    WATCHDOG_AVAILABLE = True
except Exception:
    WATCHDOG_AVAILABLE = False


DEFAULT_ENCOURAGEMENT_PHRASES = [
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

NOTE_START_PATTERN = re.compile(r"^\s*\d+\.\s+")


@dataclass
class ParsedText:
    items: List[str] = field(default_factory=list)
    mtime: float = 0.0


def parse_numbered_items(file_path: Path, pattern: re.Pattern[str]) -> ParsedText:
    items: List[str] = []
    current: List[str] = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n").strip()
                if not line:
                    continue
                if pattern.match(line):
                    if current:
                        items.append("\n".join(current).strip())
                    current = [line]
                else:
                    current.append(line)
        if current:
            items.append("\n".join(current).strip())
    except FileNotFoundError:
        return ParsedText([], 0.0)
    except Exception as exc:
        print(f"读取文件失败: {file_path} -> {exc}")
        return ParsedText([], 0.0)

    try:
        mtime = file_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    return ParsedText(items, mtime)


@dataclass
class AppState:
    last_note: Optional[str] = None
    last_inspiration: Optional[str] = None
    last_encouragement: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "last_note": self.last_note,
            "last_inspiration": self.last_inspiration,
            "last_encouragement": self.last_encouragement,
        }

    @staticmethod
    def from_dict(data: dict) -> "AppState":
        return AppState(
            last_note=data.get("last_note"),
            last_inspiration=data.get("last_inspiration"),
            last_encouragement=data.get("last_encouragement"),
        )


class FileChangeHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, target_files: set[Path], on_change):
        super().__init__()
        self.target_files = {str(p.resolve()) for p in target_files}
        self.on_change = on_change

    def on_modified(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):
            return
        try:
            src = str(Path(event.src_path).resolve())
        except Exception:
            return
        if src in self.target_files:
            self.on_change()


class InspirationApp:
    def __init__(
        self,
        notes_path: Path,
        inspirations_path: Path,
        title: str,
        window_width: int,
        window_height: int,
        topmost: bool,
        encouragement_phrases: Optional[List[str]] = None,
        state_path: Optional[Path] = None,
        auto_watch: bool = True,
    ) -> None:
        self.notes_path = notes_path
        self.inspirations_path = inspirations_path
        self.title = title
        self.window_width = window_width
        self.window_height = window_height
        self.topmost = topmost
        self.encouragement_phrases = encouragement_phrases or list(DEFAULT_ENCOURAGEMENT_PHRASES)
        self.state_path = state_path or notes_path.parent.joinpath(".daily_inspiration_state.json")
        self.state = self._load_state()

        # 数据缓存
        self._notes_cache: ParsedText = ParsedText([], 0.0)
        self._insp_cache: ParsedText = ParsedText([], 0.0)

        # GUI
        self.root = tk.Tk()
        self.root.title(self.title)
        self._configure_window()
        self._build_widgets()
        self._bind_shortcuts()

        # 初次加载
        self._refresh_content()

        # 可选热更新
        self.observer: Optional[Observer] = None
        if auto_watch and WATCHDOG_AVAILABLE:
            self._start_watching()

    # ------------- 状态持久化 -------------
    def _load_state(self) -> AppState:
        try:
            if self.state_path.exists():
                with self.state_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return AppState.from_dict(data)
        except Exception:
            pass
        return AppState()

    def _save_state(self) -> None:
        try:
            with self.state_path.open("w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------- 文件解析与选择 -------------
    def _load_items_if_needed(self) -> Tuple[List[str], List[str]]:
        notes = self._notes_cache
        insp = self._insp_cache

        if (not notes.items) or not self.notes_path.exists() or self.notes_path.stat().st_mtime != notes.mtime:
            self._notes_cache = parse_numbered_items(self.notes_path, NOTE_START_PATTERN)
        if (not insp.items) or not self.inspirations_path.exists() or self.inspirations_path.stat().st_mtime != insp.mtime:
            self._insp_cache = parse_numbered_items(self.inspirations_path, NOTE_START_PATTERN)
        return self._notes_cache.items, self._insp_cache.items

    def _pick_without_immediate_repeat(self, items: List[str], last: Optional[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        pool = [x for x in items if x != last]
        return random.choice(pool if pool else items)

    def _compose_display_text(self, inspiration: str, note: str) -> str:
        divider = "=" * 30
        return (
            f"--- 💡 每日启发 💡 ---\n"
            f"{inspiration}\n\n"
            f"{divider}\n\n"
            f"--- 📝 今日反思 📝 ---\n"
            f"{note}"
        )

    def _generate_new(self) -> Tuple[str, str, bool, str]:
        notes, insps = self._load_items_if_needed()
        if not notes:
            return "错误：无法加载主笔记文件。请检查路径和内容。", "", False, "notes"
        if not insps:
            return "错误：无法加载启发语录文件。请检查路径和内容。", "", False, "insp"

        note = self._pick_without_immediate_repeat(notes, self.state.last_note)
        insp = self._pick_without_immediate_repeat(insps, self.state.last_inspiration)
        encour = self._pick_without_immediate_repeat(self.encouragement_phrases, self.state.last_encouragement)

        self.state.last_note = note
        self.state.last_inspiration = insp
        self.state.last_encouragement = encour
        self._save_state()

        return self._compose_display_text(insp, note), encour, True, "ok"

    # ------------- GUI -------------
    def _configure_window(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w // 2) - (self.window_width // 2)
        y = (screen_h // 2) - (self.window_height // 2)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.root.resizable(True, True)
        try:
            self.root.attributes('-topmost', bool(self.topmost))
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()

    def _build_widgets(self) -> None:
        # 打气话
        bold_font = font.Font(family="Arial", size=14, weight="bold")
        self.enc_label = tk.Label(self.root, text="", font=bold_font, fg="blue", wraplength=self.window_width - 40)
        self.enc_label.pack(pady=(15, 10), padx=10)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # 文本区域 + 滚动条
        text_frame = tk.Frame(self.root)
        text_frame.pack(pady=(10, 5), padx=10, fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(text_frame)
        self.scrollbar.pack(side="right", fill="y")

        try:
            text_font = font.nametofont("TkFixedFont")
        except tk.TclError:
            text_font = ("Consolas", 10)

        self.text = tk.Text(text_frame, wrap="word", yscrollcommand=self.scrollbar.set, font=text_font, height=10)
        self.text.config(state="disabled")
        self.text.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text.yview)

        # 操作按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=(5, 5))

        self.btn_next = tk.Button(btn_frame, text="下一条", command=self._refresh_content, font=("Arial", 10), bd=2, relief="raised")
        self.btn_next.pack(side="left", padx=8)

        self.btn_copy = tk.Button(btn_frame, text="复制", command=self._copy_to_clipboard, font=("Arial", 10), bd=2, relief="raised")
        self.btn_copy.pack(side="left", padx=8)

        self.btn_open_notes = tk.Button(btn_frame, text="打开主笔记文件", command=lambda: self._open_file(self.notes_path), font=("Arial", 10), bd=2, relief="raised")
        self.btn_open_notes.pack(side="left", padx=8)

        self.btn_open_insp = tk.Button(btn_frame, text="打开今日推荐文件", command=lambda: self._open_file(self.inspirations_path), font=("Arial", 10), bd=2, relief="raised")
        self.btn_open_insp.pack(side="left", padx=8)

        self.btn_refresh = tk.Button(btn_frame, text="刷新", command=self._force_reload, font=("Arial", 10), bd=2, relief="raised")
        self.btn_refresh.pack(side="left", padx=8)

        self.btn_close = tk.Button(btn_frame, text="关闭", command=self.root.destroy, font=("Arial", 10), bd=2, relief="raised")
        self.btn_close.pack(side="left", padx=8)

        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("n", lambda e: self._refresh_content())
        self.root.bind("N", lambda e: self._refresh_content())
        self.root.bind("<Control-c>", lambda e: self._copy_to_clipboard())
        self.root.bind("<Control-C>", lambda e: self._copy_to_clipboard())
        self.root.bind("<Control-o>", lambda e: self._open_file(self.notes_path))
        self.root.bind("<Control-O>", lambda e: self._open_file(self.notes_path))

    def _set_text(self, text: str) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        self.text.config(state="disabled")

    def _copy_to_clipboard(self) -> None:
        try:
            content = self.text.get("1.0", tk.END).strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self._set_status("已复制到剪贴板")
        except Exception as exc:
            self._set_status(f"复制失败: {exc}")

    def _set_status(self, msg: str) -> None:
        # 统计信息
        notes_count = len(self._notes_cache.items) if self._notes_cache.items else 0
        insp_count = len(self._insp_cache.items) if self._insp_cache.items else 0
        self.status_var.set(f"{msg}  |  启发:{insp_count}  反思:{notes_count}")

    def _refresh_content(self) -> None:
        main_content, encouragement, ok, which = self._generate_new()
        if ok:
            self._set_text(main_content)
            self.enc_label.config(text=encouragement)
            self._set_status("已更新")
        else:
            self._set_text(main_content)
            self.enc_label.config(text="")
            self._set_status("加载失败")
            messagebox.showerror("内容加载失败", main_content)

    def _force_reload(self) -> None:
        # 置空 mtime 以触发重载
        self._notes_cache.mtime = -1.0
        self._insp_cache.mtime = -1.0
        self._refresh_content()

    def _open_file(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror("文件不存在", f"文件 '{path}' 不存在，请检查路径。")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            messagebox.showerror("打开文件失败", f"无法打开文件 '{path}'：{exc}")

    # ------------- 自动刷新 -------------
    def _start_watching(self) -> None:
        # 监听这两个文件所在目录
        try:
            notes_dir = self.notes_path.parent
            insp_dir = self.inspirations_path.parent
            self.observer = Observer()
            handler = FileChangeHandler({self.notes_path, self.inspirations_path}, self._on_files_changed)
            self.observer.schedule(handler, str(notes_dir), recursive=False)
            if insp_dir != notes_dir:
                self.observer.schedule(handler, str(insp_dir), recursive=False)
            self.observer.start()
            self._set_status("自动监听已开启")
        except Exception:
            self.observer = None

    def _on_files_changed(self) -> None:
        self.root.after(100, self._force_reload)

    # ------------- 运行 -------------
    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            if self.observer:
                try:
                    self.observer.stop()
                    self.observer.join(timeout=1.0)
                except Exception:
                    pass


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日启发与打气 - 增强版")
    base_dir = Path(__file__).resolve().parent
    parser.add_argument("--notes", default=str(base_dir / "my_daily_notes.txt"), help="主笔记文件路径")
    parser.add_argument("--inspirations", default=str(base_dir / "my_inspirations.txt"), help="启发语录文件路径")
    parser.add_argument("--title", default="每日启发与打气", help="窗口标题")
    parser.add_argument("--width", type=int, default=480, help="窗口宽度")
    parser.add_argument("--height", type=int, default=420, help="窗口高度")
    parser.add_argument("--topmost", action="store_true", help="窗口置顶")
    parser.add_argument("--no-watch", action="store_true", help="禁用文件变更自动刷新")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    app = InspirationApp(
        notes_path=Path(args.notes),
        inspirations_path=Path(args.inspirations),
        title=args.title,
        window_width=args.width,
        window_height=args.height,
        topmost=bool(args.topmost),
        encouragement_phrases=None,
        state_path=None,
        auto_watch=(not args.no_watch),
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())