"""ASGI entrypoint."""

import uvicorn

from .app import create_app

app = create_app()


def run() -> None:
    uvicorn.run("agentlens_api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
