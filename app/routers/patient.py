# app/routers/patient.py
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db import models
from app.services.form_logic import FormPack
from app.services.whatsapp import deeplink
import app.templates  # Jinja2Templates instance

from fastapi import APIRouter, Depends, Request
from app.services.quota import check_open, check_submit

router = APIRouter(prefix="/patient", tags=["patient"])


# ---------- helper ------------------------------------------------
async def get_phone(request: Request) -> str:
    """
    Extract the WhatsApp number the patient uses to authenticate.
    • GET /open  : read from query ?phone=...
    • POST /submit : read from hidden field in form
    """
    if request.method == "GET":
        phone = request.query_params.get("phone")
    else:  # POST
        form = await request.form()
        phone = form.get("patient_phone")
    if not phone:
        raise HTTPException(400, "Phone number missing")
    return phone


# ---------- routes ------------------------------------------------
@router.get("/open/{clinic_id}/{form_slug}")
async def open_form(
    clinic_id: int,
    form_slug: str,
    lang: str = "English",
    phone: str = Depends(get_phone),
):
    await check_open(phone)
    # ... existing logic to render form page ...

@router.post("/submit/{clinic_id}/{form_slug}")
async def submit_form(
    clinic_id: int,
    form_slug: str,
    request: Request,
    phone: str = Depends(get_phone),
):
    await check_submit(phone)

# ---------- open form (GET) ----------
@router.get(
    "/open/{session_id}/{form_slug}",
    response_class=HTMLResponse,
    name="open_form",
)
async def open_form(
    request: Request,
    session_id: int,
    form_slug: str,
    lang: str = "EN",
    db: Session = Depends(get_session),
):
    fp = FormPack.by_slug(db, form_slug)
    qloc = fp.localised(lang)
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "lang": lang,
            "title": fp.meta.title_en,
            "form_meta": fp.meta,
            "questions": qloc,
            "session_id": session_id,
        },
    )


# ---------- submit form (POST) ----------
@router.post(
    "/submit/{session_id}/{form_slug}",
    response_class=HTMLResponse,
    name="submit_form",
)
async def submit_form(clinic_id: int, form_slug: str, request: Request,
                       phone: str = Depends(get_phone)):
    await check_submit(phone)
    # grab data out of the HTML form
    form_data = await request.form()
    answers = {k: v for k, v in form_data.items()}  # {question_key: option_key}

    fp = FormPack.by_slug(db, form_slug)
    redflags = fp.evaluate(answers)

    # TODO:  insert rows into patient_sessions / form_submissions / answers
    #        and enforce daily-quota limits here.

    # --- stub clinic lookup (replace with real query) ---
    clinic = db.query(models.Clinic).first()
    if clinic is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic not found (seed some data first)",
        )

    wa_msg = (
        f"I just completed the {fp.meta.title_en} form and received advice. "
        "Please contact me back."
    )
    wa_link = deeplink(clinic.phone_whatsapp, wa_msg)

    return templates.TemplateResponse(
        "redflag_response.html",
        {
            "request": request,
            "lang": lang,
            "redflags": redflags,
            "clinic": clinic,
            "whatsapp_msg": wa_msg,
            "whatsapp_link": wa_link,
        },
    )


