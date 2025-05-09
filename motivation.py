import random
import tkinter as tk
from tkinter import messagebox

# 1. 预设几句打气话
PHRASES = [
    "今天也要元气满满！",
    "加油，你最棒！",
    "不要放弃，成绩就在下一步！",
    "相信自己，你可以的！",
    "努力的你，未来可期！",
    "坚持就是胜利！",
    "把每一天都当作新的开始！",
    "向着目标，再冲一把！",
]

def show_phrase():
    # 随机挑一句
    phrase = random.choice(PHRASES)

    # 弹出一个简单的 Tk 窗口
    root = tk.Tk()
    root.title("今日打气")
    root.geometry("300x150")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整大小

    label = tk.Label(root, text=phrase, wraplength=250, font=("Arial", 14))
    label.pack(pady=20)

    button = tk.Button(root, text="关闭", command=root.destroy, font=("Arial", 12))
    button.pack()

    root.mainloop()

if __name__ == "__main__":
    show_phrase()
