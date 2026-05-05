import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile

from webapp.company_repository import (
    CompanyCreateInput,
    CompanyRepository,
    CompanyService,
    CompanyUpdateInput,
)
from webapp.config import get_settings
from webapp.storage import resolve_storage_path, storage_relative_path

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

service = CompanyService()

_MAX_UPLOAD_SIZE = 2 * 1024 * 1024

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _require_auth(request: Request) -> None:
    if not request.session.get("is_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )


def _username(request: Request) -> str:
    return str(request.session.get("username") or get_settings().admin_username)


def _company_assets_dir(company_id: int) -> Path:
    settings = get_settings()
    d = settings.storage_root / "company-assets" / str(company_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_png(file: UploadFile, data: bytes) -> None:
    if len(data) > _MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 2 МБ).")
    ct = (file.content_type or "").lower()
    if ct and "image/png" not in ct:
        raise HTTPException(status_code=400, detail="Допускается только PNG.")
    fn = (file.filename or "").lower()
    if not fn.endswith(".png"):
        raise HTTPException(status_code=400, detail="Файл должен иметь расширение .png.")
    if len(data) < 8 or data[:8] != _PNG_MAGIC:
        raise HTTPException(status_code=400, detail="Файл не является корректным PNG.")


@router.get("/settings/companies")
def companies_list(request: Request):
    _require_auth(request)
    companies = service.list_companies(include_inactive=True)
    return templates.TemplateResponse(
        "companies_list.html",
        {
            "request": request,
            "username": _username(request),
            "companies": companies,
            "active_section": "settings",
        },
    )


@router.get("/settings/companies/new")
def company_new(request: Request):
    _require_auth(request)
    return templates.TemplateResponse(
        "company_detail.html",
        {
            "request": request,
            "username": _username(request),
            "company": None,
            "active_section": "settings",
        },
    )


@router.post("/settings/companies")
async def company_create(request: Request):
    _require_auth(request)
    form = await request.form()
    data = dict(form)
    company = service.create_company(
        CompanyCreateInput(
            legal_name=str(data.get("legal_name") or "").strip(),
            short_name=str(data.get("short_name") or "").strip(),
            inn=str(data.get("inn") or "").strip() or None,
            kpp=str(data.get("kpp") or "").strip() or None,
            ogrn=str(data.get("ogrn") or "").strip() or None,
            ogrnip=str(data.get("ogrnip") or "").strip() or None,
            legal_address=str(data.get("legal_address") or "").strip() or None,
            phone=str(data.get("phone") or "").strip() or None,
            email=str(data.get("email") or "").strip() or None,
            website=str(data.get("website") or "").strip() or None,
            bank_name=str(data.get("bank_name") or "").strip() or None,
            bik=str(data.get("bik") or "").strip() or None,
            account=str(data.get("account") or "").strip() or None,
            correspondent_account=str(data.get("correspondent_account") or "").strip() or None,
            director_name=str(data.get("director_name") or "").strip() or None,
            signer_name=str(data.get("signer_name") or "").strip() or None,
            watermark_text=str(data.get("watermark_text") or "").strip() or "ДЕКОРАРТСТРОЙ",
        )
    )
    return RedirectResponse(
        url=f"/settings/companies/{company.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/settings/companies/{company_id}")
def company_detail(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    return templates.TemplateResponse(
        "company_detail.html",
        {
            "request": request,
            "username": _username(request),
            "company": company,
            "active_section": "settings",
        },
    )


@router.post("/settings/companies/{company_id}")
async def company_update(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    form = await request.form()
    data = dict(form)
    service.update_company(
        company_id,
        CompanyUpdateInput(
            legal_name=str(data.get("legal_name") or "").strip() or None,
            inn=str(data.get("inn") or "").strip() or None,
            kpp=str(data.get("kpp") or "").strip() or None,
            ogrn=str(data.get("ogrn") or "").strip() or None,
            ogrnip=str(data.get("ogrnip") or "").strip() or None,
            legal_address=str(data.get("legal_address") or "").strip() or None,
            phone=str(data.get("phone") or "").strip() or None,
            email=str(data.get("email") or "").strip() or None,
            website=str(data.get("website") or "").strip() or None,
            bank_name=str(data.get("bank_name") or "").strip() or None,
            bik=str(data.get("bik") or "").strip() or None,
            account=str(data.get("account") or "").strip() or None,
            correspondent_account=str(data.get("correspondent_account") or "").strip() or None,
            director_name=str(data.get("director_name") or "").strip() or None,
            signer_name=str(data.get("signer_name") or "").strip() or None,
            watermark_text=str(data.get("watermark_text") or "").strip() or None,
        ),
    )
    return RedirectResponse(
        url=f"/settings/companies/{company_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/settings/companies/{company_id}/stamp")
async def company_upload_stamp(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    form = await request.form()
    file = form.get("file")
    if not file or not isinstance(file, UploadFile):
        raise HTTPException(status_code=400, detail="Файл не выбран.")
    data = await file.read()
    _validate_png(file, data)
    assets_dir = _company_assets_dir(company_id)
    target = assets_dir / "stamp.png"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", dir=str(assets_dir))
    try:
        os.write(tmp_fd, data)
        os.close(tmp_fd)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.close(tmp_fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    service.set_company_asset_paths(company_id, stamp_path=storage_relative_path(target))
    return RedirectResponse(
        url=f"/settings/companies/{company_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/settings/companies/{company_id}/signature")
async def company_upload_signature(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    form = await request.form()
    file = form.get("file")
    if not file or not isinstance(file, UploadFile):
        raise HTTPException(status_code=400, detail="Файл не выбран.")
    data = await file.read()
    _validate_png(file, data)
    assets_dir = _company_assets_dir(company_id)
    target = assets_dir / "signature.png"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", dir=str(assets_dir))
    try:
        os.write(tmp_fd, data)
        os.close(tmp_fd)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.close(tmp_fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    service.set_company_asset_paths(company_id, signature_path=storage_relative_path(target))
    return RedirectResponse(
        url=f"/settings/companies/{company_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/settings/companies/{company_id}/stamp")
def company_serve_stamp(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company or not company.stamp_path:
        raise HTTPException(status_code=404, detail="Файл печати не найден.")
    path = resolve_storage_path(company.stamp_path)
    if not path:
        raise HTTPException(status_code=404, detail="Файл печати не найден.")
    return FileResponse(path=path, filename="stamp.png", media_type="image/png")


@router.get("/settings/companies/{company_id}/signature")
def company_serve_signature(company_id: int, request: Request):
    _require_auth(request)
    company = service.get_company(company_id)
    if not company or not company.signature_path:
        raise HTTPException(status_code=404, detail="Файл подписи не найден.")
    path = resolve_storage_path(company.signature_path)
    if not path:
        raise HTTPException(status_code=404, detail="Файл подписи не найден.")
    return FileResponse(path=path, filename="signature.png", media_type="image/png")