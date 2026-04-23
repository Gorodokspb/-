import json
import hashlib
import hmac
import secrets
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from webapp.config import get_settings
from webapp.db import (
    create_counterparty,
    create_project,
    ensure_web_user,
    ensure_web_users_table,
    fetch_counterparties,
    fetch_dashboard_counts,
    fetch_price_library,
    fetch_project,
    fetch_project_documents,
    fetch_project_estimate,
    fetch_project_events,
    fetch_projects,
    fetch_web_user,
    save_project_estimate,
    update_project_card,
    update_web_user_password,
)
from webapp.estimate_pdf import generate_estimate_pdf
from webapp.storage import ensure_storage_dirs, resolve_storage_path


settings = get_settings()
ensure_storage_dirs()

PROJECT_STATUS_OPTIONS = [
    "Черновик",
    "В работе",
    "Пауза",
    "Завершен",
]

app = FastAPI(title="Dekorartstroy CRM Web")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)


@app.on_event("startup")
def startup_web_auth() -> None:
    ensure_auth_bootstrap()


def status_class(value: str) -> str:
    mapping = {
        "Черновик": "draft",
        "В работе": "active",
        "Пауза": "paused",
        "Завершен": "done",
        "Завершён": "done",
    }
    return mapping.get((value or "").strip(), "neutral")


templates.env.filters["status_class"] = status_class


def hash_password(password: str) -> str:
    normalized_password = str(password or "")
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        normalized_password.encode("utf-8"),
        salt,
        240000,
    )
    return f"pbkdf2_sha256$240000${salt.hex()}${derived_key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    normalized_password = str(password or "")
    normalized_hash = str(password_hash or "").strip()
    try:
        algorithm, iterations_raw, salt_hex, digest_hex = normalized_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            normalized_password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_raw),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(derived_key.hex(), digest_hex)


def ensure_auth_bootstrap() -> None:
    ensure_web_users_table()
    ensure_web_user(
        settings.admin_username,
        hash_password(settings.admin_password),
        "system-bootstrap",
    )


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("is_authenticated"))


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )


def render_project_detail(
    request: Request,
    project: dict,
    *,
    counterparties: list[dict] | None = None,
    documents: list[dict] | None = None,
    events: list[dict] | None = None,
    saved: bool = False,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    counterparties = counterparties if counterparties is not None else fetch_counterparties()
    documents = documents if documents is not None else fetch_project_documents(int(project["id"]))
    events = events if events is not None else fetch_project_events(int(project["id"]))

    for document in documents:
        document["has_file"] = bool(resolve_storage_path(document.get("file_path")))
        document["has_draft"] = bool(resolve_storage_path(document.get("draft_path")))
        document["has_pdf"] = bool(resolve_storage_path(document.get("pdf_path")))

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": project,
            "counterparties": counterparties,
            "documents": documents,
            "events": events,
            "status_options": PROJECT_STATUS_OPTIONS,
            "username": request.session.get("username", settings.admin_username),
            "saved": saved,
            "error": error,
        },
        status_code=status_code,
    )


def render_estimate_editor(
    request: Request,
    estimate: dict,
    *,
    saved: bool = False,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request=request,
        name="estimate_editor.html",
        context={
            "project": estimate["project"],
            "estimate": estimate,
            "price_library_json": json.dumps(fetch_price_library(), ensure_ascii=False),
            "estimate_calc_state_json": json.dumps(estimate.get("calc_state") or {}, ensure_ascii=False),
            "username": request.session.get("username", settings.admin_username),
            "saved": saved,
            "error": error,
        },
        status_code=status_code,
    )


def render_password_change_page(
    request: Request,
    *,
    error: str | None = None,
    saved: bool = False,
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request=request,
        name="password_change.html",
        context={
            "username": request.session.get("username", settings.admin_username),
            "error": error,
            "saved": saved,
        },
        status_code=status_code,
    )


def normalize_estimate_form_data(
    estimate: dict,
    company_name: str,
    object_name: str,
    customer_name: str,
    contract_label: str,
    discount: str,
    items_payload: str,
    calc_state_payload: str,
    watermark: str | None,
) -> tuple[dict, list[dict], dict]:
    try:
        editor_rows = json.loads(items_payload or "[]")
    except json.JSONDecodeError:
        editor_rows = []

    try:
        calc_state = json.loads(calc_state_payload or "{}")
    except json.JSONDecodeError:
        calc_state = estimate.get("calc_state") or {}
    if not isinstance(calc_state, dict):
        calc_state = estimate.get("calc_state") or {}

    normalized_object_name = (
        (object_name or "").strip()
        or estimate["project"]["address"]
        or estimate["project"]["project_name"]
    )
    normalized_customer_name = (customer_name or "").strip()
    normalized_contract_label = (contract_label or "").strip()
    normalized_company_name = (company_name or "").strip() or "ООО Декорартстрой"

    draft_estimate = {
        **estimate,
        "company": normalized_company_name,
        "object_name": normalized_object_name,
        "customer_name": normalized_customer_name,
        "contract_label": normalized_contract_label,
        "discount": discount,
        "watermark": bool(watermark),
        "calc_state": calc_state,
        "editor_rows": editor_rows,
        "editor_rows_json": json.dumps(editor_rows, ensure_ascii=False),
    }
    return draft_estimate, editor_rows, calc_state


@app.get("/")
def index():
    return RedirectResponse(url="/projects", status_code=status.HTTP_302_FOUND)


@app.get("/login")
def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/projects", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ensure_auth_bootstrap()
    user = fetch_web_user(username)
    if user and verify_password(password, user.get("password_hash", "")):
        request.session["is_authenticated"] = True
        request.session["username"] = username
        return RedirectResponse(url="/projects", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Неверный логин или пароль."},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/account/password")
def password_change_page(request: Request):
    require_auth(request)
    return render_password_change_page(
        request,
        saved=request.query_params.get("changed") == "1",
    )


@app.post("/account/password")
def password_change_submit(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
):
    require_auth(request)
    username = request.session.get("username", settings.admin_username)
    user = fetch_web_user(username)
    if not user:
        return render_password_change_page(
            request,
            error="Учетная запись не найдена. Перезайдите в систему.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not verify_password(current_password, user.get("password_hash", "")):
        return render_password_change_page(
            request,
            error="Текущий пароль указан неверно.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if len(new_password or "") < 8:
        return render_password_change_page(
            request,
            error="Новый пароль должен быть не короче 8 символов.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if new_password != confirm_password:
        return render_password_change_page(
            request,
            error="Подтверждение нового пароля не совпадает.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if verify_password(new_password, user.get("password_hash", "")):
        return render_password_change_page(
            request,
            error="Новый пароль должен отличаться от текущего.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    update_web_user_password(username, hash_password(new_password), username)
    return RedirectResponse(url="/account/password?changed=1", status_code=status.HTTP_302_FOUND)


@app.get("/projects")
def projects_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "projects": fetch_projects(),
            "counts": fetch_dashboard_counts(),
            "username": request.session.get("username", settings.admin_username),
            "created": request.query_params.get("created", ""),
        },
    )


def render_project_create_page(
    request: Request,
    *,
    form_data: dict | None = None,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    form_data = form_data or {
        "project_name": "",
        "address": "",
        "counterparty_id": "",
        "status": PROJECT_STATUS_OPTIONS[0],
        "contract": "",
        "contract_date": "",
        "notes": "",
    }
    return templates.TemplateResponse(
        request=request,
        name="project_create.html",
        context={
            "counterparties": fetch_counterparties(),
            "status_options": PROJECT_STATUS_OPTIONS,
            "form_data": form_data,
            "error": error,
            "username": request.session.get("username", settings.admin_username),
        },
        status_code=status_code,
    )


def render_counterparty_create_page(
    request: Request,
    *,
    form_data: dict | None = None,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    form_data = form_data or {
        "counterparty_type": "Физлицо",
        "display_name": "",
        "full_name": "",
        "company_name": "",
        "phone": "",
        "email": "",
        "inn": "",
        "notes": "",
    }
    return templates.TemplateResponse(
        request=request,
        name="counterparty_create.html",
        context={
            "form_data": form_data,
            "error": error,
            "username": request.session.get("username", settings.admin_username),
        },
        status_code=status_code,
    )


@app.get("/projects/new")
def project_create_page(request: Request):
    require_auth(request)
    return render_project_create_page(request)


@app.post("/projects/new")
def project_create_submit(
    request: Request,
    project_name: str = Form(""),
    address: str = Form(""),
    counterparty_id: str = Form(""),
    status_value: str = Form(""),
    contract: str = Form(""),
    contract_date: str = Form(""),
    notes: str = Form(""),
):
    require_auth(request)
    draft = {
        "project_name": (project_name or "").strip(),
        "address": (address or "").strip(),
        "counterparty_id": (counterparty_id or "").strip(),
        "status": (status_value or "").strip() or PROJECT_STATUS_OPTIONS[0],
        "contract": (contract or "").strip(),
        "contract_date": (contract_date or "").strip(),
        "notes": notes or "",
    }
    if draft["status"] not in PROJECT_STATUS_OPTIONS:
        draft["status"] = PROJECT_STATUS_OPTIONS[0]

    try:
        created_project_id = create_project(
            request.session.get("username", settings.admin_username),
            project_name=draft["project_name"],
            address=draft["address"],
            counterparty_id=int(draft["counterparty_id"]) if draft["counterparty_id"].isdigit() else None,
            status=draft["status"],
            contract=draft["contract"],
            contract_date=draft["contract_date"],
            notes=draft["notes"],
        )
    except ValueError as exc:
        return render_project_create_page(
            request,
            form_data=draft,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(
        url=f"/projects/{created_project_id}?saved=1",
        status_code=status.HTTP_302_FOUND,
    )


@app.get("/counterparties/new")
def counterparty_create_page(request: Request):
    require_auth(request)
    return render_counterparty_create_page(request)


@app.post("/counterparties/new")
def counterparty_create_submit(
    request: Request,
    counterparty_type: str = Form("Физлицо"),
    display_name: str = Form(""),
    full_name: str = Form(""),
    company_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    inn: str = Form(""),
    notes: str = Form(""),
):
    require_auth(request)
    draft = {
        "counterparty_type": (counterparty_type or "").strip() or "Физлицо",
        "display_name": (display_name or "").strip(),
        "full_name": (full_name or "").strip(),
        "company_name": (company_name or "").strip(),
        "phone": (phone or "").strip(),
        "email": (email or "").strip(),
        "inn": (inn or "").strip(),
        "notes": notes or "",
    }

    try:
        create_counterparty(
            request.session.get("username", settings.admin_username),
            counterparty_type=draft["counterparty_type"],
            display_name=draft["display_name"],
            full_name=draft["full_name"],
            company_name=draft["company_name"],
            phone=draft["phone"],
            email=draft["email"],
            inn=draft["inn"],
            notes=draft["notes"],
        )
    except ValueError as exc:
        return render_counterparty_create_page(
            request,
            form_data=draft,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(
        url="/projects?created=counterparty",
        status_code=status.HTTP_302_FOUND,
    )


@app.get("/projects/{project_id}")
def project_detail_page(project_id: int, request: Request):
    require_auth(request)
    project = fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    return render_project_detail(
        request,
        project,
        saved=request.query_params.get("saved") == "1",
    )


@app.post("/projects/{project_id}")
def project_detail_save(
    project_id: int,
    request: Request,
    project_name: str = Form(""),
    address: str = Form(""),
    customer: str = Form(""),
    counterparty_id: str = Form(""),
    status_value: str = Form(""),
    contract: str = Form(""),
    contract_date: str = Form(""),
    notes: str = Form(""),
):
    require_auth(request)
    project = fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    draft_project = {
        **project,
        "project_name": (project_name or "").strip(),
        "address": (address or "").strip(),
        "customer": (customer or "").strip(),
        "status": (status_value or "").strip() or project.get("status") or PROJECT_STATUS_OPTIONS[0],
        "contract": (contract or "").strip(),
        "contract_date": (contract_date or "").strip(),
        "notes": notes or "",
    }

    if draft_project["status"] not in PROJECT_STATUS_OPTIONS:
        draft_project["status"] = PROJECT_STATUS_OPTIONS[0]

    if not draft_project["project_name"] and not draft_project["address"]:
        return render_project_detail(
            request,
            draft_project,
            error="Заполните хотя бы название проекта или адрес.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    saved_project = update_project_card(
        project_id,
        request.session.get("username", settings.admin_username),
        project_name=draft_project["project_name"],
        address=draft_project["address"],
        customer=draft_project["customer"],
        counterparty_id=int(counterparty_id) if (counterparty_id or "").strip().isdigit() else None,
        status=draft_project["status"],
        contract=draft_project["contract"],
        contract_date=draft_project["contract_date"],
        notes=draft_project["notes"],
    )
    if not saved_project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить карточку проекта.",
        )

    return RedirectResponse(
        url=f"/projects/{project_id}?saved=1",
        status_code=status.HTTP_302_FOUND,
    )


@app.get("/projects/{project_id}/estimate")
def project_estimate_page(project_id: int, request: Request):
    require_auth(request)
    estimate = fetch_project_estimate(project_id)
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    return render_estimate_editor(
        request,
        estimate,
        saved=request.query_params.get("saved") == "1",
    )


@app.post("/projects/{project_id}/estimate")
def project_estimate_save(
    project_id: int,
    request: Request,
    company_name: str = Form("ООО Декорартстрой"),
    object_name: str = Form(""),
    customer_name: str = Form(""),
    contract_label: str = Form(""),
    discount: str = Form(""),
    items_payload: str = Form("[]"),
    calc_state_payload: str = Form("{}"),
    watermark: str | None = Form(None),
):
    require_auth(request)
    estimate = fetch_project_estimate(project_id)
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    draft_estimate, editor_rows, calc_state = normalize_estimate_form_data(
        estimate,
        company_name,
        object_name,
        customer_name,
        contract_label,
        discount,
        items_payload,
        calc_state_payload,
        watermark,
    )

    if not draft_estimate["object_name"]:
        return render_estimate_editor(
            request,
            draft_estimate,
            error="Укажите объект сметы перед сохранением.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    save_project_estimate(
        project_id=project_id,
        username=request.session.get("username", settings.admin_username),
        company_name=draft_estimate["company"],
        object_name=draft_estimate["object_name"],
        customer_name=draft_estimate["customer_name"],
        contract_label=draft_estimate["contract_label"],
        discount_raw=draft_estimate["discount"],
        watermark=draft_estimate["watermark"],
        editor_rows=editor_rows,
        calc_state=calc_state,
    )
    return RedirectResponse(
        url=f"/projects/{project_id}/estimate?saved=1",
        status_code=status.HTTP_302_FOUND,
    )


@app.post("/projects/{project_id}/estimate/pdf")
def project_estimate_pdf(
    project_id: int,
    request: Request,
    company_name: str = Form("ООО Декорартстрой"),
    object_name: str = Form(""),
    customer_name: str = Form(""),
    contract_label: str = Form(""),
    discount: str = Form(""),
    items_payload: str = Form("[]"),
    calc_state_payload: str = Form("{}"),
    watermark: str | None = Form(None),
):
    require_auth(request)
    estimate = fetch_project_estimate(project_id)
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    draft_estimate, editor_rows, calc_state = normalize_estimate_form_data(
        estimate,
        company_name,
        object_name,
        customer_name,
        contract_label,
        discount,
        items_payload,
        calc_state_payload,
        watermark,
    )

    missing_fields = []
    if not draft_estimate["object_name"]:
        missing_fields.append("объект")
    if not draft_estimate["customer_name"]:
        missing_fields.append("заказчика")
    if not draft_estimate["contract_label"]:
        missing_fields.append("договор")

    if missing_fields:
        return render_estimate_editor(
            request,
            draft_estimate,
            error=f"Для PDF заполните: {', '.join(missing_fields)}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    saved_estimate = save_project_estimate(
        project_id=project_id,
        username=request.session.get("username", settings.admin_username),
        company_name=draft_estimate["company"],
        object_name=draft_estimate["object_name"],
        customer_name=draft_estimate["customer_name"],
        contract_label=draft_estimate["contract_label"],
        discount_raw=draft_estimate["discount"],
        watermark=draft_estimate["watermark"],
        editor_rows=editor_rows,
        calc_state=calc_state,
    )
    if not saved_estimate:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить смету перед формированием PDF.",
        )

    pdf_path = generate_estimate_pdf(
        saved_estimate,
        request.session.get("username", settings.admin_username),
    )
    return FileResponse(
        path=pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf",
    )


@app.get("/documents/{document_id}/download")
def download_document(document_id: int, request: Request, kind: str = "file"):
    require_auth(request)
    document = fetch_document(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден.")

    path_by_kind = {
        "file": document.get("file_path"),
        "draft": document.get("draft_path"),
        "pdf": document.get("pdf_path"),
    }
    relative_path = path_by_kind.get(kind)
    absolute_path = resolve_storage_path(relative_path or "")
    if not absolute_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл отсутствует в серверном хранилище.",
        )

    return FileResponse(path=absolute_path, filename=absolute_path.name)
