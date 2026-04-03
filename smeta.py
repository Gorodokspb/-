import argparse
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import datetime
import sqlite3
import warnings
import json
import re
import sys
import subprocess

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DB_PATH = os.path.join(BASE_DIR, "dekorart_base.db")
PRICE_DB_PATH = os.path.join(BASE_DIR, "dekorart_prices.db")

class SmetaApp(ctk.CTk):
    def __init__(self, project_context=None):
        super().__init__()
        self.state_db_path = STATE_DB_PATH
        self.project_context = project_context or {}
        self.current_project_id = self.project_context.get("project_id")
        self.current_user = None
        self.current_draft_id = None
        self.current_draft_file = None
        self.autosave_job = None
        self.suspend_autosave = True
        self.title("Генератор смет (PDF) - Декорартстрой")
        self.geometry("1240x860")
        self.minsize(1160, 780)
        self.configure(fg_color="#cfd4da")
        self.health_text = ctk.StringVar(value="\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f: \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430...")
        self.repaired_document_paths_count = 0
        self.startup_health_checked = False
        self._text_context_menu = None
        self.setup_text_editing_support()
        self.setup_state_db()
        self.get_drafts_dir()
        self.current_user = self.prompt_user_login()
        self.setup_price_db()

        self.top_frame = ctk.CTkFrame(self, fg_color="#d9dde2", corner_radius=24)
        self.top_frame.pack(pady=(14, 8), padx=14, fill="x")

        self.header_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=18, pady=(16, 6))
        self.header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(self.header_left, text="Смета по объекту", font=("Segoe UI Semibold", 24), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(self.header_left, text="Формирование сметы, черновиков и PDF в одном рабочем окне.", font=("Segoe UI", 12), text_color="#5f7288").pack(anchor="w", pady=(4, 0))
        self.header_badge = ctk.CTkFrame(self.header_frame, fg_color="#c8d1dc", corner_radius=16)
        self.header_badge.pack(side="right", padx=(12, 0), pady=4)
        ctk.CTkLabel(self.header_badge, text="Приложение № 1", font=("Segoe UI Semibold", 12), text_color="#2f5fa7").pack(padx=14, pady=10)

        self.row1_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.row1_frame.pack(fill="x", pady=5, padx=18)
        ctk.CTkLabel(self.row1_frame, text="Компания", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(0, 8))
        self.company_var = ctk.StringVar(value="ООО Декорартстрой")
        ctk.CTkOptionMenu(self.row1_frame, variable=self.company_var, values=["ООО Декорартстрой", "ИП Гордеев А.Н."], width=200, fg_color="#2f80ed", button_color="#2567bd", button_hover_color="#1d4f96").pack(side="left", padx=5)

        ctk.CTkLabel(self.row1_frame, text="Документ", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(20, 8))
        self.doc_type_var = ctk.StringVar(value="СМЕТА")
        self.doc_type_label = ctk.CTkLabel(self.row1_frame, text="СМЕТА", font=("Segoe UI Semibold", 13), text_color="#1d2b3a")
        self.doc_type_label.pack(side="left", padx=5)

        self.row2_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.row2_frame.pack(fill="x", pady=5, padx=18)
        ctk.CTkLabel(self.row2_frame, text="Договор", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(0, 8))
        self.contract_entry = ctk.CTkEntry(self.row2_frame, width=240, height=36, corner_radius=12, placeholder_text="№00/00/26 от 00 мая 2026 г.")
        self.contract_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.row2_frame, text="Заказчик", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(14, 8))
        self.customer_entry = ctk.CTkEntry(self.row2_frame, width=360, height=36, corner_radius=12, placeholder_text="Иванов И.И.")
        self.customer_entry.pack(side="left", padx=5)

        self.row3_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.row3_frame.pack(fill="x", pady=(5, 16), padx=18)
        ctk.CTkLabel(self.row3_frame, text="Объект", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(0, 8))
        self.object_entry = ctk.CTkEntry(self.row3_frame, width=620, height=38, corner_radius=12, placeholder_text="Например: ул. Белоостровская...")
        self.object_entry.pack(side="left", padx=5)

        self.room_frame = ctk.CTkFrame(self, fg_color="#d9dde2", corner_radius=22)
        self.room_frame.pack(pady=(0, 8), padx=14, fill="x")
        self.room_label = ctk.CTkLabel(self.room_frame, text="Действия по смете", font=("Segoe UI Semibold", 14), text_color="#1d2b3a")
        self.room_label.pack(side="left", padx=(16, 10), pady=14)
        self.add_room_btn = ctk.CTkButton(self.room_frame, text="+ Раздел", command=self.add_room, fg_color="#34495e", hover_color="#253647", corner_radius=12)
        self.add_room_btn.pack(side="left", padx=6, pady=10)
        self.open_saved_btn = ctk.CTkButton(self.room_frame, text="📂 Открыть смету", command=self.open_saved_draft, fg_color="#2f80ed", hover_color="#2567bd", corner_radius=12)
        self.open_saved_btn.pack(side="left", padx=6, pady=10)
        self.spell_btn = ctk.CTkButton(self.room_frame, text="Проверить текст", command=self.run_text_check, fg_color="#6c7a89", hover_color="#556270", corner_radius=12)
        self.spell_btn.pack(side="left", padx=6, pady=10)
        self.edit_btn = ctk.CTkButton(self.room_frame, text="✎ Изменить", command=self.edit_row, fg_color="#d9a11d", hover_color="#bb8910", width=110, corner_radius=12, text_color="#233042")
        self.edit_btn.pack(side="left", padx=6, pady=10)
        self.del_btn = ctk.CTkButton(self.room_frame, text="❌ Удалить", command=self.delete_row, fg_color="#d9534f", hover_color="#b63f3b", width=110, corner_radius=12)
        self.del_btn.pack(side="left", padx=6, pady=10)
        self.price_btn = ctk.CTkButton(self.room_frame, text="📘 Прайс-лист", command=self.open_price_manager, fg_color="#183153", hover_color="#12243d", corner_radius=12)
        self.price_btn.pack(side="right", padx=14, pady=10)

        self.quick_add_frame = ctk.CTkFrame(self, fg_color="#d9dde2", corner_radius=22)
        self.quick_add_frame.pack(pady=(0, 8), padx=14, fill="x")
        ctk.CTkLabel(self.quick_add_frame, text="Быстрое добавление работ", font=("Segoe UI Semibold", 14), text_color="#1d2b3a").pack(side="left", padx=(16, 12), pady=14)
        ctk.CTkLabel(self.quick_add_frame, text="Поиск", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(0, 5), pady=8)
        self.inline_search_entry = ctk.CTkEntry(self.quick_add_frame, width=420, height=36, corner_radius=12, placeholder_text="Начните вводить название работы...")
        self.inline_search_entry.pack(side="left", padx=5, pady=8)
        self.inline_search_entry.bind("<KeyRelease>", self.filter_inline_prices)
        self.inline_search_entry.bind("<Return>", self.inline_add_to_main)
        ctk.CTkLabel(self.quick_add_frame, text="Кол-во", font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left", padx=(15, 5), pady=8)
        self.inline_qty_entry = ctk.CTkEntry(self.quick_add_frame, width=80, height=36, corner_radius=12)
        self.inline_qty_entry.pack(side="left", padx=5, pady=8)
        self.inline_qty_entry.insert(0, "1")
        self.inline_qty_entry.bind("<Return>", self.inline_add_to_main)
        ctk.CTkButton(self.quick_add_frame, text="🧮 Калькулятор", command=self.open_inline_calculator, fg_color="#4169E1", hover_color="#3154b9", corner_radius=12).pack(side="right", padx=14, pady=10)

        self.inline_results_frame = ctk.CTkFrame(self, height=150, fg_color="#d9dde2", corner_radius=22)
        self.inline_results_frame.pack(pady=(0, 8), padx=14, fill="x")
        self.inline_results_frame.pack_propagate(False)
        self.inline_db_tree = ttk.Treeview(self.inline_results_frame, columns=("id", "name", "unit", "price"), show="headings", height=4)
        self.inline_db_tree.heading("id", text="ID"); self.inline_db_tree.heading("name", text="Наименование")
        self.inline_db_tree.heading("unit", text="Ед."); self.inline_db_tree.heading("price", text="Цена")
        self.inline_db_tree.column("id", width=0, stretch=False); self.inline_db_tree.column("name", width=720)
        self.inline_db_tree.column("unit", width=70, anchor="center"); self.inline_db_tree.column("price", width=100, anchor="center")
        self.inline_db_tree.pack(fill="both", expand=True, padx=12, pady=10)
        self.inline_db_tree.bind("<Double-1>", self.inline_add_to_main)
        self.inline_db_tree.bind("<Return>", self.inline_add_to_main)
        self.filter_inline_prices()

        self.main_frame = ctk.CTkFrame(self, fg_color="#d9dde2", corner_radius=22)
        self.main_frame.pack(pady=(5, 150), padx=14, fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 9), background="#f0f2f5", fieldbackground="#f0f2f5")
        style.configure("Treeview.Heading", font=('Segoe UI Semibold', 9), background="#c8d1dc", foreground="#233042")

        columns = ("name", "unit", "qty", "price", "total", "total_disc")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="Наименование работ"); self.tree.heading("unit", text="Ед.")
        self.tree.heading("qty", text="Кол-во"); self.tree.heading("price", text="Цена")
        self.tree.heading("total", text="Итого"); self.tree.heading("total_disc", text="Со скидкой")
        self.tree.column("name", width=350, anchor="w"); self.tree.column("unit", width=60, anchor="center")
        self.tree.column("qty", width=60, anchor="center"); self.tree.column("price", width=90, anchor="center")
        self.tree.column("total", width=90, anchor="center"); self.tree.column("total_disc", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=12)
        self.tree.tag_configure("room", background="#d2d7dd")
        
        self.tree.bind("<Double-1>", lambda event: self.edit_row())
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.context_menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        self.context_menu.add_command(label="✎ Изменить выделенное", command=self.edit_row)
        self.context_menu.add_command(label="❌ Удалить выделенное", command=self.delete_row)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⬇ Растянуть объем на выделенные", command=self.fill_down)

        self.bottom_frame = ctk.CTkFrame(self, height=124, fg_color="#d9dde2", corner_radius=22)
        self.bottom_frame.pack_propagate(False)
        self.bottom_frame.place(relx=0.5, rely=1.0, anchor="s", relwidth=0.978, y=-14)

        self.bottom_top = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.bottom_top.pack(fill="x", pady=(10, 0))
        self.bottom_meta = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.bottom_meta.pack(fill="x", pady=(6, 10))

        self.bottom_left = ctk.CTkFrame(self.bottom_top, fg_color="transparent")
        self.bottom_left.pack(side="left", fill="x", expand=True)
        self.bottom_right = ctk.CTkFrame(self.bottom_top, fg_color="transparent")
        self.bottom_right.pack(side="right", padx=10)

        self.disc_label = ctk.CTkLabel(self.bottom_left, text="Скидка (%)", font=("Segoe UI Semibold", 12), text_color="#516274")
        self.disc_label.pack(side="left", padx=(10, 5), pady=10)
        self.disc_var = ctk.StringVar(value="0")
        self.disc_var.trace_add("write", self.on_discount_change)
        self.disc_entry = ctk.CTkEntry(self.bottom_left, textvariable=self.disc_var, width=60, height=34, corner_radius=12)
        self.disc_entry.pack(side="left", padx=5, pady=10)

        self.totals_text = ctk.StringVar(value="ИТОГО: 0 руб.   |   Со скидкой: 0 руб.")
        self.total_label = ctk.CTkLabel(self.bottom_left, textvariable=self.totals_text, font=("Segoe UI Semibold", 18), text_color="#1d2b3a")
        self.total_label.pack(side="left", padx=20, pady=10)

        self.user_text = ctk.StringVar(value=f"Пользователь: {self.current_user}")
        self.user_label = ctk.CTkLabel(self.bottom_meta, textvariable=self.user_text, font=("Segoe UI", 12), text_color="#5f7288")
        self.user_label.pack(side="left", padx=10, pady=(0, 8))

        self.audit_text = ctk.StringVar(value="Черновик: еще не сохранен")
        self.audit_label = ctk.CTkLabel(self.bottom_meta, textvariable=self.audit_text, font=("Segoe UI", 12), text_color="#5f7288")
        self.audit_label.pack(side="left", padx=20, pady=(0, 8))

        self.health_label = ctk.CTkLabel(self.bottom_meta, textvariable=self.health_text, font=("Segoe UI", 12), text_color="#5f7288")
        self.health_label.pack(side="right", padx=10, pady=(0, 8))

        self.watermark_var = ctk.BooleanVar(value=True)
        self.watermark_cb = ctk.CTkCheckBox(self.bottom_right, text="Черновик (водяной знак)", variable=self.watermark_var)
        self.watermark_cb.pack(side="right", padx=10, pady=10)
        self.export_btn = ctk.CTkButton(self.bottom_right, text="Сохранить PDF", fg_color="#35a66f", hover_color="#2a885a", command=self.export_to_pdf, corner_radius=12)
        self.export_btn.pack(side="right", padx=10, pady=10)
        self.project_btn = ctk.CTkButton(self.bottom_right, text="Оформить в проект", fg_color="#6c63ff", hover_color="#544ed1", command=self.ensure_project_from_estimate, corner_radius=12)
        self.project_btn.pack(side="right", padx=10, pady=10)
        self.save_btn = ctk.CTkButton(self.bottom_right, text="Сохранить смету", fg_color="#2f80ed", hover_color="#2567bd", command=self.save_draft_manually, corner_radius=12)
        self.save_btn.pack(side="right", padx=10, pady=10)

        self.company_var.trace_add("write", self.on_form_change)
        self.doc_type_var.trace_add("write", self.on_form_change)
        self.watermark_var.trace_add("write", self.on_form_change)
        self.bind_autosave_widgets(
            self.contract_entry,
            self.customer_entry,
            self.object_entry,
            self.disc_entry,
        )
        if self.project_context:
            self.apply_project_context()
            self.restore_project_draft_if_available()
        else:
            self.restore_last_draft_for_user()
        self.suspend_autosave = False
        self.schedule_autosave()
        self.after(700, self.run_startup_health_check)

    def get_category_weight(self, name):
        n = name.lower()
        if 'потол' in n: return 1
        if 'откос' in n: return 2
        if any(x in n for x in ['стен', 'обои', 'перегород', 'шпатлев', 'шпаклев', 'штукатур']): return 3
        if any(x in n for x in ['пол', 'ламинат', 'паркет', 'плитк', 'керамогранит', 'плинтус', 'стяжк']): return 4
        if any(x in n for x in ['сантех', 'труб', 'душ', 'ванн', 'унитаз', 'кран', 'смесител', 'инсталляци', 'раковин', 'фанов', 'коллектор', 'вент', 'гофр', 'вытяжк']): return 5
        if any(x in n for x in ['электр', 'кабел', 'автомат', 'розетк', 'выключател', 'штроб', 'щит', 'свет', 'слаботоч', 'сверлен']): return 6
        return 7

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            if iid not in self.tree.selection(): self.tree.selection_set(iid)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def fill_down(self):
        selected = self.tree.selection()
        if len(selected) < 2: return messagebox.showinfo("Подсказка", "Выделите несколько строк для копирования.")
        first_item = selected[0]
        if "room" in self.tree.item(first_item, "tags"): return messagebox.showwarning("Внимание", "Нельзя растягивать раздел!")
        v = list(self.tree.item(first_item, "values")); unit, qty = v[1], float(v[2])
        for item in selected[1:]:
            if "room" in self.tree.item(item, "tags"): continue
            tv = list(self.tree.item(item, "values"))
            tv[1], tv[2] = unit, qty
            total = float(tv[3]) * qty
            tv[4], tv[5] = total, total
            self.tree.item(item, values=tv)
        self.recalculate_total()

    def setup_price_db(self):
        conn = sqlite3.connect(PRICE_DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS prices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, price REAL)''')
        c.execute('''DELETE FROM prices WHERE id NOT IN (SELECT MIN(id) FROM prices GROUP BY name)''')
        c.execute("SELECT COUNT(*) FROM prices")
        if c.fetchone()[0] == 0:
            c.executemany("INSERT INTO prices (name, unit, price) VALUES (?, ?, ?)", 
                          [("Демонтаж обоев", "м.кв.", 150), ("Штукатурка стен по маякам", "м.кв.", 850), ("Монтаж плинтуса", "м.пог.", 250)])
        conn.commit(); conn.close()

    def setup_state_db(self):
        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT NOT NULL UNIQUE,
                   created_at TEXT NOT NULL
               )'''
        )
        c.execute(
            '''CREATE TABLE IF NOT EXISTS smeta_drafts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT NOT NULL,
                   created_by TEXT,
                   created_at TEXT,
                   updated_by TEXT,
                   data TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               )'''
        )
        existing_columns = {row[1] for row in c.execute("PRAGMA table_info(smeta_drafts)").fetchall()}
        if "created_by" not in existing_columns:
            c.execute("ALTER TABLE smeta_drafts ADD COLUMN created_by TEXT")
        if "created_at" not in existing_columns:
            c.execute("ALTER TABLE smeta_drafts ADD COLUMN created_at TEXT")
        if "updated_by" not in existing_columns:
            c.execute("ALTER TABLE smeta_drafts ADD COLUMN updated_by TEXT")
        conn.commit()
        self.repaired_document_paths_count = self.repair_document_paths(conn)
        conn.close()

    def prompt_user_login(self):
        default_name = os.environ.get('USERNAME', 'Пользователь')
        dialog = ctk.CTkInputDialog(
            text="Введите имя пользователя. Оно будет использоваться для внутреннего учета черновиков.",
            title="Учетная запись"
        )
        username = (dialog.get_input() or default_name).strip()
        if not username:
            username = default_name

        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (username, created_at) VALUES (?, ?)",
            (username, datetime.datetime.now().isoformat(timespec='seconds'))
        )
        conn.commit()
        conn.close()
        return username

    def bind_autosave_widgets(self, *widgets):
        for widget in widgets:
            widget.bind("<KeyRelease>", self.on_form_change)
            widget.bind("<FocusOut>", self.on_form_change)

    def on_form_change(self, *args):
        self.schedule_autosave()

    def schedule_autosave(self):
        if self.suspend_autosave:
            return
        if self.autosave_job is not None:
            self.after_cancel(self.autosave_job)
        self.autosave_job = self.after(700, self.save_draft)

    def collect_tree_items(self):
        items = []
        for child in self.tree.get_children():
            items.append({
                "values": list(self.tree.item(child, "values")),
                "tags": list(self.tree.item(child, "tags")),
            })
        return items

    def collect_draft_payload(self):
        return {
            "project_id": self.current_project_id,
            "company": self.company_var.get(),
            "contract": self.contract_entry.get().strip(),
            "customer": self.customer_entry.get().strip(),
            "object": self.object_entry.get().strip(),
            "discount": self.disc_var.get().strip(),
            "watermark": bool(self.watermark_var.get()),
            "items": self.collect_tree_items(),
            "draft_user": self.current_user,
            "saved_at": datetime.datetime.now().isoformat(timespec='seconds'),
        }

    def save_draft(self):
        if self.suspend_autosave:
            return
        self.autosave_job = None
        payload = json.dumps(self.collect_draft_payload(), ensure_ascii=False)
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()
        if self.current_draft_id is None:
            c.execute(
                "INSERT INTO smeta_drafts (username, created_by, created_at, updated_by, data, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.current_user, self.current_user, timestamp, self.current_user, payload, timestamp)
            )
            self.current_draft_id = c.lastrowid
        else:
            c.execute(
                "UPDATE smeta_drafts SET username=?, created_by=COALESCE(created_by, username), created_at=COALESCE(created_at, updated_at), updated_by=?, data=?, updated_at=? WHERE id=?",
                (self.current_user, self.current_user, payload, timestamp, self.current_draft_id)
            )
        conn.commit()
        c.execute(
            "SELECT created_by, created_at, updated_by, updated_at FROM smeta_drafts WHERE id=?",
            (self.current_draft_id,)
        )
        audit_row = c.fetchone()
        conn.close()
        self.save_draft_to_file(payload)
        self.update_audit_text(audit_row)

    def update_project_smeta_document(self, draft_path=None, pdf_path=None):
        if not self.current_project_id:
            return
        object_name = self.object_entry.get().strip()
        title = f"Смета - {object_name}" if object_name else "Смета"
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()

        doc_columns = {row[1] for row in c.execute("PRAGMA table_info(documents)").fetchall()}
        if "draft_path" not in doc_columns:
            c.execute("ALTER TABLE documents ADD COLUMN draft_path TEXT")
        if "pdf_path" not in doc_columns:
            c.execute("ALTER TABLE documents ADD COLUMN pdf_path TEXT")

        row = c.execute(
            """SELECT id, draft_path, pdf_path
               FROM documents
               WHERE project_id=? AND doc_type=?
               ORDER BY updated_at DESC, id DESC
               LIMIT 1""",
            (self.current_project_id, "Смета (приложение № 1)")
        ).fetchone()

        next_draft_path = draft_path
        next_pdf_path = pdf_path
        if row:
            if next_draft_path is None:
                next_draft_path = self.resolve_workspace_path(row[1] or "")
            if next_pdf_path is None:
                next_pdf_path = self.resolve_workspace_path(row[2] or "")
        next_draft_path = self.resolve_workspace_path(next_draft_path or "")
        next_pdf_path = self.resolve_workspace_path(next_pdf_path or "")
        draft_path_db = self.to_workspace_storage_path(next_draft_path)
        pdf_path_db = self.to_workspace_storage_path(next_pdf_path)
        preferred_file_path = pdf_path_db or draft_path_db or ""
        if row:
            c.execute(
                """UPDATE documents
                   SET title=?, status=?, file_path=?, draft_path=?, pdf_path=?, updated_at=?
                   WHERE id=?""",
                (title, "Черновик", preferred_file_path, draft_path_db, pdf_path_db, timestamp, row[0]),
            )
        else:
            c.execute(
                """INSERT INTO documents (project_id, doc_type, title, status, file_path, draft_path, pdf_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.current_project_id, "Смета (приложение № 1)", title, "Черновик", preferred_file_path, draft_path_db, pdf_path_db, timestamp, timestamp),
            )
        conn.commit()
        conn.close()

    def restore_last_draft_for_user(self):
        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()
        c.execute(
            "SELECT id, created_by, created_at, updated_by, updated_at, data FROM smeta_drafts WHERE username=? ORDER BY updated_at DESC, id DESC LIMIT 1",
            (self.current_user,)
        )
        row = c.fetchone()
        conn.close()
        if not row:
            return

        draft_id, created_by, created_at, updated_by, updated_at, payload = row
        if not messagebox.askyesno(
            "Черновик найден",
            f"Для пользователя {self.current_user} найден черновик от {updated_at.replace('T', ' ')}.\n\nВосстановить его?"
        ):
            return

        self.current_draft_id = draft_id
        self.update_audit_text((created_by, created_at, updated_by, updated_at))
        self.apply_draft_payload(json.loads(payload))

    def apply_draft_payload(self, payload):
        self.suspend_autosave = True
        self.current_project_id = payload.get("project_id") or self.current_project_id
        self.company_var.set(payload.get("company", self.company_var.get()))
        self.replace_entry_text(self.contract_entry, payload.get("contract", ""))
        self.replace_entry_text(self.customer_entry, payload.get("customer", ""))
        self.replace_entry_text(self.object_entry, payload.get("object", ""))
        self.disc_var.set(payload.get("discount", "0"))
        self.watermark_var.set(payload.get("watermark", True))

        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in payload.get("items", []):
            self.tree.insert("", "end", values=item.get("values", ()), tags=tuple(item.get("tags", ())))

        self.suspend_autosave = False
        self.recalculate_total()

    def apply_project_context(self):
        project_name = self.project_context.get("project_name", "").strip()
        contract = self.project_context.get("contract", "").strip()
        customer = self.project_context.get("customer", "").strip()
        company = self.project_context.get("company")
        if company in ("ООО Декорартстрой", "ИП Гордеев А.Н."):
            self.company_var.set(company)
        if contract:
            self.replace_entry_text(self.contract_entry, contract)
        if customer:
            self.replace_entry_text(self.customer_entry, customer)
        if project_name:
            self.replace_entry_text(self.object_entry, project_name)
            self.title(f"Генератор смет (PDF) - {project_name}")

    def restore_project_draft_if_available(self):
        draft_path = self.build_draft_file_path()
        if not os.path.exists(draft_path):
            return
        if not messagebox.askyesno(
            "Черновик проекта найден",
            f"Для объекта найден сохраненный черновик:\n{os.path.basename(draft_path)}\n\nОткрыть его?"
        ):
            return
        try:
            self.load_draft_from_file(draft_path)
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть черновик проекта:\n{exc}")

    def replace_entry_text(self, entry, value):
        entry.delete(0, 'end')
        entry.insert(0, value)

    def update_audit_text(self, audit_row):
        if not audit_row:
            self.audit_text.set("Черновик: еще не сохранен")
            return
        created_by, created_at, updated_by, updated_at = audit_row
        created_at = (created_at or "").replace("T", " ")
        updated_at = (updated_at or "").replace("T", " ")
        self.audit_text.set(
            f"Создал: {created_by or '-'} {created_at or '-'} | Изменил: {updated_by or '-'} {updated_at or '-'}"
        )

    def save_draft_manually(self):
        self.save_draft()
        saved_file = self.current_draft_file or self.build_draft_file_path()
        messagebox.showinfo("Сохранено", f"Смета сохранена.\n{saved_file}")

    def ensure_project_from_estimate(self):
        if self.current_project_id:
            self.save_draft()
            return messagebox.showinfo("Проект уже создан", f"Эта смета уже привязана к проекту №{self.current_project_id}.")

        object_name = self.object_entry.get().strip()
        customer_name = self.customer_entry.get().strip()
        if not object_name:
            return messagebox.showwarning("Внимание", "Укажите объект или адрес перед оформлением сметы в проект.")
        if not customer_name:
            return messagebox.showwarning("Внимание", "Укажите имя заказчика перед оформлением сметы в проект.")

        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        conn = sqlite3.connect(self.state_db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO projects
               (project_name, address, customer, contract, date, counterparty_id, status, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                object_name,
                object_name,
                customer_name,
                self.contract_entry.get().strip(),
                "",
                None,
                "В работе",
                "Создано из сметы",
                timestamp,
                timestamp,
            ),
        )
        self.current_project_id = c.lastrowid
        c.execute(
            """INSERT INTO project_events (project_id, event_type, event_text, author, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                self.current_project_id,
                "project",
                f"Проект создан из сметы: {object_name}",
                self.current_user,
                timestamp,
            ),
        )
        conn.commit()
        conn.close()

        self.save_draft()
        should_open_crm = messagebox.askyesno(
            "Проект создан",
            f"Смета оформлена в проект №{self.current_project_id}.\n\nОткрыть этот проект в CRM сейчас?",
        )
        if should_open_crm:
            crm_path = os.path.join(self.get_workspace_dir(), "CRM.py")
            try:
                subprocess.Popen([sys.executable, crm_path, "--project-id", str(self.current_project_id)])
            except OSError as exc:
                messagebox.showerror("Ошибка", f"Не удалось открыть CRM:\n{exc}")

    def get_workspace_dir(self):
        return BASE_DIR

    def resolve_workspace_path(self, path):
        raw_path = str(path or "").strip()
        if not raw_path:
            return ""
        if os.path.exists(raw_path):
            return raw_path

        workspace_dir = self.get_workspace_dir()
        normalized = os.path.normpath(raw_path)
        if not os.path.isabs(normalized):
            candidate = os.path.normpath(os.path.join(workspace_dir, normalized))
            if os.path.exists(candidate):
                return candidate

        parts = [part for part in re.split(r"[\\/]+", raw_path) if part]
        workspace_name = os.path.basename(workspace_dir)
        for anchor in (workspace_name, "CRM_OLD_BAD"):
            if anchor in parts:
                anchor_index = parts.index(anchor)
                candidate = os.path.join(workspace_dir, *parts[anchor_index + 1 :])
                if os.path.exists(candidate):
                    return candidate

        for marker in ("Сметы", "Договоры", "_contract_tmp"):
            if marker in parts:
                marker_index = parts.index(marker)
                candidate = os.path.join(workspace_dir, *parts[marker_index:])
                if os.path.exists(candidate):
                    return candidate

        return raw_path

    def to_workspace_storage_path(self, path):
        raw_path = str(path or "").strip()
        if not raw_path:
            return ""
        candidate = self.resolve_workspace_path(raw_path) or raw_path
        if not os.path.isabs(candidate):
            return os.path.normpath(candidate)
        workspace_dir = os.path.abspath(self.get_workspace_dir())
        candidate_abs = os.path.abspath(candidate)
        try:
            if os.path.commonpath([candidate_abs, workspace_dir]) == workspace_dir:
                return os.path.normpath(os.path.relpath(candidate_abs, workspace_dir))
        except ValueError:
            pass
        return candidate

    def repair_document_paths(self, conn=None):
        owns_connection = conn is None
        if owns_connection:
            conn = sqlite3.connect(self.state_db_path)
            conn.row_factory = sqlite3.Row
        elif conn.row_factory is None:
            conn.row_factory = sqlite3.Row
        c = conn.cursor()
        tables = {row['name'] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'documents' not in tables:
            if owns_connection:
                conn.close()
            return 0
        rows = c.execute(
            "SELECT id, COALESCE(file_path, '') AS file_path, COALESCE(draft_path, '') AS draft_path, COALESCE(pdf_path, '') AS pdf_path FROM documents"
        ).fetchall()
        repaired = 0
        for row in rows:
            updates = {}
            for column in ('file_path', 'draft_path', 'pdf_path'):
                current_path = row[column]
                resolved_path = self.resolve_workspace_path(current_path)
                if current_path and resolved_path and os.path.exists(resolved_path):
                    stored_path = self.to_workspace_storage_path(resolved_path)
                    if stored_path != current_path:
                        updates[column] = stored_path
            if updates:
                assignments = ', '.join(f"{column}=?" for column in updates)
                c.execute(
                    f"UPDATE documents SET {assignments}, updated_at=? WHERE id=?",
                    [*updates.values(), datetime.datetime.now().isoformat(timespec='seconds'), row['id']],
                )
                repaired += 1
        if repaired:
            conn.commit()
        if owns_connection:
            conn.close()
        return repaired

    def setup_text_editing_support(self):
        self._context_text_widget = None
        if self._text_context_menu is None:
            self._text_context_menu = tk.Menu(self, tearoff=0)
            self._text_context_menu.add_command(label="Вырезать", command=lambda: self._run_text_edit_action("cut", self._context_text_widget))
            self._text_context_menu.add_command(label="Копировать", command=lambda: self._run_text_edit_action("copy", self._context_text_widget))
            self._text_context_menu.add_command(label="Вставить", command=lambda: self._run_text_edit_action("paste", self._context_text_widget))
            self._text_context_menu.add_command(label="Удалить", command=lambda: self._run_text_edit_action("delete", self._context_text_widget))
            self._text_context_menu.add_separator()
            self._text_context_menu.add_command(label="Выделить все", command=lambda: self._run_text_edit_action("select_all", self._context_text_widget))
        bindings = {
            "<Control-a>": "select_all",
            "<Control-A>": "select_all",
            "<Control-c>": "copy",
            "<Control-C>": "copy",
            "<Control-v>": "paste",
            "<Control-V>": "paste",
            "<Control-x>": "cut",
            "<Control-X>": "cut",
            "<Control-Insert>": "copy",
            "<Shift-Insert>": "paste",
            "<Shift-Delete>": "cut",
            "<Delete>": "delete",
            "<KP_Delete>": "delete",
        }
        for sequence, action in bindings.items():
            self.bind_all(sequence, lambda event, action=action: self._run_text_edit_action(action, getattr(event, "widget", None)), add="+")
        self.bind_all("<Button-3>", self.show_text_context_menu, add="+")

    def _resolve_text_widget(self, widget=None):
        current = widget or self.focus_get()
        seen = set()
        while current is not None and current not in seen:
            seen.add(current)
            if isinstance(current, ctk.CTkEntry):
                return getattr(current, "_entry", current)
            if isinstance(current, ctk.CTkTextbox):
                return getattr(current, "_textbox", current)
            try:
                class_name = current.winfo_class().lower()
            except Exception:
                class_name = ""
            if class_name in {"entry", "text", "tentry"}:
                return current
            current = getattr(current, "master", None)
        return None

    def _get_text_widget_state(self, widget):
        try:
            return str(widget.cget("state"))
        except Exception:
            return "normal"

    def _get_text_widget_kind(self, widget):
        try:
            class_name = widget.winfo_class().lower()
        except Exception:
            class_name = ""
        return "text" if class_name == "text" else "entry"

    def _get_selected_text(self, widget):
        kind = self._get_text_widget_kind(widget)
        try:
            if kind == "text":
                if widget.tag_ranges("sel"):
                    return widget.get("sel.first", "sel.last")
                return ""
            if widget.selection_present():
                return widget.selection_get()
        except Exception:
            return ""
        return ""

    def _replace_selection_or_insert(self, widget, text_to_insert):
        kind = self._get_text_widget_kind(widget)
        if kind == "text":
            if widget.tag_ranges("sel"):
                widget.delete("sel.first", "sel.last")
            widget.insert("insert", text_to_insert)
            return
        try:
            if widget.selection_present():
                widget.delete("sel.first", "sel.last")
        except Exception:
            pass
        widget.insert("insert", text_to_insert)

    def _delete_from_widget(self, widget):
        kind = self._get_text_widget_kind(widget)
        if kind == "text":
            if widget.tag_ranges("sel"):
                widget.delete("sel.first", "sel.last")
            else:
                widget.delete("insert")
            return
        try:
            if widget.selection_present():
                widget.delete("sel.first", "sel.last")
            else:
                insert_index = widget.index("insert")
                if insert_index < len(widget.get()):
                    widget.delete(insert_index)
        except Exception:
            pass

    def _select_all_text(self, widget):
        if self._get_text_widget_kind(widget) == "text":
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        else:
            widget.select_range(0, "end")
            widget.icursor("end")

    def _copy_text_to_clipboard(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()

    def _run_text_edit_action(self, action, widget=None):
        target = self._resolve_text_widget(widget)
        if target is None:
            return None
        try:
            target.focus_force()
        except Exception:
            pass
        editable = self._get_text_widget_state(target) not in {"disabled", "readonly"}
        try:
            if action == "select_all":
                self._select_all_text(target)
            elif action == "copy":
                selected = self._get_selected_text(target)
                if selected:
                    self._copy_text_to_clipboard(selected)
            elif action == "cut":
                if not editable:
                    return "break"
                selected = self._get_selected_text(target)
                if selected:
                    self._copy_text_to_clipboard(selected)
                    self._delete_from_widget(target)
            elif action == "paste":
                if not editable:
                    return "break"
                try:
                    clipboard_text = self.clipboard_get()
                except Exception:
                    clipboard_text = ""
                if clipboard_text:
                    self._replace_selection_or_insert(target, clipboard_text)
            elif action == "delete":
                if not editable:
                    return "break"
                self._delete_from_widget(target)
        except Exception:
            return "break"
        return "break"

    def show_text_context_menu(self, event):
        target = self._resolve_text_widget(getattr(event, "widget", None))
        if target is None:
            return None
        self._context_text_widget = target
        editable = self._get_text_widget_state(target) not in {"disabled", "readonly"}
        self._text_context_menu.entryconfigure(0, state="normal" if editable else "disabled")
        self._text_context_menu.entryconfigure(1, state="normal")
        self._text_context_menu.entryconfigure(2, state="normal" if editable else "disabled")
        self._text_context_menu.entryconfigure(3, state="normal" if editable else "disabled")
        self._text_context_menu.entryconfigure(5, state="normal")
        try:
            self._text_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._text_context_menu.grab_release()
        return "break"

    def set_sync_health_status(self, text, tone="info"):
        if hasattr(self, "health_text"):
            self.health_text.set(text)
        if hasattr(self, "health_label"):
            palette = {
                "info": "#5f7288",
                "ok": "#2a885a",
                "warning": "#bb8910",
                "error": "#b63f3b",
            }
            self.health_label.configure(text_color=palette.get(tone, "#5f7288"))

    def collect_startup_health_issues(self):
        workspace_dir = self.get_workspace_dir()
        issues = []
        critical_files = [
            ("\u0411\u0430\u0437\u0430 CRM", self.state_db_path),
            ("\u0411\u0430\u0437\u0430 \u0446\u0435\u043d", PRICE_DB_PATH),
            ("\u0424\u0430\u0439\u043b CRM", os.path.join(workspace_dir, "CRM.py")),
        ]
        for label, path in critical_files:
            if not os.path.exists(path):
                issues.append(f"{label}: {path}")

        for dirname in ("\u0421\u043c\u0435\u0442\u044b", "\u0414\u043e\u0433\u043e\u0432\u043e\u0440\u044b", "_contract_tmp"):
            os.makedirs(os.path.join(workspace_dir, dirname), exist_ok=True)

        conn = sqlite3.connect(self.state_db_path)
        conn.row_factory = sqlite3.Row
        try:
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "documents" in tables:
                rows = conn.execute(
                    "SELECT id, project_id, title, COALESCE(file_path, '') AS file_path, COALESCE(draft_path, '') AS draft_path, COALESCE(pdf_path, '') AS pdf_path FROM documents"
                ).fetchall()
                broken_docs = []
                for row in rows:
                    missing_parts = []
                    for column, label in (("file_path", "\u0444\u0430\u0439\u043b"), ("draft_path", "\u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a"), ("pdf_path", "PDF")):
                        stored_path = str(row[column] or "").strip()
                        if stored_path and not os.path.exists(self.resolve_workspace_path(stored_path)):
                            missing_parts.append(f"{label}: {stored_path}")
                    if missing_parts:
                        title = str(row["title"] or f"\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442 #{row['id']}")
                        project_id = row["project_id"] if row["project_id"] is not None else "-"
                        broken_docs.append(f"{title} (\u043f\u0440\u043e\u0435\u043a\u0442 {project_id}) -> {'; '.join(missing_parts)}")
                if broken_docs:
                    issues.append(f"\u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b \u0444\u0430\u0439\u043b\u044b \u0443 {len(broken_docs)} \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432.")
                    issues.extend(broken_docs[:5])
                    if len(broken_docs) > 5:
                        issues.append(f"\u0415\u0449\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0445 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432: {len(broken_docs) - 5}.")
        finally:
            conn.close()

        return issues

    def run_startup_health_check(self):
        if self.startup_health_checked:
            return
        self.startup_health_checked = True

        issues = self.collect_startup_health_issues()
        repaired = getattr(self, "repaired_document_paths_count", 0)
        if issues:
            self.set_sync_health_status("\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f: \u0435\u0441\u0442\u044c \u0437\u0430\u043c\u0435\u0447\u0430\u043d\u0438\u044f", "warning")
            details = []
            if repaired:
                details.append(f"\u0410\u0432\u0442\u043e\u043f\u043e\u0447\u0438\u043d\u043a\u0430 \u043f\u0443\u0442\u0435\u0439: {repaired}.")
            details.append("\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e \u0434\u0430\u043d\u043d\u044b\u0445 \u0441\u043c\u0435\u0442\u044b:")
            details.extend(f"- {item}" for item in issues)
            messagebox.showwarning("\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0434\u0430\u043d\u043d\u044b\u0445 \u0441\u043c\u0435\u0442\u044b", "\n".join(details))
            return

        suffix = f" \u0410\u0432\u0442\u043e\u043f\u043e\u0447\u0438\u043d\u043a\u0430 \u043f\u0443\u0442\u0435\u0439: {repaired}." if repaired else ""
        self.set_sync_health_status(f"\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f: OK.{suffix}", "ok")

    def get_estimates_dir(self):
        estimates_dir = os.path.join(self.get_workspace_dir(), "Сметы")
        os.makedirs(estimates_dir, exist_ok=True)
        return estimates_dir

    def get_object_folder_name(self):
        object_entry = getattr(self, "object_entry", None)
        object_name = object_entry.get().strip() if object_entry is not None else ""
        if self.current_project_id:
            base_name = self.sanitize_filename(object_name, f"Объект_{self.current_project_id}")
            return f"{self.current_project_id:04d}_{base_name}"
        return self.sanitize_filename(object_name, "Общий список")

    def get_object_dir(self):
        object_dir = os.path.join(self.get_estimates_dir(), self.get_object_folder_name())
        os.makedirs(object_dir, exist_ok=True)
        return object_dir

    def get_drafts_dir(self):
        drafts_dir = os.path.join(self.get_object_dir(), "Черновики")
        os.makedirs(drafts_dir, exist_ok=True)
        return drafts_dir

    def sanitize_filename(self, value, fallback="СМЕТА"):
        cleaned = (value or "").strip()
        for char in '<>:"/\\|?*':
            cleaned = cleaned.replace(char, "_")
        cleaned = " ".join(cleaned.split()).strip(". ")
        return cleaned[:120] or fallback

    def get_preferred_draft_file_path(self):
        object_name = self.object_entry.get().strip()
        filename = f"{self.sanitize_filename(object_name, 'Черновик сметы')}.json"
        return os.path.join(self.get_drafts_dir(), filename)

    def build_draft_file_path(self):
        return self.current_draft_file or self.get_preferred_draft_file_path()

    def should_relocate_current_draft(self, preferred_path):
        if not self.current_draft_file:
            return False
        current_path = os.path.abspath(self.current_draft_file)
        preferred_abs = os.path.abspath(preferred_path)
        managed_root = os.path.abspath(self.get_estimates_dir())
        return current_path != preferred_abs and current_path.startswith(managed_root)

    def save_draft_to_file(self, payload):
        preferred_path = self.get_preferred_draft_file_path()
        draft_path = preferred_path
        if self.current_draft_file and not self.should_relocate_current_draft(preferred_path):
            draft_path = self.current_draft_file
        elif self.current_draft_file and self.should_relocate_current_draft(preferred_path):
            current_path = self.current_draft_file
            os.makedirs(os.path.dirname(preferred_path), exist_ok=True)
            if os.path.exists(current_path):
                try:
                    os.replace(current_path, preferred_path)
                except OSError:
                    pass
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(payload)
        self.current_draft_file = draft_path
        self.update_project_smeta_document(draft_path=draft_path)

    def load_draft_from_file(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.current_draft_file = filepath
        self.apply_draft_payload(payload)
        self.audit_text.set(f"Открыт файл: {os.path.basename(filepath)}")

    def open_saved_draft(self):
        filepath = filedialog.askopenfilename(
            title="Открыть сохраненную смету",
            initialdir=self.get_drafts_dir(),
            filetypes=[("JSON files", "*.json")]
        )
        if not filepath:
            return
        try:
            self.load_draft_from_file(filepath)
            messagebox.showinfo("Открыто", f"Смета открыта:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть смету:\n{e}")

    def split_object_lines(self, value):
        text = " ".join((value or "").split())
        if not text:
            return "", ""
        parts = [part.strip() for part in text.split(",", 1)]
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    def collect_text_fields_for_check(self):
        fields = [
            ("Договор", self.contract_entry.get().strip(), self.contract_entry),
            ("Заказчик", self.customer_entry.get().strip(), self.customer_entry),
            ("Объект", self.object_entry.get().strip(), self.object_entry),
        ]
        for idx, child in enumerate(self.tree.get_children(), 1):
            tags = self.tree.item(child, "tags")
            values = self.tree.item(child, "values")
            if not values:
                continue
            label = f"Раздел {idx}" if "room" in tags else f"Работа {idx}"
            fields.append((label, str(values[0]).strip(), None))
        return fields

    def reset_text_highlights(self):
        default_border = ("#979DA2", "#565B5E")
        for entry in (self.contract_entry, self.customer_entry, self.object_entry):
            entry.configure(border_color=default_border)

    def highlight_entry(self, entry):
        if entry is not None:
            entry.configure(border_color=("#d12f2f", "#ff6b6b"))

    def analyze_text_issues(self, label, text):
        issues = []
        if not text:
            return issues

        if "  " in text:
            issues.append("есть двойные пробелы")
        if re.search(r"[A-Za-z][А-Яа-яЁё]|[А-Яа-яЁё][A-Za-z]", text):
            issues.append("смешаны латинские и русские буквы")
        if re.search(r"[.,;:!?]{2,}", text):
            issues.append("повторяются знаки препинания")
        if re.search(r"\s+[.,;:!?]", text):
            issues.append("есть пробел перед знаком препинания")
        if re.search(r"[А-Яа-яЁё]{4,}", text) and text[:1].isalpha() and text[:1].islower():
            issues.append("возможно, строка должна начинаться с заглавной буквы")

        suspicious_words = {
            "жы": "возможна ошибка с 'жи/ши'",
            "шы": "возможна ошибка с 'жи/ши'",
            "чя": "возможна ошибка с 'ча/ща'",
            "щя": "возможна ошибка с 'ча/ща'",
            "чю": "возможна ошибка с 'чу/щу'",
            "щю": "возможна ошибка с 'чу/щу'",
        }
        lower_text = text.lower()
        for fragment, message in suspicious_words.items():
            if fragment in lower_text:
                issues.append(message)
                break

        return issues

    def run_text_check(self):
        self.reset_text_highlights()
        results = []
        for label, text, entry in self.collect_text_fields_for_check():
            issues = self.analyze_text_issues(label, text)
            if issues:
                self.highlight_entry(entry)
                results.append(f"{label}: {text}\n- " + "\n- ".join(issues))

        if not results:
            messagebox.showinfo("Проверка текста", "Явных текстовых ошибок не найдено.")
            return

        win = ctk.CTkToplevel(self)
        win.title("Проверка текста")
        win.geometry("760x520")
        win.attributes('-topmost', True)
        ctk.CTkLabel(win, text="Потенциальные ошибки и подозрительные места", font=("Arial", 14, "bold")).pack(padx=12, pady=(12, 8), anchor="w")
        box = ctk.CTkTextbox(win, wrap="word")
        box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        box.insert("1.0", "\n\n".join(results))
        box.configure(state="disabled")

    def get_company_details(self, company_name):
        companies = {
            "ООО Декорартстрой": {
                "title": "<b>ООО «Декорартстрой»</b>",
                "details": [
                    "ИНН 7811530330 / КПП 780501001",
                    "ОГРН 1127847464942",
                    "Юр. адрес: г. Санкт-Петербург, Ленинский пр-кт,",
                    "д. 144, кор. 1, стр. 2, оф. 302",
                    "Тел.: +7 (911) 921-30-39, +7 (911) 031-61-01",
                    "E-mail: info@dekorartstroy.ru",
                    "Сайт: remontstroyspb.ru",
                ],
            },
            "ИП Гордеев А.Н.": {
                "title": "<b>ИП Гордеев А.Н.</b>",
                "details": [
                    "ИНН 781144532689",
                    "ОГРНИП 318784700361262",
                    "Адрес: г. Санкт-Петербург, Ленинский пр-кт,",
                    "д. 144, кор. 1, стр. 2, оф. 302",
                    "Тел.: +7 (911) 921-30-39, +7 (911) 031-61-01",
                    "Почта: gorodok198@yandex.ru",
                    "Сайт: remontstroyspb.ru",
                ],
            },
        }
        return companies.get(company_name, companies["ООО Декорартстрой"])

    def parse_float_input(self, value, field_name, *, allow_zero=False):
        text = str(value).strip().replace(",", ".")
        try:
            number = float(text)
        except ValueError:
            raise ValueError(f"Поле «{field_name}» должно быть числом.")
        if number < 0 or (not allow_zero and number == 0):
            comparator = "не меньше 0" if allow_zero else "больше 0"
            raise ValueError(f"Поле «{field_name}» должно быть {comparator}.")
        return number

    def get_discount_percent(self):
        raw_value = self.disc_var.get().strip()
        if not raw_value:
            return 0.0
        try:
            discount = float(raw_value.replace(",", "."))
        except ValueError:
            return 0.0
        return max(0.0, min(discount, 100.0))

    def has_estimate_rows(self):
        for child in self.tree.get_children():
            if "room" not in self.tree.item(child, "tags"):
                return True
        return False

    def validate_required_document_fields(self):
        required_fields = (
            ("Договор", self.contract_entry),
            ("Заказчик", self.customer_entry),
            ("Объект", self.object_entry),
        )
        for label, entry in required_fields:
            if entry.get().strip():
                continue
            messagebox.showwarning("Не хватает данных", f"Заполните поле «{label}» перед сохранением PDF.")
            entry.focus_set()
            return False
        return True

    def parse_price_cell(self, price_raw):
        if price_raw is None:
            raise ValueError("Цена не указана.")
        if isinstance(price_raw, str):
            cleaned = (
                price_raw.lower()
                .replace("руб.", "")
                .replace("руб", "")
                .replace("р.", "")
                .replace("р", "")
                .replace(" ", "")
                .replace(",", ".")
            )
            return self.parse_float_input(cleaned, "Цена", allow_zero=False)
        return self.parse_float_input(price_raw, "Цена", allow_zero=False)

    def open_price_manager(self):
        self.pm_win = ctk.CTkToplevel(self)
        self.pm_win.title("Управление прайс-листом")
        self.pm_win.geometry("850x550")
        self.pm_win.attributes('-topmost', True)

        self.pm_tree = ttk.Treeview(self.pm_win, columns=("num", "name", "unit", "price", "db_id"), show="headings", displaycolumns=("num", "name", "unit", "price"))
        self.pm_tree.heading("num", text="№"); self.pm_tree.heading("name", text="Наименование")
        self.pm_tree.heading("unit", text="Ед."); self.pm_tree.heading("price", text="Цена")
        self.pm_tree.column("num", width=40, anchor="center"); self.pm_tree.column("name", width=400, anchor="w")
        self.pm_tree.column("unit", width=80, anchor="center"); self.pm_tree.column("price", width=100, anchor="center")
        self.pm_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.pm_tree.bind("<ButtonRelease-1>", self.select_price_item)

        edit_frame = ctk.CTkFrame(self.pm_win)
        edit_frame.pack(fill="x", padx=10, pady=10)
        self.pm_id_var = ctk.StringVar()
        
        ctk.CTkLabel(edit_frame, text="Название:").grid(row=0, column=0, padx=5, pady=5)
        self.pm_name = ctk.CTkEntry(edit_frame, width=300); self.pm_name.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(edit_frame, text="Ед:").grid(row=0, column=2, padx=5, pady=5)
        self.pm_unit = ctk.CTkEntry(edit_frame, width=60); self.pm_unit.grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkLabel(edit_frame, text="Цена:").grid(row=0, column=4, padx=5, pady=5)
        self.pm_price = ctk.CTkEntry(edit_frame, width=80); self.pm_price.grid(row=0, column=5, padx=5, pady=5)

        btn_frame = ctk.CTkFrame(self.pm_win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(btn_frame, text="Добавить", command=self.pm_add, fg_color="green").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.pm_update, fg_color="#b8860b").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Удалить", command=self.pm_delete, fg_color="#8b0000").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📥 Импорт из Excel", command=self.import_from_excel, fg_color="#1f538d").pack(side="right", padx=5)
        self.pm_refresh_list()

    def import_from_excel(self):
        filepath = filedialog.askopenfilename(title="Выберите файл Excel", filetypes=[("Excel files", "*.xlsx")])
        if not filepath:
            return
        try:
            import openpyxl
        except ImportError:
            return messagebox.showerror("Ошибка", "Для импорта Excel нужна библиотека openpyxl.")

        try:
            warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
            wb = openpyxl.load_workbook(filepath, data_only=True)
            sheet = wb.active
            conn = sqlite3.connect(PRICE_DB_PATH)
            c = conn.cursor()
            c.execute("SELECT name FROM prices")
            existing_names = {row[0].lower().strip() for row in c.fetchall()}

            inserted_count = 0
            duplicate_count = 0
            skipped_count = 0
            header_values = {'наименование', 'имя', 'работа', 'наименование работ'}
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if not row or len(row) < 3:
                    skipped_count += 1
                    continue
                name, unit, price_raw = row[0], row[1], row[2]
                if not name or price_raw is None:
                    skipped_count += 1
                    continue

                name_str = str(name).strip()
                name_key = name_str.lower()
                if not name_str or name_key in header_values:
                    skipped_count += 1
                    continue

                if name_key in existing_names:
                    duplicate_count += 1
                    continue

                try:
                    price = self.parse_price_cell(price_raw)
                except ValueError:
                    skipped_count += 1
                    continue

                c.execute(
                    "INSERT INTO prices (name, unit, price) VALUES (?, ?, ?)",
                    (name_str, str(unit).strip() if unit else "шт.", price),
                )
                existing_names.add(name_key)
                inserted_count += 1

            conn.commit()
            conn.close()
            self.pm_refresh_list()
            messagebox.showinfo(
                "Успешно",
                "Импорт завершен!\n"
                f"Добавлено: {inserted_count}\n"
                f"Дубликатов пропущено: {duplicate_count}\n"
                f"Некорректных строк пропущено: {skipped_count}",
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Техническая ошибка: {e}")

    def pm_refresh_list(self):
        for item in self.pm_tree.get_children(): self.pm_tree.delete(item)
        conn = sqlite3.connect(PRICE_DB_PATH)
        rows = conn.cursor().execute("SELECT id, name, unit, price FROM prices").fetchall()
        conn.close()
        rows.sort(key=lambda x: (self.get_category_weight(x[1]), x[1]))
        for idx, row in enumerate(rows, 1): self.pm_tree.insert("", "end", values=(idx, row[1], row[2], row[3], row[0]))

    def select_price_item(self, event):
        selected = self.pm_tree.selection()
        if not selected: return
        v = self.pm_tree.item(selected[0], "values")
        self.pm_id_var.set(v[4]) 
        self.pm_name.delete(0, 'end'); self.pm_name.insert(0, v[1])
        self.pm_unit.delete(0, 'end'); self.pm_unit.insert(0, v[2])
        self.pm_price.delete(0, 'end'); self.pm_price.insert(0, v[3])

    def pm_add(self):
        name, unit, price = self.pm_name.get().strip(), self.pm_unit.get().strip(), self.pm_price.get().strip()
        if not name or not price: return messagebox.showwarning("Внимание", "Заполните название и цену!")
        try:
            price_float = self.parse_float_input(price, "Цена", allow_zero=False)
        except ValueError as exc:
            return messagebox.showwarning("Ошибка", str(exc))

        conn = sqlite3.connect(PRICE_DB_PATH)
        conn.cursor().execute("INSERT INTO prices (name, unit, price) VALUES (?, ?, ?)", (name, unit, price_float))
        conn.commit(); conn.close()
        self.pm_refresh_list()
        self.pm_name.delete(0, 'end'); self.pm_unit.delete(0, 'end'); self.pm_price.delete(0, 'end')
        messagebox.showinfo("Успешно", f"Работа «{name}» добавлена в базу!")

    def pm_update(self):
        item_id, name, unit, price = self.pm_id_var.get(), self.pm_name.get().strip(), self.pm_unit.get().strip(), self.pm_price.get().strip()
        if not item_id or not name: return
        try:
            price_float = self.parse_float_input(price, "Цена", allow_zero=False)
        except ValueError as exc:
            return messagebox.showwarning("Ошибка", str(exc))
            
        conn = sqlite3.connect(PRICE_DB_PATH)
        conn.cursor().execute("UPDATE prices SET name=?, unit=?, price=? WHERE id=?", (name, unit, price_float, item_id))
        conn.commit(); conn.close()
        self.pm_refresh_list()
        self.pm_name.delete(0, 'end'); self.pm_unit.delete(0, 'end'); self.pm_price.delete(0, 'end'); self.pm_id_var.set("")
        messagebox.showinfo("Успешно", "Изменения сохранены!")

    def pm_delete(self):
        if not self.pm_id_var.get(): return
        conn = sqlite3.connect(PRICE_DB_PATH)
        conn.cursor().execute("DELETE FROM prices WHERE id=?", (self.pm_id_var.get(),))
        conn.commit(); conn.close()
        self.pm_refresh_list()
        self.pm_name.delete(0, 'end'); self.pm_unit.delete(0, 'end'); self.pm_price.delete(0, 'end')

    # --- ОКНО ДОБАВЛЕНИЯ И ПОИСК БЕЗ УЧЕТА РЕГИСТРА ---
    def open_add_window(self):
        self.add_window = ctk.CTkToplevel(self)
        self.add_window.title("Выбор работы")
        self.add_window.geometry("750x500")
        self.add_window.attributes('-topmost', True)

        sf = ctk.CTkFrame(self.add_window, fg_color="transparent")
        sf.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(sf, text="Поиск:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(sf, width=400)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_prices_list)

        self.db_tree = ttk.Treeview(self.add_window, columns=("id", "name", "unit", "price"), show="headings")
        self.db_tree.heading("id", text="ID"); self.db_tree.heading("name", text="Наименование")
        self.db_tree.heading("unit", text="Ед."); self.db_tree.heading("price", text="Цена")
        self.db_tree.column("id", width=0, stretch=False); self.db_tree.column("name", width=400)
        self.db_tree.column("unit", width=50, anchor="center"); self.db_tree.column("price", width=80, anchor="center")
        self.db_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.filter_prices_list()

        bot = ctk.CTkFrame(self.add_window)
        bot.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(bot, text="🧮 Калькулятор", command=self.open_calculator, fg_color="#4169E1").pack(side="left", padx=5)
        ctk.CTkLabel(bot, text="Кол-во:").pack(side="left", padx=(30, 5))
        self.qty_entry = ctk.CTkEntry(bot, width=80); self.qty_entry.pack(side="left", padx=5); self.qty_entry.insert(0, "1")
        ctk.CTkButton(bot, text="Добавить", command=self.add_to_main, fg_color="green").pack(side="right", padx=5)

    def fetch_price_rows(self):
        conn = sqlite3.connect(PRICE_DB_PATH)
        rows = conn.cursor().execute("SELECT id, name, unit, price FROM prices").fetchall()
        conn.close()
        rows.sort(key=lambda x: (self.get_category_weight(x[1]), x[1]))
        return rows

    def filter_rows_by_query(self, query):
        query = query.lower().strip()
        return [row for row in self.fetch_price_rows() if query in row[1].lower()]

    def populate_price_tree(self, tree, rows):
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=row)

    def filter_prices_list(self, event=None):
        self.populate_price_tree(self.db_tree, self.filter_rows_by_query(self.search_entry.get()))

    def filter_inline_prices(self, event=None):
        self.populate_price_tree(self.inline_db_tree, self.filter_rows_by_query(self.inline_search_entry.get()))

    def add_to_main(self):
        sel = self.db_tree.selection()
        if not sel: return
        v = self.db_tree.item(sel[0], "values")
        try:
            qty = self.parse_float_input(self.qty_entry.get(), "Количество", allow_zero=False)
        except ValueError as exc:
            return messagebox.showwarning("Ошибка", str(exc))
        self.tree.insert("", "end", values=(v[1], v[2], qty, float(v[3]), float(v[3])*qty, float(v[3])*qty))
        self.recalculate_total()
        self.add_window.destroy()

    def inline_add_to_main(self, event=None):
        sel = self.inline_db_tree.selection()
        if not sel:
            children = self.inline_db_tree.get_children()
            if not children:
                return
            self.inline_db_tree.selection_set(children[0])
            sel = (children[0],)
        v = self.inline_db_tree.item(sel[0], "values")
        try:
            qty = self.parse_float_input(self.inline_qty_entry.get(), "Количество", allow_zero=False)
        except ValueError as exc:
            return messagebox.showwarning("Ошибка", str(exc))
        self.tree.insert("", "end", values=(v[1], v[2], qty, float(v[3]), float(v[3]) * qty, float(v[3]) * qty))
        self.recalculate_total()
        self.inline_search_entry.delete(0, 'end')
        self.inline_qty_entry.delete(0, 'end')
        self.inline_qty_entry.insert(0, "1")
        self.filter_inline_prices()
        self.inline_search_entry.focus_set()

    def open_inline_calculator(self):
        self.qty_entry = self.inline_qty_entry
        self.open_calculator()

    # --- КАЛЬКУЛЯТОР ОБЪЕМОВ ---
    def open_calculator(self):
        parent = getattr(self, "add_window", self)
        self.calc_win = ctk.CTkToplevel(parent)
        self.calc_win.title("Продвинутый калькулятор")
        self.calc_win.geometry("700x800")
        self.calc_win.attributes('-topmost', True)
        self.scroll = ctk.CTkScrollableFrame(self.calc_win)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.var_h = ctk.StringVar(value="0"); self.var_floor_l = ctk.StringVar(value="0"); self.var_floor_w = ctk.StringVar(value="0")
        self.var_h.trace_add("write", self.update_advanced_calc); self.var_floor_l.trace_add("write", self.update_advanced_calc); self.var_floor_w.trace_add("write", self.update_advanced_calc)
        self.walls, self.openings, self.floor_mods = [], [], []

        ctk.CTkLabel(self.scroll, text="1. Длина каждой стены", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        f_h = ctk.CTkFrame(self.scroll, fg_color="transparent"); f_h.pack(fill="x", pady=5)
        ctk.CTkLabel(f_h, text="Высота (м):").pack(side="left", padx=5); ctk.CTkEntry(f_h, textvariable=self.var_h, width=70).pack(side="left", padx=5)
        self.f_walls = ctk.CTkFrame(self.scroll, fg_color="transparent"); self.f_walls.pack(fill="x", pady=5)
        for _ in range(4): self.add_wall_row()
        ctk.CTkButton(self.scroll, text="+ Стену", width=100, command=self.add_wall_row).pack(anchor="w", padx=5, pady=5)

        ctk.CTkLabel(self.scroll, text="2. Окна и Двери", font=("Arial", 14, "bold")).pack(anchor="w", pady=(15,5))
        f_op_b = ctk.CTkFrame(self.scroll, fg_color="transparent"); f_op_b.pack(fill="x")
        ctk.CTkButton(f_op_b, text="+ Окно", width=100, command=lambda: self.add_dynamic_row('window')).pack(side="left", padx=5)
        ctk.CTkButton(f_op_b, text="+ Дверь", width=100, fg_color="#8b8b00", command=lambda: self.add_dynamic_row('door')).pack(side="left", padx=5)
        self.f_openings = ctk.CTkFrame(self.scroll, fg_color="transparent", height=1); self.f_openings.pack(fill="x", pady=2)

        ctk.CTkLabel(self.scroll, text="3. Базовый пол", font=("Arial", 14, "bold")).pack(anchor="w", pady=(15,5))
        f_fl_b = ctk.CTkFrame(self.scroll, fg_color="transparent"); f_fl_b.pack(fill="x", pady=5)
        ctk.CTkLabel(f_fl_b, text="Длина:").pack(side="left", padx=5); ctk.CTkEntry(f_fl_b, textvariable=self.var_floor_l, width=70).pack(side="left", padx=5)
        ctk.CTkLabel(f_fl_b, text="Ширина:").pack(side="left", padx=(10, 2)); ctk.CTkEntry(f_fl_b, textvariable=self.var_floor_w, width=70).pack(side="left", padx=2)

        ctk.CTkLabel(self.scroll, text="4. Короба и Ниши", font=("Arial", 14, "bold")).pack(anchor="w", pady=(15,5))
        f_fl_m = ctk.CTkFrame(self.scroll, fg_color="transparent"); f_fl_m.pack(fill="x")
        ctk.CTkButton(f_fl_m, text="+ Короб (-)", width=100, fg_color="#8b0000", command=lambda: self.add_dynamic_row('box')).pack(side="left", padx=5)
        ctk.CTkButton(f_fl_m, text="+ Ниша (+)", width=100, fg_color="green", command=lambda: self.add_dynamic_row('niche')).pack(side="left", padx=5)
        self.f_floor_mods = ctk.CTkFrame(self.scroll, fg_color="transparent", height=1); self.f_floor_mods.pack(fill="x", pady=2)

        ctk.CTkLabel(self.scroll, text="5. ИТОГИ", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20,5))
        rf = ctk.CTkFrame(self.scroll); rf.pack(fill="x", pady=5, padx=5)
        
        self.lbl_r_f = ctk.CTkLabel(rf, text="Пол/потолок: 0 м.кв", font=("Arial", 13)); self.lbl_r_f.grid(row=0, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(rf, text="Вставить", width=80, command=lambda: self.insert_calc(self.val_floor)).grid(row=0, column=1, padx=10, pady=6)
        self.lbl_r_w = ctk.CTkLabel(rf, text="Стены: 0 м.кв", font=("Arial", 13)); self.lbl_r_w.grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(rf, text="Вставить", width=80, command=lambda: self.insert_calc(self.val_walls)).grid(row=1, column=1, padx=10, pady=6)
        self.lbl_r_p = ctk.CTkLabel(rf, text="Плинтус: 0 м", font=("Arial", 13)); self.lbl_r_p.grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(rf, text="Вставить", width=80, command=lambda: self.insert_calc(self.val_plin)).grid(row=2, column=1, padx=10, pady=6)
        self.lbl_r_ws = ctk.CTkLabel(rf, text="Откосы окон (3 ст): 0 м.пог", font=("Arial", 13)); self.lbl_r_ws.grid(row=3, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(rf, text="Вставить", width=80, command=lambda: self.insert_calc(self.val_win_slopes)).grid(row=3, column=1, padx=10, pady=6)
        self.lbl_r_ds = ctk.CTkLabel(rf, text="Откосы дверей (3 ст): 0 м.пог", font=("Arial", 13)); self.lbl_r_ds.grid(row=4, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(rf, text="Вставить", width=80, command=lambda: self.insert_calc(self.val_door_slopes)).grid(row=4, column=1, padx=10, pady=6)

        self.update_advanced_calc()

    def add_wall_row(self):
        var_w = ctk.StringVar(value="0"); var_w.trace_add("write", self.update_advanced_calc)
        row_frame = ctk.CTkFrame(self.f_walls, fg_color="transparent"); row_frame.pack(fill="x", pady=2)
        idx = len(self.walls) + 1
        lbl = ctk.CTkLabel(row_frame, text=f"Стена {idx} (м):", width=80, anchor="w"); lbl.pack(side="left", padx=5)
        ctk.CTkEntry(row_frame, textvariable=var_w, width=70).pack(side="left", padx=5)
        item = {'var': var_w, 'frame': row_frame, 'lbl': lbl}
        if idx > 4: ctk.CTkButton(row_frame, text="X", width=30, fg_color="gray", command=lambda i=item: self.remove_wall_row(i)).pack(side="left", padx=15)
        self.walls.append(item); self.update_advanced_calc()

    def remove_wall_row(self, item):
        item['frame'].destroy(); self.walls.remove(item)
        for i, w in enumerate(self.walls): w['lbl'].configure(text=f"Стена {i+1} (м):")
        self.update_advanced_calc()

    def add_dynamic_row(self, row_type):
        var_w, var_h = ctk.StringVar(value="0"), ctk.StringVar(value="0")
        var_w.trace_add("write", self.update_advanced_calc); var_h.trace_add("write", self.update_advanced_calc)
        if row_type in ['window', 'door']: parent, title, color, lst = self.f_openings, ("Окно" if row_type=='window' else "Дверь"), ("#1f538d" if row_type=='window' else "#8b8b00"), self.openings
        else: parent, title, color, lst = self.f_floor_mods, ("Короб(-)" if row_type=='box' else "Ниша(+)"), ("#8b0000" if row_type=='box' else "green"), self.floor_mods
        rf = ctk.CTkFrame(parent, fg_color="transparent"); rf.pack(fill="x", pady=2)
        ctk.CTkLabel(rf, text=title, text_color=color, font=("Arial", 12, "bold"), width=70, anchor="w").pack(side="left", padx=2)
        ctk.CTkLabel(rf, text="Шир:").pack(side="left", padx=2); ctk.CTkEntry(rf, textvariable=var_w, width=55).pack(side="left", padx=2)
        ctk.CTkLabel(rf, text="Выс:").pack(side="left", padx=2); ctk.CTkEntry(rf, textvariable=var_h, width=55).pack(side="left", padx=2)
        item = {'type': row_type, 'w': var_w, 'h': var_h, 'frame': rf}
        ctk.CTkButton(rf, text="X", width=30, fg_color="gray", command=lambda i=item: self.remove_dynamic_row(i, lst)).pack(side="left", padx=10)
        lst.append(item); self.update_advanced_calc()

    def remove_dynamic_row(self, item, lst): item['frame'].destroy(); lst.remove(item); self.update_advanced_calc()

    def update_advanced_calc(self, *args):
        def get_float(var):
            try:
                return float(var.get().replace(',', '.'))
            except (AttributeError, ValueError):
                return 0.0
        P = sum([get_float(w['var']) for w in self.walls]); H = get_float(self.var_h)
        floor_area = get_float(self.var_floor_l) * get_float(self.var_floor_w)
        for mod in self.floor_mods:
            if mod['type'] == 'box': floor_area -= (get_float(mod['w']) * get_float(mod['h']))
            else: floor_area += (get_float(mod['w']) * get_float(mod['h']))
        walls_area, doors_width, win_slopes, door_slopes = P * H, 0.0, 0.0, 0.0
        for op in self.openings:
            ow, oh = get_float(op['w']), get_float(op['h'])
            walls_area -= (ow * oh)
            if op['type'] == 'door': doors_width += ow; door_slopes += (2 * oh + ow)
            if op['type'] == 'window': win_slopes += (2 * oh + ow)

        self.val_floor = max(0.0, floor_area); self.val_walls = max(0.0, walls_area); self.val_plin = max(0.0, P - doors_width)
        self.val_win_slopes = max(0.0, win_slopes); self.val_door_slopes = max(0.0, door_slopes)

        if hasattr(self, 'lbl_r_f') and self.lbl_r_f.winfo_exists():
            self.lbl_r_f.configure(text=f"Площадь пола/потолка: {self.val_floor:.2f} м.кв")
            self.lbl_r_w.configure(text=f"Площадь стен (без проемов): {self.val_walls:.2f} м.кв")
            self.lbl_r_p.configure(text=f"Периметр плинтуса (без дверей): {self.val_plin:.2f} м")
            self.lbl_r_ws.configure(text=f"Откосы окон (3 стороны): {self.val_win_slopes:.2f} м.пог")
            self.lbl_r_ds.configure(text=f"Откосы дверей (3 стороны): {self.val_door_slopes:.2f} м.пог")

    def insert_calc(self, val):
        self.qty_entry.delete(0, 'end')
        self.qty_entry.insert(0, str(int(val)) if val.is_integer() else f"{val:.2f}")
        self.calc_win.destroy()
        self.schedule_autosave()

    # --- БАЗОВЫЕ ФУНКЦИИ ---
    def add_room(self):
        d = ctk.CTkInputDialog(text="Название раздела:", title="Раздел")
        r = d.get_input()
        if r:
            self.tree.insert("", "end", values=(r, "", "", "", "", ""), tags=("room",))
            self.schedule_autosave()

    def delete_row(self):
        for i in self.tree.selection(): self.tree.delete(i)
        self.recalculate_total()

    def edit_row(self):
        s = self.tree.selection()
        if not s: return
        self.edit_item_id = s[0]
        v = self.tree.item(self.edit_item_id, "values")
        if "room" in self.tree.item(self.edit_item_id, "tags"):
            d = ctk.CTkInputDialog(text="Изменить название:", title="Редактирование")
            n = d.get_input()
            if n:
                self.tree.item(self.edit_item_id, values=(n, "", "", "", "", ""))
                self.schedule_autosave()
        else:
            self.edit_win = ctk.CTkToplevel(self)
            self.edit_win.geometry("400x250"); self.edit_win.attributes('-topmost', True)
            ctk.CTkLabel(self.edit_win, text="Наименование:").pack()
            self.ed_name = ctk.CTkEntry(self.edit_win, width=350); self.ed_name.pack(); self.ed_name.insert(0, v[0])
            f = ctk.CTkFrame(self.edit_win, fg_color="transparent"); f.pack(pady=10)
            self.ed_unit = ctk.CTkEntry(f, width=60); self.ed_unit.grid(row=0, column=0, padx=5); self.ed_unit.insert(0, v[1])
            self.ed_qty = ctk.CTkEntry(f, width=60); self.ed_qty.grid(row=0, column=1, padx=5); self.ed_qty.insert(0, v[2])
            self.ed_price = ctk.CTkEntry(f, width=80); self.ed_price.grid(row=0, column=2, padx=5); self.ed_price.insert(0, v[3])
            ctk.CTkButton(self.edit_win, text="Сохранить", command=self.save_edit).pack(pady=10)

    def save_edit(self):
        name = self.ed_name.get().strip()
        unit = self.ed_unit.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Название работы не может быть пустым.")
            self.ed_name.focus_set()
            return
        try:
            q = self.parse_float_input(self.ed_qty.get(), "Количество", allow_zero=False)
            p = self.parse_float_input(self.ed_price.get(), "Цена", allow_zero=False)
        except ValueError as exc:
            messagebox.showwarning("Ошибка", str(exc))
            return
        self.tree.item(self.edit_item_id, values=(name, unit, q, p, q*p, q*p))
        self.recalculate_total()
        self.edit_win.destroy()

    def on_discount_change(self, *args): self.recalculate_total()

    def recalculate_total(self):
        d_pct = self.get_discount_percent()
        t_sum = t_disc = 0
        for child in self.tree.get_children():
            if "room" in self.tree.item(child, "tags"): continue
            v = list(self.tree.item(child, "values"))
            v[5] = float(v[4]) * (1 - d_pct / 100)
            self.tree.item(child, values=v)
            t_sum += float(v[4]); t_disc += v[5]
        self.totals_text.set(f"ИТОГО: {t_sum:,.0f} руб.   |   Со скидкой: {t_disc:,.0f} руб.".replace(',', ' '))
        self.schedule_autosave()

    def export_to_pdf(self):
        if not self.has_estimate_rows():
            return messagebox.showwarning("Внимание", "Добавьте хотя бы одну работу перед сохранением PDF.")
        if not self.validate_required_document_fields():
            return
        object_name = self.object_entry.get().strip()
        fp = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialdir=self.get_object_dir(),
            initialfile=f"{self.sanitize_filename(object_name, 'СМЕТА')}.pdf"
        )
        if not fp: return
        try:
            self.save_draft()
            pdfmetrics.registerFont(TTFont('Arial', os.path.join(os.environ['WINDIR'], 'Fonts', 'arial.ttf')))
            pdfmetrics.registerFont(TTFont('Arial-Bold', os.path.join(os.environ['WINDIR'], 'Fonts', 'arialbd.ttf')))
            doc = SimpleDocTemplate(fp, pagesize=A4, rightMargin=7*mm, leftMargin=7*mm, topMargin=8*mm, bottomMargin=10*mm)
            comp = self.company_var.get()
            wt = "ИП ГОРДЕЕВ А.Н." if comp == "ИП Гордеев А.Н." else "ДЕКОРАРТСТРОЙ"
            def aw(c, d):
                if self.watermark_var.get():
                    c.saveState(); c.setFont('Arial-Bold', 65); c.setFillGray(0.5, 0.15)
                    c.translate(A4[0]/2, A4[1]/2); c.rotate(45); c.drawCentredString(0, 0, wt); c.restoreState()
            
            els, s = [], getSampleStyleSheet()
            sl = ParagraphStyle('L', fontName='Arial', fontSize=6.6, leading=8, alignment=0)
            sr = ParagraphStyle('R', fontName='Arial', fontSize=6.6, leading=8, alignment=2)
            c_n = self.contract_entry.get().strip()
            c_name = self.customer_entry.get().strip()
            company_details = self.get_company_details(comp)
            li = "<br/>".join([company_details["title"], *company_details["details"]])
            object_head, object_tail = self.split_object_lines(object_name)
            meta_lines = [
                "Приложение № 1",
                f"К договору: {c_n or 'не указан'}",
                f"Заказчик: {c_name or 'не указан'}",
                f"Объект: {object_head or 'не указан'}",
            ]
            if object_tail:
                meta_lines.append(object_tail)
            ri = "<br/>".join(meta_lines)

            header = Table(
                [[Paragraph(li, sl), "", Paragraph(ri, sr)]],
                colWidths=[84*mm, 16*mm, 84*mm]
            )
            header.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

            els.append(header)
            els.append(Spacer(1, 6))
            els.append(Paragraph("СМЕТА", ParagraphStyle('T', fontName='Arial-Bold', fontSize=11.5, alignment=1, spaceAfter=4)))
            els.append(Spacer(1, 2*mm))
            
            d_pct = self.get_discount_percent()
            
            td = [["Наименование", "Ед.", "Кол-во", "Цена", "Итого", f"Со скидкой ({int(d_pct) if d_pct.is_integer() else d_pct}%)" if d_pct>0 else "Со скидкой"]]
            row_style = ParagraphStyle('N', fontName='Arial', fontSize=6.0, leading=6.4)
            ts = TableStyle([('FONTNAME', (0,0), (-1,-1), 'Arial'), ('FONTSIZE', (0,0), (-1,-1), 6.0), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                             ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                             ('FONTNAME', (0,0), (-1,0), 'Arial-Bold'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                             ('TOPPADDING', (0,0), (-1,-1), 0.5), ('BOTTOMPADDING', (0,0), (-1,-1), 0.5),
                             ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3)])
            
            ridx, rs, rds, gs, gds = 1, 0, 0, 0, 0
            for child in self.tree.get_children():
                tags, v = self.tree.item(child, "tags"), self.tree.item(child, "values")
                if "room" in tags:
                    if rs > 0:
                        td.append(["Итого по разделу:", "", "", "", f"{rs:,.0f}".replace(',',' '), f"{rds:,.0f}".replace(',',' ')])
                        ts.add('SPAN', (0, ridx), (3, ridx)); ts.add('FONTNAME', (0, ridx), (-1, ridx), 'Arial-Bold'); ts.add('ALIGN', (0, ridx), (3, ridx), 'RIGHT'); ridx += 1; rs = rds = 0
                    td.append([v[0], "", "", "", "", ""]); ts.add('SPAN', (0, ridx), (-1, ridx)); ts.add('BACKGROUND', (0, ridx), (-1, ridx), colors.HexColor('#e8e8e8'))
                    ts.add('FONTNAME', (0, ridx), (-1, ridx), 'Arial-Bold'); ts.add('ALIGN', (0, ridx), (-1, ridx), 'CENTER'); ridx += 1
                else:
                    td.append([Paragraph(v[0], row_style), v[1], f"{float(v[2]):.2f}".rstrip('0').rstrip('.'), f"{float(v[3]):,.0f}".replace(',',' '), f"{float(v[4]):,.0f}".replace(',',' '), f"{float(v[5]):,.0f}".replace(',',' ')])
                    rs += float(v[4]); rds += float(v[5]); gs += float(v[4]); gds += float(v[5]); ridx += 1

            if rs > 0:
                td.append(["Итого по разделу:", "", "", "", f"{rs:,.0f}".replace(',',' '), f"{rds:,.0f}".replace(',',' ')])
                ts.add('SPAN', (0, ridx), (3, ridx)); ts.add('FONTNAME', (0, ridx), (-1, ridx), 'Arial-Bold'); ts.add('ALIGN', (0, ridx), (3, ridx), 'RIGHT')
            
            mt = Table(td, colWidths=[78*mm, 12*mm, 16*mm, 23*mm, 24*mm, 27*mm]); mt.setStyle(ts); els.append(mt); els.append(Spacer(1, 4*mm))
            
            fcd = [["Итого по документу:", f"{gs:,.0f} руб.".replace(',', ' ')]]
            if d_pct > 0: fcd.append([f"Скидка:", f"{(gs - gds):,.0f} руб.".replace(',', ' ')]); fcd.append(["ИТОГО СО СКИДКОЙ:", f"{gds:,.0f} руб.".replace(',', ' ')])
            ct = Table(fcd, colWidths=[145*mm, 40*mm]); ct.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Arial-Bold'), ('FONTSIZE', (0,0), (-1,-1), 7.2), ('ALIGN', (0,0), (1,-1), 'RIGHT'),
                                                                                  ('TOPPADDING', (0,0), (-1,-1), 0.5), ('BOTTOMPADDING', (0,0), (-1,-1), 0.5)]))
            els.append(ct); els.append(Spacer(1, 5*mm))

            cy = datetime.datetime.now().year
            sig_style_left = ParagraphStyle('SigL', fontName='Arial', fontSize=6.5, leading=7.2, alignment=0)
            sig_style_right = ParagraphStyle('SigR', fontName='Arial', fontSize=6.5, leading=7.2, alignment=2)
            sl_sig = f"<b>Подрядчик:</b><br/>{comp}<br/><br/>________________ / ____________ /<br/>« ___ » ____________ {cy} г.<br/>М.П."
            sr_sig = f"<b>Заказчик:</b><br/>{c_name}<br/><br/>________________ / ____________ /<br/>« ___ » ____________ {cy} г."
            sig_table = Table([[Paragraph(sl_sig, sig_style_left), "", Paragraph(sr_sig, sig_style_right)]], colWidths=[85*mm, 15*mm, 85*mm])
            sig_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
            els.append(sig_table)

            doc.build(els, onFirstPage=aw, onLaterPages=aw)
            self.update_project_smeta_document(pdf_path=fp)
            messagebox.showinfo("Успешно", f"Файл сохранен:\n{fp}")
        except Exception as e: messagebox.showerror("Ошибка", f"Ошибка: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--project-id", type=int)
    args, _ = parser.parse_known_args(sys.argv[1:])
    project_context = None
    if args.project_id:
        conn = sqlite3.connect(STATE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        row = c.execute(
            """SELECT p.id AS project_id,
                      COALESCE(NULLIF(p.project_name, ''), p.address, '') AS project_name,
                      COALESCE(p.contract, '') AS contract,
                      COALESCE(
                          NULLIF(cp.full_name, ''),
                          NULLIF(cp.company_name, ''),
                          NULLIF(cp.name, ''),
                          NULLIF(p.customer, ''),
                          ''
                      ) AS customer
               FROM projects p
               LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
               WHERE p.id=?""",
            (args.project_id,),
        ).fetchone()
        conn.close()
        if row:
            project_context = dict(row)
    SmetaApp(project_context=project_context).mainloop()
