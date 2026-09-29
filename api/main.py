"""Point d'entrée de l'API FastAPI."""
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import recommandations, stations

app = FastAPI(title="Comparateur intelligent de stations de ski")

# Frontend servi séparément (npm start dans frontend/, port 5500 fixé dans
# package.json — le 3000 par défaut de `serve` est déjà pris sur cette
# machine par un autre projet) : origines de dev explicites, pas de wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(stations.router)
api_v1.include_router(recommandations.router)
app.include_router(api_v1)


@app.get("/")
def root():
    return {"status": "ok"}
