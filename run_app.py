from __future__ import annotations

import threading
import webbrowser

import uvicorn


if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    uvicorn.run("web.main:app", host="127.0.0.1", port=8000, reload=True)
