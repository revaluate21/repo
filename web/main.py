from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes import api, pages


def create_app() -> FastAPI:
    app = FastAPI(title="Quant Terminal", version="1.0")
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
    app.include_router(pages.router)
    app.include_router(api.router, prefix="/api")
    return app


app = create_app()
