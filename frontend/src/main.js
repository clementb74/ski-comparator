// Point d'entrée du frontend.
// TODO: initialiser la carte interactive (Leaflet/Mapbox), appeler l'API FastAPI
// pour récupérer les stations et afficher les marqueurs.

async function fetchStations(filtres = {}) {
    const params = new URLSearchParams(filtres);
    const response = await fetch(`/stations?${params}`);
    return response.json();
}
