from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from webapp.db import format_tree_number, get_connection, parse_tree_number
from webapp.storage import build_estimate_pdf_path


FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
SMETA_DOC_TYPE = "Смета (приложение № 1)"


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

    raise RuntimeError("Не удалось найти шрифт для генерации PDF сметы.")


def _split_object_lines(value: str) -> tuple[str, str]:
    text = " ".join((value or "").split())
    if not text:
        return "", ""
    parts = [part.strip() for part in text.split(",", 1)]
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _get_company_details(company_name: str) -> dict:
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


def _format_rub(value: float) -> str:
    return f"{round(value):,.0f}".replace(",", " ")


def _build_pdf_rows(estimate: dict) -> list[dict]:
    discount_percent = parse_tree_number(estimate.get("discount"))
    rows = []
    for row in estimate.get("editor_rows", []):
        if row.get("row_type") == "section":
            rows.append({"type": "section", "name": row.get("name", "Раздел")})
            continue

        qty = parse_tree_number(row.get("quantity"))
        price = parse_tree_number(row.get("price"))
        total = qty * price
        total_discount = total * max(0.0, 1.0 - discount_percent / 100.0)
        rows.append(
            {
                "type": "item",
                "name": row.get("name", ""),
                "unit": row.get("unit", ""),
                "qty": format_tree_number(qty) if qty else "",
                "price": format_tree_number(price) if price else "",
                "total": total,
                "discounted_total": total_discount,
            }
        )
    return rows


def _update_estimate_pdf_document(project_id: int, pdf_relative_path: str, title: str, username: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET title = %s, status = %s, file_path = %s, pdf_path = %s, updated_at = %s
                WHERE project_id = %s AND doc_type = %s
                """,
                (title, "Черновик", pdf_relative_path, pdf_relative_path, now, project_id, SMETA_DOC_TYPE),
            )
            cur.execute(
                """
                INSERT INTO project_events (project_id, event_type, event_text, author, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (project_id, "document", "Сформирован PDF сметы из web-редактора", username, now),
            )
        conn.commit()


def generate_estimate_pdf(estimate: dict, username: str) -> Path:
    _ensure_fonts()

    project = estimate["project"]
    project_id = int(project["id"])
    project_name = str(project.get("project_name") or "").strip()
    company_name = str(estimate.get("company") or "ООО Декорартстрой").strip() or "ООО Декорартстрой"
    object_name = str(estimate.get("object_name") or project_name).strip()
    customer_name = str(estimate.get("customer_name") or "").strip()
    contract_name = str(estimate.get("contract_label") or "").strip()
    watermark = bool(estimate.get("watermark", True))
    discount_percent = parse_tree_number(estimate.get("discount"))
    rows = _build_pdf_rows(estimate)

    absolute_pdf_path, relative_pdf_path = build_estimate_pdf_path(project_id, project_name, object_name)
    absolute_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(absolute_pdf_path),
        pagesize=A4,
        rightMargin=7 * mm,
        leftMargin=7 * mm,
        topMargin=8 * mm,
        bottomMargin=10 * mm,
    )

    watermark_text = "ИП ГОРДЕЕВ А.Н." if company_name == "ИП Гордеев А.Н." else "ДЕКОРАРТСТРОЙ"

    def add_watermark(canvas, _doc):
        if not watermark:
            return
        canvas.saveState()
        canvas.setFont(FONT_BOLD, 65)
        canvas.setFillGray(0.5, 0.15)
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

    company_details = _get_company_details(company_name)
    left_style = ParagraphStyle("L", fontName=FONT_REGULAR, fontSize=6.6, leading=8, alignment=0)
    right_style = ParagraphStyle("R", fontName=FONT_REGULAR, fontSize=6.6, leading=8, alignment=2)
    row_style = ParagraphStyle("N", fontName=FONT_REGULAR, fontSize=6.0, leading=6.4)

    left_info = "<br/>".join([company_details["title"], *company_details["details"]])
    object_head, object_tail = _split_object_lines(object_name)
    meta_lines = [
        "Приложение № 1",
        f"К договору: {contract_name}",
        f"Заказчик: {customer_name}",
        f"Объект: {object_head or 'не указан'}",
    ]
    if object_tail:
        meta_lines.append(object_tail)
    right_info = "<br/>".join(meta_lines)

    elements = []
    header = Table(
        [[Paragraph(left_info, left_style), "", Paragraph(right_info, right_style)]],
        colWidths=[84 * mm, 16 * mm, 84 * mm],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(header)
    elements.append(Spacer(1, 2 * mm))

    discount_label = (
        f"Со скидкой ({int(discount_percent) if float(discount_percent).is_integer() else discount_percent}%)"
        if discount_percent > 0
        else "Со скидкой"
    )
    table_data = [["Наименование", "Ед.", "Кол-во", "Цена", "Итого", discount_label]]
    table_style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTSIZE", (0, 0), (-1, -1), 6.0),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 0.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
    )

    row_index = 1
    room_total = 0.0
    room_total_disc = 0.0
    grand_total = 0.0
    grand_total_disc = 0.0

    for row in rows:
        if row["type"] == "section":
            if room_total > 0:
                table_data.append(
                    [
                        "Итого по разделу:",
                        "",
                        "",
                        "",
                        _format_rub(room_total),
                        _format_rub(room_total_disc),
                    ]
                )
                table_style.add("SPAN", (0, row_index), (3, row_index))
                table_style.add("FONTNAME", (0, row_index), (-1, row_index), FONT_BOLD)
                table_style.add("ALIGN", (0, row_index), (3, row_index), "RIGHT")
                row_index += 1
                room_total = 0.0
                room_total_disc = 0.0

            table_data.append([row.get("name", "Раздел"), "", "", "", "", ""])
            table_style.add("SPAN", (0, row_index), (-1, row_index))
            table_style.add("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#e8e8e8"))
            table_style.add("FONTNAME", (0, row_index), (-1, row_index), FONT_BOLD)
            table_style.add("ALIGN", (0, row_index), (-1, row_index), "CENTER")
            row_index += 1
            continue

        total_value = float(row.get("total") or 0)
        total_disc_value = float(row.get("discounted_total") or 0)
        table_data.append(
            [
                Paragraph(str(row.get("name") or ""), row_style),
                str(row.get("unit") or ""),
                str(row.get("qty") or ""),
                _format_rub(parse_tree_number(row.get("price"))),
                _format_rub(total_value),
                _format_rub(total_disc_value),
            ]
        )
        room_total += total_value
        room_total_disc += total_disc_value
        grand_total += total_value
        grand_total_disc += total_disc_value
        row_index += 1

    if room_total > 0:
        table_data.append(
            [
                "Итого по разделу:",
                "",
                "",
                "",
                _format_rub(room_total),
                _format_rub(room_total_disc),
            ]
        )
        table_style.add("SPAN", (0, row_index), (3, row_index))
        table_style.add("FONTNAME", (0, row_index), (-1, row_index), FONT_BOLD)
        table_style.add("ALIGN", (0, row_index), (3, row_index), "RIGHT")

    table = Table(table_data, colWidths=[78 * mm, 12 * mm, 16 * mm, 23 * mm, 24 * mm, 27 * mm])
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 4 * mm))

    footer_data = [["Итого по документу:", f"{_format_rub(grand_total)} руб."]]
    if discount_percent > 0:
        footer_data.append(["Скидка:", f"{_format_rub(grand_total - grand_total_disc)} руб."])
        footer_data.append(["ИТОГО СО СКИДКОЙ:", f"{_format_rub(grand_total_disc)} руб."])
    footer = Table(footer_data, colWidths=[145 * mm, 40 * mm])
    footer.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("ALIGN", (0, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(footer)

    year = datetime.now().year
    sign_left = ParagraphStyle("SigL", fontName=FONT_REGULAR, fontSize=6.5, leading=7.2, alignment=0)
    sign_right = ParagraphStyle("SigR", fontName=FONT_REGULAR, fontSize=6.5, leading=7.2, alignment=2)
    left_sign = (
        f"<b>Подрядчик:</b><br/>{company_name}<br/><br/>________________ / ____________ /"
        f"<br/>« ___ » ____________ {year} г.<br/>М.П."
    )
    right_sign = (
        f"<b>Заказчик:</b><br/>{customer_name}<br/><br/>________________ / ____________ /"
        f"<br/>« ___ » ____________ {year} г."
    )
    sign_table = Table([[Paragraph(left_sign, sign_left), "", Paragraph(right_sign, sign_right)]], colWidths=[85 * mm, 15 * mm, 85 * mm])
    sign_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(Spacer(1, 5 * mm))
    elements.append(sign_table)

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)

    title = f"Смета - {object_name}" if object_name else "Смета"
    _update_estimate_pdf_document(project_id, relative_pdf_path, title, username)
    return absolute_pdf_path
