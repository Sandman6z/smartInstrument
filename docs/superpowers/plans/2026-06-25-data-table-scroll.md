# 数据记录表格：冻结首列 + 水平滚动 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `data_panel.py` 中的单 Treeview 表格改为双 Treeview 布局（左列固定设备名，右列数据区域绑定水平滚动条），解决列数增多时数据被压缩的问题。

**Architecture:** 使用两个 `ttk.Treeview` 并排，左侧仅显示设备名（固定宽度不滚动），右侧显示所有触发数据列并绑定水平滚动条（`stretch=tk.NO` 防止列被压缩）。两个 Treeview 行高一致。

**Tech Stack:** Python tkinter / ttk

---

### Task 1: 重写 data_panel.py 为双 Treeview 布局

**Files:**
- Modify: `src/smart_instrument/gui/components/data_panel.py`（完整重写 `create_widgets()`、`add_data_column()`、`clear_data()`）

- [ ] **Step 1: 导入所需模块（保持不变）**

`data_panel.py` 顶部导入无需改动，保持现有：
```python
import tkinter as tk
from tkinter import ttk, messagebox
import logging
```

- [ ] **Step 2: 重写 `create_widgets()` 为双 Treeview 布局**

替换原有单 Treeview 创建逻辑，改为左右两个并排 Treeview：

```python
def create_widgets(self):
    # ── 容器 ──
    tree_frame = ttk.Frame(self)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    # ── 左侧：设备名（固定） ──
    self.left_tree = ttk.Treeview(tree_frame, height=3, show="tree")
    self.left_tree.column("#0", width=145, minwidth=145, stretch=tk.NO)
    self.left_tree.heading("#0", text="设备")
    self.left_tree.insert("", tk.END, text="IT8811 (电阻)")
    self.left_tree.insert("", tk.END, text="DMM6500 (电压)")
    self.left_tree.insert("", tk.END, text="KEYSIGHT 34461A (电流)")
    self.left_tree.pack(side=tk.LEFT, fill=tk.Y)

    # ── 右侧：数据列（可水平滚动） ──
    right_frame = ttk.Frame(tree_frame)
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 水平滚动条
    hscrollbar = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
    hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    self.right_tree = ttk.Treeview(
        right_frame,
        height=3,
        show="headings",
        xscrollcommand=hscrollbar.set,
        columns=("col1", "col2"),
    )
    hscrollbar.config(command=self.right_tree.xview)

    # 初始数据列
    for col_name in ("col1", "col2"):
        self.right_tree.column(col_name, width=90, minwidth=80, stretch=tk.NO, anchor=tk.CENTER)
    self.right_tree.heading("col1", text="触发1")
    self.right_tree.heading("col2", text="触发2")

    # 预占位三行空数据（行索引与 left_tree 一一对应）
    self.right_tree.insert("", tk.END, values=("", ""))
    self.right_tree.insert("", tk.END, values=("", ""))
    self.right_tree.insert("", tk.END, values=("", ""))

    self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ── 清除按钮 ──
    clear_frame = ttk.Frame(self)
    clear_frame.pack(fill=tk.X, pady=5)

    self.clear_data_button = ttk.Button(
        clear_frame,
        text="清除测试数据",
        command=self.confirm_clear_data,
    )
    self.clear_data_button.pack(side=tk.RIGHT, padx=5)
```

说明：
- `show="tree"` 使左侧 Treeview 只显示树列（#0），无表头列
- `show="headings"` 使右侧 Treeview 只显示表头列，无树列
- `anchor=tk.CENTER` 让数据列中的数值居中显示
- 左 Treeview 用 `pack(side=LEFT, fill=Y)` 固定宽度不拉伸
- 右 Treeview 用 `pack(side=LEFT, fill=BOTH, expand=True)` 填充剩余宽度并绑定水平滚动条
- 两侧 Treeview 都 `insert` 了 3 行，行索引一一对应

- [ ] **Step 3: 重写 `add_data_column()`**

```python
def add_data_column(self, col_index, resistance, voltage, current):
    col_name = f"col{col_index}"

    # 如果列不存在，添加到右 Treeview
    if col_name not in self.right_tree["columns"]:
        self.right_tree["columns"] = self.right_tree["columns"] + (col_name,)
        self.right_tree.column(col_name, width=90, minwidth=80, stretch=tk.NO, anchor=tk.CENTER)
        self.right_tree.heading(col_name, text=f"触发{col_index}")

    # 更新三行数据（行索引 0=电阻, 1=电压, 2=电流）
    try:
        children = self.right_tree.get_children()
        if len(children) >= 3:
            self.right_tree.set(children[0], col_name, resistance)
            self.right_tree.set(children[1], col_name, voltage)
            self.right_tree.set(children[2], col_name, current)
    except Exception as e:
        logging.error(f"更新表格失败: {e}")
```

说明：
- 所有操作只在 `self.right_tree` 上进行
- `self.left_tree` 的行数据只在初始化时设置一次，后续不变

- [ ] **Step 4: 重写 `clear_data()`**

```python
def clear_data(self):
    success, msg = self.data_manager.clear_data()
    if success:
        # 清空右 Treeview 所有数据列的值
        for item in self.right_tree.get_children():
            for col in list(self.right_tree["columns"]):
                self.right_tree.set(item, col, "")
        logging.info(msg)
        messagebox.showinfo("成功", msg)
    else:
        messagebox.showerror("错误", msg)
```

- `confirm_clear_data()` 方法**无需改动**

- [ ] **Step 5: 应用配色方案**

在 `create_widgets()` 中补充样式配置，使用 `ttk.Style()` 调整 Treeview 的配色。在 `create_widgets()` 开头添加：

```python
# ── 配色 ──
style = ttk.Style()
style.theme_use("clam")  # clam 主题支持配置更多颜色
style.configure("Treeview",
    background="#ffffff",
    foreground="#999999",
    fieldbackground="#ffffff",
    borderwidth=0)
style.configure("Treeview.Heading",
    background="#f8f8f8",
    foreground="#999999",
    borderwidth=0)
style.map("Treeview", background=[("selected", "#f0f0f0")])
style.map("Treeview.Heading", background=[("active", "#f0f0f0")])
```

注意：先检查当前主题支持情况。在 Windows 上，`clam` 主题的 Treeview 边框可能不符合预期，需要根据实际效果调整或省略部分样式。

- [ ] **Step 6: 确保初始列（col1, col2）正确**

注意 `__init__` 中的初始列声明（`columns=("col1", "col2")`）和 `add_data_column` 的动态添加逻辑不要冲突。当 `add_data_column(1, ...)` 首次调用时，col1 已存在，直接设置值而不重复添加列。验证 `add_data_column` 中的 `if col_name not in self.right_tree["columns"]` 检查能正确处理初始列。

- [ ] **Step 7: 验证改动**

手动检查项：
1. 启动应用，确认双 Treeview 布局正常：左侧显示设备名，右侧显示数据列
2. 点击触发采集，确认新数据列追加到右侧 Treeview
3. 增加多个触发（≥8次），确认水平滚动条出现，数据列不再被压缩
4. 点击"清除测试数据"，确认右侧数据被清空、左侧设备名保持不变
5. 调整窗口宽度，确认右侧 Treeview 自适应填充、左侧宽度固定
6. 检查颜色是否符合预期的浅色方案
