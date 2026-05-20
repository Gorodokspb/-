import unittest

from tests.db_guard import guard_live_database
from webapp.db import get_connection
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


if __name__ == "__main__":
    unittest.main()