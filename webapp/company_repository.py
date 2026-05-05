from dataclasses import dataclass, field
from typing import Any

from webapp.db import get_connection


@dataclass(frozen=True)
class Company:
    id: int
    legal_name: str
    short_name: str
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    legal_address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    bank_name: str | None = None
    bik: str | None = None
    account: str | None = None
    correspondent_account: str | None = None
    director_name: str | None = None
    signer_name: str | None = None
    stamp_path: str | None = None
    signature_path: str | None = None
    watermark_text: str = "ДЕКОРАРТСТРОЙ"
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class CompanyCreateInput:
    legal_name: str
    short_name: str
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    legal_address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    bank_name: str | None = None
    bik: str | None = None
    account: str | None = None
    correspondent_account: str | None = None
    director_name: str | None = None
    signer_name: str | None = None
    watermark_text: str = "ДЕКОРАРТСТРОЙ"


@dataclass(frozen=True)
class CompanyUpdateInput:
    legal_name: str | None = None
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    legal_address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    bank_name: str | None = None
    bik: str | None = None
    account: str | None = None
    correspondent_account: str | None = None
    director_name: str | None = None
    signer_name: str | None = None
    watermark_text: str | None = None
    is_active: bool | None = None


_COMPANY_COLUMNS = [
    "id", "legal_name", "short_name", "inn", "kpp", "ogrn", "ogrnip",
    "legal_address", "phone", "email", "website", "bank_name", "bik",
    "account", "correspondent_account", "director_name", "signer_name",
    "stamp_path", "signature_path", "watermark_text", "is_active",
    "created_at", "updated_at",
]


def _row_to_company(row: dict[str, Any]) -> Company:
    return Company(
        id=int(row["id"]),
        legal_name=row["legal_name"],
        short_name=row["short_name"],
        inn=row.get("inn"),
        kpp=row.get("kpp"),
        ogrn=row.get("ogrn"),
        ogrnip=row.get("ogrnip"),
        legal_address=row.get("legal_address"),
        phone=row.get("phone"),
        email=row.get("email"),
        website=row.get("website"),
        bank_name=row.get("bank_name"),
        bik=row.get("bik"),
        account=row.get("account"),
        correspondent_account=row.get("correspondent_account"),
        director_name=row.get("director_name"),
        signer_name=row.get("signer_name"),
        stamp_path=row.get("stamp_path"),
        signature_path=row.get("signature_path"),
        watermark_text=row.get("watermark_text", "ДЕКОРАРТСТРОЙ"),
        is_active=row.get("is_active", True),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


class CompanyRepository:
    def list_companies(self, *, include_inactive: bool = False) -> list[Company]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if include_inactive:
                    cur.execute("SELECT * FROM companies ORDER BY id")
                else:
                    cur.execute("SELECT * FROM companies WHERE is_active = TRUE ORDER BY id")
                return [_row_to_company(row) for row in cur.fetchall()]

    def get_company(self, company_id: int) -> Company | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
                row = cur.fetchone()
        return _row_to_company(row) if row else None

    def get_company_by_short_name(self, short_name: str) -> Company | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM companies WHERE short_name = %s", (short_name,))
                row = cur.fetchone()
        return _row_to_company(row) if row else None

    def create_company(self, data: CompanyCreateInput) -> Company:
        from datetime import datetime
        now = datetime.now().isoformat(timespec="seconds")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO companies (
                        legal_name, short_name, inn, kpp, ogrn, ogrnip,
                        legal_address, phone, email, website, bank_name, bik,
                        account, correspondent_account, director_name, signer_name,
                        watermark_text, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    ) RETURNING *
                    """,
                    (
                        data.legal_name, data.short_name, data.inn, data.kpp,
                        data.ogrn, data.ogrnip, data.legal_address, data.phone,
                        data.email, data.website, data.bank_name, data.bik,
                        data.account, data.correspondent_account,
                        data.director_name, data.signer_name,
                        data.watermark_text, now, now,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_company(row)

    def update_company(self, company_id: int, data: CompanyUpdateInput) -> Company | None:
        existing = self.get_company(company_id)
        if not existing:
            return None
        from datetime import datetime
        now = datetime.now().isoformat(timespec="seconds")
        fields = []
        values = []
        for attr in [
            "legal_name", "inn", "kpp", "ogrn", "ogrnip", "legal_address",
            "phone", "email", "website", "bank_name", "bik", "account",
            "correspondent_account", "director_name", "signer_name",
            "watermark_text", "is_active",
        ]:
            val = getattr(data, attr)
            if val is not None:
                fields.append(f"{attr} = %s")
                values.append(val)
        if not fields:
            return existing
        fields.append("updated_at = %s")
        values.append(now)
        values.append(company_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE companies SET {', '.join(fields)} WHERE id = %s RETURNING *",
                    tuple(values),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_company(row) if row else None

    def set_company_asset_paths(
        self,
        company_id: int,
        *,
        stamp_path: str | None = None,
        signature_path: str | None = None,
    ) -> Company | None:
        existing = self.get_company(company_id)
        if not existing:
            return None
        from datetime import datetime
        now = datetime.now().isoformat(timespec="seconds")
        fields = ["updated_at = %s"]
        values = [now]
        if stamp_path is not None:
            fields.append("stamp_path = %s")
            values.append(stamp_path)
        if signature_path is not None:
            fields.append("signature_path = %s")
            values.append(signature_path)
        values.append(company_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE companies SET {', '.join(fields)} WHERE id = %s RETURNING *",
                    tuple(values),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_company(row) if row else None

    def deactivate_company(self, company_id: int) -> Company | None:
        from datetime import datetime
        now = datetime.now().isoformat(timespec="seconds")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE companies SET is_active = FALSE, updated_at = %s WHERE id = %s RETURNING *",
                    (now, company_id),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_company(row) if row else None


class CompanyService:
    def __init__(self, repository: CompanyRepository | None = None):
        self.repository = repository or CompanyRepository()

    def list_companies(self, *, include_inactive: bool = False) -> list[Company]:
        return self.repository.list_companies(include_inactive=include_inactive)

    def get_company(self, company_id: int) -> Company | None:
        return self.repository.get_company(company_id)

    def get_company_by_short_name(self, short_name: str) -> Company | None:
        return self.repository.get_company_by_short_name(short_name)

    def create_company(self, data: CompanyCreateInput) -> Company:
        return self.repository.create_company(data)

    def update_company(self, company_id: int, data: CompanyUpdateInput) -> Company | None:
        return self.repository.update_company(company_id, data)

    def set_company_asset_paths(
        self,
        company_id: int,
        *,
        stamp_path: str | None = None,
        signature_path: str | None = None,
    ) -> Company | None:
        return self.repository.set_company_asset_paths(
            company_id, stamp_path=stamp_path, signature_path=signature_path
        )

    def deactivate_company(self, company_id: int) -> Company | None:
        return self.repository.deactivate_company(company_id)