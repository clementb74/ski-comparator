"""Point d'entrée de l'API FastAPI."""
from fastapi import APIRouter, FastAPI

from api.routers import recommandations, stations

app = FastAPI(title="Comparateur intelligent de stations de ski")

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(stations.router)
api_v1.include_router(recommandations.router)
app.include_router(api_v1)


@app.get("/")
def root():
    return {"status": "ok"}
