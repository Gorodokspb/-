"""File export helpers for standalone estimates.

These helpers are intentionally isolated from legacy project-bound estimate
storage. They persist generated JSON/PDF artifacts under a dedicated
standalone-estimates subtree inside the existing storage root.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from webapp.config import get_settings
from webapp.storage import resolve_storage_path, sanitize_filename

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from webapp.company_repository import Company

FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"


def _ensure_fonts() -> None:
    registered = set(pdfmetrics.getRegisteredFontNames())
    if FONT_REGULAR in registered and FONT_BOLD in registered:
        return

    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            if FONT_REGULAR not in registered:
                pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
            if FONT_BOLD not in registered:
                pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
            return
    raise RuntimeError("Не удалось найти шрифт для генерации PDF standalone-сметы.")


def _standalone_estimate_dir(estimate_id: int, title: str = "") -> Path:
    settings = get_settings()
    label = sanitize_filename(title or f"Смета_{estimate_id}", f"Смета_{estimate_id}")
    directory = settings.estimates_dir / "standalone-estimates" / f"{int(estimate_id):06d}_{label}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_standalone_estimate_json_path(estimate_id: int, title: str = "") -> Path:
    directory = _standalone_estimate_dir(estimate_id, title)
    return directory / f"{sanitize_filename(title or f'Смета_{estimate_id}', 'Смета')}.json"


def build_standalone_estimate_pdf_path(estimate_id: int, title: str = "", *, approved: bool = False) -> Path:
    directory = _standalone_estimate_dir(estimate_id, title)
    suffix = "approved" if approved else "draft"
    return directory / f"{sanitize_filename(title or f'Смета_{estimate_id}', 'Смета')}-{suffix}.pdf"


def export_standalone_estimate_json(snapshot: dict[str, Any]) -> Path:
    estimate = snapshot["estimate"]
    path = build_standalone_estimate_json_path(int(estimate["id"]), estimate.get("title") or estimate.get("object_name") or estimate.get("estimate_number") or "")
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _is_approved_pdf_status(status_value: Any) -> bool:
    return str(status_value or "") in {"approved", "in_progress"}


def _to_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _format_money(value: float) -> str:
    rounded = round(value, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _draft_watermark_enabled(estimate: dict[str, Any], *, approved: bool) -> bool:
    return not approved and bool(estimate.get("watermark"))


def _build_pdf_table(snapshot: dict[str, Any]) -> tuple[list[list[str]], list[tuple[Any, ...]], float, float]:
    table_data = [["Наименование", "Ед.", "Кол-во", "Цена", "Итого", "Со скидкой"]]
    section_styles: list[tuple[Any, ...]] = []
    grand_total = 0.0
    discounted_total = 0.0

    for item in snapshot.get("items", []):
        row_type = str(item.get("row_type") or "item")
        row_index = len(table_data)
        if row_type == "section":
            table_data.append([str(item.get("name") or "Раздел"), "", "", "", "", ""])
            section_styles.extend(
                [
                    ("SPAN", (0, row_index), (-1, row_index)),
                    ("FONTNAME", (0, row_index), (-1, row_index), FONT_BOLD),
                    ("BACKGROUND", (0, row_index), (-1, row_index), colors.whitesmoke),
                ]
            )
            continue

        row_total = _to_float(item.get("total"))
        row_discounted_total = _to_float(item.get("discounted_total"))
        table_data.append(
            [
                str(item.get("name") or ""),
                str(item.get("unit") or ""),
                str(item.get("quantity") or ""),
                str(item.get("price") or ""),
                str(item.get("total") or ""),
                str(item.get("discounted_total") or ""),
            ]
        )
        grand_total += row_total
        discounted_total += row_discounted_total

    return table_data, section_styles, grand_total, discounted_total


def _company_details_elements(company: Company, body_style: ParagraphStyle) -> list:
    elements = []
    elements.append(Paragraph(f"Компания: {company.legal_name or company.short_name}", body_style))
    lines: list[str] = []
    if company.inn:
        parts = [f"ИНН: {company.inn}"]
        if company.kpp:
            parts.append(f"КПП: {company.kpp}")
        lines.append("  ".join(parts))
    if company.ogrn:
        lines.append(f"ОГРН: {company.ogrn}")
    elif company.ogrnip:
        lines.append(f"ОГРНИП: {company.ogrnip}")
    if company.legal_address:
        lines.append(f"Адрес: {company.legal_address}")
    contact_parts = []
    if company.phone:
        contact_parts.append(f"Тел.: {company.phone}")
    if company.email:
        contact_parts.append(f"E-mail: {company.email}")
    if contact_parts:
        lines.append("  ".join(contact_parts))
    if company.website:
        lines.append(f"Сайт: {company.website}")
    if company.bank_name:
        bank_parts = [f"Банк: {company.bank_name}"]
        if company.bik:
            bank_parts.append(f"БИК: {company.bik}")
        lines.append("  ".join(bank_parts))
    bank_account_parts = []
    if company.account:
        bank_account_parts.append(f"Р/с: {company.account}")
    if company.correspondent_account:
        bank_account_parts.append(f"К/с: {company.correspondent_account}")
    if bank_account_parts:
        lines.append("  ".join(bank_account_parts))
    signer = company.signer_name or company.director_name
    if signer:
        lines.append(f"Подписант: {signer}")
    for line in lines:
        elements.append(Paragraph(line, body_style))
    return elements


def _resolve_company_asset(company: Company, attr: str) -> Path | None:
    relative_path = getattr(company, attr, None)
    if not relative_path:
        return None
    return resolve_storage_path(relative_path)


def _resolve_watermark_text(company_name: str, company: Company | None = None) -> str:
    if company is not None and company.watermark_text:
        return company.watermark_text
    if company_name == "ИП Гордеев А.Н.":
        return "ИП ГОРДЕЕВ А.Н."
    return "ДЕКОРАРТСТРОЙ"


def _build_pdf_elements(
    snapshot: dict[str, Any],
    *,
    stamp_applied: bool = False,
    signature_applied: bool = False,
    is_final_approved: bool = False,
    company: Company | None = None,
) -> list:
    _ensure_fonts()
    estimate = snapshot["estimate"]
    object_name = estimate.get("object_name") or "Не указан"
    customer_name = estimate.get("customer_name") or "Не указан"
    contract_label = estimate.get("contract_label") or "Не указан"
    company_name = estimate.get("company_name") or "ООО Декорартстрой"
    status_label = str(estimate.get("status") or "draft")
    discount_label = str(estimate.get("discount") or "0")

    header_style = ParagraphStyle("header", fontName=FONT_BOLD, fontSize=12, leading=14)
    body_style = ParagraphStyle("body", fontName=FONT_REGULAR, fontSize=8, leading=10)
    small_style = ParagraphStyle("small", fontName=FONT_REGULAR, fontSize=7, leading=9)
    stamp_style = ParagraphStyle("stamp", fontName=FONT_REGULAR, fontSize=9, leading=12)

    elements = [
        Paragraph(f"Самостоятельная смета № {estimate.get('estimate_number')}", header_style),
        Spacer(1, 3 * mm),
        Paragraph(f"Статус: {status_label}", body_style),
        Paragraph(f"Объект: {object_name}", body_style),
        Paragraph(f"Заказчик: {customer_name}", body_style),
        Paragraph(f"Договор: {contract_label}", body_style),
    ]
    if company is not None:
        elements.extend(_company_details_elements(company, body_style))
    else:
        elements.append(Paragraph(f"Компания: {company_name}", body_style))
    elements.append(Paragraph(f"Скидка: {discount_label}%", body_style))
    elements.append(Spacer(1, 4 * mm))

    table_data, section_styles, grand_total, discounted_total = _build_pdf_table(snapshot)

    table = Table(table_data, colWidths=[74 * mm, 14 * mm, 18 * mm, 24 * mm, 26 * mm, 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                *section_styles,
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(f"Итого до скидки: {_format_money(grand_total)}", body_style))
    elements.append(Paragraph(f"Скидка: {discount_label}%", body_style))
    elements.append(Paragraph(f"Итого после скидки: {_format_money(discounted_total)}", body_style))
    elements.append(Spacer(1, 5 * mm))

    if is_final_approved:
        elements.append(Spacer(1, 8 * mm))
        stamp_cell_content: Any = ""
        sig_cell_content: Any = ""
        if stamp_applied:
            stamp_file = _resolve_company_asset(company, "stamp_path") if company else None
            if stamp_file:
                stamp_cell_content = Image(str(stamp_file), width=35 * mm, height=35 * mm)
            else:
                stamp_cell_content = Paragraph("М.П.", stamp_style)
        if signature_applied:
            sig_file = _resolve_company_asset(company, "signature_path") if company else None
            if sig_file:
                sig_cell_content = Image(str(sig_file), width=55 * mm, height=20 * mm)
            else:
                sig_cell_content = Paragraph("Подпись", stamp_style)
        signature_table = Table(
            [[stamp_cell_content, sig_cell_content]],
            colWidths=[80 * mm, 80 * mm],
        )
        signature_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("LINEBELOW", (0, 0), (0, 0), 0.5, colors.black),
                    ("LINEBELOW", (1, 0), (1, 0), 0.5, colors.black),
                ]
            )
        )
        elements.append(signature_table)
        elements.append(Spacer(1, 12 * mm))
        elements.append(
            Paragraph(
                f"Финальная согласованная версия: печать={'да' if stamp_applied else 'нет'}, подпись={'да' if signature_applied else 'нет'}",
                small_style,
            )
        )
    elif stamp_applied or signature_applied:
        elements.append(
            Paragraph(
                f"Финальная версия: печать={'да' if stamp_applied else 'нет'}, подпись={'да' if signature_applied else 'нет'}",
                small_style,
            )
        )
    elements.append(Paragraph(f"Сформировано: {datetime.now().isoformat(timespec='seconds')}", small_style))
    return elements


def export_standalone_estimate_pdf(snapshot: dict[str, Any], *, stamp_applied: bool = False, signature_applied: bool = False, company: Company | None = None) -> Path:
    estimate = snapshot["estimate"]
    approved = _is_approved_pdf_status(estimate.get("status"))
    if not approved and (stamp_applied or signature_applied):
        raise ValueError("Печать и подпись допустимы только для согласованной standalone-сметы.")

    _ensure_fonts()
    title = estimate.get("title") or estimate.get("object_name") or estimate.get("estimate_number") or "Смета"
    path = build_standalone_estimate_pdf_path(int(estimate["id"]), title, approved=approved)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    elements = _build_pdf_elements(snapshot, stamp_applied=stamp_applied, signature_applied=signature_applied, company=company)

    watermark_enabled = _draft_watermark_enabled(estimate, approved=approved)
    company_name = estimate.get("company_name") or "ООО Декорартстрой"
    watermark_text = _resolve_watermark_text(company_name, company)

    def add_watermark(canvas, _doc):
        if not watermark_enabled:
            return
        canvas.saveState()
        canvas.setFont(FONT_BOLD, 65)
        canvas.setFillGray(0.5, 0.15)
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    return path


def export_final_approved_pdf(
    snapshot: dict[str, Any],
    *,
    stamp_applied: bool = False,
    signature_applied: bool = False,
    company: Company | None = None,
) -> Path:
    estimate = snapshot["estimate"]
    if not _is_approved_pdf_status(estimate.get("status")):
        raise ValueError("Final PDF можно создать только из snapshot со статусом approved/in_progress.")
    if not _is_approved_pdf_status(estimate.get("status")) and (stamp_applied or signature_applied):
        raise ValueError("Печать и подпись допустимы только для согласованной standalone-сметы.")

    _ensure_fonts()
    title = estimate.get("title") or estimate.get("object_name") or estimate.get("estimate_number") or "Смета"
    path = build_standalone_estimate_pdf_path(int(estimate["id"]), title, approved=True)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    elements = _build_pdf_elements(snapshot, stamp_applied=stamp_applied, signature_applied=signature_applied, is_final_approved=True, company=company)

    watermark_text = _resolve_watermark_text(estimate.get("company_name") or "ООО Декорартстрой", company)

    def add_watermark(canvas, _doc):
        return

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    return path
