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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from webapp.config import get_settings
from webapp.storage import sanitize_filename

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


def export_standalone_estimate_pdf(snapshot: dict[str, Any], *, stamp_applied: bool = False, signature_applied: bool = False) -> Path:
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
    header_style = ParagraphStyle("header", fontName=FONT_BOLD, fontSize=12, leading=14)
    body_style = ParagraphStyle("body", fontName=FONT_REGULAR, fontSize=8, leading=10)
    small_style = ParagraphStyle("small", fontName=FONT_REGULAR, fontSize=7, leading=9)

    object_name = estimate.get("object_name") or "Не указан"
    customer_name = estimate.get("customer_name") or "Не указан"
    contract_label = estimate.get("contract_label") or "Не указан"
    company_name = estimate.get("company_name") or "ООО Декорартстрой"
    status_label = str(estimate.get("status") or "draft")
    discount_label = str(estimate.get("discount") or "0")

    elements = [
        Paragraph(f"Самостоятельная смета № {estimate.get('estimate_number')}", header_style),
        Spacer(1, 3 * mm),
        Paragraph(f"Статус: {status_label}", body_style),
        Paragraph(f"Объект: {object_name}", body_style),
        Paragraph(f"Заказчик: {customer_name}", body_style),
        Paragraph(f"Договор: {contract_label}", body_style),
        Paragraph(f"Компания: {company_name}", body_style),
        Paragraph(f"Скидка: {discount_label}%", body_style),
        Spacer(1, 4 * mm),
    ]

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

    if stamp_applied or signature_applied:
        elements.append(
            Paragraph(
                f"Финальная версия: печать={'да' if stamp_applied else 'нет'}, подпись={'да' if signature_applied else 'нет'}",
                small_style,
            )
        )
    elements.append(Paragraph(f"Сформировано: {datetime.now().isoformat(timespec='seconds')}", small_style))

    watermark_enabled = _draft_watermark_enabled(estimate, approved=approved)
    watermark_text = "ИП ГОРДЕЕВ А.Н." if company_name == "ИП Гордеев А.Н." else "ДЕКОРАРТСТРОЙ"

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
