"""Point d'entrée de l'API FastAPI."""
from fastapi import FastAPI

from api.routers import stations

app = FastAPI(title="Comparateur intelligent de stations de ski")

app.include_router(stations.router)


@app.get("/")
def root():
    return {"status": "ok"}
