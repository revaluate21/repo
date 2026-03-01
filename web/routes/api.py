from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from web.routes.state import BOT

router = APIRouter()


@router.get("/status")
async def status() -> dict:
    return BOT.status()


@router.post("/start")
async def start(live: bool = Form(False), confirmation: str = Form("")) -> dict:
    try:
        await BOT.start(live=live, live_phrase=confirmation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "status": BOT.status()}


@router.post("/stop")
async def stop() -> dict:
    await BOT.stop()
    return {"ok": True}


@router.post("/pause")
async def pause(value: bool = Form(True)) -> dict:
    BOT.pause(value)
    return {"ok": True}


@router.post("/strategy")
async def strategy(name: str = Form(...), enabled: bool = Form(...)) -> dict:
    BOT.update_strategy(name, enabled)
    return {"ok": True}


@router.post("/wallet")
async def wallet(private_key: str = Form(""), mnemonic: str = Form("")) -> dict:
    BOT.set_wallet(private_key=private_key, mnemonic=mnemonic)
    return {"ok": True}


@router.post("/trade")
async def trade(side: str = Form(...), price: float = Form(...), size: float = Form(...)) -> dict:
    fill = await BOT.manual_trade(side, price, size)
    return {"ok": True, "fill": fill}


@router.get("/export-csv")
async def export_csv() -> FileResponse:
    return FileResponse(BOT.csv_path, filename="trade_journal.csv")


@router.post("/settings")
async def settings(
    refresh_hz: int = Form(...),
    fractional_kelly: float = Form(...),
    max_balance_fraction_per_trade: float = Form(...),
) -> dict:
    BOT.settings.refresh_hz = refresh_hz
    BOT.settings.risk.fractional_kelly = fractional_kelly
    BOT.settings.risk.max_balance_fraction_per_trade = max_balance_fraction_per_trade
    return {"ok": True}


@router.websocket("/ws")
async def ws_updates(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            await ws.send_json(BOT.status())
            await ws.receive_text()
    except WebSocketDisconnect:
        return
