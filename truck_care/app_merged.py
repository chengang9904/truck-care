"""合并版本的应用界面 - 将牵引车/挂车的三个标签页各自合并成一个"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .constants import (
    MAINTENANCE_TYPES,
    TRACTOR_TIRE_POSITIONS,
    TRAILER_TIRE_POSITIONS,
    VEHICLE_TYPE_TRACTOR,
    VEHICLE_TYPE_TRAILER,
)
from .db import Database, MaintenanceRecord, TireEvent, Tractor, Trailer
from .exporter import export_csv


def _parse_int(value: str, field_name: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name}不能为空")
    try:
        n = int(value)
    except ValueError as e:
        raise ValueError(f"{field_name}必须是整数") from e
    if n < 0:
        raise ValueError(f"{field_name}不能为负数")
    return n


def _parse_date(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name}不能为空")
    date.fromisoformat(value)
    return value


class TireVisualizer(tk.Canvas):
    """轮胎可视化组件"""
    
    def __init__(
        self,
        parent: tk.Widget,
        tire_positions: tuple[str, ...],
        vehicle_label: str,
        on_select: Callable[[str], None],
    ) -> None:
        if len(tire_positions) == 4:
            height = 300
        else:
            height = 350
        
        super().__init__(parent, width=200, height=height, bg="#f0f0f0", highlightthickness=0)
        self.tire_positions = tire_positions
        self.vehicle_label = vehicle_label
        self.on_select = on_select
        self.selected_pos: str | None = None
        self._item_map: dict[str, int] = {}
        self._text_map: dict[str, int] = {}

        self._draw_vehicle()

    def _draw_vehicle(self) -> None:
        cx = 100
        w, h = 25, 40
        offset_x = 45

        if len(self.tire_positions) == 4:  # 牵引车
            self.create_rectangle(cx - 30, 50, cx + 30, 270, fill="#d0d0d0", outline="#999")
            self.create_polygon(
                cx - 40, 50, cx + 40, 50, cx + 35, 15, cx - 35, 15,
                fill="#a0c0e0", outline="#6080a0", width=2
            )
            self.create_text(cx, 32, text=self.vehicle_label, fill="#333", font=("Segoe UI", 9, "bold"))

            y_positions = [90, 150, 210]
            layout = [
                (self.tire_positions[0], cx - offset_x - w / 2, y_positions[0]),
                (self.tire_positions[1], cx + offset_x - w / 2, y_positions[0]),
                (self.tire_positions[2], cx - offset_x - w / 2, y_positions[1]),
                (self.tire_positions[3], cx + offset_x - w / 2, y_positions[1]),
            ]
            axle_ys = [y_positions[0], y_positions[1]]

        else:  # 挂车
            self.create_rectangle(cx - 30, 30, cx + 30, 320, fill="#c8c8c8", outline="#888")
            self.create_text(cx, 50, text=self.vehicle_label, fill="#333", font=("Segoe UI", 9, "bold"))

            y_positions = [100, 170, 240]
            layout = [
                (self.tire_positions[0], cx - offset_x - w / 2, y_positions[0]),
                (self.tire_positions[1], cx + offset_x - w / 2, y_positions[0]),
                (self.tire_positions[2], cx - offset_x - w / 2, y_positions[1]),
                (self.tire_positions[3], cx + offset_x - w / 2, y_positions[1]),
                (self.tire_positions[4], cx - offset_x - w / 2, y_positions[2]),
                (self.tire_positions[5], cx + offset_x - w / 2, y_positions[2]),
            ]
            axle_ys = y_positions

        for y in axle_ys:
            self.create_line(cx - 50, y + h / 2, cx + 50, y + h / 2, width=3, fill="#555")

        for pos, x, y in layout:
            tag = self.create_rectangle(
                x, y, x + w, y + h,
                fill="#444", outline="#000", width=1,
                tags=("tire", f"tire:{pos}")
            )
            self._item_map[pos] = tag

            label_x = x - 15 if x < cx else x + w + 15
            t_tag = self.create_text(
                label_x, y + h / 2,
                text=pos, font=("Segoe UI", 8, "bold"), fill="#333"
            )
            self._text_map[pos] = t_tag

            self.tag_bind(tag, "<Button-1>", lambda e, p=pos: self.on_select(p))
            self.tag_bind(tag, "<Enter>", lambda e, p=pos: self._on_hover(p, True))
            self.tag_bind(tag, "<Leave>", lambda e, p=pos: self._on_hover(p, False))

    def _on_hover(self, pos: str, enter: bool) -> None:
        if pos == self.selected_pos:
            return
        tag = self._item_map[pos]
        self.itemconfigure(tag, fill="#666" if enter else "#444")

    def select(self, pos: str | None) -> None:
        if self.selected_pos and self.selected_pos in self._item_map:
            self.itemconfigure(self._item_map[self.selected_pos], fill="#444", outline="#000", width=1)

        self.selected_pos = pos
        if pos and pos in self._item_map:
            tag = self._item_map[pos]
            self.itemconfigure(tag, fill="#3b8ed0", outline="#1d4f7c", width=2)


class EntryDialog(tk.Toplevel):
    """通用输入对话框"""
    
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        fields: list[tuple[str, str]],
        initial: dict[str, str] | None = None,
        option_fields: dict[str, tuple[str, ...]] | None = None,
        on_submit: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.resizable(False, False)
        self._on_submit = on_submit

        initial = initial or {}
        option_fields = option_fields or {}

        body = ttk.Frame(self, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        self._vars: dict[str, tk.StringVar] = {}

        for i, (key, label) in enumerate(fields):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=4)
            var = tk.StringVar(value=initial.get(key, ""))
            self._vars[key] = var

            if key in option_fields:
                combo = ttk.Combobox(body, textvariable=var, values=list(option_fields[key]), state="readonly")
                combo.grid(row=i, column=1, sticky="ew", pady=4)
                if not var.get() and option_fields[key]:
                    var.set(option_fields[key][0])
            else:
                entry = ttk.Entry(body, textvariable=var, width=36)
                entry.grid(row=i, column=1, sticky="ew", pady=4)

        body.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self, padding=(12, 0, 12, 12))
        buttons.grid(row=1, column=0, sticky="ew")
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="保存", command=self._submit).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._submit())

        self.grab_set()
        self.wait_visibility()
        self.focus_set()

    def _submit(self) -> None:
        data = {k: v.get() for k, v in self._vars.items()}
        if self._on_submit is not None:
            self._on_submit(data)
        self.destroy()


class TractorManagementFrame(ttk.Frame):
    """牵引车综合管理（车辆+轮胎+保养）"""
    
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_id: int | None = None
        self.selected_tire_position: str | None = None
        self.selected_tire_event_id: int | None = None
        self.selected_maint_id: int | None = None

        # 水平分割
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # 左：车辆列表
        left = self._create_vehicle_panel(paned)
        paned.add(left, weight=1)

        # 右：轮胎+保养
        right = self._create_details_panel(paned)
        paned.add(right, weight=2)

        self.refresh_all()

    def _create_vehicle_panel(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        
        header = ttk.Frame(frame)
        header.pack(fill="x", padx=5, pady=5)
        ttk.Label(header, text="牵引车列表", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_vehicle, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_vehicle, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_vehicle, width=6).pack(side="left", padx=2)

        self.vehicle_tree = ttk.Treeview(frame, columns=("plate", "mileage"), show="headings", height=25)
        self.vehicle_tree.heading("plate", text="车牌号")
        self.vehicle_tree.heading("mileage", text="里程数")
        self.vehicle_tree.column("plate", width=120)
        self.vehicle_tree.column("mileage", width=90)
        self.vehicle_tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.vehicle_tree.bind("<<TreeviewSelect>>", self._on_vehicle_select)

        return frame

    def _create_details_panel(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # 轮胎页
        tire_tab = self._create_tire_tab(notebook)
        notebook.add(tire_tab, text="轮胎（4轮）")

        # 保养页
        maint_tab = self._create_maintenance_tab(notebook)
        notebook.add(maint_tab, text="保养记录")

        return frame

    def _create_tire_tab(self, parent) -> ttk.Frame:
        tab = ttk.Frame(parent)
        
        header = ttk.Frame(tab)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text="轮胎更换记录", font=("Segoe UI", 11, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_tire, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_tire, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_tire, width=6).pack(side="left", padx=2)

        self.tire_info_var = tk.StringVar(value="请先选择牵引车")
        ttk.Label(tab, textvariable=self.tire_info_var, foreground="blue").pack(padx=10, pady=(0, 5))

        paned = ttk.Panedwindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 左：可视化
        vis_frame = ttk.Frame(paned)
        paned.add(vis_frame, weight=0)
        self.tire_visualizer = TireVisualizer(
            vis_frame,
            TRACTOR_TIRE_POSITIONS,
            "牵引车",
            self._on_tire_position_select
        )
        self.tire_visualizer.pack()

        # 右：历史
        hist_frame = ttk.Frame(paned)
        paned.add(hist_frame, weight=1)
        ttk.Label(hist_frame, text="更换历史", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.tire_tree = ttk.Treeview(
            hist_frame,
            columns=("date", "mileage", "brand", "model"),
            show="headings",
            height=18
        )
        for col, text, width in [("date", "日期", 90), ("mileage", "里程", 70), ("brand", "品牌", 90), ("model", "型号", 90)]:
            self.tire_tree.heading(col, text=text)
            self.tire_tree.column(col, width=width)
        self.tire_tree.pack(fill="both", expand=True)
        self.tire_tree.bind("<<TreeviewSelect>>", self._on_tire_select)

        return tab

    def _create_maintenance_tab(self, parent) -> ttk.Frame:
        tab = ttk.Frame(parent)
        
        header = ttk.Frame(tab)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text="保养维护记录", font=("Segoe UI", 11, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_maint, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_maint, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_maint, width=6).pack(side="left", padx=2)

        self.maint_info_var = tk.StringVar(value="请先选择牵引车")
        ttk.Label(tab, textvariable=self.maint_info_var, foreground="blue").pack(padx=10, pady=(0, 5))

        self.maint_tree = ttk.Treeview(
            tab,
            columns=("date", "type", "mileage", "note"),
            show="headings",
            height=20
        )
        for col, text, width in [("date", "日期", 100), ("type", "类型", 100), ("mileage", "里程", 80), ("note", "备注", 250)]:
            self.maint_tree.heading(col, text=text)
            self.maint_tree.column(col, width=width)
        self.maint_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.maint_tree.bind("<<TreeviewSelect>>", self._on_maint_select)

        return tab

    def refresh_all(self) -> None:
        # 刷新车辆列表
        for item in self.vehicle_tree.get_children():
            self.vehicle_tree.delete(item)
        for v in self.db.list_tractors():
            self.vehicle_tree.insert("", "end", iid=str(v.id), values=(v.plate, v.mileage))
        
        # 清空选择
        self.selected_id = None
        self.tire_info_var.set("请先选择牵引车")
        self.maint_info_var.set("请先选择牵引车")
        self._refresh_tire_panel()
        self._refresh_maint_panel()

    def _on_vehicle_select(self, _event) -> None:
        sel = self.vehicle_tree.selection()
        if not sel:
            self.selected_id = None
            self.tire_info_var.set("请先选择牵引车")
            self.maint_info_var.set("请先选择牵引车")
            self._refresh_tire_panel()
            self._refresh_maint_panel()
            return
        
        self.selected_id = int(sel[0])
        v = self.db.get_tractor(self.selected_id)
        if v:
            self.tire_info_var.set(f"当前车辆：{v.plate}")
            self.maint_info_var.set(f"当前车辆：{v.plate}")
        
        self.selected_tire_position = TRACTOR_TIRE_POSITIONS[0]
        self.tire_visualizer.select(self.selected_tire_position)
        self._refresh_tire_panel()
        self._refresh_maint_panel()

    def _on_tire_position_select(self, pos: str) -> None:
        self.selected_tire_position = pos
        self.tire_visualizer.select(pos)
        self._refresh_tire_panel()

    def _on_tire_select(self, _event) -> None:
        sel = self.tire_tree.selection()
        self.selected_tire_event_id = int(sel[0]) if sel else None

    def _on_maint_select(self, _event) -> None:
        sel = self.maint_tree.selection()
        self.selected_maint_id = int(sel[0]) if sel else None

    def _refresh_tire_panel(self) -> None:
        for item in self.tire_tree.get_children():
            self.tire_tree.delete(item)
        
        if not self.selected_id or not self.selected_tire_position:
            return
        
        events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, self.selected_id, self.selected_tire_position)
        for e in events:
            self.tire_tree.insert("", "end", iid=str(e.id), values=(e.change_date, e.mileage, e.brand, e.model))

    def _refresh_maint_panel(self) -> None:
        for item in self.maint_tree.get_children():
            self.maint_tree.delete(item)
        
        if not self.selected_id:
            return
        
        records = self.db.list_maintenance_records(VEHICLE_TYPE_TRACTOR, self.selected_id)
        for r in records:
            self.maint_tree.insert("", "end", iid=str(r.id), values=(r.service_date, r.record_type, r.mileage, r.note))

    # 车辆操作
    def add_vehicle(self) -> None:
        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_tractor(data["plate"].strip(), _parse_int(data["mileage"], "里程数"), data.get("note", ""))
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增牵引车", [("plate", "车牌号"), ("mileage", "里程数"), ("note", "备注")], {"mileage": "0"}, on_submit=submit)

    def edit_vehicle(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_tractor(self.selected_id)
        if not v:
            self.refresh_all()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_tractor(v.id, data["plate"].strip(), _parse_int(data["mileage"], "里程数"), data.get("note", ""))
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "编辑牵引车", [("plate", "车牌号"), ("mileage", "里程数"), ("note", "备注")],
                    {"plate": v.plate, "mileage": str(v.mileage), "note": v.note}, on_submit=submit)

    def delete_vehicle(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_tractor(self.selected_id)
        if v and messagebox.askyesno("确认", f"删除 {v.plate}？", parent=self):
            try:
                self.db.delete_tractor(v.id)
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

    # 轮胎操作
    def add_tire(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_tire_event(
                    VEHICLE_TYPE_TRACTOR, self.selected_id, data["position"],
                    _parse_date(data["date"], "日期"), _parse_int(data["mileage"], "里程数"),
                    data.get("brand", ""), data.get("model", ""), data.get("note", "")
                )
                self._refresh_tire_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增轮胎记录", 
                    [("position", "位置"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("brand", "品牌"), ("model", "型号"), ("note", "备注")],
                    {"position": self.selected_tire_position or "F1", "date": date.today().isoformat()},
                    {"position": TRACTOR_TIRE_POSITIONS}, submit)

    def edit_tire(self) -> None:
        if not self.selected_tire_event_id:
            messagebox.showinfo("提示", "请先选择轮胎记录", parent=self)
            return
        
        events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, self.selected_id, self.selected_tire_position)
        e = next((x for x in events if x.id == self.selected_tire_event_id), None)
        if not e:
            self._refresh_tire_panel()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_tire_event(
                    e.id, data["position"], _parse_date(data["date"], "日期"),
                    _parse_int(data["mileage"], "里程数"), data.get("brand", ""), data.get("model", ""), data.get("note", "")
                )
                self._refresh_tire_panel()
            except Exception as ex:
                messagebox.showerror("错误", str(ex), parent=self)

        EntryDialog(self, "编辑轮胎记录",
                    [("position", "位置"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("brand", "品牌"), ("model", "型号"), ("note", "备注")],
                    {"position": e.position, "date": e.change_date, "mileage": str(e.mileage), "brand": e.brand, "model": e.model, "note": e.note},
                    {"position": TRACTOR_TIRE_POSITIONS}, submit)

    def delete_tire(self) -> None:
        if not self.selected_tire_event_id:
            messagebox.showinfo("提示", "请先选择轮胎记录", parent=self)
            return
        if messagebox.askyesno("确认", "删除该记录？", parent=self):
            try:
                self.db.delete_tire_event(self.selected_tire_event_id)
                self.selected_tire_event_id = None
                self._refresh_tire_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

    # 保养操作
    def add_maint(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_maintenance_record(
                    VEHICLE_TYPE_TRACTOR, self.selected_id, data["type"],
                    _parse_date(data["date"], "日期"), _parse_int(data["mileage"], "里程数"), data.get("note", "")
                )
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增保养记录",
                    [("type", "类型"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
                    {"date": date.today().isoformat()}, {"type": MAINTENANCE_TYPES}, submit)

    def edit_maint(self) -> None:
        if not self.selected_maint_id:
            messagebox.showinfo("提示", "请先选择保养记录", parent=self)
            return
        
        records = {r.id: r for r in self.db.list_maintenance_records(VEHICLE_TYPE_TRACTOR, self.selected_id)}
        r = records.get(self.selected_maint_id)
        if not r:
            self._refresh_maint_panel()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_maintenance_record(
                    r.id, data["type"], _parse_date(data["date"], "日期"),
                    _parse_int(data["mileage"], "里程数"), data.get("note", "")
                )
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "编辑保养记录",
                    [("type", "类型"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
                    {"type": r.record_type, "date": r.service_date, "mileage": str(r.mileage), "note": r.note},
                    {"type": MAINTENANCE_TYPES}, submit)

    def delete_maint(self) -> None:
        if not self.selected_maint_id:
            messagebox.showinfo("提示", "请先选择保养记录", parent=self)
            return
        if messagebox.askyesno("确认", "删除该记录？", parent=self):
            try:
                self.db.delete_maintenance_record(self.selected_maint_id)
                self.selected_maint_id = None
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)


# 挂车管理（类似结构）
class TrailerManagementFrame(ttk.Frame):
    """挂车综合管理（车辆+轮胎+保养）"""
    
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_id: int | None = None
        self.selected_tire_position: str | None = None
        self.selected_tire_event_id: int | None = None
        self.selected_maint_id: int | None = None

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left = self._create_vehicle_panel(paned)
        paned.add(left, weight=1)

        right = self._create_details_panel(paned)
        paned.add(right, weight=2)

        self.refresh_all()

    def _create_vehicle_panel(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        
        header = ttk.Frame(frame)
        header.pack(fill="x", padx=5, pady=5)
        ttk.Label(header, text="挂车列表", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_vehicle, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_vehicle, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_vehicle, width=6).pack(side="left", padx=2)

        self.vehicle_tree = ttk.Treeview(frame, columns=("plate",), show="headings", height=25)
        self.vehicle_tree.heading("plate", text="车牌号")
        self.vehicle_tree.column("plate", width=150)
        self.vehicle_tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.vehicle_tree.bind("<<TreeviewSelect>>", self._on_vehicle_select)

        return frame

    def _create_details_panel(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        tire_tab = self._create_tire_tab(notebook)
        notebook.add(tire_tab, text="轮胎（6轮）")

        maint_tab = self._create_maintenance_tab(notebook)
        notebook.add(maint_tab, text="保养记录")

        return frame

    def _create_tire_tab(self, parent) -> ttk.Frame:
        tab = ttk.Frame(parent)
        
        header = ttk.Frame(tab)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text="轮胎更换记录", font=("Segoe UI", 11, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_tire, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_tire, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_tire, width=6).pack(side="left", padx=2)

        self.tire_info_var = tk.StringVar(value="请先选择挂车")
        ttk.Label(tab, textvariable=self.tire_info_var, foreground="blue").pack(padx=10, pady=(0, 5))

        paned = ttk.Panedwindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        vis_frame = ttk.Frame(paned)
        paned.add(vis_frame, weight=0)
        self.tire_visualizer = TireVisualizer(
            vis_frame,
            TRAILER_TIRE_POSITIONS,
            "挂车",
            self._on_tire_position_select
        )
        self.tire_visualizer.pack()

        hist_frame = ttk.Frame(paned)
        paned.add(hist_frame, weight=1)
        ttk.Label(hist_frame, text="更换历史", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.tire_tree = ttk.Treeview(
            hist_frame,
            columns=("date", "mileage", "brand", "model"),
            show="headings",
            height=18
        )
        for col, text, width in [("date", "日期", 90), ("mileage", "里程", 70), ("brand", "品牌", 90), ("model", "型号", 90)]:
            self.tire_tree.heading(col, text=text)
            self.tire_tree.column(col, width=width)
        self.tire_tree.pack(fill="both", expand=True)
        self.tire_tree.bind("<<TreeviewSelect>>", self._on_tire_select)

        return tab

    def _create_maintenance_tab(self, parent) -> ttk.Frame:
        tab = ttk.Frame(parent)
        
        header = ttk.Frame(tab)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text="保养维护记录", font=("Segoe UI", 11, "bold")).pack(side="left")
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="新增", command=self.add_maint, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_maint, width=6).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_maint, width=6).pack(side="left", padx=2)

        self.maint_info_var = tk.StringVar(value="请先选择挂车")
        ttk.Label(tab, textvariable=self.maint_info_var, foreground="blue").pack(padx=10, pady=(0, 5))

        self.maint_tree = ttk.Treeview(
            tab,
            columns=("date", "type", "mileage", "note"),
            show="headings",
            height=20
        )
        for col, text, width in [("date", "日期", 100), ("type", "类型", 100), ("mileage", "里程", 80), ("note", "备注", 250)]:
            self.maint_tree.heading(col, text=text)
            self.maint_tree.column(col, width=width)
        self.maint_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.maint_tree.bind("<<TreeviewSelect>>", self._on_maint_select)

        return tab

    def refresh_all(self) -> None:
        for item in self.vehicle_tree.get_children():
            self.vehicle_tree.delete(item)
        for v in self.db.list_trailers():
            self.vehicle_tree.insert("", "end", iid=str(v.id), values=(v.plate,))
        
        self.selected_id = None
        self.tire_info_var.set("请先选择挂车")
        self.maint_info_var.set("请先选择挂车")
        self._refresh_tire_panel()
        self._refresh_maint_panel()

    def _on_vehicle_select(self, _event) -> None:
        sel = self.vehicle_tree.selection()
        if not sel:
            self.selected_id = None
            self.tire_info_var.set("请先选择挂车")
            self.maint_info_var.set("请先选择挂车")
            self._refresh_tire_panel()
            self._refresh_maint_panel()
            return
        
        self.selected_id = int(sel[0])
        v = self.db.get_trailer(self.selected_id)
        if v:
            self.tire_info_var.set(f"当前车辆：{v.plate}")
            self.maint_info_var.set(f"当前车辆：{v.plate}")
        
        self.selected_tire_position = TRAILER_TIRE_POSITIONS[0]
        self.tire_visualizer.select(self.selected_tire_position)
        self._refresh_tire_panel()
        self._refresh_maint_panel()

    def _on_tire_position_select(self, pos: str) -> None:
        self.selected_tire_position = pos
        self.tire_visualizer.select(pos)
        self._refresh_tire_panel()

    def _on_tire_select(self, _event) -> None:
        sel = self.tire_tree.selection()
        self.selected_tire_event_id = int(sel[0]) if sel else None

    def _on_maint_select(self, _event) -> None:
        sel = self.maint_tree.selection()
        self.selected_maint_id = int(sel[0]) if sel else None

    def _refresh_tire_panel(self) -> None:
        for item in self.tire_tree.get_children():
            self.tire_tree.delete(item)
        
        if not self.selected_id or not self.selected_tire_position:
            return
        
        events = self.db.list_tire_events(VEHICLE_TYPE_TRAILER, self.selected_id, self.selected_tire_position)
        for e in events:
            self.tire_tree.insert("", "end", iid=str(e.id), values=(e.change_date, e.mileage, e.brand, e.model))

    def _refresh_maint_panel(self) -> None:
        for item in self.maint_tree.get_children():
            self.maint_tree.delete(item)
        
        if not self.selected_id:
            return
        
        records = self.db.list_maintenance_records(VEHICLE_TYPE_TRAILER, self.selected_id)
        for r in records:
            self.maint_tree.insert("", "end", iid=str(r.id), values=(r.service_date, r.record_type, r.mileage, r.note))

    def add_vehicle(self) -> None:
        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_trailer(data["plate"].strip(), data.get("note", ""))
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增挂车", [("plate", "车牌号"), ("note", "备注")], on_submit=submit)

    def edit_vehicle(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_trailer(self.selected_id)
        if not v:
            self.refresh_all()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_trailer(v.id, data["plate"].strip(), data.get("note", ""))
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "编辑挂车", [("plate", "车牌号"), ("note", "备注")],
                    {"plate": v.plate, "note": v.note}, on_submit=submit)

    def delete_vehicle(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_trailer(self.selected_id)
        if v and messagebox.askyesno("确认", f"删除 {v.plate}？", parent=self):
            try:
                self.db.delete_trailer(v.id)
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

    def add_tire(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_tire_event(
                    VEHICLE_TYPE_TRAILER, self.selected_id, data["position"],
                    _parse_date(data["date"], "日期"), _parse_int(data["mileage"], "里程数"),
                    data.get("brand", ""), data.get("model", ""), data.get("note", "")
                )
                self._refresh_tire_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增轮胎记录",
                    [("position", "位置"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("brand", "品牌"), ("model", "型号"), ("note", "备注")],
                    {"position": self.selected_tire_position or "R1", "date": date.today().isoformat()},
                    {"position": TRAILER_TIRE_POSITIONS}, submit)

    def edit_tire(self) -> None:
        if not self.selected_tire_event_id:
            messagebox.showinfo("提示", "请先选择轮胎记录", parent=self)
            return
        
        events = self.db.list_tire_events(VEHICLE_TYPE_TRAILER, self.selected_id, self.selected_tire_position)
        e = next((x for x in events if x.id == self.selected_tire_event_id), None)
        if not e:
            self._refresh_tire_panel()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_tire_event(
                    e.id, data["position"], _parse_date(data["date"], "日期"),
                    _parse_int(data["mileage"], "里程数"), data.get("brand", ""), data.get("model", ""), data.get("note", "")
                )
                self._refresh_tire_panel()
            except Exception as ex:
                messagebox.showerror("错误", str(ex), parent=self)

        EntryDialog(self, "编辑轮胎记录",
                    [("position", "位置"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("brand", "品牌"), ("model", "型号"), ("note", "备注")],
                    {"position": e.position, "date": e.change_date, "mileage": str(e.mileage), "brand": e.brand, "model": e.model, "note": e.note},
                    {"position": TRAILER_TIRE_POSITIONS}, submit)

    def delete_tire(self) -> None:
        if not self.selected_tire_event_id:
            messagebox.showinfo("提示", "请先选择轮胎记录", parent=self)
            return
        if messagebox.askyesno("确认", "删除该记录？", parent=self):
            try:
                self.db.delete_tire_event(self.selected_tire_event_id)
                self.selected_tire_event_id = None
                self._refresh_tire_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

    def add_maint(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.create_maintenance_record(
                    VEHICLE_TYPE_TRAILER, self.selected_id, data["type"],
                    _parse_date(data["date"], "日期"), _parse_int(data["mileage"], "里程数"), data.get("note", "")
                )
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "新增保养记录",
                    [("type", "类型"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
                    {"date": date.today().isoformat()}, {"type": MAINTENANCE_TYPES}, submit)

    def edit_maint(self) -> None:
        if not self.selected_maint_id:
            messagebox.showinfo("提示", "请先选择保养记录", parent=self)
            return
        
        records = {r.id: r for r in self.db.list_maintenance_records(VEHICLE_TYPE_TRAILER, self.selected_id)}
        r = records.get(self.selected_maint_id)
        if not r:
            self._refresh_maint_panel()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                self.db.update_maintenance_record(
                    r.id, data["type"], _parse_date(data["date"], "日期"),
                    _parse_int(data["mileage"], "里程数"), data.get("note", "")
                )
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        EntryDialog(self, "编辑保养记录",
                    [("type", "类型"), ("date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
                    {"type": r.record_type, "date": r.service_date, "mileage": str(r.mileage), "note": r.note},
                    {"type": MAINTENANCE_TYPES}, submit)

    def delete_maint(self) -> None:
        if not self.selected_maint_id:
            messagebox.showinfo("提示", "请先选择保养记录", parent=self)
            return
        if messagebox.askyesno("确认", "删除该记录？", parent=self):
            try:
                self.db.delete_maintenance_record(self.selected_maint_id)
                self.selected_maint_id = None
                self._refresh_maint_panel()
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)


class ExportFrame(ttk.Frame):
    """数据导出"""
    
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent, padding=20)
        self.db = db
        
        ttk.Label(self, text="数据导出", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(self, text="将导出所有牵引车、挂车、轮胎记录和保养记录到CSV文件").pack(anchor="w")
        ttk.Label(self, text="CSV文件可用Excel直接打开").pack(anchor="w", pady=(5, 20))
        
        ttk.Button(self, text="选择目录并导出", command=self._export).pack(anchor="w")
        
        self.result_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.result_var, foreground="green").pack(anchor="w", pady=(15, 0))

    def _export(self) -> None:
        folder = filedialog.askdirectory(title="选择导出目录")
        if not folder:
            return
        try:
            paths = export_csv(self.db, Path(folder))
            self.result_var.set("导出成功：" + ", ".join([p.name for p in paths]))
            messagebox.showinfo("成功", f"已导出 {len(paths)} 个文件", parent=self)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self)


class TruckCareApp(tk.Tk):
    """主应用"""
    
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.title("TruckCare - 牵引车/挂车管理系统")
        self.geometry("1100x700")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        notebook.add(TractorManagementFrame(notebook, db), text="牵引车")
        notebook.add(TrailerManagementFrame(notebook, db), text="挂车")
        notebook.add(ExportFrame(notebook, db), text="数据导出")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        try:
            self.db.close()
        finally:
            self.destroy()


def main() -> None:
    db = Database()
    db.init_db()
    app = TruckCareApp(db)
    app.mainloop()
