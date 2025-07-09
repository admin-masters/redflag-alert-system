# app/routers/patient.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST

from app.db.session import get_session
from app.services.form_logic import FormPack
from app.services.whatsapp import deeplink
from app.db import models
from app.main import templates   # import the Jinja2Templates instance

router = APIRouter(prefix="/patient", tags=["patient"])


@router.get("/open/{session_id}/{form_slug}", response_class=HTMLResponse)
def open_form(
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


@router.post("/submit/{session_id}/{form_slug}", response_class=HTMLResponse)
def submit_form(
    request: Request,
    session_id: int,
    form_slug: str,
    db: Session = Depends(get_session),
    lang: str = "EN",
):
    form_data = await request.form()
    answers = {k: v for k, v in form_data.items()}  # question_key: option_key

    fp = FormPack.by_slug(db, form_slug)
    redflags = fp.evaluate(answers)

    # TODO: insert rows into form_submissions / answers / submission_redflags
    #       enforce daily quota, etc.

    # Dummy clinic object (replace with actual join):
    clinic = db.query(models.Clinic).first()

    wf_msg = f"I just submitted the {fp.meta.title_en} form and saw red-flags."
    wa_link = deeplink(clinic.phone_whatsapp, wf_msg)

    return templates.TemplateResponse(
        "redflag_response.html",
        {
            "request": request,
            "lang": lang,
            "redflags": redflags,
            "clinic": clinic,
            "whatsapp_msg": wf_msg,
        },
    )