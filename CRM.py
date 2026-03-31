import os
import subprocess
import sys

import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import datetime


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


DB_PATH = "dekorart_base.db"

COUNTERPARTY_TYPES = ["Физическое лицо", "Юридическое лицо ООО", "Юридическое лицо ИП"]
PROJECT_STATUSES = ["В работе", "Пауза", "Завершен"]
DOCUMENT_TYPES = [
    "Договор",
    "Смета (приложение № 1)",
    "Промежуточный акт выполненных работ (приложение № 2)",
    "Акт дополнительных работ (приложение № 3)",
    "Акт невыполненных работ (приложение № 4)",
    "Итоговый акт выполненных работ (приложение № 5)",
]
DOCUMENT_STATUSES = ["Черновик", "На согласовании", "Согласован", "Подписан", "Отменен"]
CASH_TYPES = ["Приход", "Расход"]

COUNTERPARTY_FIELD_CONFIG = {
    "Физическое лицо": [
        ("full_name", "ФИО"),
        ("passport_series_number", "Серия и номер паспорта"),
        ("passport_issued_by", "Кем и когда выдан паспорт"),
        ("passport_department_code", "Код подразделения"),
        ("registration_address", "Адрес прописки"),
        ("work_address", "Адрес проведения работ"),
        ("birth_date", "Дата рождения"),
        ("phone", "Телефон"),
        ("email", "E-mail"),
    ],
    "Юридическое лицо ООО": [
        ("company_name", "Наименование ООО"),
        ("inn", "ИНН"),
        ("kpp", "КПП"),
        ("ogrn", "ОГРН"),
        ("checking_account", "Расчетный счет"),
        ("correspondent_account", "Корреспондентский счет"),
        ("bank_name", "Банк"),
        ("bank_bik", "БИК банка"),
        ("legal_address", "Юридический адрес"),
        ("postal_address", "Почтовый адрес"),
        ("phone", "Телефон"),
        ("email", "E-mail"),
        ("director_name", "ФИО гендиректора"),
        ("director_basis", "На основании чего действует"),
    ],
    "Юридическое лицо ИП": [
        ("company_name", "Наименование ИП"),
        ("inn", "ИНН"),
        ("ogrnip", "ОГРНИП"),
        ("checking_account", "Расчетный счет"),
        ("correspondent_account", "Корреспондентский счет"),
        ("bank_name", "Банк"),
        ("bank_bik", "БИК банка"),
        ("legal_address", "Юридический адрес"),
        ("actual_address", "Фактический адрес"),
        ("phone", "Телефон"),
        ("email", "E-mail"),
    ],
}


class CRMApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CRM Декорартстрой")
        self.geometry("1440x900")
        self.minsize(1280, 780)
        self.configure(fg_color="#eef2f7")
        self.selected_project_id = None
        self.counterparty_map = {}
        self.project_map = {}
        self.nav_buttons = {}

        self.setup_database()
        self.configure_styles()
        self.build_ui()
        self.refresh_all()

    def configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background="#dfe7f2", foreground="#233042", relief="flat")
        style.map("Treeview", background=[("selected", "#d6e4ff")], foreground=[("selected", "#10233f")])
        style.configure("TNotebook", background="#ffffff", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Segoe UI Semibold", 10))

    def get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_database(self):
        conn = self.get_connection()
        c = conn.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS counterparties (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   type TEXT NOT NULL,
                   name TEXT NOT NULL,
                   full_name TEXT,
                   phone TEXT,
                   email TEXT,
                   inn TEXT,
                   company_name TEXT,
                   kpp TEXT,
                   ogrn TEXT,
                   ogrnip TEXT,
                   passport_series_number TEXT,
                   passport_issued_by TEXT,
                   passport_department_code TEXT,
                   registration_address TEXT,
                   work_address TEXT,
                   birth_date TEXT,
                   checking_account TEXT,
                   correspondent_account TEXT,
                   bank_name TEXT,
                   bank_bik TEXT,
                   legal_address TEXT,
                   postal_address TEXT,
                   actual_address TEXT,
                   director_name TEXT,
                   director_basis TEXT,
                   notes TEXT,
                   created_at TEXT NOT NULL
               )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS projects (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   project_name TEXT,
                   address TEXT,
                   customer TEXT,
                   contract TEXT,
                   date TEXT,
                   counterparty_id INTEGER,
                   status TEXT DEFAULT 'В работе',
                   notes TEXT,
                   created_at TEXT,
                   updated_at TEXT
               )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   project_id INTEGER NOT NULL,
                   doc_type TEXT NOT NULL,
                   title TEXT NOT NULL,
                   status TEXT NOT NULL DEFAULT 'Черновик',
                   file_path TEXT,
                   draft_path TEXT,
                   pdf_path TEXT,
                   version INTEGER NOT NULL DEFAULT 1,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS cash_transactions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   txn_date TEXT NOT NULL,
                   txn_type TEXT NOT NULL,
                   amount REAL NOT NULL,
                   project_id INTEGER,
                   counterparty_id INTEGER,
                   category TEXT,
                   description TEXT,
                   created_at TEXT NOT NULL
               )"""
        )

        counterparty_columns = {row[1] for row in c.execute("PRAGMA table_info(counterparties)").fetchall()}
        for name, ddl in [
            ("full_name", "ALTER TABLE counterparties ADD COLUMN full_name TEXT"),
            ("kpp", "ALTER TABLE counterparties ADD COLUMN kpp TEXT"),
            ("ogrn", "ALTER TABLE counterparties ADD COLUMN ogrn TEXT"),
            ("ogrnip", "ALTER TABLE counterparties ADD COLUMN ogrnip TEXT"),
            ("passport_series_number", "ALTER TABLE counterparties ADD COLUMN passport_series_number TEXT"),
            ("passport_issued_by", "ALTER TABLE counterparties ADD COLUMN passport_issued_by TEXT"),
            ("passport_department_code", "ALTER TABLE counterparties ADD COLUMN passport_department_code TEXT"),
            ("registration_address", "ALTER TABLE counterparties ADD COLUMN registration_address TEXT"),
            ("work_address", "ALTER TABLE counterparties ADD COLUMN work_address TEXT"),
            ("birth_date", "ALTER TABLE counterparties ADD COLUMN birth_date TEXT"),
            ("checking_account", "ALTER TABLE counterparties ADD COLUMN checking_account TEXT"),
            ("correspondent_account", "ALTER TABLE counterparties ADD COLUMN correspondent_account TEXT"),
            ("bank_name", "ALTER TABLE counterparties ADD COLUMN bank_name TEXT"),
            ("bank_bik", "ALTER TABLE counterparties ADD COLUMN bank_bik TEXT"),
            ("legal_address", "ALTER TABLE counterparties ADD COLUMN legal_address TEXT"),
            ("postal_address", "ALTER TABLE counterparties ADD COLUMN postal_address TEXT"),
            ("actual_address", "ALTER TABLE counterparties ADD COLUMN actual_address TEXT"),
            ("director_name", "ALTER TABLE counterparties ADD COLUMN director_name TEXT"),
            ("director_basis", "ALTER TABLE counterparties ADD COLUMN director_basis TEXT"),
        ]:
            if name not in counterparty_columns:
                c.execute(ddl)

        c.execute("UPDATE counterparties SET full_name = COALESCE(full_name, name)")

        project_columns = {row[1] for row in c.execute("PRAGMA table_info(projects)").fetchall()}
        for name, ddl in [
            ("project_name", "ALTER TABLE projects ADD COLUMN project_name TEXT"),
            ("counterparty_id", "ALTER TABLE projects ADD COLUMN counterparty_id INTEGER"),
            ("status", "ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'В работе'"),
            ("notes", "ALTER TABLE projects ADD COLUMN notes TEXT"),
            ("created_at", "ALTER TABLE projects ADD COLUMN created_at TEXT"),
            ("updated_at", "ALTER TABLE projects ADD COLUMN updated_at TEXT"),
        ]:
            if name not in project_columns:
                c.execute(ddl)

        document_columns = {row[1] for row in c.execute("PRAGMA table_info(documents)").fetchall()}
        for name, ddl in [
            ("draft_path", "ALTER TABLE documents ADD COLUMN draft_path TEXT"),
            ("pdf_path", "ALTER TABLE documents ADD COLUMN pdf_path TEXT"),
        ]:
            if name not in document_columns:
                c.execute(ddl)

        now = datetime.datetime.now().isoformat(timespec="seconds")
        c.execute(
            """UPDATE projects
               SET project_name = COALESCE(NULLIF(project_name, ''), address),
                   status = COALESCE(NULLIF(status, ''), 'В работе'),
                   created_at = COALESCE(created_at, ?),
                   updated_at = COALESCE(updated_at, ?)""",
            (now, now),
        )

        conn.commit()
        conn.close()

    def build_ui(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        self.sidebar = ctk.CTkFrame(shell, width=250, corner_radius=24, fg_color="#183153")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(20, 10))
        ctk.CTkLabel(brand, text="Dekorartstroy", font=("Segoe UI Semibold", 22), text_color="#f8fbff").pack(anchor="w")
        ctk.CTkLabel(brand, text="CRM система проектов", font=("Segoe UI", 12), text_color="#a9bdd8").pack(anchor="w", pady=(4, 0))

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=14, pady=(18, 0))
        self.nav_buttons["counterparties"] = ctk.CTkButton(nav, text="Контрагенты", height=42, anchor="w", fg_color="#27476f", hover_color="#325887", command=lambda: self.show_main_tab("counterparties"))
        self.nav_buttons["counterparties"].pack(fill="x", pady=5)
        self.nav_buttons["projects"] = ctk.CTkButton(nav, text="Проекты", height=42, anchor="w", fg_color="#27476f", hover_color="#325887", command=lambda: self.show_main_tab("projects"))
        self.nav_buttons["projects"].pack(fill="x", pady=5)
        self.nav_buttons["finance"] = ctk.CTkButton(nav, text="Финансы", height=42, anchor="w", fg_color="#27476f", hover_color="#325887", command=self.open_finance_window)
        self.nav_buttons["finance"].pack(fill="x", pady=5)

        sidebar_actions = ctk.CTkFrame(self.sidebar, fg_color="#214066", corner_radius=18)
        sidebar_actions.pack(fill="x", padx=14, pady=(24, 0))
        ctk.CTkLabel(sidebar_actions, text="Быстрые действия", font=("Segoe UI Semibold", 14), text_color="#f8fbff").pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkButton(sidebar_actions, text="+ Новый контрагент", height=38, fg_color="#35a66f", hover_color="#2a885a", command=self.open_add_counterparty_window).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="+ Новый проект", height=38, fg_color="#2f80ed", hover_color="#2567bd", command=self.open_add_project_window).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="Открыть проект", height=38, fg_color="#f0b429", text_color="#233042", hover_color="#d99a11", command=self.open_project_card).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="Удалить проект", height=38, fg_color="#d9534f", hover_color="#b63f3b", command=self.delete_project).pack(fill="x", padx=12, pady=(6, 14))

        info_block = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        info_block.pack(side="bottom", fill="x", padx=18, pady=20)
        ctk.CTkLabel(info_block, text="Рабочая зона", font=("Segoe UI Semibold", 13), text_color="#f8fbff").pack(anchor="w")
        ctk.CTkLabel(info_block, text="Проекты, документы, финансы\nи контрагенты в одной системе.", justify="left", font=("Segoe UI", 11), text_color="#a9bdd8").pack(anchor="w", pady=(4, 0))

        self.content = ctk.CTkFrame(shell, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=(18, 0))

        hero = ctk.CTkFrame(self.content, corner_radius=24, fg_color="#ffffff")
        hero.pack(fill="x", pady=(0, 16))
        hero_left = ctk.CTkFrame(hero, fg_color="transparent")
        hero_left.pack(side="left", fill="both", expand=True, padx=22, pady=18)
        ctk.CTkLabel(hero_left, text="Управление объектами и документами", font=("Segoe UI Semibold", 24), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(hero_left, text="Здесь мы ведем клиентов, проекты, сметы и движение денег по объектам.", font=("Segoe UI", 12), text_color="#5f7288").pack(anchor="w", pady=(6, 0))
        hero_right = ctk.CTkFrame(hero, fg_color="transparent")
        hero_right.pack(side="right", padx=22, pady=18)
        ctk.CTkButton(hero_right, text="+ Контрагент", width=130, fg_color="#35a66f", hover_color="#2a885a", command=self.open_add_counterparty_window).pack(side="left", padx=5)
        ctk.CTkButton(hero_right, text="+ Проект", width=130, fg_color="#2f80ed", hover_color="#2567bd", command=self.open_add_project_window).pack(side="left", padx=5)
        ctk.CTkButton(hero_right, text="Финансы", width=120, fg_color="#e8eef7", text_color="#233042", hover_color="#d9e4f3", command=self.open_finance_window).pack(side="left", padx=5)

        self.stats_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(0, 16))
        self.stat_projects = self.build_stat_card(self.stats_frame, "Проекты", "0", "#2f80ed")
        self.stat_projects.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.stat_active = self.build_stat_card(self.stats_frame, "В работе", "0", "#35a66f")
        self.stat_active.pack(side="left", fill="x", expand=True, padx=8)
        self.stat_counterparties = self.build_stat_card(self.stats_frame, "Контрагенты", "0", "#f0b429")
        self.stat_counterparties.pack(side="left", fill="x", expand=True, padx=8)
        self.stat_docs = self.build_stat_card(self.stats_frame, "Документы", "0", "#8e6ad8")
        self.stat_docs.pack(side="left", fill="x", expand=True, padx=(8, 0))

        notebook_shell = ctk.CTkFrame(self.content, corner_radius=24, fg_color="#ffffff")
        notebook_shell.pack(fill="both", expand=True)
        self.main_notebook = ttk.Notebook(notebook_shell)
        self.main_notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.counterparties_tab = ctk.CTkFrame(self.main_notebook, fg_color="#ffffff")
        self.projects_tab = ctk.CTkFrame(self.main_notebook, fg_color="#ffffff")
        self.main_notebook.add(self.counterparties_tab, text="Контрагенты")
        self.main_notebook.add(self.projects_tab, text="Проекты")

        self.build_counterparties_tab()
        self.build_projects_tab()
        self.show_main_tab("projects")

    def build_stat_card(self, parent, title, value, accent_color):
        card = ctk.CTkFrame(parent, corner_radius=20, fg_color="#ffffff")
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkFrame(top, width=12, height=12, corner_radius=6, fg_color=accent_color).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top, text=title, font=("Segoe UI Semibold", 13), text_color="#516274").pack(side="left")
        value_var = ctk.StringVar(value=value)
        ctk.CTkLabel(card, textvariable=value_var, font=("Segoe UI Semibold", 30), text_color="#1d2b3a").pack(anchor="w", padx=18, pady=(0, 8))
        card.value_var = value_var
        return card

    def show_main_tab(self, tab_name):
        if tab_name == "counterparties":
            self.main_notebook.select(self.counterparties_tab)
        elif tab_name == "projects":
            self.main_notebook.select(self.projects_tab)
        for name, button in self.nav_buttons.items():
            if name == tab_name:
                button.configure(fg_color="#3f6ea3")
            elif name != "finance":
                button.configure(fg_color="#27476f")

    def build_counterparties_tab(self):
        header = ctk.CTkFrame(self.counterparties_tab, fg_color="#f5f8fc", corner_radius=18)
        header.pack(fill="x", padx=10, pady=10)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(left, text="Контрагенты", font=("Segoe UI Semibold", 18), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(left, text="Физические лица, ООО и ИП с полными реквизитами.", font=("Segoe UI", 11), text_color="#617487").pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(header, text="+ Добавить контрагента", command=self.open_add_counterparty_window, fg_color="#35a66f", hover_color="#2a885a").pack(side="right", padx=16, pady=16)

        columns = ("id", "type", "name", "phone", "email", "inn")
        self.counterparties_tree = ttk.Treeview(self.counterparties_tab, columns=columns, show="headings")
        for name, text, width in [
            ("id", "ID", 50),
            ("type", "Тип", 170),
            ("name", "Контрагент", 330),
            ("phone", "Телефон", 160),
            ("email", "E-mail", 240),
            ("inn", "ИНН", 150),
        ]:
            self.counterparties_tree.heading(name, text=text)
            self.counterparties_tree.column(name, width=width, anchor="w" if name in ("name", "email") else "center")
        self.counterparties_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.counterparties_tree.bind("<Double-1>", lambda event: self.open_counterparty_card())

    def build_projects_tab(self):
        filters = ctk.CTkFrame(self.projects_tab, fg_color="#f5f8fc", corner_radius=18)
        filters.pack(fill="x", padx=10, pady=10)
        left = ctk.CTkFrame(filters, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(left, text="Проекты по объектам", font=("Segoe UI Semibold", 18), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(left, text="Открывайте проект, смету и карточку клиента прямо из CRM.", font=("Segoe UI", 11), text_color="#617487").pack(anchor="w", pady=(4, 0))
        actions = ctk.CTkFrame(filters, fg_color="transparent")
        actions.pack(side="right", padx=16, pady=16)
        ctk.CTkButton(actions, text="+ Проект", width=110, fg_color="#2f80ed", hover_color="#2567bd", command=self.open_add_project_window).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Открыть", width=110, fg_color="#35a66f", hover_color="#2a885a", command=self.open_project_card).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Удалить", width=110, fg_color="#d9534f", hover_color="#b63f3b", command=self.delete_project).pack(side="left", padx=4)

        columns = ("id", "project_name", "counterparty", "contract", "date", "status")
        self.projects_tree = ttk.Treeview(self.projects_tab, columns=columns, show="headings")
        for name, text, width in [
            ("id", "ID", 50),
            ("project_name", "Проект / адрес", 520),
            ("counterparty", "Контрагент", 260),
            ("contract", "Договор", 140),
            ("date", "Дата", 120),
            ("status", "Статус", 120),
        ]:
            self.projects_tree.heading(name, text=text)
            self.projects_tree.column(name, width=width, anchor="w" if name in ("project_name", "counterparty") else "center")
        self.projects_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.projects_tree.bind("<Double-1>", lambda event: self.open_project_card())

    def get_counterparty_display_name(self, row):
        if row["type"] == "Физическое лицо":
            return row["full_name"] if "full_name" in row.keys() and row["full_name"] else row["name"]
        if row["company_name"]:
            return row["company_name"]
        return row["name"]

    def get_counterparty_identifier(self, row):
        if row["type"] == "Физическое лицо":
            return ""
        if row["type"] == "Юридическое лицо ООО":
            return row["inn"] or ""
        return row["inn"] or row["ogrnip"] or ""

    def fetch_counterparties(self):
        conn = self.get_connection()
        c = conn.cursor()
        raw_rows = c.execute("SELECT * FROM counterparties ORDER BY COALESCE(company_name, name)").fetchall()
        conn.close()
        return [
            (
                row["id"],
                row["type"],
                self.get_counterparty_display_name(row),
                row["phone"] or "",
                row["email"] or "",
                self.get_counterparty_identifier(row),
            )
            for row in raw_rows
        ]

    def fetch_projects(self):
        conn = self.get_connection()
        c = conn.cursor()
        raw_rows = c.execute(
            """SELECT p.id,
                      COALESCE(NULLIF(p.project_name, ''), p.address) AS project_name,
                      COALESCE(
                          NULLIF(cp.full_name, ''),
                          NULLIF(cp.company_name, ''),
                          NULLIF(cp.name, ''),
                          NULLIF(p.customer, ''),
                          ''
                      ) AS counterparty_name,
                      COALESCE(p.contract, '') AS contract,
                      COALESCE(p.date, '') AS doc_date,
                      COALESCE(p.status, 'В работе') AS status
               FROM projects p
               LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
               ORDER BY CASE COALESCE(p.status, 'В работе')
                            WHEN 'В работе' THEN 0
                            WHEN 'Пауза' THEN 1
                            ELSE 2
                        END,
                        project_name"""
        ).fetchall()
        conn.close()
        return [
            (
                row["id"],
                row["project_name"] or "",
                row["counterparty_name"] or "",
                row["contract"] or "",
                row["doc_date"] or "",
                row["status"] or "В работе",
            )
            for row in raw_rows
        ]

    def get_project_details(self, project_id):
        conn = self.get_connection()
        c = conn.cursor()
        row = c.execute(
            """SELECT p.id,
                      COALESCE(NULLIF(p.project_name, ''), p.address, '') AS project_name,
                      COALESCE(
                          NULLIF(cp.full_name, ''),
                          NULLIF(cp.company_name, ''),
                          NULLIF(cp.name, ''),
                          NULLIF(p.customer, ''),
                          ''
                      ) AS counterparty_name,
                      COALESCE(p.contract, '') AS contract,
                      COALESCE(p.date, '') AS doc_date,
                      COALESCE(p.status, 'В работе') AS status,
                      COALESCE(p.notes, '') AS notes,
                      p.counterparty_id
               FROM projects p
               LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
               WHERE p.id=?""",
            (project_id,),
        ).fetchone()
        conn.close()
        return row

    def ensure_project_smeta_document(self, project_id, project_name):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        default_title = f"Смета - {project_name}" if project_name else "Смета"
        conn = self.get_connection()
        c = conn.cursor()
        existing = c.execute(
            """SELECT id
               FROM documents
               WHERE project_id=? AND doc_type=?
               ORDER BY updated_at DESC, id DESC
               LIMIT 1""",
            (project_id, "Смета (приложение № 1)"),
        ).fetchone()
        if not existing:
            c.execute(
                """INSERT INTO documents (project_id, doc_type, title, status, file_path, draft_path, pdf_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (project_id, "Смета (приложение № 1)", default_title, "Черновик", "", "", "", now, now),
            )
            conn.commit()
        conn.close()

    def refresh_counterparties(self):
        for item in self.counterparties_tree.get_children():
            self.counterparties_tree.delete(item)

        rows = self.fetch_counterparties()
        self.counterparty_map = {str(row[0]): row for row in rows}
        for row in rows:
            self.counterparties_tree.insert("", "end", values=row)

    def refresh_projects(self):
        for item in self.projects_tree.get_children():
            self.projects_tree.delete(item)

        rows = self.fetch_projects()
        self.project_map = {str(row[0]): row for row in rows}
        for row in rows:
            self.projects_tree.insert("", "end", values=row)

    def refresh_all(self):
        self.refresh_counterparties()
        self.refresh_projects()
        self.update_dashboard_metrics()

    def update_dashboard_metrics(self):
        conn = self.get_connection()
        c = conn.cursor()
        project_total = c.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        active_total = c.execute("SELECT COUNT(*) FROM projects WHERE COALESCE(status, 'В работе')='В работе'").fetchone()[0]
        counterparties_total = c.execute("SELECT COUNT(*) FROM counterparties").fetchone()[0]
        docs_total = c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        conn.close()
        self.stat_projects.value_var.set(str(project_total))
        self.stat_active.value_var.set(str(active_total))
        self.stat_counterparties.value_var.set(str(counterparties_total))
        self.stat_docs.value_var.set(str(docs_total))

    def get_selected_counterparty_id(self):
        selected = self.counterparties_tree.selection()
        if not selected:
            return None
        return self.counterparties_tree.item(selected[0], "values")[0]

    def open_add_counterparty_window(self):
        self.open_counterparty_form()

    def open_counterparty_form(self, counterparty_id=None):
        win = ctk.CTkToplevel(self)
        win.title("Карточка контрагента" if counterparty_id else "Новый контрагент")
        win.geometry("700x820")
        win.attributes("-topmost", True)

        existing = None
        if counterparty_id:
            conn = self.get_connection()
            c = conn.cursor()
            existing = c.execute("SELECT * FROM counterparties WHERE id=?", (counterparty_id,)).fetchone()
            conn.close()

        ctk.CTkLabel(win, text="Тип контрагента").pack(anchor="w", padx=18, pady=(14, 4))
        type_var = ctk.StringVar(value=existing["type"] if existing else COUNTERPARTY_TYPES[0])
        ctk.CTkOptionMenu(win, variable=type_var, values=COUNTERPARTY_TYPES, width=280).pack(anchor="w", padx=18)

        form_scroll = ctk.CTkScrollableFrame(win, width=650, height=620)
        form_scroll.pack(fill="both", expand=True, padx=18, pady=(12, 0))

        field_widgets = {}

        ctk.CTkLabel(form_scroll, text="Основные данные", font=("Arial", 15, "bold")).pack(anchor="w", pady=(0, 6))
        dynamic_container = ctk.CTkFrame(form_scroll, fg_color="transparent")
        dynamic_container.pack(fill="x")

        ctk.CTkLabel(form_scroll, text="Примечание").pack(anchor="w", pady=(14, 4))
        notes_box = ctk.CTkTextbox(form_scroll, width=620, height=110)
        notes_box.pack(fill="x")
        if existing and existing["notes"]:
            notes_box.insert("1.0", existing["notes"])

        def rebuild_fields(*args):
            for child in dynamic_container.winfo_children():
                child.destroy()
            field_widgets.clear()

            for field_name, label in COUNTERPARTY_FIELD_CONFIG[type_var.get()]:
                ctk.CTkLabel(dynamic_container, text=label).pack(anchor="w", pady=(10, 4))
                entry = ctk.CTkEntry(dynamic_container, width=620)
                entry.pack(fill="x")
                if existing and field_name in existing.keys() and existing[field_name]:
                    entry.insert(0, existing[field_name])
                field_widgets[field_name] = entry

        type_var.trace_add("write", rebuild_fields)
        rebuild_fields()

        def save():
            values = {key: widget.get().strip() for key, widget in field_widgets.items()}
            name = values.get("full_name") or values.get("company_name") or ""
            if not name:
                return messagebox.showwarning("Внимание", "Укажите ФИО или название контрагента.")
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = self.get_connection()
            c = conn.cursor()
            payload = (
                type_var.get(),
                name,
                values.get("full_name", ""),
                values.get("phone", ""),
                values.get("email", ""),
                values.get("inn", ""),
                values.get("company_name", ""),
                values.get("kpp", ""),
                values.get("ogrn", ""),
                values.get("ogrnip", ""),
                values.get("passport_series_number", ""),
                values.get("passport_issued_by", ""),
                values.get("passport_department_code", ""),
                values.get("registration_address", ""),
                values.get("work_address", ""),
                values.get("birth_date", ""),
                values.get("checking_account", ""),
                values.get("correspondent_account", ""),
                values.get("bank_name", ""),
                values.get("bank_bik", ""),
                values.get("legal_address", ""),
                values.get("postal_address", ""),
                values.get("actual_address", ""),
                values.get("director_name", ""),
                values.get("director_basis", ""),
                notes_box.get("1.0", "end").strip(),
            )
            if counterparty_id:
                c.execute(
                    """UPDATE counterparties SET
                           type=?, name=?, full_name=?, phone=?, email=?, inn=?, company_name=?, kpp=?, ogrn=?, ogrnip=?,
                           passport_series_number=?, passport_issued_by=?, passport_department_code=?, registration_address=?,
                           work_address=?, birth_date=?, checking_account=?, correspondent_account=?, bank_name=?, bank_bik=?,
                           legal_address=?, postal_address=?, actual_address=?, director_name=?, director_basis=?, notes=?
                       WHERE id=?""",
                    payload + (counterparty_id,),
                )
            else:
                c.execute(
                    """INSERT INTO counterparties (
                           type, name, full_name, phone, email, inn, company_name, kpp, ogrn, ogrnip,
                           passport_series_number, passport_issued_by, passport_department_code,
                           registration_address, work_address, birth_date, checking_account,
                           correspondent_account, bank_name, bank_bik, legal_address, postal_address,
                           actual_address, director_name, director_basis, notes, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    payload + (now,),
                )
            conn.commit()
            conn.close()
            win.destroy()
            self.refresh_counterparties()
            self.refresh_projects()

        ctk.CTkButton(win, text="Сохранить", command=save, fg_color="green").pack(pady=18)

    def open_counterparty_card(self):
        counterparty_id = self.get_selected_counterparty_id()
        if not counterparty_id:
            return messagebox.showinfo("Инфо", "Выберите контрагента из списка.")
        self.open_counterparty_form(counterparty_id)

    def open_add_project_window(self):
        counterparties = self.fetch_counterparties()
        if not counterparties:
            messagebox.showinfo("Контрагенты", "Сначала добавьте хотя бы одного контрагента.")
            return

        label_to_id = {f"{row[1]} | {row[2]}": row[0] for row in counterparties}
        default_label = next(iter(label_to_id))

        win = ctk.CTkToplevel(self)
        win.title("Новый проект")
        win.geometry("620x640")
        win.attributes("-topmost", True)

        form_frame = ctk.CTkFrame(win, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=18, pady=(14, 0))

        ctk.CTkLabel(form_frame, text="Название проекта / адрес").pack(anchor="w", pady=(0, 4))
        project_name_entry = ctk.CTkEntry(form_frame, width=560, placeholder_text="Например: ул. Тамбасова, д. 7, кв. 214")
        project_name_entry.pack(fill="x")

        ctk.CTkLabel(form_frame, text="Контрагент").pack(anchor="w", pady=(12, 4))
        counterparty_var = ctk.StringVar(value=default_label)
        ctk.CTkOptionMenu(form_frame, variable=counterparty_var, values=list(label_to_id.keys()), width=560).pack(fill="x")

        ctk.CTkLabel(form_frame, text="Номер договора").pack(anchor="w", pady=(12, 4))
        contract_entry = ctk.CTkEntry(form_frame, width=560)
        contract_entry.pack(fill="x")

        ctk.CTkLabel(form_frame, text="Дата договора").pack(anchor="w", pady=(12, 4))
        date_entry = ctk.CTkEntry(form_frame, width=560, placeholder_text="31.03.2026")
        date_entry.pack(fill="x")

        ctk.CTkLabel(form_frame, text="Статус").pack(anchor="w", pady=(12, 4))
        status_var = ctk.StringVar(value=PROJECT_STATUSES[0])
        ctk.CTkOptionMenu(form_frame, variable=status_var, values=PROJECT_STATUSES, width=220).pack(anchor="w")

        ctk.CTkLabel(form_frame, text="Примечание").pack(anchor="w", pady=(12, 4))
        notes_box = ctk.CTkTextbox(form_frame, width=560, height=120)
        notes_box.pack(fill="both", expand=True)

        def save():
            project_name = project_name_entry.get().strip()
            if not project_name:
                return messagebox.showwarning("Внимание", "Укажите название или адрес проекта.")
            now = datetime.datetime.now().isoformat(timespec="seconds")
            counterparty_id = label_to_id[counterparty_var.get()]
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM counterparties WHERE id=?", (counterparty_id,))
            counterparty_row = c.fetchone()
            counterparty_name = self.get_counterparty_display_name(counterparty_row)
            c.execute(
                """INSERT INTO projects
                   (project_name, address, customer, contract, date, counterparty_id, status, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_name,
                    project_name,
                    counterparty_name,
                    contract_entry.get().strip(),
                    date_entry.get().strip(),
                    counterparty_id,
                    status_var.get(),
                    notes_box.get("1.0", "end").strip(),
                    now,
                    now,
                ),
            )
            conn.commit()
            conn.close()
            win.destroy()
            self.refresh_projects()

        buttons_frame = ctk.CTkFrame(win)
        buttons_frame.pack(fill="x", padx=18, pady=18)
        ctk.CTkButton(buttons_frame, text="Отмена", command=win.destroy, fg_color="#5a5a5a").pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons_frame, text="Создать проект", command=save, fg_color="green").pack(side="right")

    def get_selected_project_id(self):
        selected = self.projects_tree.selection()
        if not selected:
            return None
        return self.projects_tree.item(selected[0], "values")[0]

    def delete_project(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            return messagebox.showinfo("Инфо", "Выберите проект для удаления.")
        if not messagebox.askyesno("Подтверждение", "Удалить проект и связанные документы/финансы?"):
            return
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM documents WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM cash_transactions WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM projects WHERE id=?", (project_id,))
        conn.commit()
        conn.close()
        self.refresh_projects()

    def open_project_counterparty(self, counterparty_id):
        if not counterparty_id:
            return messagebox.showinfo("Контрагент", "У этого проекта пока не привязан контрагент.")
        self.open_counterparty_form(counterparty_id)

    def open_project_smeta(self, project_id, project_name):
        self.ensure_project_smeta_document(project_id, project_name)
        smeta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smeta.py")
        try:
            subprocess.Popen([sys.executable, smeta_path, "--project-id", str(project_id)])
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть смету проекта:\n{exc}")

    def open_document_file(self, doc_row):
        if not doc_row:
            return messagebox.showinfo("Документ", "Выберите документ из списка.")
        candidate_path = doc_row.get("pdf_path") or doc_row.get("draft_path") or doc_row.get("file_path") or ""
        if not candidate_path:
            return messagebox.showinfo("Документ", "У этого документа пока нет сохраненного файла.")
        if not os.path.exists(candidate_path):
            return messagebox.showwarning("Файл не найден", f"Не удалось найти файл:\n{candidate_path}")
        try:
            os.startfile(candidate_path)
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{exc}")

    def open_selected_project_document(self, docs_tree, document_lookup):
        selected = docs_tree.selection()
        if not selected:
            return messagebox.showinfo("Документ", "Выберите документ из списка.")
        doc_id = str(docs_tree.item(selected[0], "values")[0])
        self.open_document_file(document_lookup.get(doc_id))

    def open_change_document_status_window(self, docs_tree, document_lookup, project_window):
        selected = docs_tree.selection()
        if not selected:
            return messagebox.showinfo("Документ", "Выберите документ из списка.")
        doc_id = str(docs_tree.item(selected[0], "values")[0])
        doc_row = document_lookup.get(doc_id)
        if not doc_row:
            return messagebox.showwarning("Документ", "Не удалось найти данные выбранного документа.")

        win = ctk.CTkToplevel(project_window)
        win.title("Статус документа")
        win.geometry("420x220")
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text=doc_row.get("title") or doc_row.get("doc_type") or "Документ", font=("Arial", 15, "bold")).pack(anchor="w", padx=18, pady=(16, 6))
        ctk.CTkLabel(win, text="Новый статус").pack(anchor="w", padx=18, pady=(8, 4))
        status_var = ctk.StringVar(value=doc_row.get("status") or DOCUMENT_STATUSES[0])
        ctk.CTkOptionMenu(win, variable=status_var, values=DOCUMENT_STATUSES, width=220).pack(anchor="w", padx=18)

        def save_status():
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = self.get_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE documents SET status=?, updated_at=? WHERE id=?",
                (status_var.get(), now, doc_row["id"]),
            )
            conn.commit()
            conn.close()
            win.destroy()
            project_window.destroy()
            self.open_project_card()

        buttons = ctk.CTkFrame(win, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=18)
        ctk.CTkButton(buttons, text="Отмена", command=win.destroy, fg_color="#5a5a5a").pack(side="left")
        ctk.CTkButton(buttons, text="Сохранить статус", command=save_status, fg_color="#1f8a43").pack(side="right")

    def open_project_card(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            return messagebox.showinfo("Инфо", "Выберите проект из списка.")

        row = self.get_project_details(project_id)
        if row is None:
            self.refresh_projects()
            return messagebox.showwarning(
                "Проект не найден",
                "Не удалось открыть проект. Возможно, запись была удалена или список устарел.\n\nСписок проектов обновлен."
            )
        conn = self.get_connection()
        c = conn.cursor()
        raw_documents = c.execute(
            """SELECT id,
                      doc_type,
                      title,
                      status,
                      version,
                      COALESCE(file_path, '') AS file_path,
                      COALESCE(draft_path, '') AS draft_path,
                      COALESCE(pdf_path, '') AS pdf_path
               FROM documents
               WHERE project_id=?
               ORDER BY doc_type, updated_at DESC""",
            (project_id,),
        ).fetchall()
        finances = c.execute(
            """SELECT txn_date, txn_type, amount, COALESCE(category, ''), COALESCE(description, '')
               FROM cash_transactions
               WHERE project_id=?
               ORDER BY txn_date DESC, id DESC""",
            (project_id,),
        ).fetchall()
        conn.close()
        documents = []
        document_lookup = {}
        for doc in raw_documents:
            doc_id = doc["id"]
            preferred_path = doc["pdf_path"] or doc["draft_path"] or doc["file_path"] or ""
            documents.append(
                (
                    doc_id,
                    doc["doc_type"] or "",
                    doc["title"] or "",
                    doc["status"] or "",
                    doc["version"] or 1,
                    "Да" if doc["draft_path"] else "—",
                    "Да" if doc["pdf_path"] else "—",
                    preferred_path,
                )
            )
            document_lookup[str(doc_id)] = dict(doc)

        win = ctk.CTkToplevel(self)
        win.title(f"Проект: {row[1]}")
        win.geometry("1100x760")

        header = ctk.CTkFrame(win)
        header.pack(fill="x", padx=12, pady=12)
        header_top = ctk.CTkFrame(header, fg_color="transparent")
        header_top.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(header_top, text=row[1], font=("Arial", 20, "bold")).pack(side="left")
        ctk.CTkButton(
            header_top,
            text="Открыть смету",
            command=lambda: self.open_project_smeta(project_id, row[1]),
            fg_color="#1f8a43",
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            header_top,
            text="Открыть контрагента",
            command=lambda: self.open_project_counterparty(row[7]),
            fg_color="#1f538d",
        ).pack(side="right")
        ctk.CTkLabel(
            header,
            text=f"Контрагент: {row[2]} | Договор: {row[3] or 'не указан'} | Дата: {row[4] or 'не указана'} | Статус: {row[5]}",
            font=("Arial", 12),
        ).pack(anchor="w", padx=12, pady=(0, 10))

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        overview_tab = ctk.CTkFrame(notebook)
        documents_tab = ctk.CTkFrame(notebook)
        finance_tab = ctk.CTkFrame(notebook)
        notebook.add(overview_tab, text="Обзор")
        notebook.add(documents_tab, text="Документы")
        notebook.add(finance_tab, text="Финансы")

        ctk.CTkLabel(overview_tab, text="Описание проекта", font=("Arial", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        notes_box = ctk.CTkTextbox(overview_tab, height=220)
        notes_box.pack(fill="x", padx=12, pady=(0, 12))
        notes_box.insert("1.0", row[6])
        notes_box.configure(state="disabled")

        overview_info = ctk.CTkTextbox(overview_tab, height=180)
        overview_info.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        overview_info.insert(
            "1.0",
            "Документы, которые будут жить внутри проекта:\n"
            "- Договор\n"
            "- Смета (приложение № 1)\n"
            "- Промежуточные акты\n"
            "- Акт дополнительных работ\n"
            "- Акт невыполненных работ\n"
            "- Итоговый акт\n\n"
            "Смета уже открывается прямо из карточки проекта. Следующий шаг - связать с ней создание актов и статусы согласования.",
        )
        overview_info.configure(state="disabled")

        docs_top = ctk.CTkFrame(documents_tab)
        docs_top.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(
            docs_top,
            text="+ Добавить документ",
            command=lambda: self.open_add_document_window(project_id, win),
            fg_color="green",
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            docs_top,
            text="Открыть файл",
            command=lambda: self.open_selected_project_document(docs_tree, document_lookup),
            fg_color="#1f538d",
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            docs_top,
            text="Изменить статус",
            command=lambda: self.open_change_document_status_window(docs_tree, document_lookup, win),
            fg_color="#b8860b",
            hover_color="#8b6508",
        ).pack(side="left", padx=6)

        docs_tree = ttk.Treeview(documents_tab, columns=("id", "type", "title", "status", "version", "draft", "pdf", "path"), show="headings")
        for name, text, width in [
            ("id", "ID", 50),
            ("type", "Тип", 270),
            ("title", "Название", 240),
            ("status", "Статус", 120),
            ("version", "Версия", 80),
            ("draft", "Черновик", 90),
            ("pdf", "PDF", 70),
            ("path", "Файл", 220),
        ]:
            docs_tree.heading(name, text=text)
            docs_tree.column(name, width=width, anchor="w" if name in ("type", "title", "path") else "center")
        docs_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for doc in documents:
            docs_tree.insert("", "end", values=doc)
        docs_tree.bind("<Double-1>", lambda event: self.open_selected_project_document(docs_tree, document_lookup))

        finance_summary = ctk.CTkFrame(finance_tab)
        finance_summary.pack(fill="x", padx=12, pady=12)

        total_income = sum(row_[2] for row_ in finances if row_[1] == "Приход")
        total_expense = sum(row_[2] for row_ in finances if row_[1] == "Расход")
        total_balance = total_income - total_expense
        ctk.CTkLabel(finance_summary, text=f"Приход: {total_income:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=8)
        ctk.CTkLabel(finance_summary, text=f"Расход: {total_expense:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=20)
        ctk.CTkLabel(finance_summary, text=f"Баланс: {total_balance:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=20)

        finance_tree = ttk.Treeview(finance_tab, columns=("date", "type", "amount", "category", "desc"), show="headings")
        for name, text, width in [
            ("date", "Дата", 120),
            ("type", "Тип", 100),
            ("amount", "Сумма", 140),
            ("category", "Категория", 180),
            ("desc", "Комментарий", 420),
        ]:
            finance_tree.heading(name, text=text)
            finance_tree.column(name, width=width, anchor="w" if name in ("category", "desc") else "center")
        finance_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for txn in finances:
            finance_tree.insert("", "end", values=(txn[0], txn[1], f"{txn[2]:,.0f}".replace(",", " "), txn[3], txn[4]))

    def open_add_document_window(self, project_id, parent_window):
        win = ctk.CTkToplevel(parent_window)
        win.title("Новый документ")
        win.geometry("620x360")
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="Тип документа").pack(anchor="w", padx=18, pady=(14, 4))
        doc_type_var = ctk.StringVar(value=DOCUMENT_TYPES[0])
        ctk.CTkOptionMenu(win, variable=doc_type_var, values=DOCUMENT_TYPES, width=560).pack(padx=18)

        ctk.CTkLabel(win, text="Название").pack(anchor="w", padx=18, pady=(12, 4))
        title_entry = ctk.CTkEntry(win, width=560)
        title_entry.pack(padx=18)

        ctk.CTkLabel(win, text="Статус").pack(anchor="w", padx=18, pady=(12, 4))
        status_var = ctk.StringVar(value=DOCUMENT_STATUSES[0])
        ctk.CTkOptionMenu(win, variable=status_var, values=DOCUMENT_STATUSES, width=220).pack(anchor="w", padx=18)

        ctk.CTkLabel(win, text="Путь к файлу").pack(anchor="w", padx=18, pady=(12, 4))
        path_entry = ctk.CTkEntry(win, width=560)
        path_entry.pack(padx=18)

        def save():
            title = title_entry.get().strip() or doc_type_var.get()
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = self.get_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO documents (project_id, doc_type, title, status, file_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, doc_type_var.get(), title, status_var.get(), path_entry.get().strip(), now, now),
            )
            conn.commit()
            conn.close()
            win.destroy()
            parent_window.destroy()
            self.open_project_card()

        ctk.CTkButton(win, text="Сохранить", command=save, fg_color="green").pack(pady=18)

    def open_finance_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Финансы компании")
        win.geometry("1240x760")

        top = ctk.CTkFrame(win)
        top.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(top, text="+ Операция", command=lambda: self.open_add_transaction_window(win), fg_color="green").pack(side="left", padx=6)

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        all_tab = ctk.CTkFrame(notebook)
        notebook.add(all_tab, text="Общая касса")

        projects = self.fetch_projects()
        project_tabs = []
        for project in projects:
            if project[5] != "В работе":
                continue
            tab = ctk.CTkFrame(notebook)
            notebook.add(tab, text=str(project[1])[:28])
            project_tabs.append((project[0], tab))

        self.fill_finance_tab(all_tab, None)
        for project_id, tab in project_tabs:
            self.fill_finance_tab(tab, project_id)

    def fill_finance_tab(self, tab, project_id):
        conn = self.get_connection()
        c = conn.cursor()
        if project_id is None:
            rows = c.execute(
                """SELECT t.txn_date,
                          t.txn_type,
                          t.amount,
                          COALESCE(p.project_name, p.address, 'Общая касса'),
                          COALESCE(t.category, ''),
                          COALESCE(t.description, '')
                   FROM cash_transactions t
                   LEFT JOIN projects p ON p.id = t.project_id
                   ORDER BY t.txn_date DESC, t.id DESC"""
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT t.txn_date,
                          t.txn_type,
                          t.amount,
                          COALESCE(p.project_name, p.address, ''),
                          COALESCE(t.category, ''),
                          COALESCE(t.description, '')
                   FROM cash_transactions t
                   LEFT JOIN projects p ON p.id = t.project_id
                   WHERE t.project_id=?
                   ORDER BY t.txn_date DESC, t.id DESC""",
                (project_id,),
            ).fetchall()
        conn.close()

        income = sum(row[2] for row in rows if row[1] == "Приход")
        expense = sum(row[2] for row in rows if row[1] == "Расход")
        summary = ctk.CTkFrame(tab)
        summary.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(summary, text=f"Приход: {income:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=8)
        ctk.CTkLabel(summary, text=f"Расход: {expense:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=18)
        ctk.CTkLabel(summary, text=f"Баланс: {income-expense:,.0f} руб.".replace(",", " "), font=("Arial", 14, "bold")).pack(side="left", padx=18)

        tree = ttk.Treeview(tab, columns=("date", "type", "amount", "project", "category", "desc"), show="headings")
        for name, text, width in [
            ("date", "Дата", 120),
            ("type", "Тип", 100),
            ("amount", "Сумма", 120),
            ("project", "Проект", 280),
            ("category", "Категория", 180),
            ("desc", "Комментарий", 320),
        ]:
            tree.heading(name, text=text)
            tree.column(name, width=width, anchor="w" if name in ("project", "category", "desc") else "center")
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for row in rows:
            tree.insert("", "end", values=(row[0], row[1], f"{row[2]:,.0f}".replace(",", " "), row[3], row[4], row[5]))

    def open_add_transaction_window(self, finance_window):
        projects = self.fetch_projects()
        project_labels = {"Общая касса": None}
        for project in projects:
            project_labels[str(project[1])] = project[0]

        win = ctk.CTkToplevel(finance_window)
        win.title("Новая операция")
        win.geometry("620x460")
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="Дата").pack(anchor="w", padx=18, pady=(14, 4))
        date_entry = ctk.CTkEntry(win, width=560, placeholder_text="31.03.2026")
        date_entry.insert(0, datetime.datetime.now().strftime("%d.%m.%Y"))
        date_entry.pack(padx=18)

        ctk.CTkLabel(win, text="Тип операции").pack(anchor="w", padx=18, pady=(12, 4))
        type_var = ctk.StringVar(value=CASH_TYPES[0])
        ctk.CTkOptionMenu(win, variable=type_var, values=CASH_TYPES, width=220).pack(anchor="w", padx=18)

        ctk.CTkLabel(win, text="Сумма").pack(anchor="w", padx=18, pady=(12, 4))
        amount_entry = ctk.CTkEntry(win, width=560)
        amount_entry.pack(padx=18)

        ctk.CTkLabel(win, text="Проект").pack(anchor="w", padx=18, pady=(12, 4))
        project_var = ctk.StringVar(value="Общая касса")
        ctk.CTkOptionMenu(win, variable=project_var, values=list(project_labels.keys()), width=560).pack(padx=18)

        ctk.CTkLabel(win, text="Категория").pack(anchor="w", padx=18, pady=(12, 4))
        category_entry = ctk.CTkEntry(win, width=560, placeholder_text="Например: аванс, зарплата, материалы")
        category_entry.pack(padx=18)

        ctk.CTkLabel(win, text="Комментарий").pack(anchor="w", padx=18, pady=(12, 4))
        desc_entry = ctk.CTkEntry(win, width=560)
        desc_entry.pack(padx=18)

        def save():
            try:
                amount = float(amount_entry.get().replace(",", "."))
            except ValueError:
                return messagebox.showwarning("Ошибка", "Сумма должна быть числом.")
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = self.get_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO cash_transactions
                   (txn_date, txn_type, amount, project_id, category, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    date_entry.get().strip(),
                    type_var.get(),
                    amount,
                    project_labels[project_var.get()],
                    category_entry.get().strip(),
                    desc_entry.get().strip(),
                    now,
                ),
            )
            conn.commit()
            conn.close()
            win.destroy()
            finance_window.destroy()
            self.open_finance_window()

        ctk.CTkButton(win, text="Сохранить операцию", command=save, fg_color="green").pack(pady=18)


if __name__ == "__main__":
    app = CRMApp()
    app.mainloop()
