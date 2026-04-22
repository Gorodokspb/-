import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from webapp.config import get_settings
from webapp.db import (
    fetch_dashboard_counts,
    fetch_document,
    fetch_project,
    fetch_project_documents,
    fetch_project_estimate,
    fetch_project_events,
    fetch_projects,
    save_project_estimate,
)
from webapp.estimate_pdf import generate_estimate_pdf
from webapp.storage import ensure_storage_dirs, resolve_storage_path


settings = get_settings()
ensure_storage_dirs()

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


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("is_authenticated"))


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
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
            "username": request.session.get("username", settings.admin_username),
            "saved": saved,
            "error": error,
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
    watermark: str | None,
) -> tuple[dict, list[dict]]:
    try:
        editor_rows = json.loads(items_payload or "[]")
    except json.JSONDecodeError:
        editor_rows = []

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
        "editor_rows": editor_rows,
        "editor_rows_json": json.dumps(editor_rows, ensure_ascii=False),
    }
    return draft_estimate, editor_rows


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
    if username == settings.admin_username and password == settings.admin_password:
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
        },
    )


@app.get("/projects/{project_id}")
def project_detail_page(project_id: int, request: Request):
    require_auth(request)
    project = fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    documents = fetch_project_documents(project_id)
    events = fetch_project_events(project_id)
    for document in documents:
        document["has_file"] = bool(resolve_storage_path(document.get("file_path")))
        document["has_draft"] = bool(resolve_storage_path(document.get("draft_path")))
        document["has_pdf"] = bool(resolve_storage_path(document.get("pdf_path")))

    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": project,
            "documents": documents,
            "events": events,
            "username": request.session.get("username", settings.admin_username),
        },
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
    watermark: str | None = Form(None),
):
    require_auth(request)
    estimate = fetch_project_estimate(project_id)
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    draft_estimate, editor_rows = normalize_estimate_form_data(
        estimate,
        company_name,
        object_name,
        customer_name,
        contract_label,
        discount,
        items_payload,
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
    watermark: str | None = Form(None),
):
    require_auth(request)
    estimate = fetch_project_estimate(project_id)
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден.")

    draft_estimate, editor_rows = normalize_estimate_form_data(
        estimate,
        company_name,
        object_name,
        customer_name,
        contract_label,
        discount,
        items_payload,
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
