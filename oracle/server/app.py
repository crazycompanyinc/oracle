from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket

from oracle.core.db import OracleDB
from oracle.dashboard.api import DashboardAPI
from oracle.predictor.predictor import IncidentPredictor
from oracle.prevention.engine import PreventionEngine


def create_app(db_path: str = ".oracle") -> FastAPI:
    db = OracleDB(db_path)
    app = FastAPI(title="Oracle Incident Predictor")
    dashboard = DashboardAPI(db)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/dashboard")
    def dashboard_snapshot() -> dict:
        return dashboard.snapshot()

    @app.post("/predict")
    def predict(service: str | None = None) -> dict:
        predictions = IncidentPredictor(db).predict(service=service)
        engine = PreventionEngine(db)
        actions = [action for p in predictions for action in engine.handle_prediction(p)]
        return {"predictions": [p.to_dict() for p in predictions], "actions": [a.to_dict() for a in actions]}

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        while True:
            await websocket.send_json(dashboard.snapshot())
            await asyncio.sleep(1)

    return app

