from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from .constants import MAINTENANCE_TYPES, TIRE_POSITIONS


class TireVisualizer(tk.Canvas):
    def __init__(self, parent: tk.Widget, on_select: Callable[[str], None]) -> None:
        super().__init__(parent, width=300, height=520, bg="#f0f0f0", highlightthickness=0)
        self.on_select = on_select
        self.selected_pos: str | None = None
        self._item_map: dict[str, int] = {}  # pos -> tag_id (rectangle)
        self._text_map: dict[str, int] = {}  # pos -> tag_id (text)

        self._draw_truck()

    def _draw_truck(self) -> None:
        cx = 150  # Center X
        # Chassis (Frame)
        self.create_rectangle(cx - 40, 60, cx + 40, 500, fill="#d0d0d0", outline="#999")
        # Head (Cab)
        self.create_path(
            cx - 50, 60,
            cx + 50, 60,
            cx + 45, 20,
            cx - 45, 20,
            fill="#a0c0e0", outline="#6080a0", width=2
        )
        self.create_text(cx, 40, text="车头", fill="#fff", font=("Segoe UI", 10, "bold"))

        # Axle Y positions
        y_f1 = 100
        y_f2 = 170
        # Gap between Front and Rear
        y_r1 = 280
        y_r2 = 350
        y_r3 = 420

        # Wheel dimensions
        w, h = 30, 50
        offset_x = 60  # Distance from center to wheel center

        # Layout: (pos, x, y)
        layout = [
            # Front 4 (2 Axles)
            ("F1", cx - offset_x - w / 2, y_f1), ("F2", cx + offset_x - w / 2, y_f1),
            ("F3", cx - offset_x - w / 2, y_f2), ("F4", cx + offset_x - w / 2, y_f2),
            # Rear 6 (3 Axles)
            ("R1", cx - offset_x - w / 2, y_r1), ("R2", cx + offset_x - w / 2, y_r1),
            ("R3", cx - offset_x - w / 2, y_r2), ("R4", cx + offset_x - w / 2, y_r2),
            ("R5", cx - offset_x - w / 2, y_r3), ("R6", cx + offset_x - w / 2, y_r3),
        ]

        # Draw connecting axles
        for _, y in [(1, y_f1), (1, y_f2), (1, y_r1), (1, y_r2), (1, y_r3)]:
            self.create_line(cx - 60, y + h / 2, cx + 60, y + h / 2, width=4, fill="#555")

        for pos, x, y in layout:
            # Wheel Rect
            tag = self.create_rectangle(
                x, y, x + w, y + h,
                fill="#444", outline="#000", width=1,
                tags=("tire", f"tire:{pos}")
            )
            self._item_map[pos] = tag

            # Label
            label_y = y + h / 2
            label_x = x - 20 if x < cx else x + w + 20
            t_tag = self.create_text(
                label_x, label_y,
                text=pos, font=("Segoe UI", 9, "bold"), fill="#333"
            )
            self._text_map[pos] = t_tag

            # Bind click
            self.tag_bind(tag, "<Button-1>", lambda e, p=pos: self.on_select(p))
            self.tag_bind(tag, "<Enter>", lambda e, p=pos: self._on_hover(p, True))
            self.tag_bind(tag, "<Leave>", lambda e, p=pos: self._on_hover(p, False))

    def _on_hover(self, pos: str, enter: bool) -> None:
        if pos == self.selected_pos:
            return
        tag = self._item_map[pos]
        self.itemconfigure(tag, fill="#666" if enter else "#444")

    def select(self, pos: str | None) -> None:
        # Reset old
        if self.selected_pos and self.selected_pos in self._item_map:
            self.itemconfigure(self._item_map[self.selected_pos], fill="#444", outline="#000", width=1)

        self.selected_pos = pos
        if pos and pos in self._item_map:
            tag = self._item_map[pos]
            self.itemconfigure(tag, fill="#3b8ed0", outline="#1d4f7c", width=2)

    def create_path(self, *coords, **kwargs):
        # Helper for polygon
        return self.create_polygon(*coords, **kwargs)

from .db import Database, MaintenanceRecord, TireEvent, Vehicle
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


class EntryDialog(tk.Toplevel):
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


class VehicleFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database, on_select: Callable[[int | None], None]) -> None:
        super().__init__(parent, padding=10)
        self.db = db
        self.on_select = on_select
        self.selected_vehicle_id: int | None = None

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="车辆信息", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(header, text="新增", command=self.add_vehicle).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="编辑", command=self.edit_vehicle).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="删除", command=self.delete_vehicle).pack(side="right")

        self.tree = ttk.Treeview(self, columns=("plate", "mileage", "note"), show="headings", height=14)
        self.tree.heading("plate", text="车牌号")
        self.tree.heading("mileage", text="里程数")
        self.tree.heading("note", text="备注")
        self.tree.column("plate", width=180, anchor="w")
        self.tree.column("mileage", width=120, anchor="e")
        self.tree.column("note", width=420, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=(10, 0))

        self.tree.bind("<<TreeviewSelect>>", self._handle_select)

        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=(10, 0))
        self.detail_var = tk.StringVar(value="未选择车辆")
        ttk.Label(footer, textvariable=self.detail_var).pack(side="left")

        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for v in self.db.list_vehicles():
            self.tree.insert("", "end", iid=str(v.id), values=(v.plate, v.mileage, v.note))

        self.selected_vehicle_id = None
        self.detail_var.set("未选择车辆")
        self.on_select(None)

    def _handle_select(self, _event: object) -> None:
        sel = self.tree.selection()
        if not sel:
            self.selected_vehicle_id = None
            self.detail_var.set("未选择车辆")
            self.on_select(None)
            return
        vehicle_id = int(sel[0])
        v = self.db.get_vehicle(vehicle_id)
        self.selected_vehicle_id = vehicle_id
        if v:
            self.detail_var.set(f"当前车辆：{v.plate} | 里程：{v.mileage}")
        else:
            self.detail_var.set("未选择车辆")
        self.on_select(vehicle_id)

    def add_vehicle(self) -> None:
        def submit(data: dict[str, str]) -> None:
            try:
                plate = data["plate"].strip()
                mileage = _parse_int(data["mileage"], "里程数")
                note = data.get("note", "")
                self.db.create_vehicle(plate=plate, mileage=mileage, note=note)
                self.refresh()
            except Exception as e:
                messagebox.showerror("新增失败", str(e), parent=self)

        EntryDialog(
            self,
            title="新增车辆",
            fields=[("plate", "车牌号"), ("mileage", "里程数"), ("note", "备注")],
            initial={"mileage": "0"},
            on_submit=submit,
        )

    def edit_vehicle(self) -> None:
        if self.selected_vehicle_id is None:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_vehicle(self.selected_vehicle_id)
        if not v:
            self.refresh()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                plate = data["plate"].strip()
                mileage = _parse_int(data["mileage"], "里程数")
                note = data.get("note", "")
                self.db.update_vehicle(vehicle_id=v.id, plate=plate, mileage=mileage, note=note)
                self.refresh()
            except Exception as e:
                messagebox.showerror("编辑失败", str(e), parent=self)

        EntryDialog(
            self,
            title="编辑车辆",
            fields=[("plate", "车牌号"), ("mileage", "里程数"), ("note", "备注")],
            initial={"plate": v.plate, "mileage": str(v.mileage), "note": v.note},
            on_submit=submit,
        )

    def delete_vehicle(self) -> None:
        if self.selected_vehicle_id is None:
            messagebox.showinfo("提示", "请先选择车辆", parent=self)
            return
        v = self.db.get_vehicle(self.selected_vehicle_id)
        if not v:
            self.refresh()
            return
        ok = messagebox.askyesno("确认删除", f"删除车辆 {v.plate}？相关轮胎/保养记录将一并删除。", parent=self)
        if not ok:
            return
        try:
            self.db.delete_vehicle(v.id)
            self.refresh()
        except Exception as e:
            messagebox.showerror("删除失败", str(e), parent=self)


class TireFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent, padding=10)
        self.db = db
        self.vehicle_id: int | None = None
        self.selected_position: str | None = None
        self.selected_event_id: int | None = None

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="轮胎更换记录（前4后6，共10条）", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(header, text="新增记录", command=self.add_event).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="编辑记录", command=self.edit_event).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="删除记录", command=self.delete_event).pack(side="right")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(10, 0))
        self.vehicle_label_var = tk.StringVar(value="未选择车辆（请在“车辆”页选择）")
        ttk.Label(top, textvariable=self.vehicle_label_var).pack(side="left")
        self.tire_label_var = tk.StringVar(value="未选择轮胎")
        ttk.Label(top, textvariable=self.tire_label_var).pack(side="right")

        split = ttk.Panedwindow(self, orient="horizontal")
        split.pack(fill="both", expand=True, pady=(10, 0))

        left = ttk.Frame(split, padding=(0, 0, 10, 0))
        right = ttk.Frame(split)
        split.add(left, weight=0)  # Canvas fixed width
        split.add(right, weight=1)

        ttk.Label(left, text="轮胎俯视图（点击选择）").pack(anchor="w")
        self.visualizer = TireVisualizer(left, on_select=self._handle_position_select)
        self.visualizer.pack(fill="both", expand=True, pady=(6, 0))

        ttk.Label(right, text="该轮胎的更换历史记录").pack(anchor="w")
        self.history_tree = ttk.Treeview(
            right, columns=("change_date", "mileage", "brand", "model", "note"), show="headings", height=16
        )
        for col, text, width, anchor in [
            ("change_date", "更换日期", 100, "center"),
            ("mileage", "里程", 90, "e"),
            ("brand", "品牌", 120, "w"),
            ("model", "型号", 120, "w"),
            ("note", "备注", 380, "w"),
        ]:
            self.history_tree.heading(col, text=text)
            self.history_tree.column(col, width=width, anchor=anchor)
        self.history_tree.pack(fill="both", expand=True, pady=(6, 0))
        self.history_tree.bind("<<TreeviewSelect>>", self._handle_history_select)

        self.refresh()

    def set_vehicle(self, vehicle_id: int | None, vehicle_plate: str | None) -> None:
        self.vehicle_id = vehicle_id
        self.selected_position = TIRE_POSITIONS[0] if vehicle_id is not None else None
        self.selected_event_id = None
        if vehicle_id is None:
            self.vehicle_label_var.set("未选择车辆（请在“车辆”页选择）")
        else:
            self.vehicle_label_var.set(f"当前车辆：{vehicle_plate or vehicle_id}")
        self.refresh()

    def _handle_position_select(self, position: str) -> None:
        if position in TIRE_POSITIONS:
            self.selected_position = position
            self.selected_event_id = None
            self.visualizer.select(position)
            self.refresh_history()

    def _handle_history_select(self, _event: object) -> None:
        sel = self.history_tree.selection()
        self.selected_event_id = int(sel[0]) if sel else None

    def refresh(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        if self.vehicle_id is None:
            self.tire_label_var.set("未选择轮胎")
            self.visualizer.select(None)
            return

        if self.selected_position is None:
            self.selected_position = TIRE_POSITIONS[0]
        
        self.visualizer.select(self.selected_position)
        self.refresh_history()

    def refresh_history(self) -> None:

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        if self.vehicle_id is None or self.selected_position is None:
            self.tire_label_var.set("未选择轮胎")
            return
        events = self.db.list_tire_events(self.vehicle_id, position=self.selected_position)
        self.tire_label_var.set(f"当前轮胎：{self.selected_position}（{len(events)}条记录）")
        for e in events:
            self.history_tree.insert(
                "",
                "end",
                iid=str(e.id),
                values=(e.change_date, e.mileage, e.brand, e.model, e.note),
            )

    def _ensure_vehicle(self) -> bool:
        if self.vehicle_id is None:
            messagebox.showinfo("提示", "请先在“车辆”页选择车辆", parent=self)
            return False
        return True

    def add_event(self) -> None:
        if not self._ensure_vehicle():
            return
        if self.selected_position is None:
            messagebox.showinfo("提示", "请先选择轮胎位置", parent=self)
            return

        def submit(data: dict[str, str]) -> None:
            try:
                position = data["position"]
                change_date = _parse_date(data["change_date"], "更换日期")
                mileage = _parse_int(data["mileage"], "里程数")
                brand = data.get("brand", "")
                model = data.get("model", "")
                note = data.get("note", "")
                self.db.create_tire_event(
                    vehicle_id=self.vehicle_id or 0,
                    position=position,
                    change_date=change_date,
                    mileage=mileage,
                    brand=brand,
                    model=model,
                    note=note,
                )
                self.refresh()
            except Exception as e:
                messagebox.showerror("新增失败", str(e), parent=self)

        EntryDialog(
            self,
            title="新增轮胎更换记录",
            fields=[
                ("position", "位置"),
                ("change_date", "更换日期(YYYY-MM-DD)"),
                ("mileage", "里程数"),
                ("brand", "品牌"),
                ("model", "型号"),
                ("note", "备注"),
            ],
            initial={"position": self.selected_position, "change_date": date.today().isoformat()},
            option_fields={"position": (self.selected_position,)},
            on_submit=submit,
        )

    def edit_event(self) -> None:
        if not self._ensure_vehicle():
            return
        if self.selected_position is None:
            messagebox.showinfo("提示", "请先选择轮胎位置", parent=self)
            return
        if self.selected_event_id is None:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self)
            return

        events = self.db.list_tire_events(self.vehicle_id or 0, position=self.selected_position)
        e = next((x for x in events if x.id == self.selected_event_id), None)
        if e is None:
            self.refresh_history()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                position = data["position"]
                change_date = _parse_date(data["change_date"], "更换日期")
                mileage = _parse_int(data["mileage"], "里程数")
                brand = data.get("brand", "")
                model = data.get("model", "")
                note = data.get("note", "")
                self.db.update_tire_event(
                    event_id=e.id,
                    position=position,
                    change_date=change_date,
                    mileage=mileage,
                    brand=brand,
                    model=model,
                    note=note,
                )
                self.refresh()
            except Exception as ex:
                messagebox.showerror("编辑失败", str(ex), parent=self)

        EntryDialog(
            self,
            title="编辑轮胎更换记录",
            fields=[
                ("position", "位置"),
                ("change_date", "更换日期(YYYY-MM-DD)"),
                ("mileage", "里程数"),
                ("brand", "品牌"),
                ("model", "型号"),
                ("note", "备注"),
            ],
            initial={
                "position": e.position,
                "change_date": e.change_date,
                "mileage": str(e.mileage),
                "brand": e.brand,
                "model": e.model,
                "note": e.note,
            },
            option_fields={"position": (e.position,)},
            on_submit=submit,
        )

    def delete_event(self) -> None:
        if not self._ensure_vehicle():
            return
        if self.selected_position is None:
            messagebox.showinfo("提示", "请先选择轮胎位置", parent=self)
            return
        if self.selected_event_id is None:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self)
            return
        ok = messagebox.askyesno("确认删除", "删除该轮胎更换记录？", parent=self)
        if not ok:
            return
        try:
            self.db.delete_tire_event(self.selected_event_id)
            self.selected_event_id = None
            self.refresh()
        except Exception as e:
            messagebox.showerror("删除失败", str(e), parent=self)


class MaintenanceFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent, padding=10)
        self.db = db
        self.vehicle_id: int | None = None
        self.selected_record_id: int | None = None

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="机油更换 / 保养记录", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(header, text="新增记录", command=self.add_record).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="编辑记录", command=self.edit_record).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="删除记录", command=self.delete_record).pack(side="right")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(10, 0))
        self.vehicle_label_var = tk.StringVar(value="未选择车辆（请在“车辆”页选择）")
        ttk.Label(top, textvariable=self.vehicle_label_var).pack(side="left")

        self.tree = ttk.Treeview(self, columns=("service_date", "record_type", "mileage", "note"), show="headings", height=16)
        for col, text, width, anchor in [
            ("service_date", "日期", 100, "center"),
            ("record_type", "类型", 120, "w"),
            ("mileage", "里程", 80, "e"),
            ("note", "备注", 420, "w"),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", self._handle_select)

        self.refresh()

    def set_vehicle(self, vehicle_id: int | None, vehicle_plate: str | None) -> None:
        self.vehicle_id = vehicle_id
        self.selected_record_id = None
        if vehicle_id is None:
            self.vehicle_label_var.set("未选择车辆（请在“车辆”页选择）")
        else:
            self.vehicle_label_var.set(f"当前车辆：{vehicle_plate or vehicle_id}")
        self.refresh()

    def _ensure_vehicle(self) -> bool:
        if self.vehicle_id is None:
            messagebox.showinfo("提示", "请先在“车辆”页选择车辆", parent=self)
            return False
        return True

    def _handle_select(self, _event: object) -> None:
        sel = self.tree.selection()
        self.selected_record_id = int(sel[0]) if sel else None

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.vehicle_id is None:
            return
        for r in self.db.list_maintenance_records(self.vehicle_id):
            self.tree.insert("", "end", iid=str(r.id), values=(r.service_date, r.record_type, r.mileage, r.note))

    def add_record(self) -> None:
        if not self._ensure_vehicle():
            return

        def submit(data: dict[str, str]) -> None:
            try:
                record_type = data["record_type"]
                service_date = _parse_date(data["service_date"], "日期")
                mileage = _parse_int(data["mileage"], "里程数")
                note = data.get("note", "")
                self.db.create_maintenance_record(
                    vehicle_id=self.vehicle_id or 0,
                    record_type=record_type,
                    service_date=service_date,
                    mileage=mileage,
                    note=note,
                )
                self.refresh()
            except Exception as e:
                messagebox.showerror("新增失败", str(e), parent=self)

        EntryDialog(
            self,
            title="新增维护记录",
            fields=[("record_type", "类型"), ("service_date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
            initial={"service_date": date.today().isoformat()},
            option_fields={"record_type": MAINTENANCE_TYPES},
            on_submit=submit,
        )

    def edit_record(self) -> None:
        if not self._ensure_vehicle():
            return
        if self.selected_record_id is None:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self)
            return

        records = {r.id: r for r in self.db.list_maintenance_records(self.vehicle_id or 0)}
        r = records.get(self.selected_record_id)
        if r is None:
            self.refresh()
            return

        def submit(data: dict[str, str]) -> None:
            try:
                record_type = data["record_type"]
                service_date = _parse_date(data["service_date"], "日期")
                mileage = _parse_int(data["mileage"], "里程数")
                note = data.get("note", "")
                self.db.update_maintenance_record(
                    record_id=r.id,
                    record_type=record_type,
                    service_date=service_date,
                    mileage=mileage,
                    note=note,
                )
                self.refresh()
            except Exception as e:
                messagebox.showerror("编辑失败", str(e), parent=self)

        EntryDialog(
            self,
            title="编辑维护记录",
            fields=[("record_type", "类型"), ("service_date", "日期(YYYY-MM-DD)"), ("mileage", "里程数"), ("note", "备注")],
            initial={"record_type": r.record_type, "service_date": r.service_date, "mileage": str(r.mileage), "note": r.note},
            option_fields={"record_type": MAINTENANCE_TYPES},
            on_submit=submit,
        )

    def delete_record(self) -> None:
        if not self._ensure_vehicle():
            return
        if self.selected_record_id is None:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self)
            return
        ok = messagebox.askyesno("确认删除", "删除该维护记录？", parent=self)
        if not ok:
            return
        try:
            self.db.delete_maintenance_record(self.selected_record_id)
            self.selected_record_id = None
            self.refresh()
        except Exception as e:
            messagebox.showerror("删除失败", str(e), parent=self)


class ExportFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database) -> None:
        super().__init__(parent, padding=10)
        self.db = db
        ttk.Label(self, text="数据导出", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(self, text="导出为CSV（可用Excel直接打开）").pack(anchor="w", pady=(6, 0))
        ttk.Button(self, text="选择目录并导出", command=self._export).pack(anchor="w", pady=(12, 0))
        self.result_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.result_var).pack(anchor="w", pady=(12, 0))

    def _export(self) -> None:
        folder = filedialog.askdirectory(title="选择导出目录")
        if not folder:
            return
        try:
            paths = export_csv(self.db, Path(folder))
            self.result_var.set("已导出： " + " | ".join([p.name for p in paths]))
            messagebox.showinfo("导出成功", "已导出CSV文件。", parent=self)
        except Exception as e:
            messagebox.showerror("导出失败", str(e), parent=self)


class TruckCareApp(tk.Tk):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.title("Truck Care - 离线卡车健康管理")
        self.geometry("1050x640")

        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.tire_frame = TireFrame(self.notebook, db)
        self.maintenance_frame = MaintenanceFrame(self.notebook, db)
        self.export_frame = ExportFrame(self.notebook, db)

        self.vehicle_frame = VehicleFrame(self.notebook, db, on_select=self._on_vehicle_selected)

        self.notebook.add(self.vehicle_frame, text="车辆")
        self.notebook.add(self.tire_frame, text="轮胎")
        self.notebook.add(self.maintenance_frame, text="保养")
        self.notebook.add(self.export_frame, text="导出")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_vehicle_selected(self, vehicle_id: int | None) -> None:
        plate = None
        if vehicle_id is not None:
            v = self.db.get_vehicle(vehicle_id)
            plate = v.plate if v else None
        self.tire_frame.set_vehicle(vehicle_id, plate)
        self.maintenance_frame.set_vehicle(vehicle_id, plate)

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
