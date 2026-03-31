import os
import subprocess
import sys
import json
import re
import shutil

import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import datetime


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


DB_PATH = "dekorart_base.db"
CONTRACT_TEMPLATE_SOURCE_PATH = r"C:\Users\Алексей\OneDrive\Рабочий стол\ОБРАЗЕЦ ДОГОВОРА.doc"
CONTRACT_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_template_physical.docx")

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
AUTH_USERS = ["Алексей", "Коллега"]

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
        self.project_sidebar_buttons = {}
        self.current_module = "projects"
        self.current_user = AUTH_USERS[0]

        self.setup_database()
        self.configure_styles()
        self.build_ui()
        self.prompt_user_login()
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

    def get_workspace_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    def sanitize_filename(self, value, fallback="Документ"):
        cleaned = (value or "").strip()
        for char in '<>:"/\\|?*':
            cleaned = cleaned.replace(char, "_")
        cleaned = " ".join(cleaned.split()).strip(". ")
        return cleaned[:120] or fallback

    def get_contracts_dir(self, project_name):
        base_dir = os.path.join(self.get_workspace_dir(), "Договоры", self.sanitize_filename(project_name, "Проект"))
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def format_contract_date(self, raw_value):
        months = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }
        text = (raw_value or "").strip()
        if not text:
            today = datetime.date.today()
            return f'" {today.day:02d} " {months[today.month]} {today.year} г.'
        try:
            dt = datetime.datetime.strptime(text, "%d.%m.%Y").date()
            return f'" {dt.day:02d} " {months[dt.month]} {dt.year} г.'
        except ValueError:
            return text

    def format_money_value(self, raw_value):
        text = str(raw_value or "").strip().replace(" ", "").replace(",", ".")
        if not text:
            return ""
        try:
            amount = float(text)
        except ValueError:
            return raw_value or ""
        return f"{amount:,.2f}".replace(",", " ").replace(".", ",")

    def parse_money_value(self, raw_value):
        text = str(raw_value or "").strip()
        if not text:
            return None
        cleaned = re.sub(r"[^0-9,.-]", "", text).replace(",", ".")
        if cleaned.count(".") > 1:
            head, tail = cleaned.rsplit(".", 1)
            cleaned = head.replace(".", "") + "." + tail
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    def pluralize(self, value, forms):
        number = abs(int(value)) % 100
        if 11 <= number <= 19:
            return forms[2]
        remainder = number % 10
        if remainder == 1:
            return forms[0]
        if 2 <= remainder <= 4:
            return forms[1]
        return forms[2]

    def number_to_words_ru(self, value):
        units = {
            0: "ноль",
            1: "один",
            2: "два",
            3: "три",
            4: "четыре",
            5: "пять",
            6: "шесть",
            7: "семь",
            8: "восемь",
            9: "девять",
            10: "десять",
            11: "одиннадцать",
            12: "двенадцать",
            13: "тринадцать",
            14: "четырнадцать",
            15: "пятнадцать",
            16: "шестнадцать",
            17: "семнадцать",
            18: "восемнадцать",
            19: "девятнадцать",
        }
        tens = {
            20: "двадцать",
            30: "тридцать",
            40: "сорок",
            50: "пятьдесят",
            60: "шестьдесят",
            70: "семьдесят",
            80: "восемьдесят",
            90: "девяносто",
        }
        hundreds = {
            100: "сто",
            200: "двести",
            300: "триста",
            400: "четыреста",
            500: "пятьсот",
            600: "шестьсот",
            700: "семьсот",
            800: "восемьсот",
            900: "девятьсот",
        }
        groups = [
            ("", "", "", False),
            ("тысяча", "тысячи", "тысяч", True),
            ("миллион", "миллиона", "миллионов", False),
            ("миллиард", "миллиарда", "миллиардов", False),
        ]
        number = int(value)
        if number == 0:
            return units[0]

        parts = []
        group_index = 0
        while number > 0 and group_index < len(groups):
            chunk = number % 1000
            number //= 1000
            if chunk:
                words = []
                h = chunk // 100 * 100
                if h:
                    words.append(hundreds[h])
                last_two = chunk % 100
                if last_two < 20:
                    if last_two:
                        if last_two == 1:
                            words.append("одна" if groups[group_index][3] else "один")
                        elif last_two == 2:
                            words.append("две" if groups[group_index][3] else "два")
                        else:
                            words.append(units[last_two])
                else:
                    t = last_two // 10 * 10
                    u = last_two % 10
                    words.append(tens[t])
                    if u:
                        if u == 1:
                            words.append("одна" if groups[group_index][3] else "один")
                        elif u == 2:
                            words.append("две" if groups[group_index][3] else "два")
                        else:
                            words.append(units[u])
                if group_index > 0:
                    words.append(self.pluralize(chunk, groups[group_index][:3]))
                parts.insert(0, " ".join(words))
            group_index += 1
        return " ".join(parts)

    def format_money_with_words(self, raw_value):
        amount = self.parse_money_value(raw_value)
        if amount is None:
            return str(raw_value or "").strip()
        rubles = int(amount)
        kopecks = int(round((amount - rubles) * 100))
        amount_text = f"{rubles:,}".replace(",", " ")
        rubles_words = self.number_to_words_ru(rubles)
        return (
            f"{amount_text} ({rubles_words}) {self.pluralize(rubles, ('рубль', 'рубля', 'рублей'))} "
            f"{kopecks:02d} {self.pluralize(kopecks, ('копейка', 'копейки', 'копеек'))}"
        )

    def parse_date_value(self, raw_value):
        text = str(raw_value or "").strip()
        if not text:
            return None
        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def format_long_date(self, raw_value, fallback=""):
        months = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }
        dt = self.parse_date_value(raw_value)
        if dt:
            return f"{dt.day} {months[dt.month]} {dt.year} года"
        return str(raw_value or fallback).strip()

    def format_deadline_text(self, raw_value):
        months = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }
        dt = self.parse_date_value(raw_value)
        if dt:
            return f"не позднее «{dt.day}» {months[dt.month]} {dt.year} г.;"
        text = str(raw_value or "").strip()
        return text or "не указано;"

    def detect_customer_gender(self, full_name):
        parts = [part for part in str(full_name or "").strip().split() if part]
        if len(parts) >= 3:
            patronymic = parts[2].lower()
            if patronymic.endswith(("вна", "ична", "кызы")):
                return "female"
            if patronymic.endswith(("вич", "оглы")):
                return "male"
        if len(parts) >= 2:
            first_name = parts[1].lower()
            if first_name.endswith(("а", "я")) and not first_name.endswith(("илья", "никита", "кузьма", "фома")):
                return "female"
        return "male" if parts else "unknown"

    def get_executor_profile(self, contractor_mode):
        if contractor_mode == "ip":
            return {"email": "gorodok198@yandex.ru", "label": "ИП"}
        return {"email": "info@dekorartstroy.ru", "label": "ООО"}

    def get_project_smeta_total(self, project_id):
        payload = self.get_project_smeta_payload(project_id)
        if not payload:
            return None
        return self.calculate_smeta_total_from_payload(payload)

    def calculate_smeta_total_from_payload(self, payload):
        total = 0.0
        for item in payload.get("items", []):
            tags = set(item.get("tags") or [])
            if "room" in tags:
                continue
            values = item.get("values") or []
            if len(values) < 6:
                continue
            amount = self.parse_money_value(values[5])
            if amount is None:
                amount = self.parse_money_value(values[4])
            if amount is not None:
                total += amount
        return round(total, 2) if total > 0 else None

    def get_project_smeta_payload(self, project_id, project_name=""):
        if project_id:
            conn = self.get_connection()
            c = conn.cursor()
            row = c.execute(
                "SELECT data FROM smeta_drafts ORDER BY updated_at DESC, id DESC"
            ).fetchall()
            conn.close()
            for draft_row in row:
                try:
                    payload = json.loads(draft_row["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if payload.get("project_id") == project_id:
                    return payload

        draft_path = self.get_project_smeta_draft_path(project_id, project_name)
        if draft_path:
            try:
                with open(draft_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def get_project_smeta_draft_path(self, project_id, project_name=""):
        if project_id:
            conn = self.get_connection()
            c = conn.cursor()
            row = c.execute(
                """SELECT draft_path
                   FROM documents
                   WHERE project_id=? AND doc_type=?
                   ORDER BY updated_at DESC, id DESC
                   LIMIT 1""",
                (project_id, "Смета (приложение № 1)"),
            ).fetchone()
            conn.close()
            if row:
                draft_path = row["draft_path"] or ""
                if draft_path and os.path.exists(draft_path):
                    return draft_path

        search_names = set()
        if project_name:
            search_names.add(f"{self.sanitize_filename(project_name, 'Черновик сметы')}.json")
            search_names.add(f"{project_name}.json")

        drafts_dir = os.path.join(self.get_workspace_dir(), "Сметы", "Черновики")
        if os.path.isdir(drafts_dir):
            if search_names:
                for candidate in search_names:
                    candidate_path = os.path.join(drafts_dir, candidate)
                    if os.path.exists(candidate_path):
                        return candidate_path
            generic_path = os.path.join(drafts_dir, "Черновик сметы.json")
            if os.path.exists(generic_path):
                return generic_path
        return None

    def normalize_contract_settings(self, settings):
        normalized = dict(settings or {})
        payments = normalized.get("payments")
        if isinstance(payments, list):
            clean_payments = []
            for item in payments:
                if not isinstance(item, dict):
                    continue
                payment_date = str(item.get("date", "")).strip()
                payment_amount = str(item.get("amount", "")).strip()
                if payment_date or payment_amount:
                    clean_payments.append({"date": payment_date, "amount": payment_amount})
            normalized["payments"] = clean_payments
        else:
            legacy_payments = []
            for index in range(1, 4):
                payment_date = str(normalized.get(f"payment_{index}_date", "")).strip()
                payment_amount = str(normalized.get(f"payment_{index}_amount", "")).strip()
                if payment_date or payment_amount:
                    legacy_payments.append({"date": payment_date, "amount": payment_amount})
            normalized["payments"] = legacy_payments
        return normalized

    def compose_smeta_contract_label(self, contract_number, contract_date):
        number = str(contract_number or "").strip()
        date_text = self.format_long_date(contract_date)
        if number and not number.startswith("№"):
            number = f"№{number}"
        if number and date_text:
            return f"{number} от {date_text}"
        return number or date_text

    def build_default_payment_schedule(self):
        return [{"date": "", "amount": ""}, {"date": "", "amount": ""}]

    def get_default_contract_settings(self, project_row=None, counterparty_row=None):
        project_name = ""
        contract_number = ""
        contract_date = ""
        customer_email = ""
        customer_name = ""
        passport_series_number = ""
        passport_issued_by = ""
        passport_department_code = ""
        registration_address = ""
        work_address = ""
        phone = ""
        project_id = project_row["id"] if project_row and "id" in project_row.keys() else None
        if project_row:
            project_name = project_row["project_name"] or project_row["address"] or ""
            contract_number = project_row["contract"] or ""
            contract_date = project_row["date"] or ""
            customer_name = project_row["customer"] or ""
        if counterparty_row:
            display_name = self.get_counterparty_display_name(counterparty_row)
            customer_email = counterparty_row["email"] or ""
            customer_name = display_name or customer_name
            passport_series_number = counterparty_row["passport_series_number"] or ""
            passport_issued_by = counterparty_row["passport_issued_by"] or ""
            passport_department_code = counterparty_row["passport_department_code"] or ""
            registration_address = counterparty_row["registration_address"] or counterparty_row["legal_address"] or ""
            work_address = counterparty_row["work_address"] or project_name
            phone = counterparty_row["phone"] or ""
        smeta_total = self.get_project_smeta_total(project_id) if project_id else None
        return {
            "contract_variant": "physical",
            "contractor_mode": "ooo",
            "contract_number": contract_number.replace("№", "").split(" от ")[0].strip() if contract_number else "",
            "contract_date": contract_date,
            "customer_gender": "auto",
            "customer_name": customer_name,
            "passport_series_number": passport_series_number,
            "passport_issued_by": passport_issued_by,
            "passport_department_code": passport_department_code,
            "registration_address": registration_address,
            "customer_phone": phone,
            "customer_email": customer_email,
            "object_address": work_address or project_name,
            "work_end_date": "",
            "price_total": self.format_money_value(smeta_total) if smeta_total is not None else "",
            "advance_amount": "",
            "final_payment_amount": "",
            "payments": self.build_default_payment_schedule(),
            "working_group_text": "",
            "materials_mode": "customer",
            "intro_override": "",
            "payments_override": "",
            "communications_override": "",
        }

    def load_contract_settings(self, project_row, counterparty_row=None):
        settings = self.get_default_contract_settings(project_row, counterparty_row)
        raw_settings = project_row["contract_settings_json"] if "contract_settings_json" in project_row.keys() else ""
        if raw_settings:
            try:
                settings.update(json.loads(raw_settings))
            except json.JSONDecodeError:
                pass
        settings = self.normalize_contract_settings(settings)
        if not settings.get("payments"):
            settings["payments"] = self.build_default_payment_schedule()
        return settings

    def save_contract_settings(self, project_id, settings):
        settings = self.normalize_contract_settings(settings)
        contract_number = settings.get("contract_number", "")
        contract_date = settings.get("contract_date", "")
        smeta_contract = self.compose_smeta_contract_label(contract_number, contract_date)
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE projects SET contract_settings_json=?, contract=?, date=?, updated_at=? WHERE id=?",
            (
                json.dumps(settings, ensure_ascii=False),
                smeta_contract,
                contract_date,
                datetime.datetime.now().isoformat(timespec="seconds"),
                project_id,
            ),
        )
        conn.commit()
        conn.close()

    def build_customer_intro(self, counterparty_row, settings):
        intro_override = str(settings.get("intro_override", "")).strip()
        if intro_override:
            return intro_override
        counterparty_type = counterparty_row["type"] if counterparty_row else ""
        display_name = str(settings.get("customer_name") or (self.get_counterparty_display_name(counterparty_row) if counterparty_row else "") or "Заказчик").strip()
        contractor_mode = settings.get("contractor_mode", "ooo")
        if contractor_mode == "ip":
            contractor_intro = (
                "Индивидуальный предприниматель Гордеев Алексей Николаевич, именуемый в дальнейшем "
                "«Подрядчик», с одной стороны, "
            )
        else:
            contractor_intro = (
                "Общество с ограниченной ответственностью «ДекорАртСтрой» именуемое в дальнейшем "
                "«Подрядчик», в лице Генерального директора Шарипова Шехрозжона Шавкатовича, "
                "действующего на основании Устава с одной стороны, "
            )
        if counterparty_type == "Физическое лицо":
            gender = settings.get("customer_gender", "auto")
            if gender == "auto":
                gender = self.detect_customer_gender(display_name)
            if gender == "female":
                customer_intro = f"и гражданка {display_name}, именуемая в дальнейшем «Заказчик», "
            elif gender == "male":
                customer_intro = f"и гражданин {display_name}, именуемый в дальнейшем «Заказчик», "
            else:
                customer_intro = f"и гражданин(ка) {display_name}, именуемый(ая) в дальнейшем «Заказчик», "
            return contractor_intro + customer_intro + "вместе именуемые «Стороны», заключили настоящий договор (далее – «Договор») о нижеследующем:"
        if counterparty_type == "Юридическое лицо ООО":
            company_name = counterparty_row["company_name"] or display_name
            director_name = counterparty_row["director_name"] or "уполномоченного представителя"
            director_basis = counterparty_row["director_basis"] or "Устава"
            return (
                contractor_intro
                + f"и {company_name}, именуемое в дальнейшем «Заказчик», в лице {director_name}, действующего на основании {director_basis}, "
                "вместе именуемые «Стороны», заключили настоящий договор (далее – «Договор») о нижеследующем:"
            )
        company_name = counterparty_row["company_name"] or display_name
        return (
            contractor_intro
            + f"и Индивидуальный предприниматель {company_name}, именуемый в дальнейшем «Заказчик», вместе именуемые «Стороны», заключили настоящий договор (далее – «Договор») о нижеследующем:"
        )

    def build_customer_contract_clause(self, counterparty_row, settings):
        display_name = str(settings.get("customer_name") or (self.get_counterparty_display_name(counterparty_row) if counterparty_row else "") or "Заказчик").strip()
        gender = settings.get("customer_gender", "auto")
        if gender == "auto":
            gender = self.detect_customer_gender(display_name)
        if gender == "female":
            return f"и гражданка {display_name}, именуемая в дальнейшем «Заказчик»,"
        if gender == "male":
            return f"и гражданин {display_name}, именуемый в дальнейшем «Заказчик»,"
        return f"и гражданин(ка) {display_name}, именуемый(ая) в дальнейшем «Заказчик»,"

    def build_payment_line(self, payment, index):
        if not payment:
            return ""
        payment_date = self.format_long_date(payment.get("date", ""), fallback=f"дата платежа {index}")
        payment_amount = self.format_money_with_words(payment.get("amount", "")) or "0 (ноль) рублей 00 копеек"
        return (
            f"4.4.{index}. В срок не позднее «{payment_date}» «Заказчик» выплачивает «Подрядчику» денежные средства "
            f"в размере {payment_amount}, НДС не облагается."
        )

    def build_dynamic_payment_block(self, settings):
        override = str(settings.get("payments_override", "")).strip()
        if override:
            return override.replace("\n", "\r")
        payments = settings.get("payments") or []
        lines = []
        for index, payment in enumerate(payments, start=1):
            payment_date = self.format_long_date(payment.get("date", ""), fallback=f"дата платежа {index}")
            payment_amount = self.format_money_with_words(payment.get("amount", "")) or "0 (ноль) рублей 00 копеек"
            lines.append(
                f"4.4.{index}. В срок не позднее «{payment_date}» «Заказчик» выплачивает «Подрядчику» денежные средства "
                f"в размере {payment_amount}, НДС не облагается."
            )
        return "\r".join(lines)

    def build_payment_lines_for_template(self, settings):
        payments = settings.get("payments") or []
        if not payments:
            return "", "", ""
        line_1 = self.build_payment_line(payments[0], 1) if len(payments) > 0 else ""
        line_2 = self.build_payment_line(payments[1], 2) if len(payments) > 1 else ""
        tail_lines = []
        for index, payment in enumerate(payments[2:], start=3):
            line = self.build_payment_line(payment, index)
            if line:
                tail_lines.append(line)
        line_3_plus = "\r".join(tail_lines)
        return line_1, line_2, line_3_plus

    def build_communications_block(self, settings):
        override = str(settings.get("communications_override", "")).strip()
        if override:
            return override.replace("\n", "\r")
        customer_email = settings.get("customer_email", "").strip() or "не указан"
        contractor_email = settings.get("contractor_email", "").strip() or self.get_executor_profile(settings.get("contractor_mode", "ooo"))["email"]
        working_group_text = settings.get("working_group_text", "").strip()
        lines = [
            "8.1. Стороны пришли к соглашению об использовании в рамках настоящего Договора следующих адресов электронной почты:",
            f"Заказчик: {customer_email},",
            f"Подрядчик: {contractor_email} ,",
        ]
        if working_group_text:
            lines.append(working_group_text)
        lines.append(
            "С подписанием настоящего Договора, Стороны признают, что направление уведомления и (или) сообщения, связанных с исполнением настоящего Договора, "
            "по адресам электронной почты указанных в настоящем пункте, считается надлежащим уведомлением сторон. Датой получения уведомления и (или) сообщения "
            "Стороной настоящего Договора, будет считаться день, следующий за днем направления исходящего письма другой Стороны с адреса электронной почты указанного "
            "в настоящем пункте Договора. При исполнении Договора Стороны обязуются надлежащим образом обеспечивать режим доступа к указанным адресам электронной почты. "
            "Сторона, не обеспечившая режим доступа к адресу электронной почты, указанной в настоящем пункте Договора, самостоятельно несет риск наступления неблагоприятных последствий, связанных с исполнением указанной обязанности."
        )
        return "\r".join(lines)

    def build_contract_replacements(self, project_row, counterparty_row, contract_settings=None):
        project_name = project_row["project_name"] or project_row["address"] or ""
        settings = self.get_default_contract_settings(project_row, counterparty_row)
        if contract_settings:
            settings.update(contract_settings)
        settings = self.normalize_contract_settings(settings)
        executor_profile = self.get_executor_profile(settings.get("contractor_mode", "ooo"))
        contract_number = settings.get("contract_number") or project_row["contract"] or "б/н"
        contract_date = self.format_contract_date(settings.get("contract_date") or project_row["date"])
        counterparty_name = self.get_counterparty_display_name(counterparty_row) if counterparty_row else ""
        customer_name = settings.get("customer_name") or counterparty_name or project_row["customer"] or "Заказчик"

        if counterparty_row and counterparty_row["type"] == "Физическое лицо":
            passport_main = settings.get("passport_series_number") or counterparty_row["passport_series_number"] or "не указано"
            issued_by = settings.get("passport_issued_by") or counterparty_row["passport_issued_by"] or "не указано"
            department_code = settings.get("passport_department_code") or counterparty_row["passport_department_code"] or "не указано"
            registration_address = settings.get("registration_address") or counterparty_row["registration_address"] or "не указано"
            work_address = settings.get("object_address") or counterparty_row["work_address"] or project_name or registration_address
            phone = settings.get("customer_phone") or counterparty_row["phone"] or "не указан"
            email = settings.get("customer_email") or counterparty_row["email"] or "не указан"
        elif counterparty_row and counterparty_row["type"] == "Юридическое лицо ООО":
            passport_main = counterparty_row["inn"] or "не указано"
            issued_by = " / ".join(part for part in [counterparty_row["kpp"], counterparty_row["ogrn"]] if part) or "не указано"
            department_code = " / ".join(part for part in [counterparty_row["bank_name"], counterparty_row["bank_bik"]] if part) or "не указано"
            registration_address = counterparty_row["legal_address"] or "не указано"
            work_address = settings.get("object_address") or counterparty_row["work_address"] or project_name or registration_address
            phone = settings.get("customer_phone") or counterparty_row["phone"] or "не указан"
            email = settings.get("customer_email") or counterparty_row["email"] or "не указан"
        else:
            passport_main = counterparty_row["inn"] if counterparty_row else "не указано"
            issued_by = counterparty_row["ogrnip"] if counterparty_row else "не указано"
            department_code = " / ".join(
                part for part in [
                    counterparty_row["bank_name"] if counterparty_row else "",
                    counterparty_row["bank_bik"] if counterparty_row else "",
                ]
                if part
            ) or "не указано"
            registration_address = settings.get("registration_address") or (counterparty_row["legal_address"] if counterparty_row else "") or "не указано"
            work_address = settings.get("object_address") or (counterparty_row["work_address"] if counterparty_row else "") or project_name or registration_address
            phone = settings.get("customer_phone") or (counterparty_row["phone"] if counterparty_row else "") or "не указан"
            email = settings.get("customer_email") or (counterparty_row["email"] if counterparty_row else "") or "не указан"

        object_address = settings.get("object_address") or project_name or "не указано"
        work_end_date = self.format_deadline_text(settings.get("work_end_date"))
        smeta_total = self.get_project_smeta_total(project_row["id"]) if project_row and "id" in project_row.keys() else None
        price_total_value = self.parse_money_value(settings.get("price_total"))
        if price_total_value is None and smeta_total is not None:
            price_total_value = smeta_total
        advance_value = self.parse_money_value(settings.get("advance_amount")) or 0.0
        payment_values = []
        for payment in settings.get("payments", []):
            payment_amount = self.parse_money_value(payment.get("amount"))
            if payment_amount is not None:
                payment_values.append(payment_amount)
        computed_final = None
        if price_total_value is not None:
            computed_final = round(price_total_value - advance_value - sum(payment_values), 2)
        final_payment_value = self.parse_money_value(settings.get("final_payment_amount"))
        if final_payment_value is None:
            final_payment_value = computed_final

        price_total = self.format_money_with_words(price_total_value) if price_total_value is not None else ""
        advance_amount = self.format_money_with_words(advance_value)
        final_payment_amount = self.format_money_with_words(final_payment_value) if final_payment_value is not None else ""

        materials_mode = settings.get("materials_mode", "customer")
        materials_phrase = "выполняются из материалов, предоставляемых «Заказчиком»" if materials_mode == "customer" else "выполняются с возможностью закупки материалов «Подрядчиком» по согласованию с «Заказчиком»"
        payment_1_line, payment_2_line, payment_3_line = self.build_payment_lines_for_template(settings)

        replacements = {
            "[[CONTRACT_NUMBER]]": f"ДОГОВОР № {contract_number}",
            "[[CONTRACT_DATE]]": contract_date,
            "[[CUSTOMER_CLAUSE]]": self.build_customer_contract_clause(counterparty_row, settings),
            "[[CUSTOMER_NAME]]": customer_name,
            "[[OBJECT_ADDRESS]]": object_address,
            "[[PASSPORT]]": passport_main,
            "[[PASSPORT_ISSUED_BY]]": issued_by,
            "[[PASSPORT_CODE]]": department_code,
            "[[REGISTRATION_ADDRESS]]": registration_address,
            "[[WORK_ADDRESS]]": work_address,
            "[[CUSTOMER_PHONE]]": phone,
            "[[CUSTOMER_EMAIL]]": email,
            "[[WORK_END_DATE]]": work_end_date,
            "[[PRICE_TOTAL]]": price_total,
            "[[FINAL_PAYMENT]]": final_payment_amount,
            "[[ADVANCE_PAYMENT_LINE]]": f"В день подписания настоящего Договора «Заказчик» выплачивает «Подрядчику» авансовый платеж в размере {advance_amount}, НДС не облагается.",
            "[[PAYMENT_LINE_1]]": payment_1_line,
            "[[PAYMENT_LINE_2]]": payment_2_line,
            "[[PAYMENT_LINE_3_PLUS]]": payment_3_line,
            "[[CONTRACTOR_EMAIL]]": settings.get('contractor_email') or executor_profile['email'],
            "[[WORKING_GROUP_TEXT]]": settings.get("working_group_text", "").strip(),
            "Работы, предусмотренные настоящим Договором, выполняются из материалов, предоставляемых «Заказчиком» (давальческий материал) до начала выполнения Работ.": f"Работы, предусмотренные настоящим Договором, {materials_phrase} (давальческий материал) до начала выполнения Работ." if materials_mode == "customer" else f"Работы, предусмотренные настоящим Договором, {materials_phrase}.",
        }
        return {key: value for key, value in replacements.items() if value}

    def upsert_project_document(self, project_id, doc_type, title, file_path, status="Черновик"):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = self.get_connection()
        c = conn.cursor()
        existing = c.execute(
            """SELECT id
               FROM documents
               WHERE project_id=? AND doc_type=?
               ORDER BY updated_at DESC, id DESC
               LIMIT 1""",
            (project_id, doc_type),
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE documents SET title=?, status=?, file_path=?, updated_at=? WHERE id=?",
                (title, status, file_path, now, existing["id"]),
            )
        else:
            c.execute(
                """INSERT INTO documents
                   (project_id, doc_type, title, status, file_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, doc_type, title, status, file_path, now, now),
            )
        conn.commit()
        conn.close()
        self.log_project_event(project_id, "document", f"Обновлен документ: {title} [{status}]")

    def generate_contract_for_project(self, project_id, project_window=None):
        if not os.path.exists(CONTRACT_TEMPLATE_PATH):
            return messagebox.showerror("Шаблон не найден", f"Не найден файл шаблона договора:\n{CONTRACT_TEMPLATE_PATH}")

        conn = self.get_connection()
        c = conn.cursor()
        project_row = c.execute(
            """SELECT p.*,
                      cp.*
               FROM projects p
               LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
               WHERE p.id=?""",
            (project_id,),
        ).fetchone()
        conn.close()
        if project_row is None:
            return messagebox.showwarning("Проект не найден", "Не удалось найти данные проекта для генерации договора.")

        project_name = project_row["project_name"] or project_row["address"] or f"Проект_{project_id}"
        contract_settings = self.load_contract_settings(project_row, project_row)
        contract_number = contract_settings.get("contract_number") or project_row["contract"] or f"Договор_{project_id}"
        output_dir = self.get_contracts_dir(project_name)
        output_name = f"{self.sanitize_filename(contract_number, 'Договор')}.docx"
        output_path = os.path.join(output_dir, output_name)
        replacements = self.build_contract_replacements(project_row, project_row, contract_settings)

        temp_root = os.path.join(self.get_workspace_dir(), "_contract_tmp")
        os.makedirs(temp_root, exist_ok=True)
        temp_dir = os.path.join(temp_root, f"job_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
        os.makedirs(temp_dir, exist_ok=True)
        replacements_path = os.path.join(temp_dir, "replacements.json")
        script_path = os.path.join(temp_dir, "generate_contract.ps1")
        log_path = os.path.join(temp_dir, "word_generation.log")
        try:
            with open(replacements_path, "w", encoding="utf-8-sig") as f:
                json.dump(replacements, f, ensure_ascii=False)
            script_content = r"""
$templatePath = $args[0]
$outputPath = $args[1]
$replacementsPath = $args[2]
$logPath = $args[3]
$word = $null
$doc = $null
function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Value "$stamp $Message" -Encoding UTF8
}
try {
    Write-Log "Start Word automation"
    $word = New-Object -ComObject Word.Application
    Write-Log "Word COM object created"
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($templatePath, $false, $true)
    Write-Log "Template opened"
    $replacements = Get-Content -LiteralPath $replacementsPath -Raw | ConvertFrom-Json
    Write-Log ("Loaded replacements: " + $replacements.PSObject.Properties.Count)
    foreach ($item in $replacements.PSObject.Properties) {
        Write-Log ("Replacing key length=" + $item.Name.Length + " value length=" + [string]$item.Value.Length + " key=" + $item.Name)
        $range = $doc.Content
        $find = $range.Find
        $find.ClearFormatting()
        $find.Replacement.ClearFormatting()
        [void]$find.Execute($item.Name, $false, $false, $false, $false, $false, $true, 1, $false, $item.Value, 2)
    }
    Write-Log "Replacements complete"
    $formatDocx = 16
    $doc.SaveAs([ref]$outputPath, [ref]$formatDocx)
    Write-Log "Document saved"
}
catch {
    Write-Log ("ERROR: " + $_.Exception.Message)
    throw
}
finally {
    Write-Log "Cleanup start"
    if ($doc -ne $null) { $doc.Close([ref]$false) | Out-Null }
    if ($word -ne $null) { $word.Quit() | Out-Null }
    Write-Log "Cleanup end"
}
"""
            with open(script_path, "w", encoding="utf-8-sig") as f:
                f.write(script_content)

            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        script_path,
                        CONTRACT_TEMPLATE_PATH,
                        output_path,
                        replacements_path,
                        log_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
            except subprocess.TimeoutExpired:
                details = f"Превышено время ожидания Word/PowerShell (90 сек).\nЛог: {log_path}"
                if os.path.exists(log_path):
                    try:
                        with open(log_path, "r", encoding="utf-8", errors="replace") as log_file:
                            log_text = log_file.read().strip()
                        if log_text:
                            details += f"\n\nПоследние шаги:\n{log_text}"
                    except OSError:
                        pass
                return messagebox.showerror("Таймаут генерации", details)
        finally:
            pass

        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip() or "Неизвестная ошибка Word/PowerShell."
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as log_file:
                        log_text = log_file.read().strip()
                    if log_text:
                        details += f"\n\nЛог Word:\n{log_text}"
                except OSError:
                    pass
            return messagebox.showerror("Ошибка", f"Не удалось сформировать договор:\n{details}")

        title = f"Договор - {project_name}"
        self.upsert_project_document(project_id, "Договор", title, output_path, status="Черновик")
        if project_window is not None and project_window.winfo_exists():
            project_window.destroy()
        messagebox.showinfo(
            "Договор сформирован",
            "Базовый договор сформирован успешно.\n\n"
            "Сейчас в документ автоматически подставляются реквизиты клиента, номер и дата договора, "
            "адрес объекта и контактные данные.\n"
            f"\nФайл:\n{output_path}",
        )
        self.refresh_projects()

    def open_contract_settings_window(self, project_id, project_window=None):
        conn = self.get_connection()
        c = conn.cursor()
        project_row = c.execute(
            """SELECT p.*,
                      cp.*
               FROM projects p
               LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
               WHERE p.id=?""",
            (project_id,),
        ).fetchone()
        conn.close()
        if project_row is None:
            return messagebox.showwarning("Проект не найден", "Не удалось найти проект для настройки договора.")

        settings = self.load_contract_settings(project_row, project_row)
        win = ctk.CTkToplevel(self)
        win.title("Настройки договора")
        win.geometry("920x900")
        win.attributes("-topmost", True)
        self.present_window(win)

        scroll = ctk.CTkScrollableFrame(win, width=860, height=760)
        scroll.pack(fill="both", expand=True, padx=18, pady=(18, 0))

        ctk.CTkLabel(scroll, text="Физическое лицо: настройки договора", font=("Segoe UI Semibold", 18)).pack(anchor="w", pady=(4, 10))
        ctk.CTkLabel(
            scroll,
            text="Все ключевые поля можно исправить вручную. Если поле не менять, CRM подставит данные из карточки клиента и проекта.",
            font=("Segoe UI", 11),
            text_color="#5f7288",
        ).pack(anchor="w", pady=(0, 10))

        field_specs = [
            ("contract_number", "Номер договора"),
            ("contract_date", "Дата договора"),
            ("customer_name", "ФИО заказчика"),
            ("object_address", "Адрес объекта"),
            ("work_end_date", "Дата окончания работ"),
            ("price_total", "Сумма по смете"),
            ("advance_amount", "Авансовый платёж"),
            ("final_payment_amount", "Окончательный расчёт (если нужно вручную)"),
            ("customer_email", "E-mail заказчика"),
            ("customer_phone", "Телефон заказчика"),
            ("passport_series_number", "Паспорт"),
            ("passport_issued_by", "Кем и когда выдан"),
            ("passport_department_code", "Код подразделения"),
            ("registration_address", "Адрес регистрации"),
            ("working_group_text", "Пункт 8.1: рабочая группа"),
        ]
        field_widgets = {}
        for key, label in field_specs:
            ctk.CTkLabel(scroll, text=label).pack(anchor="w", pady=(10, 4))
            entry = ctk.CTkEntry(scroll, width=760)
            entry.pack(fill="x")
            entry.insert(0, settings.get(key, ""))
            field_widgets[key] = entry

        finance_frame = ctk.CTkFrame(scroll)
        finance_frame.pack(fill="x", pady=(18, 8))
        ctk.CTkLabel(finance_frame, text="Финансовый блок", font=("Segoe UI Semibold", 15)).pack(anchor="w", padx=14, pady=(12, 8))
        ctk.CTkLabel(
            finance_frame,
            text="Сумма договора может подтягиваться из согласованной сметы. Окончательный расчёт считается как сумма по смете минус аванс и все последующие платежи.",
            font=("Segoe UI", 11),
            text_color="#5f7288",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        finance_actions = ctk.CTkFrame(finance_frame, fg_color="transparent")
        finance_actions.pack(fill="x", padx=14, pady=(0, 8))
        finance_summary_var = ctk.StringVar(value="")
        finance_summary_label = ctk.CTkLabel(finance_frame, textvariable=finance_summary_var, font=("Segoe UI Semibold", 12), text_color="#1d2b3a")
        finance_summary_label.pack(anchor="w", padx=14, pady=(0, 12))

        options_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        options_frame.pack(fill="x", pady=(12, 6))

        ctk.CTkLabel(options_frame, text="Род заказчика").grid(row=0, column=0, sticky="w", pady=(0, 4))
        gender_var = ctk.StringVar(value=settings.get("customer_gender", "auto"))
        ctk.CTkOptionMenu(options_frame, variable=gender_var, values=["auto", "male", "female"], width=220).grid(row=1, column=0, sticky="w")

        ctk.CTkLabel(options_frame, text="Исполнитель").grid(row=0, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        contractor_var = ctk.StringVar(value=settings.get("contractor_mode", "ooo"))
        ctk.CTkOptionMenu(options_frame, variable=contractor_var, values=["ooo", "ip"], width=220).grid(row=1, column=1, sticky="w", padx=(24, 0))

        ctk.CTkLabel(options_frame, text="Материалы").grid(row=0, column=2, sticky="w", padx=(24, 0), pady=(0, 4))
        materials_var = ctk.StringVar(value=settings.get("materials_mode", "customer"))
        ctk.CTkOptionMenu(options_frame, variable=materials_var, values=["customer", "contractor"], width=220).grid(row=1, column=2, sticky="w", padx=(24, 0))

        ctk.CTkLabel(scroll, text="E-mail исполнителя").pack(anchor="w", pady=(10, 4))
        contractor_email_entry = ctk.CTkEntry(scroll, width=760)
        contractor_email_entry.pack(fill="x")
        contractor_email_entry.insert(0, settings.get("contractor_email") or self.get_executor_profile(contractor_var.get())["email"])

        payments_frame = ctk.CTkFrame(scroll)
        payments_frame.pack(fill="x", pady=(18, 6))
        ctk.CTkLabel(payments_frame, text="График последующих платежей", font=("Segoe UI Semibold", 15)).pack(anchor="w", padx=14, pady=(12, 8))
        ctk.CTkLabel(
            payments_frame,
            text="Добавляйте 2, 3, 4 и более платежей. CRM считает окончательный расчёт как сумма по смете минус аванс и все последующие платежи.",
            font=("Segoe UI", 11),
            text_color="#5f7288",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        payments_rows_frame = ctk.CTkFrame(payments_frame, fg_color="transparent")
        payments_rows_frame.pack(fill="x", padx=14, pady=(0, 10))
        payment_rows = []

        def refresh_contractor_email(*_args):
            current = contractor_email_entry.get().strip()
            if current in ("", "info@dekorartstroy.ru", "gorodok198@yandex.ru"):
                contractor_email_entry.delete(0, "end")
                contractor_email_entry.insert(0, self.get_executor_profile(contractor_var.get())["email"])

        contractor_var.trace_add("write", refresh_contractor_email)

        last_auto_final = {"value": ""}

        def compute_financials():
            total_value = self.parse_money_value(field_widgets["price_total"].get())
            advance_value = self.parse_money_value(field_widgets["advance_amount"].get()) or 0.0
            payments_total = 0.0
            filled_payments = 0
            for row_info in payment_rows:
                payment_amount = self.parse_money_value(row_info["amount"].get())
                if payment_amount is not None:
                    payments_total += payment_amount
                    filled_payments += 1
            final_value = None
            if total_value is not None:
                final_value = round(total_value - advance_value - payments_total, 2)
            return total_value, advance_value, payments_total, final_value, filled_payments

        def refresh_finance_summary(*_args):
            total_value, advance_value, payments_total, final_value, filled_payments = compute_financials()
            total_text = self.format_money_value(total_value) if total_value is not None else "не указана"
            advance_text = self.format_money_value(advance_value)
            payments_text = self.format_money_value(payments_total)
            final_text = self.format_money_value(final_value) if final_value is not None else "не рассчитан"
            current_final_text = field_widgets["final_payment_amount"].get().strip()
            auto_final_text = self.format_money_value(final_value) if final_value is not None else ""
            if auto_final_text and (not current_final_text or current_final_text == last_auto_final["value"]):
                field_widgets["final_payment_amount"].delete(0, "end")
                field_widgets["final_payment_amount"].insert(0, auto_final_text)
                current_final_text = auto_final_text
            last_auto_final["value"] = auto_final_text
            finance_summary_var.set(
                f"Смета: {total_text}   |   Аванс: {advance_text}   |   Платежей: {filled_payments} на {payments_text}   |   Остаток: {final_text}"
            )

        def pull_sum_from_smeta():
            smeta_total = self.get_project_smeta_total(project_id)
            if smeta_total is None:
                draft_path = self.get_project_smeta_draft_path(project_id, project_row["project_name"] or project_row["address"] or "")
                details = "Для этого проекта пока не найден сохранённый черновик сметы, из которого можно взять итоговую сумму."
                if draft_path:
                    details += f"\n\nНайден файл черновика, но итог не удалось прочитать:\n{draft_path}"
                return messagebox.showinfo("Смета", details)
            field_widgets["price_total"].delete(0, "end")
            field_widgets["price_total"].insert(0, self.format_money_value(smeta_total))
            refresh_finance_summary()

        ctk.CTkButton(
            finance_actions,
            text="Подтянуть сумму из сметы",
            command=pull_sum_from_smeta,
            fg_color="#1f538d",
        ).pack(side="left")

        ctk.CTkButton(
            finance_actions,
            text="Пересчитать остаток",
            command=refresh_finance_summary,
            fg_color="#4a6572",
        ).pack(side="left", padx=(8, 0))

        def add_payment_row(date_value="", amount_value=""):
            row_frame = ctk.CTkFrame(payments_rows_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)
            date_entry = ctk.CTkEntry(row_frame, width=280, placeholder_text="Дата платежа")
            date_entry.pack(side="left", padx=(0, 8))
            amount_entry = ctk.CTkEntry(row_frame, width=220, placeholder_text="Сумма платежа")
            amount_entry.pack(side="left", padx=(0, 8))
            if date_value:
                date_entry.insert(0, date_value)
            if amount_value:
                amount_entry.insert(0, amount_value)

            amount_entry.bind("<KeyRelease>", refresh_finance_summary)
            date_entry.bind("<KeyRelease>", refresh_finance_summary)

            row_info = {"frame": row_frame, "date": date_entry, "amount": amount_entry}
            payment_rows.append(row_info)

            def remove_row():
                if row_info in payment_rows:
                    payment_rows.remove(row_info)
                row_frame.destroy()
                refresh_finance_summary()

            ctk.CTkButton(row_frame, text="Удалить", width=110, fg_color="#b63f3b", hover_color="#99312d", command=remove_row).pack(side="left")

        for payment in settings.get("payments") or self.build_default_payment_schedule():
            add_payment_row(payment.get("date", ""), payment.get("amount", ""))

        for watched_key in ("price_total", "advance_amount", "final_payment_amount", "contract_number", "contract_date"):
            field_widgets[watched_key].bind("<KeyRelease>", refresh_finance_summary)

        ctk.CTkButton(payments_frame, text="+ Добавить платеж", command=lambda: add_payment_row(), fg_color="#1f538d").pack(anchor="w", padx=14, pady=(0, 12))

        ctk.CTkLabel(scroll, text="Ручная правка вводного абзаца", font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(14, 4))
        intro_box = ctk.CTkTextbox(scroll, height=90)
        intro_box.pack(fill="x")
        intro_box.insert("1.0", settings.get("intro_override", ""))

        ctk.CTkLabel(scroll, text="Ручная правка блока платежей", font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(14, 4))
        payments_box = ctk.CTkTextbox(scroll, height=110)
        payments_box.pack(fill="x")
        payments_box.insert("1.0", settings.get("payments_override", ""))

        ctk.CTkLabel(scroll, text="Ручная правка пункта 8.1", font=("Segoe UI Semibold", 14)).pack(anchor="w", pady=(14, 4))
        communications_box = ctk.CTkTextbox(scroll, height=120)
        communications_box.pack(fill="x")
        communications_box.insert("1.0", settings.get("communications_override", ""))
        refresh_finance_summary()

        buttons = ctk.CTkFrame(win)
        buttons.pack(fill="x", padx=18, pady=18)

        def save_settings(generate_after=False):
            new_settings = {key: widget.get().strip() for key, widget in field_widgets.items()}
            payments = []
            for row_info in payment_rows:
                payment_date = row_info["date"].get().strip()
                payment_amount = row_info["amount"].get().strip()
                if payment_date or payment_amount:
                    payments.append({"date": payment_date, "amount": payment_amount})
            new_settings["payments"] = payments
            _, _, _, final_value, _ = compute_financials()
            if not new_settings.get("final_payment_amount") and final_value is not None:
                new_settings["final_payment_amount"] = self.format_money_value(final_value)
            new_settings["customer_gender"] = gender_var.get()
            new_settings["contractor_mode"] = contractor_var.get()
            new_settings["contractor_email"] = contractor_email_entry.get().strip() or self.get_executor_profile(contractor_var.get())["email"]
            new_settings["materials_mode"] = materials_var.get()
            new_settings["intro_override"] = intro_box.get("1.0", "end").strip()
            new_settings["payments_override"] = payments_box.get("1.0", "end").strip()
            new_settings["communications_override"] = communications_box.get("1.0", "end").strip()
            self.save_contract_settings(project_id, new_settings)
            win.destroy()
            if generate_after:
                self.generate_contract_for_project(project_id, project_window)
            elif project_window is not None and project_window.winfo_exists():
                project_window.destroy()
                self.open_project_card()

        ctk.CTkButton(buttons, text="Отмена", command=win.destroy, fg_color="#5a5a5a").pack(side="left")
        ctk.CTkButton(buttons, text="Сохранить", command=save_settings, fg_color="#1f538d").pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Сохранить и сформировать", command=lambda: save_settings(True), fg_color="#1f8a43").pack(side="right")

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
                   contract_settings_json TEXT,
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
                   created_by TEXT,
                   created_at TEXT NOT NULL
               )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS project_events (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   project_id INTEGER NOT NULL,
                   event_type TEXT NOT NULL,
                   event_text TEXT NOT NULL,
                   author TEXT,
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
            ("contract_settings_json", "ALTER TABLE projects ADD COLUMN contract_settings_json TEXT"),
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

        cash_columns = {row[1] for row in c.execute("PRAGMA table_info(cash_transactions)").fetchall()}
        if "created_by" not in cash_columns:
            c.execute("ALTER TABLE cash_transactions ADD COLUMN created_by TEXT")

        event_columns = {row[1] for row in c.execute("PRAGMA table_info(project_events)").fetchall()}
        if "author" not in event_columns:
            c.execute("ALTER TABLE project_events ADD COLUMN author TEXT")

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

        self.sidebar = ctk.CTkFrame(shell, width=280, corner_radius=24, fg_color="#171b22")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(20, 12))
        ctk.CTkLabel(brand, text="Dekorartstroy", font=("Segoe UI Semibold", 21), text_color="#f8fbff").pack(anchor="w")
        ctk.CTkLabel(brand, text="Объекты и сметы", font=("Segoe UI", 12), text_color="#9faec0").pack(anchor="w", pady=(4, 0))

        object_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        object_header.pack(fill="x", padx=14, pady=(4, 8))
        ctk.CTkLabel(object_header, text="МОИ ОБЪЕКТЫ", font=("Segoe UI Semibold", 11), text_color="#7f92a9").pack(side="left")
        ctk.CTkButton(
            object_header,
            text="+",
            width=28,
            height=28,
            corner_radius=10,
            fg_color="#1f8fff",
            hover_color="#1873cf",
            command=self.open_add_project_window,
        ).pack(side="right")

        self.sidebar_project_caption = ctk.StringVar(value="Выбери объект слева, чтобы открыть карточку проекта.")
        self.sidebar_project_list = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#2b3441",
            scrollbar_button_hover_color="#3a4656",
        )
        self.sidebar_project_list.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        sidebar_actions = ctk.CTkFrame(self.sidebar, fg_color="#202733", corner_radius=18)
        sidebar_actions.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(sidebar_actions, text="Быстрые действия", font=("Segoe UI Semibold", 14), text_color="#f8fbff").pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkButton(sidebar_actions, text="+ Новый проект", height=38, fg_color="#1f8fff", hover_color="#1873cf", command=self.open_add_project_window).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="+ Новый контрагент", height=38, fg_color="#35a66f", hover_color="#2a885a", command=self.open_add_counterparty_window).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="Открыть проект", height=38, fg_color="#f0b429", text_color="#233042", hover_color="#d99a11", command=self.open_project_card).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(sidebar_actions, text="Удалить проект", height=38, fg_color="#d9534f", hover_color="#b63f3b", command=self.delete_project).pack(fill="x", padx=12, pady=(6, 14))

        info_block = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        info_block.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(info_block, text="Текущий фокус", font=("Segoe UI Semibold", 12), text_color="#f8fbff").pack(anchor="w")
        ctk.CTkLabel(info_block, textvariable=self.sidebar_project_caption, justify="left", wraplength=220, font=("Segoe UI", 11), text_color="#9faec0").pack(anchor="w", pady=(4, 0))

        self.content = ctk.CTkFrame(shell, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=(18, 0))

        topbar = ctk.CTkFrame(self.content, corner_radius=24, fg_color="#ffffff")
        topbar.pack(fill="x", pady=(0, 14))
        topbar_inner = ctk.CTkFrame(topbar, fg_color="transparent")
        topbar_inner.pack(fill="x", padx=18, pady=14)

        module_bar = ctk.CTkFrame(topbar_inner, fg_color="transparent")
        module_bar.pack(side="left", fill="x", expand=True)
        self.nav_buttons["projects"] = self.create_module_button(module_bar, "Объекты и сметы", lambda: self.show_main_tab("projects"))
        self.nav_buttons["projects"].pack(side="left", padx=(0, 8))
        self.nav_buttons["counterparties"] = self.create_module_button(module_bar, "Контрагенты", lambda: self.show_main_tab("counterparties"))
        self.nav_buttons["counterparties"].pack(side="left", padx=8)
        self.nav_buttons["finance"] = self.create_module_button(module_bar, "Финансы", self.open_finance_window)
        self.nav_buttons["finance"].pack(side="left", padx=8)
        self.nav_buttons["payments"] = self.create_module_button(module_bar, "Платежи", lambda: self.show_placeholder_module("Платежи"))
        self.nav_buttons["payments"].pack(side="left", padx=8)
        self.nav_buttons["purchases"] = self.create_module_button(module_bar, "Закупки", lambda: self.show_placeholder_module("Закупки"))
        self.nav_buttons["purchases"].pack(side="left", padx=8)
        self.nav_buttons["company"] = self.create_module_button(module_bar, "Компания", lambda: self.show_placeholder_module("Компания"))
        self.nav_buttons["company"].pack(side="left", padx=8)

        ctk.CTkLabel(
            topbar_inner,
            text="Единая панель CRM",
            font=("Segoe UI", 12),
            text_color="#6d7b8a",
        ).pack(side="right", padx=(12, 0))
        self.user_badge_var = ctk.StringVar(value=f"Пользователь: {self.current_user}")
        ctk.CTkLabel(
            topbar_inner,
            textvariable=self.user_badge_var,
            font=("Segoe UI Semibold", 12),
            text_color="#1f538d",
        ).pack(side="right", padx=(0, 16))

        hero = ctk.CTkFrame(self.content, corner_radius=24, fg_color="#ffffff")
        hero.pack(fill="x", pady=(0, 16))
        hero_left = ctk.CTkFrame(hero, fg_color="transparent")
        hero_left.pack(side="left", fill="both", expand=True, padx=22, pady=18)
        ctk.CTkLabel(hero_left, text="Центр управления объектами", font=("Segoe UI Semibold", 24), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(hero_left, text="Проекты, сметы, документы и деньги по объектам теперь живут в одной рабочей панели.", font=("Segoe UI", 12), text_color="#5f7288").pack(anchor="w", pady=(6, 0))
        hero_right = ctk.CTkFrame(hero, fg_color="transparent")
        hero_right.pack(side="right", padx=22, pady=18)
        ctk.CTkButton(hero_right, text="+ Проект", width=130, fg_color="#2f80ed", hover_color="#2567bd", command=self.open_add_project_window).pack(side="left", padx=5)
        ctk.CTkButton(hero_right, text="+ Контрагент", width=130, fg_color="#35a66f", hover_color="#2a885a", command=self.open_add_counterparty_window).pack(side="left", padx=5)
        ctk.CTkButton(hero_right, text="Открыть проект", width=140, fg_color="#0f2d52", hover_color="#143b6d", command=self.open_project_card).pack(side="left", padx=5)

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

    def create_module_button(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            height=36,
            corner_radius=14,
            fg_color="#edf2f7",
            hover_color="#d9e6f7",
            text_color="#233042",
            font=("Segoe UI Semibold", 12),
            command=command,
        )

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

    def present_window(self, win, parent=None):
        try:
            if parent is None:
                parent = self
            win.transient(parent)
        except Exception:
            pass
        try:
            win.lift()
            win.focus_force()
            win.attributes("-topmost", True)
            win.after(250, lambda: win.attributes("-topmost", False))
        except Exception:
            pass

    def prompt_user_login(self):
        win = ctk.CTkToplevel(self)
        win.title("Вход в CRM")
        win.geometry("420x220")
        win.resizable(False, False)
        win.grab_set()
        self.present_window(win)

        ctk.CTkLabel(win, text="Кто работает в программе", font=("Segoe UI Semibold", 18)).pack(anchor="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(win, text="Выбор пользователя нужен, чтобы фиксировать автора изменений.", font=("Segoe UI", 12), text_color="#667b90").pack(anchor="w", padx=18, pady=(0, 14))
        user_var = ctk.StringVar(value=self.current_user)
        ctk.CTkOptionMenu(win, variable=user_var, values=AUTH_USERS, width=260).pack(anchor="w", padx=18)

        def confirm():
            self.current_user = user_var.get()
            if hasattr(self, "user_badge_var"):
                self.user_badge_var.set(f"Пользователь: {self.current_user}")
            win.destroy()

        ctk.CTkButton(win, text="Войти", command=confirm, fg_color="#1f8fff", hover_color="#1873cf").pack(anchor="e", padx=18, pady=18)
        self.wait_window(win)

    def show_main_tab(self, tab_name):
        if tab_name == "counterparties":
            self.main_notebook.select(self.counterparties_tab)
        elif tab_name == "projects":
            self.main_notebook.select(self.projects_tab)
        self.current_module = tab_name
        for name, button in self.nav_buttons.items():
            if name == tab_name:
                button.configure(fg_color="#1f8fff", hover_color="#1873cf", text_color="#ffffff")
            else:
                button.configure(fg_color="#edf2f7", hover_color="#d9e6f7", text_color="#233042")

    def show_placeholder_module(self, module_name):
        messagebox.showinfo("Раздел в работе", f"Раздел '{module_name}' будет следующим этапом развития CRM.")

    def get_project_status_colors(self, status):
        palette = {
            "В работе": ("#214a7a", "#d8ebff"),
            "Пауза": ("#6e5412", "#fff0c8"),
            "Завершен": ("#2f5a41", "#d9f7e5"),
        }
        return palette.get(status or "", ("#2d3440", "#d7dde6"))

    def truncate_text(self, value, limit=34):
        text = (value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

    def update_project_focus_panel(self, row):
        if not hasattr(self, "project_focus_title_var"):
            return
        if not row:
            self.project_focus_title_var.set("Объект не выбран")
            self.project_focus_meta_var.set("Выберите проект слева или в таблице, чтобы увидеть сводку.")
            self.project_focus_status_var.set("Статус: —")
            return
        project_name = row[1] or "Без названия"
        counterparty = row[2] or "Контрагент не указан"
        contract = row[3] or "Договор не указан"
        date_value = row[4] or "Дата не указана"
        status = row[5] or "Без статуса"
        self.project_focus_title_var.set(project_name)
        self.project_focus_meta_var.set(f"{counterparty}\n{contract} • {date_value}")
        self.project_focus_status_var.set(f"Статус: {status}")

    def update_project_sidebar_selection(self):
        for project_id, button in self.project_sidebar_buttons.items():
            row = self.project_map.get(project_id)
            status = row[5] if row else ""
            normal_color, text_color = self.get_project_status_colors(status)
            if str(self.selected_project_id) == str(project_id):
                button.configure(fg_color="#1f8fff", hover_color="#1873cf", text_color="#ffffff")
            else:
                button.configure(fg_color=normal_color, hover_color="#2e3744", text_color=text_color)

    def select_project(self, project_id, open_card=False):
        self.selected_project_id = str(project_id)
        if hasattr(self, "projects_tree"):
            for item in self.projects_tree.get_children():
                values = self.projects_tree.item(item, "values")
                if values and str(values[0]) == str(project_id):
                    self.projects_tree.selection_set(item)
                    self.projects_tree.focus(item)
                    self.projects_tree.see(item)
                    break
        row = self.project_map.get(str(project_id))
        if row:
            counterparty = row[2] or "контрагент не указан"
            self.sidebar_project_caption.set(f"{row[1]}\n{counterparty}\nСтатус: {row[5]}")
            self.update_project_focus_panel(row)
        self.update_project_sidebar_selection()
        if open_card:
            self.open_project_card()

    def sync_selected_project_from_table(self, event=None):
        selected = self.projects_tree.selection()
        if not selected:
            return
        project_id = self.projects_tree.item(selected[0], "values")[0]
        self.selected_project_id = str(project_id)
        row = self.project_map.get(str(project_id))
        if row:
            counterparty = row[2] or "контрагент не указан"
            self.sidebar_project_caption.set(f"{row[1]}\n{counterparty}\nСтатус: {row[5]}")
            self.update_project_focus_panel(row)
        self.update_project_sidebar_selection()

    def populate_project_sidebar(self, rows):
        if not hasattr(self, "sidebar_project_list"):
            return
        for child in self.sidebar_project_list.winfo_children():
            child.destroy()
        self.project_sidebar_buttons = {}
        if not rows:
            ctk.CTkLabel(
                self.sidebar_project_list,
                text="Пока нет объектов.\nСоздай первый проект.",
                justify="left",
                text_color="#9faec0",
                font=("Segoe UI", 12),
            ).pack(anchor="w", padx=8, pady=10)
            self.sidebar_project_caption.set("Проекты еще не созданы.")
            return

        for row in rows:
            project_id, project_name, counterparty, contract, date_value, status = row
            status_line = status or "Без статуса"
            sub_line = counterparty or "Контрагент не указан"
            compact_date = date_value or ""
            compact_contract = contract or "Без договора"
            title_line = self.truncate_text(project_name, 26)
            sub_line = self.truncate_text(sub_line, 25)
            meta = " • ".join(part for part in [status_line, compact_contract, compact_date] if part)
            meta = self.truncate_text(meta, 31)
            normal_color, text_color = self.get_project_status_colors(status_line)
            button = ctk.CTkButton(
                self.sidebar_project_list,
                text=f"{title_line}\n{sub_line}\n{meta}",
                anchor="w",
                height=86,
                corner_radius=16,
                fg_color=normal_color,
                hover_color="#2e3744",
                text_color=text_color,
                font=("Segoe UI", 11),
                border_spacing=14,
                command=lambda pid=project_id: self.select_project(pid),
            )
            button.pack(fill="x", padx=2, pady=5)
            self.project_sidebar_buttons[str(project_id)] = button

        current_id = str(self.selected_project_id) if self.selected_project_id else None
        if current_id not in self.project_sidebar_buttons:
            current_id = str(rows[0][0])
        self.select_project(current_id)

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
        focus = ctk.CTkFrame(self.projects_tab, fg_color="#eef4fb", corner_radius=18)
        focus.pack(fill="x", padx=10, pady=(10, 0))
        focus_left = ctk.CTkFrame(focus, fg_color="transparent")
        focus_left.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(focus_left, text="Выбранный объект", font=("Segoe UI Semibold", 13), text_color="#5d738a").pack(anchor="w")
        self.project_focus_title_var = ctk.StringVar(value="Объект не выбран")
        self.project_focus_meta_var = ctk.StringVar(value="Выберите проект слева или в таблице, чтобы увидеть сводку.")
        self.project_focus_status_var = ctk.StringVar(value="Статус: —")
        ctk.CTkLabel(focus_left, textvariable=self.project_focus_title_var, font=("Segoe UI Semibold", 19), text_color="#1d2b3a").pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(focus_left, textvariable=self.project_focus_meta_var, justify="left", font=("Segoe UI", 11), text_color="#667b90").pack(anchor="w")
        ctk.CTkLabel(focus_left, textvariable=self.project_focus_status_var, font=("Segoe UI Semibold", 11), text_color="#1f8fff").pack(anchor="w", pady=(8, 0))
        focus_actions = ctk.CTkFrame(focus, fg_color="transparent")
        focus_actions.pack(side="right", padx=16, pady=16)
        ctk.CTkButton(focus_actions, text="Открыть смету", width=120, fg_color="#1f8a43", hover_color="#186d35", command=self.open_selected_project_smeta).pack(pady=4)
        ctk.CTkButton(focus_actions, text="Карточка проекта", width=120, fg_color="#1f538d", hover_color="#163d68", command=self.open_project_card).pack(pady=4)

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
        self.projects_tree.bind("<<TreeviewSelect>>", self.sync_selected_project_from_table)
        self.projects_tree.bind("<Double-1>", lambda event: self.open_project_card())

    def get_counterparty_display_name(self, row):
        if not row:
            return ""
        row_keys = row.keys() if hasattr(row, "keys") else []
        row_type = row["type"] if "type" in row_keys else ""
        if row_type == "Физическое лицо":
            return row["full_name"] if "full_name" in row_keys and row["full_name"] else (row["name"] if "name" in row_keys else "")
        if "company_name" in row_keys and row["company_name"]:
            return row["company_name"]
        if "name" in row_keys and row["name"]:
            return row["name"]
        return ""

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
            self.log_project_event(project_id, "document", "Создан документ проекта: Смета (приложение № 1)")
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
        self.populate_project_sidebar(rows)

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
        self.present_window(win)

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
        self.present_window(win)

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
            project_id = c.lastrowid
            conn.commit()
            conn.close()
            self.log_project_event(project_id, "project", f"Создан проект: {project_name}")
            win.destroy()
            self.refresh_projects()

        buttons_frame = ctk.CTkFrame(win)
        buttons_frame.pack(fill="x", padx=18, pady=18)
        ctk.CTkButton(buttons_frame, text="Отмена", command=win.destroy, fg_color="#5a5a5a").pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons_frame, text="Создать проект", command=save, fg_color="green").pack(side="right")

    def get_selected_project_id(self):
        selected = self.projects_tree.selection()
        if not selected:
            return self.selected_project_id
        project_id = self.projects_tree.item(selected[0], "values")[0]
        self.selected_project_id = str(project_id)
        return project_id

    def open_selected_project_smeta(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            return messagebox.showinfo("Смета", "Сначала выберите проект.")
        row = self.project_map.get(str(project_id))
        project_name = row[1] if row else ""
        self.open_project_smeta(project_id, project_name)

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
        if str(self.selected_project_id) == str(project_id):
            self.selected_project_id = None
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

    def log_project_event(self, project_id, event_type, event_text):
        if not project_id or not event_text:
            return
        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO project_events (project_id, event_type, event_text, author, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, event_type, event_text, self.current_user, now),
        )
        conn.commit()
        conn.close()

    def get_project_summary_metrics(self, project_id, project_name, documents, finances):
        smeta_total = self.get_project_smeta_total(project_id) or 0
        income_total = sum(row_[2] for row_ in finances if row_[1] == "Приход")
        expense_total = sum(row_[2] for row_ in finances if row_[1] == "Расход")
        document_total = len(documents)
        approved_total = sum(1 for doc in documents if doc[3] == "Согласован")
        draft_path = self.get_project_smeta_draft_path(project_id, project_name) or ""
        has_smeta = "Да" if draft_path else "Нет"
        return {
            "smeta_total": smeta_total,
            "income_total": income_total,
            "expense_total": expense_total,
            "balance_total": income_total - expense_total,
            "document_total": document_total,
            "approved_total": approved_total,
            "has_smeta": has_smeta,
            "draft_path": draft_path,
        }

    def build_metric_tile(self, parent, title, value, subtitle="", accent="#2f80ed"):
        card = ctk.CTkFrame(parent, fg_color="#f5f8fc", corner_radius=18)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkFrame(head, width=10, height=10, corner_radius=5, fg_color=accent).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(head, text=title, font=("Segoe UI Semibold", 12), text_color="#516274").pack(side="left")
        ctk.CTkLabel(card, text=value, font=("Segoe UI Semibold", 24), text_color="#1d2b3a").pack(anchor="w", padx=16)
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, font=("Segoe UI", 11), text_color="#6b7d90").pack(anchor="w", padx=16, pady=(2, 12))
        else:
            ctk.CTkLabel(card, text="", font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(2, 12))
        return card

    def build_info_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row, text=label, width=150, anchor="w", font=("Segoe UI Semibold", 11), text_color="#5f7288").pack(side="left")
        ctk.CTkLabel(row, text=value or "—", anchor="w", justify="left", font=("Segoe UI", 11), text_color="#1d2b3a").pack(side="left", fill="x", expand=True)
        return row

    def build_progress_card(self, parent, title, value, total, accent, suffix="руб."):
        card = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=18)
        ctk.CTkLabel(card, text=title, font=("Segoe UI Semibold", 12), text_color="#55687c").pack(anchor="w", padx=16, pady=(14, 4))
        value_text = f"{value:,.0f} {suffix}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
        ctk.CTkLabel(card, text=value_text, font=("Segoe UI Semibold", 20), text_color="#1d2b3a").pack(anchor="w", padx=16)
        progress = 0
        if total and total > 0:
            progress = max(0, min(value / total, 1))
        progress_bar = ctk.CTkProgressBar(card, progress_color=accent, fg_color="#dfe7f2")
        progress_bar.pack(fill="x", padx=16, pady=(10, 8))
        progress_bar.set(progress)
        caption = f"От базы: {total:,.0f} {suffix}".replace(",", " ") if isinstance(total, (int, float)) else str(total)
        ctk.CTkLabel(card, text=caption, font=("Segoe UI", 11), text_color="#7a8da2").pack(anchor="w", padx=16, pady=(0, 14))
        return card

    def collect_project_files(self, project_id, project_name, raw_documents):
        rows = []
        seen_paths = set()
        for doc in raw_documents:
            for kind, path in (("PDF", doc["pdf_path"] or ""), ("Черновик", doc["draft_path"] or ""), ("Файл", doc["file_path"] or "")):
                if not path or path in seen_paths:
                    continue
                seen_paths.add(path)
                rows.append((doc["title"] or doc["doc_type"] or "Документ", kind, path, "Да" if os.path.exists(path) else "Нет"))

        contracts_dir = self.get_contracts_dir(project_name)
        if os.path.isdir(contracts_dir):
            for name in sorted(os.listdir(contracts_dir)):
                path = os.path.join(contracts_dir, name)
                if os.path.isfile(path) and path not in seen_paths:
                    seen_paths.add(path)
                    rows.append(("Договор", "Файл", path, "Да"))
        return rows

    def fetch_project_history(self, project_id):
        conn = self.get_connection()
        c = conn.cursor()
        rows = c.execute(
            """SELECT created_at, event_type, COALESCE(author, '') AS author, event_text
               FROM project_events
               WHERE project_id=?
               ORDER BY created_at DESC, id DESC""",
            (project_id,),
        ).fetchall()
        conn.close()
        return [(row["created_at"].replace("T", " "), row["event_type"], row["author"] or "—", row["event_text"]) for row in rows]

    def open_file_from_tree(self, tree):
        selected = tree.selection()
        if not selected:
            return messagebox.showinfo("Файл", "Выберите файл из списка.")
        values = tree.item(selected[0], "values")
        if not values or len(values) < 3:
            return messagebox.showwarning("Файл", "Не удалось определить путь к файлу.")
        self.open_document_file({"file_path": values[2], "draft_path": "", "pdf_path": ""})

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
            self.log_project_event(doc_row["project_id"], "status", f"Изменен статус документа '{doc_row.get('title') or doc_row.get('doc_type')}' -> {status_var.get()}")
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
                      project_id,
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
            """SELECT txn_date, txn_type, amount, COALESCE(category, ''), COALESCE(description, ''), COALESCE(created_by, '')
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
        metrics = self.get_project_summary_metrics(project_id, row[1], documents, finances)
        project_files = self.collect_project_files(project_id, row[1], raw_documents)
        project_history = self.fetch_project_history(project_id)

        win = ctk.CTkToplevel(self)
        win.title(f"Проект: {row[1]}")
        win.geometry("1280x980")
        win.minsize(1220, 900)
        self.present_window(win)

        header = ctk.CTkFrame(win, fg_color="#f5f8fc", corner_radius=18)
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

        metrics_row = ctk.CTkFrame(win, fg_color="transparent")
        metrics_row.pack(fill="x", padx=12, pady=(0, 12))
        self.build_metric_tile(metrics_row, "Смета", f"{metrics['smeta_total']:,.0f} руб.".replace(",", " "), f"Черновик: {metrics['has_smeta']}", "#2f80ed").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.build_metric_tile(metrics_row, "Оплачено", f"{metrics['income_total']:,.0f} руб.".replace(",", " "), "Поступления по объекту", "#35a66f").pack(side="left", fill="x", expand=True, padx=6)
        self.build_metric_tile(metrics_row, "Расход", f"{metrics['expense_total']:,.0f} руб.".replace(",", " "), "Затраты по объекту", "#d9534f").pack(side="left", fill="x", expand=True, padx=6)
        self.build_metric_tile(metrics_row, "Документы", str(metrics["document_total"]), f"Согласовано: {metrics['approved_total']}", "#8e6ad8").pack(side="left", fill="x", expand=True, padx=(6, 0))

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        overview_tab = ctk.CTkFrame(notebook)
        smeta_tab = ctk.CTkFrame(notebook)
        documents_tab = ctk.CTkFrame(notebook)
        files_tab = ctk.CTkFrame(notebook)
        history_tab = ctk.CTkFrame(notebook)
        finance_tab = ctk.CTkFrame(notebook)
        notebook.add(overview_tab, text="Обзор")
        notebook.add(smeta_tab, text="Смета")
        notebook.add(documents_tab, text="Документы")
        notebook.add(files_tab, text="Файлы")
        notebook.add(history_tab, text="История")
        notebook.add(finance_tab, text="Финансы")

        overview_scroll = ctk.CTkScrollableFrame(overview_tab, fg_color="transparent")
        overview_scroll.pack(fill="both", expand=True, padx=12, pady=12)
        overview_grid = ctk.CTkFrame(overview_scroll, fg_color="transparent")
        overview_grid.pack(fill="both", expand=True)

        top_overview = ctk.CTkFrame(overview_grid, fg_color="transparent")
        top_overview.pack(fill="x", pady=(0, 12))
        bottom_overview = ctk.CTkFrame(overview_grid, fg_color="transparent")
        bottom_overview.pack(fill="both", expand=True)

        info_card = ctk.CTkFrame(top_overview, fg_color="#ffffff", corner_radius=18)
        info_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(info_card, text="Информация об объекте", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 6))
        self.build_info_row(info_card, "Объект", row[1])
        self.build_info_row(info_card, "Заказчик", row[2] or "не указан")
        self.build_info_row(info_card, "Договор", row[3] or "не указан")
        self.build_info_row(info_card, "Дата", row[4] or "не указана")
        self.build_info_row(info_card, "Статус", row[5] or "без статуса")
        notes_preview = row[6].strip() if row[6] else "Описание и заметки по объекту пока не добавлены."
        notes_preview = self.truncate_text(notes_preview.replace("\n", " "), 180)
        ctk.CTkLabel(info_card, text="Описание", font=("Segoe UI Semibold", 12), text_color="#5f7288").pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(info_card, text=notes_preview, wraplength=420, justify="left", font=("Segoe UI", 11), text_color="#6b7d90").pack(anchor="w", padx=16, pady=(0, 14))

        docs_card = ctk.CTkFrame(top_overview, fg_color="#ffffff", corner_radius=18)
        docs_card.pack(side="left", fill="both", expand=True, padx=6)
        ctk.CTkLabel(docs_card, text="Документы и действия", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        ctk.CTkLabel(
            docs_card,
            text=f"Всего документов: {metrics['document_total']}  •  Согласовано: {metrics['approved_total']}",
            font=("Segoe UI", 11),
            text_color="#667b90",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        recent_documents = documents[:4] if documents else []
        if recent_documents:
            for doc in recent_documents:
                ctk.CTkLabel(
                    docs_card,
                    text=f"{doc[1]}  •  {doc[3]}",
                    anchor="w",
                    font=("Segoe UI", 11),
                    text_color="#1f538d",
                ).pack(fill="x", padx=16, pady=3)
        else:
            ctk.CTkLabel(docs_card, text="Документы по объекту пока не добавлены.", font=("Segoe UI", 11), text_color="#7a8da2").pack(anchor="w", padx=16, pady=(4, 8))
        doc_actions = ctk.CTkFrame(docs_card, fg_color="transparent")
        doc_actions.pack(fill="x", padx=12, pady=(10, 14))
        ctk.CTkButton(doc_actions, text="Открыть смету", width=120, fg_color="#1f8a43", command=lambda: self.open_project_smeta(project_id, row[1])).pack(side="left", padx=4)
        ctk.CTkButton(doc_actions, text="Добавить документ", width=140, fg_color="#355c7d", command=lambda: self.open_add_document_window(project_id, win)).pack(side="left", padx=4)

        summary_right = ctk.CTkFrame(top_overview, fg_color="#ffffff", corner_radius=18)
        summary_right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(summary_right, text="Смета и баланс объекта", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        ctk.CTkLabel(
            summary_right,
            text=f"Черновик сметы: {metrics['has_smeta']}  •  Файлов: {len(project_files)}",
            font=("Segoe UI", 11),
            text_color="#667b90",
        ).pack(anchor="w", padx=16)
        quick_total = ctk.CTkFrame(summary_right, fg_color="#f5f8fc", corner_radius=14)
        quick_total.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(quick_total, text="Текущая сумма по смете", font=("Segoe UI", 11), text_color="#5f7288").pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(quick_total, text=f"{metrics['smeta_total']:,.0f} руб.".replace(",", " "), font=("Segoe UI Semibold", 26), text_color="#1d2b3a").pack(anchor="w", padx=14, pady=(0, 10))
        ctk.CTkLabel(
            summary_right,
            text=f"Баланс по объекту: {metrics['balance_total']:,.0f} руб.".replace(",", " "),
            font=("Segoe UI Semibold", 12),
            text_color="#1f8fff" if metrics["balance_total"] >= 0 else "#d9534f",
        ).pack(anchor="w", padx=16, pady=(0, 14))

        financials_wrap = ctk.CTkFrame(bottom_overview, fg_color="transparent")
        financials_wrap.pack(fill="x", pady=(0, 12))
        self.build_progress_card(financials_wrap, "Оплачено", metrics["income_total"], max(metrics["smeta_total"], metrics["income_total"], 1), "#35a66f").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.build_progress_card(financials_wrap, "Расход", metrics["expense_total"], max(metrics["smeta_total"], metrics["expense_total"], 1), "#d9534f").pack(side="left", fill="x", expand=True, padx=6)
        self.build_progress_card(financials_wrap, "Баланс", max(metrics["balance_total"], 0), max(metrics["smeta_total"], max(metrics["balance_total"], 0), 1), "#2f80ed").pack(side="left", fill="x", expand=True, padx=(6, 0))

        notes_card = ctk.CTkFrame(bottom_overview, fg_color="#ffffff", corner_radius=18)
        notes_card.pack(fill="both", expand=True)
        ctk.CTkLabel(notes_card, text="Заметки по проекту", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        notes_box = ctk.CTkTextbox(notes_card, height=260)
        notes_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        notes_box.insert("1.0", row[6] or "Здесь можно хранить заметки по объекту, договоренностям и следующему шагу.")
        notes_box.configure(state="disabled")

        smeta_header = ctk.CTkFrame(smeta_tab, fg_color="#f5f8fc", corner_radius=18)
        smeta_header.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(smeta_header, text="Смета проекта", font=("Segoe UI Semibold", 18), text_color="#1d2b3a").pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(smeta_header, text=f"Сумма по смете: {metrics['smeta_total']:,.0f} руб.".replace(",", " "), font=("Segoe UI", 12), text_color="#516274").pack(anchor="w", padx=14, pady=(0, 12))
        smeta_actions = ctk.CTkFrame(smeta_tab, fg_color="transparent")
        smeta_actions.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(smeta_actions, text="Открыть смету", command=lambda: self.open_project_smeta(project_id, row[1]), fg_color="#1f8a43").pack(side="left", padx=6)
        ctk.CTkButton(smeta_actions, text="Открыть черновик", command=lambda: self.open_document_file({"draft_path": metrics["draft_path"], "pdf_path": "", "file_path": ""}), fg_color="#1f538d").pack(side="left", padx=6)
        smeta_info = ctk.CTkTextbox(smeta_tab, height=260)
        smeta_info.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        smeta_info.insert(
            "1.0",
            f"Объект: {row[1]}\n"
            f"Заказчик: {row[2] or 'не указан'}\n"
            f"Договор: {row[3] or 'не указан'}\n"
            f"Черновик сметы: {metrics['draft_path'] or 'не найден'}\n"
            f"Сумма по смете: {metrics['smeta_total']:,.0f} руб.".replace(",", " ")
        )
        smeta_info.configure(state="disabled")

        docs_top = ctk.CTkFrame(documents_tab)
        docs_top.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(
            docs_top,
            text="Настроить договор",
            command=lambda: self.open_contract_settings_window(project_id, win),
            fg_color="#355c7d",
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            docs_top,
            text="Сформировать договор",
            command=lambda: self.generate_contract_for_project(project_id, win),
            fg_color="#1f8a43",
        ).pack(side="left", padx=6)
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

        files_top = ctk.CTkFrame(files_tab)
        files_top.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(files_top, text="Файлы проекта", font=("Segoe UI Semibold", 16)).pack(side="left", padx=6)
        files_tree = ttk.Treeview(files_tab, columns=("title", "kind", "path", "exists"), show="headings")
        for name, text, width in [
            ("title", "Документ", 260),
            ("kind", "Тип файла", 120),
            ("path", "Путь", 620),
            ("exists", "Есть на диске", 120),
        ]:
            files_tree.heading(name, text=text)
            files_tree.column(name, width=width, anchor="w" if name in ("title", "path") else "center")
        files_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for file_row in project_files:
            files_tree.insert("", "end", values=file_row)
        files_tree.bind("<Double-1>", lambda event: self.open_file_from_tree(files_tree))

        history_top = ctk.CTkFrame(history_tab)
        history_top.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(history_top, text="История проекта", font=("Segoe UI Semibold", 16)).pack(side="left", padx=6)
        history_tree = ttk.Treeview(history_tab, columns=("date", "type", "author", "text"), show="headings")
        for name, text, width in [
            ("date", "Дата", 180),
            ("type", "Тип", 120),
            ("author", "Автор", 140),
            ("text", "Событие", 620),
        ]:
            history_tree.heading(name, text=text)
            history_tree.column(name, width=width, anchor="w" if name == "text" else "center")
        history_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for history_row in project_history:
            history_tree.insert("", "end", values=history_row)

        total_income = sum(row_[2] for row_ in finances if row_[1] == "Приход")
        total_expense = sum(row_[2] for row_ in finances if row_[1] == "Расход")
        total_balance = total_income - total_expense

        finance_dashboard = ctk.CTkFrame(finance_tab, fg_color="transparent")
        finance_dashboard.pack(fill="both", expand=True, padx=12, pady=12)

        finance_top = ctk.CTkFrame(finance_dashboard, fg_color="transparent")
        finance_top.pack(fill="x", pady=(0, 12))

        finance_left = ctk.CTkFrame(finance_top, fg_color="#ffffff", corner_radius=18)
        finance_left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(finance_left, text="Финансовые показатели объекта", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        finance_cards = ctk.CTkFrame(finance_left, fg_color="transparent")
        finance_cards.pack(fill="x", padx=16, pady=(0, 8))
        self.build_progress_card(finance_cards, "Поступления", total_income, max(metrics["smeta_total"], total_income, 1), "#35a66f").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.build_progress_card(finance_cards, "Затраты", total_expense, max(metrics["smeta_total"], total_expense, 1), "#d9534f").pack(side="left", fill="x", expand=True, padx=(6, 0))

        finance_balance = ctk.CTkFrame(finance_left, fg_color="#f5f8fc", corner_radius=14)
        finance_balance.pack(fill="x", padx=16, pady=(2, 16))
        ctk.CTkLabel(finance_balance, text="Текущий баланс объекта", font=("Segoe UI", 11), text_color="#5f7288").pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            finance_balance,
            text=f"{total_balance:,.0f} руб.".replace(",", " "),
            font=("Segoe UI Semibold", 26),
            text_color="#1f8fff" if total_balance >= 0 else "#d9534f",
        ).pack(anchor="w", padx=14, pady=(0, 4))
        ctk.CTkLabel(
            finance_balance,
            text=f"Сумма по смете: {metrics['smeta_total']:,.0f} руб.".replace(",", " "),
            font=("Segoe UI", 11),
            text_color="#7a8da2",
        ).pack(anchor="w", padx=14, pady=(0, 12))

        finance_right = ctk.CTkFrame(finance_top, fg_color="#ffffff", corner_radius=18)
        finance_right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(finance_right, text="Последние движения", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        if finances:
            for txn in finances[:5]:
                amount_color = "#35a66f" if txn[1] == "Приход" else "#d9534f"
                txn_row = ctk.CTkFrame(finance_right, fg_color="#f5f8fc", corner_radius=12)
                txn_row.pack(fill="x", padx=16, pady=5)
                ctk.CTkLabel(txn_row, text=txn[0], width=110, anchor="w", font=("Segoe UI", 11), text_color="#5f7288").pack(side="left", padx=(12, 6), pady=10)
                ctk.CTkLabel(txn_row, text=txn[1], width=90, anchor="w", font=("Segoe UI Semibold", 11), text_color=amount_color).pack(side="left", padx=6)
                ctk.CTkLabel(txn_row, text=f"{txn[2]:,.0f} руб.".replace(",", " "), width=130, anchor="w", font=("Segoe UI Semibold", 11), text_color="#1d2b3a").pack(side="left", padx=6)
                ctk.CTkLabel(txn_row, text=f"{txn[5] or '—'} • {txn[3] or txn[4] or 'Без комментария'}", anchor="w", font=("Segoe UI", 11), text_color="#6b7d90").pack(side="left", fill="x", expand=True, padx=(6, 12))
        else:
            ctk.CTkLabel(finance_right, text="По этому объекту пока нет операций.", font=("Segoe UI", 11), text_color="#7a8da2").pack(anchor="w", padx=16, pady=(8, 12))
        ctk.CTkButton(finance_right, text="Открыть общие финансы", fg_color="#1f538d", command=self.open_finance_window).pack(anchor="w", padx=16, pady=(8, 16))

        finance_table_shell = ctk.CTkFrame(finance_dashboard, fg_color="#ffffff", corner_radius=18)
        finance_table_shell.pack(fill="both", expand=True)
        ctk.CTkLabel(finance_table_shell, text="Реестр операций по объекту", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 10))
        finance_tree = ttk.Treeview(finance_table_shell, columns=("date", "type", "amount", "category", "author", "desc"), show="headings")
        for name, text, width in [
            ("date", "Дата", 120),
            ("type", "Тип", 100),
            ("amount", "Сумма", 140),
            ("category", "Категория", 180),
            ("author", "Автор", 140),
            ("desc", "Комментарий", 300),
        ]:
            finance_tree.heading(name, text=text)
            finance_tree.column(name, width=width, anchor="w" if name in ("category", "author", "desc") else "center")
        finance_tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        for txn in finances:
            finance_tree.insert("", "end", values=(txn[0], txn[1], f"{txn[2]:,.0f}".replace(",", " "), txn[3], txn[5] or "—", txn[4]))

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
            self.log_project_event(project_id, "document", f"Добавлен документ: {title} [{status_var.get()}]")
            win.destroy()
            parent_window.destroy()
            self.open_project_card()

        ctk.CTkButton(win, text="Сохранить", command=save, fg_color="green").pack(pady=18)

    def open_finance_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Финансы компании")
        win.geometry("1400x980")
        win.minsize(1320, 920)
        win.configure(fg_color="#eef2f7")
        self.present_window(win)

        header = ctk.CTkFrame(win, fg_color="#ffffff", corner_radius=22)
        header.pack(fill="x", padx=14, pady=14)
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", fill="x", expand=True, padx=18, pady=16)
        ctk.CTkLabel(header_left, text="Финансы компании", font=("Segoe UI Semibold", 24), text_color="#1d2b3a").pack(anchor="w")
        ctk.CTkLabel(header_left, text="Общая касса и отдельные вкладки по активным объектам.", font=("Segoe UI", 12), text_color="#667b90").pack(anchor="w", pady=(6, 0))

        notebook_shell = ctk.CTkFrame(win, fg_color="#ffffff", corner_radius=22)
        notebook_shell.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        notebook = ttk.Notebook(notebook_shell)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        all_tab = ctk.CTkFrame(notebook)
        notebook.add(all_tab, text="Общая касса")
        tab_project_map = {str(all_tab): None}

        projects = self.fetch_projects()
        project_tabs = []
        for project in projects:
            if project[5] != "В работе":
                continue
            tab = ctk.CTkFrame(notebook)
            notebook.add(tab, text=str(project[1])[:28])
            project_tabs.append((project[0], tab))
            tab_project_map[str(tab)] = project[0]

        def open_operation_for_current_tab():
            current_tab = notebook.select()
            default_project_id = tab_project_map.get(current_tab)
            self.open_add_transaction_window(win, default_project_id=default_project_id)

        ctk.CTkButton(
            header,
            text="+ Операция",
            width=150,
            height=40,
            fg_color="#35a66f",
            hover_color="#2a885a",
            command=open_operation_for_current_tab,
        ).pack(side="right", padx=18, pady=18)

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
                          COALESCE(t.description, ''),
                          COALESCE(t.created_by, '')
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
                          COALESCE(t.description, ''),
                          COALESCE(t.created_by, '')
                   FROM cash_transactions t
                   LEFT JOIN projects p ON p.id = t.project_id
                   WHERE t.project_id=?
                   ORDER BY t.txn_date DESC, t.id DESC""",
                (project_id,),
            ).fetchall()
        conn.close()

        income = sum(row[2] for row in rows if row[1] == "Приход")
        expense = sum(row[2] for row in rows if row[1] == "Расход")
        balance = income - expense
        scope_name = "Общая касса компании" if project_id is None else (rows[0][3] if rows else "Объект")

        for child in tab.winfo_children():
            child.destroy()

        dashboard = ctk.CTkFrame(tab, fg_color="transparent")
        dashboard.pack(fill="both", expand=True, padx=12, pady=12)

        summary_header = ctk.CTkFrame(dashboard, fg_color="#f5f8fc", corner_radius=18)
        summary_header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(summary_header, text=scope_name, font=("Segoe UI Semibold", 18), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(summary_header, text=f"Операций: {len(rows)}", font=("Segoe UI", 11), text_color="#6b7d90").pack(anchor="w", padx=16, pady=(0, 14))

        metrics_row = ctk.CTkFrame(dashboard, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 12))
        self.build_metric_tile(metrics_row, "Приход", f"{income:,.0f} руб.".replace(",", " "), "Поступления", "#35a66f").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.build_metric_tile(metrics_row, "Расход", f"{expense:,.0f} руб.".replace(",", " "), "Списания и выплаты", "#d9534f").pack(side="left", fill="x", expand=True, padx=6)
        self.build_metric_tile(metrics_row, "Баланс", f"{balance:,.0f} руб.".replace(",", " "), "Текущее состояние", "#2f80ed").pack(side="left", fill="x", expand=True, padx=(6, 0))

        charts_row = ctk.CTkFrame(dashboard, fg_color="transparent")
        charts_row.pack(fill="x", pady=(0, 12))
        self.build_progress_card(charts_row, "Поступления", income, max(income + expense, 1), "#35a66f").pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.build_progress_card(charts_row, "Затраты", expense, max(income + expense, 1), "#d9534f").pack(side="left", fill="x", expand=True, padx=(6, 0))

        latest_shell = ctk.CTkFrame(dashboard, fg_color="#ffffff", corner_radius=18)
        latest_shell.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(latest_shell, text="Последние операции", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 8))
        if rows:
            for row in rows[:3]:
                color = "#35a66f" if row[1] == "Приход" else "#d9534f"
                item = ctk.CTkFrame(latest_shell, fg_color="#f5f8fc", corner_radius=12)
                item.pack(fill="x", padx=16, pady=4)
                ctk.CTkLabel(item, text=row[0], width=110, anchor="w", font=("Segoe UI", 11), text_color="#5f7288").pack(side="left", padx=(12, 6), pady=10)
                ctk.CTkLabel(item, text=row[1], width=90, anchor="w", font=("Segoe UI Semibold", 11), text_color=color).pack(side="left", padx=6)
                ctk.CTkLabel(item, text=f"{row[2]:,.0f} руб.".replace(",", " "), width=140, anchor="w", font=("Segoe UI Semibold", 11), text_color="#1d2b3a").pack(side="left", padx=6)
                ctk.CTkLabel(item, text=f"{row[6] or '—'} • {row[4] or row[5] or 'Без комментария'}", anchor="w", font=("Segoe UI", 11), text_color="#6b7d90").pack(side="left", fill="x", expand=True, padx=(6, 12))
        else:
            ctk.CTkLabel(latest_shell, text="Операций пока нет.", font=("Segoe UI", 11), text_color="#7a8da2").pack(anchor="w", padx=16, pady=(4, 14))

        table_shell = ctk.CTkFrame(dashboard, fg_color="#ffffff", corner_radius=18)
        table_shell.pack(fill="both", expand=True)
        ctk.CTkLabel(table_shell, text="Реестр операций", font=("Segoe UI Semibold", 16), text_color="#1d2b3a").pack(anchor="w", padx=16, pady=(14, 10))

        tree = ttk.Treeview(table_shell, columns=("date", "type", "amount", "project", "category", "author", "desc"), show="headings")
        for name, text, width in [
            ("date", "Дата", 120),
            ("type", "Тип", 100),
            ("amount", "Сумма", 120),
            ("project", "Проект", 280),
            ("category", "Категория", 180),
            ("author", "Автор", 130),
            ("desc", "Комментарий", 250),
        ]:
            tree.heading(name, text=text)
            tree.column(name, width=width, anchor="w" if name in ("project", "category", "author", "desc") else "center")
        tree.configure(height=14)
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        for row in rows:
            tree.insert("", "end", values=(row[0], row[1], f"{row[2]:,.0f}".replace(",", " "), row[3], row[4], row[6] or "—", row[5]))

    def open_add_transaction_window(self, finance_window, default_project_id=None):
        projects = self.fetch_projects()
        project_labels = {"Общая касса": None}
        project_label_by_id = {None: "Общая касса"}
        for project in projects:
            label = str(project[1])
            project_labels[label] = project[0]
            project_label_by_id[project[0]] = label

        win = ctk.CTkToplevel(finance_window)
        win.title("Новая операция")
        win.geometry("700x620")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self.present_window(win, finance_window)

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

        ctk.CTkLabel(win, text="Привязать к объекту").pack(anchor="w", padx=18, pady=(12, 4))
        project_var = ctk.StringVar(value=project_label_by_id.get(default_project_id, "Общая касса"))
        ctk.CTkOptionMenu(win, variable=project_var, values=list(project_labels.keys()), width=560).pack(padx=18)
        ctk.CTkLabel(
            win,
            text="Если оставить 'Общая касса', операция не попадет во вкладку конкретного объекта.",
            font=("Segoe UI", 11),
            text_color="#6b7d90",
        ).pack(anchor="w", padx=18, pady=(4, 0))

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
            selected_project_id = project_labels[project_var.get()]
            if selected_project_id is None:
                confirmed = messagebox.askyesno(
                    "Подтвердите сохранение",
                    "Операция будет сохранена только в общей кассе и не появится во вкладке объекта.\n\nСохранить без привязки к проекту?",
                )
                if not confirmed:
                    return
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = self.get_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO cash_transactions
                   (txn_date, txn_type, amount, project_id, category, description, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    date_entry.get().strip(),
                    type_var.get(),
                    amount,
                    selected_project_id,
                    category_entry.get().strip(),
                    desc_entry.get().strip(),
                    self.current_user,
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
