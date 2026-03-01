from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/partials/status", response_class=HTMLResponse)
async def status_partial(request: Request) -> HTMLResponse:
    from web.routes.state import BOT

    status = BOT.status()
    return templates.TemplateResponse("partials/status_panel.html", {"request": request, "status": status})


@router.get("/partials/journal", response_class=HTMLResponse)
async def journal_partial(request: Request) -> HTMLResponse:
    from web.routes.state import BOT

    rows = await BOT.fetch_journal(limit=100)
    return templates.TemplateResponse("partials/journal_table.html", {"request": request, "rows": rows})
