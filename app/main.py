# app/main.py (updated)
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services import form_logic

app = FastAPI(title="Inditech RFA")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------- patient entry ----------------
@app.get("/patient/open/{session_id}/{form_slug}", response_class=HTMLResponse)
def open_form(
    request: Request,
    session_id: int,
    form_slug: str,
    lang: str = "EN",
    db: Session = Depends(get_session),
):
    fp = form_logic.FormPack.by_slug(db, form_slug)
    qs_loc = fp.localised(lang)
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "lang": lang,
            "title": fp.meta.title_en,
            "form_meta": fp.meta,
            "questions": qs_loc,
            "session_id": session_id,
        },
    )