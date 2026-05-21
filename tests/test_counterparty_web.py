import unittest

from tests.db_guard import guard_live_database
from webapp.db import get_connection, fetch_counterparty, update_counterparty
from webapp.main import create_counterparty


class CounterpartyWebTests(unittest.TestCase):
    def setUp(self):
        guard_live_database()
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        guard_live_database()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM counterparties WHERE id > 2")
            conn.commit()

    def _get_counterparty(self, counterparty_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM counterparties WHERE id = %s", (counterparty_id,))
                return cur.fetchone()

    def test_create_counterparty_minimal_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Тест Минималов",
            full_name="", company_name="", phone="", email="", inn="", notes="",
        )
        row = self._get_counterparty(c_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "Тест Минималов")
        self.assertEqual(row["type"], "Физлицо")

    def test_create_counterparty_full_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="Тест ООО Полное",
            full_name="Иванов Иван Иванович",
            company_name="ООО Тестовая Компания",
            phone="+7 (999) 123-45-67",
            email="test@example.com",
            inn="7811530330",
            notes="Тестовая заметка",
            kpp="781001001",
            ogrn="1127847464942",
            ogrnip="",
            passport_series_number="4015 467273",
            passport_issued_by="Отделом УФМС",
            passport_department_code="780-032",
            registration_address="г. Санкт-Петербург, ул. Тестовая, д. 1",
            work_address="г. Санкт-Петербург, ул. Ремонтная, д. 5",
            birth_date="15.03.1985",
            checking_account="40702810955160002794",
            correspondent_account="30101810500000000653",
            bank_name="ПАО Сбербанк",
            bank_bik="044030653",
            legal_address="196191, Санкт-Петербург, пл. Конституции, д. 7",
            postal_address="196191, Санкт-Петербург, пл. Конституции, д. 7",
            actual_address="196191, Санкт-Петербург, пл. Конституции, д. 7",
            director_name="Шарипов Шехрозжон Шавкатович",
            director_basis="Устава",
        )
        row = self._get_counterparty(c_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["type"], "ООО")
        self.assertEqual(row["name"], "Тест ООО Полное")
        self.assertEqual(row["full_name"], "Иванов Иван Иванович")
        self.assertEqual(row["company_name"], "ООО Тестовая Компания")
        self.assertEqual(row["phone"], "+7 (999) 123-45-67")
        self.assertEqual(row["email"], "test@example.com")
        self.assertEqual(row["inn"], "7811530330")
        self.assertEqual(row["kpp"], "781001001")
        self.assertEqual(row["ogrn"], "1127847464942")
        self.assertEqual(row["passport_series_number"], "4015 467273")
        self.assertEqual(row["passport_issued_by"], "Отделом УФМС")
        self.assertEqual(row["passport_department_code"], "780-032")
        self.assertEqual(row["registration_address"], "г. Санкт-Петербург, ул. Тестовая, д. 1")
        self.assertEqual(row["work_address"], "г. Санкт-Петербург, ул. Ремонтная, д. 5")
        self.assertEqual(row["birth_date"], "15.03.1985")
        self.assertEqual(row["checking_account"], "40702810955160002794")
        self.assertEqual(row["correspondent_account"], "30101810500000000653")
        self.assertEqual(row["bank_name"], "ПАО Сбербанк")
        self.assertEqual(row["bank_bik"], "044030653")
        self.assertEqual(row["legal_address"], "196191, Санкт-Петербург, пл. Конституции, д. 7")
        self.assertEqual(row["postal_address"], "196191, Санкт-Петербург, пл. Конституции, д. 7")
        self.assertEqual(row["actual_address"], "196191, Санкт-Петербург, пл. Конституции, д. 7")
        self.assertEqual(row["director_name"], "Шарипов Шехрозжон Шавкатович")
        self.assertEqual(row["director_basis"], "Устава")
        self.assertEqual(row["notes"], "Тестовая заметка")

    def test_create_counterparty_individual_passport_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Петров Пётр Петрович",
            full_name="Петров Пётр Петрович",
            company_name="", phone="+7 (916) 555-44-33", email="petrov@example.com", inn="", notes="",
            passport_series_number="4010 123456",
            passport_issued_by="ОВД района Тверской г. Москвы",
            passport_department_code="770-042",
            birth_date="20.05.1990",
            registration_address="г. Москва, ул. Тверская, д. 10, кв. 5",
            work_address="г. Москва, Ленинский пр-т, д. 50",
        )
        row = self._get_counterparty(c_id)
        self.assertEqual(row["type"], "Физлицо")
        self.assertEqual(row["passport_series_number"], "4010 123456")
        self.assertEqual(row["passport_issued_by"], "ОВД района Тверской г. Москвы")
        self.assertEqual(row["passport_department_code"], "770-042")
        self.assertEqual(row["birth_date"], "20.05.1990")
        self.assertEqual(row["registration_address"], "г. Москва, ул. Тверская, д. 10, кв. 5")
        self.assertEqual(row["work_address"], "г. Москва, Ленинский пр-т, д. 50")

    def test_create_counterparty_ip_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ИП",
            display_name="ИП Гордеев",
            full_name="", company_name="ИП Гордеев А.Н.", phone="", email="", inn="782002123456", notes="",
            ogrnip="304782012345678",
            checking_account="40802810955000012345",
            bank_name="Филиал ПАО Банк ФК Открытие",
            bank_bik="044030706",
            legal_address="г. Санкт-Петербург, наб. реки Фонтанки, д. 10",
        )
        row = self._get_counterparty(c_id)
        self.assertEqual(row["type"], "ИП")
        self.assertEqual(row["ogrnip"], "304782012345678")
        self.assertEqual(row["bank_name"], "Филиал ПАО Банк ФК Открытие")
        self.assertEqual(row["bank_bik"], "044030706")
        self.assertEqual(row["legal_address"], "г. Санкт-Петербург, наб. реки Фонтанки, д. 10")

    def test_create_counterparty_bank_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="ООО БанкТест",
            full_name="", company_name="ООО Банк Тест", phone="", email="", inn="7811530331", notes="",
            checking_account="40702810500000001234",
            correspondent_account="30101810500000001234",
            bank_name="АО Альфа-Банк",
            bank_bik="044525593",
        )
        row = self._get_counterparty(c_id)
        self.assertEqual(row["checking_account"], "40702810500000001234")
        self.assertEqual(row["correspondent_account"], "30101810500000001234")
        self.assertEqual(row["bank_name"], "АО Альфа-Банк")
        self.assertEqual(row["bank_bik"], "044525593")

    def test_create_counterparty_director_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="ООО ДиректорТест",
            full_name="", company_name="", phone="", email="", inn="", notes="",
            director_name="Иванов Иван Иванович",
            director_basis="Устава",
        )
        row = self._get_counterparty(c_id)
        self.assertEqual(row["director_name"], "Иванов Иван Иванович")
        self.assertEqual(row["director_basis"], "Устава")

    def test_create_counterparty_old_minimal_still_works(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="",
            full_name="Сидоров Сидор Сидорович",
            company_name="",
            phone="+7 (911) 000-00-01",
            email="",
            inn="",
            notes="",
        )
        row = self._get_counterparty(c_id)
        self.assertEqual(row["name"], "Сидоров Сидор Сидорович")
        self.assertEqual(row["full_name"], "Сидоров Сидор Сидорович")
        self.assertEqual(row["phone"], "+7 (911) 000-00-01")
        empty_fields = [
            "kpp", "ogrn", "ogrnip", "passport_series_number",
            "passport_issued_by", "passport_department_code",
            "registration_address", "work_address", "birth_date",
            "checking_account", "correspondent_account", "bank_name", "bank_bik",
            "legal_address", "postal_address", "actual_address",
            "director_name", "director_basis",
        ]
        for field in empty_fields:
            self.assertEqual(row[field], "", f"Field {field} should be empty string")

    def test_create_counterparty_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            create_counterparty(
                "tester",
                counterparty_type="Физлицо",
                display_name="",
                full_name="",
                company_name="",
                phone="",
                email="",
                inn="",
                notes="",
            )

    def test_fetch_counterparty_returns_all_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="Тест Fetch",
            full_name="Тестов Тест Тестович",
            company_name="ООО Тест Fetch",
            phone="+7 (999) 000-00-00",
            email="fetch@test.com",
            inn="1234567890",
            notes="fetch test",
            director_name="Директоров Директ Директович",
            director_basis="Устава",
        )
        row = fetch_counterparty(c_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], c_id)
        self.assertEqual(row["type"], "ООО")
        self.assertEqual(row["name"], "Тест Fetch")
        self.assertEqual(row["director_name"], "Директоров Директ Директович")
        self.assertEqual(row["director_basis"], "Устава")
        self.assertIn("display_name", row)

    def test_fetch_counterparty_nonexistent_returns_none(self):
        row = fetch_counterparty(999999)
        self.assertIsNone(row)

    def test_update_counterparty_individual_fields(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Тест Обновление",
            full_name="Тест Обновление",
            company_name="", phone="", email="", inn="", notes="",
        )
        updated = update_counterparty(
            c_id,
            phone="+7 (999) 111-22-33",
            passport_series_number="1234 567890",
            registration_address="Новый адрес регистрации",
        )
        self.assertEqual(updated["phone"], "+7 (999) 111-22-33")
        self.assertEqual(updated["passport_series_number"], "1234 567890")
        self.assertEqual(updated["registration_address"], "Новый адрес регистрации")
        self.assertEqual(updated["name"], "Тест Обновление")

    def test_update_counterparty_full_update(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Тест Full Update",
            full_name="Старое Имя",
            company_name="", phone="", email="", inn="", notes="",
        )
        updated = update_counterparty(
            c_id,
            type="ООО",
            name="ООО Полное Обновление",
            full_name="Новое ФИО",
            company_name="ООО Новая Компания",
            phone="+7 (999) 999-88-77",
            email="updated@test.com",
            inn="9876543210",
            kpp="987654321",
            ogrn="1234567890123",
            bank_name="Новый Банк",
            bank_bik="044555444",
            checking_account="40702810955160009999",
            correspondent_account="30101810500000009999",
            legal_address="Новый юридический адрес",
            director_name="Новый Директор",
            director_basis="Доверенности №5",
            notes="Обновленные заметки",
        )
        self.assertEqual(updated["type"], "ООО")
        self.assertEqual(updated["name"], "ООО Полное Обновление")
        self.assertEqual(updated["full_name"], "Новое ФИО")
        self.assertEqual(updated["company_name"], "ООО Новая Компания")
        self.assertEqual(updated["phone"], "+7 (999) 999-88-77")
        self.assertEqual(updated["email"], "updated@test.com")
        self.assertEqual(updated["inn"], "9876543210")
        self.assertEqual(updated["kpp"], "987654321")
        self.assertEqual(updated["ogrn"], "1234567890123")
        self.assertEqual(updated["bank_name"], "Новый Банк")
        self.assertEqual(updated["bank_bik"], "044555444")
        self.assertEqual(updated["checking_account"], "40702810955160009999")
        self.assertEqual(updated["correspondent_account"], "30101810500000009999")
        self.assertEqual(updated["legal_address"], "Новый юридический адрес")
        self.assertEqual(updated["director_name"], "Новый Директор")
        self.assertEqual(updated["director_basis"], "Доверенности №5")
        self.assertEqual(updated["notes"], "Обновленные заметки")

    def test_update_counterparty_nonexistent_returns_none(self):
        result = update_counterparty(999999, phone="+7 (999) 000-00-00")
        self.assertIsNone(result)

    def test_fetch_counterparties_returns_list_with_display_name(self):
        from webapp.db import fetch_counterparties
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="ТестООО Список",
            full_name="", company_name="ООО Тест Список", phone="", email="", inn="", notes="",
        )
        rows = fetch_counterparties()
        found = [r for r in rows if r["id"] == c_id]
        self.assertTrue(len(found) > 0, "Created counterparty not found in list")
        row = found[0]
        self.assertIn("display_name", row)
        self.assertEqual(row["display_name"], "ООО Тест Список")
        self.assertIn("type", row)
        self.assertEqual(row["type"], "ООО")

    def test_fetch_counterparties_ordered_by_name(self):
        from webapp.db import fetch_counterparties
        create_counterparty("tester", counterparty_type="Физлицо", display_name="ЯЯЯ Яяев", full_name="", company_name="", phone="", email="", inn="", notes="")
        create_counterparty("tester", counterparty_type="Физлицо", display_name="Ааа Аааев", full_name="", company_name="", phone="", email="", inn="", notes="")
        rows = fetch_counterparties()
        filtered = [r for r in rows if r["id"] > 2]
        self.assertTrue(len(filtered) >= 2)
        names = [r["display_name"] for r in filtered]
        sorted_names = sorted(names, key=lambda n: n.lower())
        self.assertEqual(names, sorted_names, "Counterparties should be ordered by name")

    def test_fetch_counterparty_includes_display_name(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="ООО",
            display_name="Тест Display",
            full_name="",
            company_name="ООО Тестовая Компания",
            phone="", email="", inn="", notes="",
        )
        row = fetch_counterparty(c_id)
        self.assertIsNotNone(row)
        self.assertIn("display_name", row)
        self.assertEqual(row["display_name"], "ООО Тестовая Компания")

    def test_fetch_counterparty_falls_back_to_name(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Тест Фоллбэк",
            full_name="",
            company_name="",
            phone="",
            email="",
            inn="",
            notes="",
        )
        row = fetch_counterparty(c_id)
        self.assertEqual(row["display_name"], "Тест Фоллбэк")

    def test_update_counterparty_no_fields_returns_same(self):
        c_id = create_counterparty(
            "tester",
            counterparty_type="Физлицо",
            display_name="Тест NoUpdate",
            full_name="Тест NoUpdate",
            company_name="", phone="", email="", inn="", notes="",
        )
        result = update_counterparty(c_id)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Тест NoUpdate")


class CounterpartyTemplateRouteTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.templates_dir = Path(__file__).resolve().parents[1] / "webapp" / "templates"
        self.main_py = Path(__file__).resolve().parents[1] / "webapp" / "main.py"

    def test_counterparties_list_template_exists(self):
        path = self.templates_dir / "counterparties_list.html"
        self.assertTrue(path.exists(), f"Missing template: {path}")

    def test_counterparty_detail_template_exists(self):
        path = self.templates_dir / "counterparty_detail.html"
        self.assertTrue(path.exists(), f"Missing template: {path}")

    def test_counterparty_edit_template_exists(self):
        path = self.templates_dir / "counterparty_edit.html"
        self.assertTrue(path.exists(), f"Missing template: {path}")

    def test_counterparties_list_template_has_table_and_links(self):
        content = (self.templates_dir / "counterparties_list.html").read_text(encoding="utf-8")
        self.assertIn('href="/counterparties/new"', content)
        self.assertIn('href="/counterparties/{{ cp.id }}', content)
        self.assertIn('href="/counterparties/{{ cp.id }}/edit"', content)
        self.assertIn("{% for cp in counterparties %}", content)

    def test_counterparty_detail_template_shows_all_fields(self):
        content = (self.templates_dir / "counterparty_detail.html").read_text(encoding="utf-8")
        self.assertIn("counterparty.type", content)
        self.assertIn("counterparty.full_name", content)
        self.assertIn("counterparty.company_name", content)
        self.assertIn("counterparty.phone", content)
        self.assertIn("counterparty.inn", content)
        self.assertIn("counterparty.passport_series_number", content)
        self.assertIn("counterparty.passport_issued_by", content)
        self.assertIn("counterparty.birth_date", content)
        self.assertIn("counterparty.kpp", content)
        self.assertIn("counterparty.ogrn", content)
        self.assertIn("counterparty.bank_name", content)
        self.assertIn("counterparty.bank_bik", content)
        self.assertIn("counterparty.checking_account", content)
        self.assertIn("counterparty.director_name", content)
        self.assertIn("counterparty.director_basis", content)
        self.assertIn('href="/counterparties/{{ counterparty.id }}/edit"', content)
        self.assertIn('href="/counterparties"', content)

    def test_counterparty_edit_template_has_form_and_fields(self):
        content = (self.templates_dir / "counterparty_edit.html").read_text(encoding="utf-8")
        self.assertIn('method="post" action="/counterparties/{{ counterparty.id }}/edit"', content)
        self.assertIn('name="counterparty_type"', content)
        self.assertIn('name="display_name"', content)
        self.assertIn('name="full_name"', content)
        self.assertIn('name="company_name"', content)
        self.assertIn('name="phone"', content)
        self.assertIn('name="inn"', content)
        self.assertIn('name="passport_series_number"', content)
        self.assertIn('name="kpp"', content)
        self.assertIn('name="ogrn"', content)
        self.assertIn('name="bank_name"', content)
        self.assertIn('name="checking_account"', content)
        self.assertIn('name="director_name"', content)
        self.assertIn('name="director_basis"', content)
        self.assertIn('name="notes"', content)
        self.assertIn("form_data", content)

    def test_main_py_has_counterparty_list_route(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('@app.get("/counterparties")', content)
        self.assertIn('name="counterparties_list.html"', content)

    def test_main_py_has_counterparty_detail_route(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('@app.get("/counterparties/{counterparty_id}")', content)
        self.assertIn('name="counterparty_detail.html"', content)

    def test_main_py_has_counterparty_edit_get_route(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('@app.get("/counterparties/{counterparty_id}/edit")', content)
        self.assertIn('name="counterparty_edit.html"', content)

    def test_main_py_has_counterparty_edit_post_route(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('@app.post("/counterparties/{counterparty_id}/edit")', content)

    def test_main_py_create_redirects_to_detail_page(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('url=f"/counterparties/{cp_id}"', content)

    def test_main_py_edit_redirects_to_detail_page(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('url=f"/counterparties/{counterparty_id}"', content)

    def test_main_py_edit_has_all_28_form_params(self):
        content = self.main_py.read_text(encoding="utf-8")
        idx = content.find('@app.post("/counterparties/{counterparty_id}/edit")')
        self.assertGreater(idx, 0, "POST edit route not found")
        section = content[idx:idx + 3000]
        form_params = [
            "display_name", "full_name", "company_name",
            "phone", "email", "inn", "notes", "kpp", "ogrn", "ogrnip",
            "passport_series_number", "passport_issued_by", "passport_department_code",
            "registration_address", "work_address", "birth_date",
            "checking_account", "correspondent_account", "bank_name", "bank_bik",
            "legal_address", "postal_address", "actual_address",
            "director_name", "director_basis",
        ]
        for param in form_params:
            self.assertIn(f'{param}: str = Form("")', section, f"Missing Form param: {param}")
        self.assertIn('counterparty_type: str = Form("Физлицо")', section, "Missing Form param: counterparty_type")

    def test_main_py_detail_raises_404_for_missing(self):
        content = self.main_py.read_text(encoding="utf-8")
        self.assertIn('raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Контрагент не найден.")', content)

    def test_main_py_edit_raises_404_for_missing(self):
        content = self.main_py.read_text(encoding="utf-8")
        count = content.count('raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Контрагент не найден.")')
        self.assertGreaterEqual(count, 2, "Expected at least 2 404 raises for detail and edit routes")

    def test_projects_template_links_to_counterparties(self):
        content = (self.templates_dir / "projects.html").read_text(encoding="utf-8")
        self.assertIn('href="/counterparties"', content)


if __name__ == "__main__":
    unittest.main()