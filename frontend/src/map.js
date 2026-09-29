const CENTRE_ALPES_DU_NORD = [45.5, 6.6];
const ZOOM_INITIAL = 9;

export function initCarte() {
    const carte = L.map("map").setView(CENTRE_ALPES_DU_NORD, ZOOM_INITIAL);

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 18,
    }).addTo(carte);

    return carte;
}

function couleurScore(score) {
    if (score === null || score === undefined) return "#9ca3af"; // gris : pas de donnée
    const ratio = Math.max(0, Math.min(1, score / 100));
    const rouge = Math.round(220 - ratio * 140);
    const vert = Math.round(70 + ratio * 140);
    return `rgb(${rouge}, ${vert}, 70)`;
}

function creerMarqueur(station) {
    return L.circleMarker([station.latitude, station.longitude], {
        radius: 9,
        color: "#1f2937",
        weight: 1,
        fillColor: couleurScore(station.score_qualite_neige),
        fillOpacity: 0.9,
    });
}

function contenuPopup(station, onAjouterComparateur) {
    const conteneur = document.createElement("div");
    conteneur.className = "popup-station";

    const score =
        station.score_qualite_neige === null || station.score_qualite_neige === undefined
            ? "pas de donnée (hors-saison)"
            : `${station.score_qualite_neige.toFixed(1)} / 100`;
    const risque = station.niveau_risque_avalanche ?? "non disponible";
    const altitude =
        station.altitude_m === null || station.altitude_m === undefined
            ? "inconnue"
            : `${Math.round(station.altitude_m)} m`;

    conteneur.innerHTML = `
        <h3>${station.nom_station}</h3>
        <p><strong>Massif :</strong> ${station.massif}</p>
        <p><strong>Altitude :</strong> ${altitude}</p>
        <p><strong>Score qualité neige :</strong> ${score}</p>
        <p><strong>Risque avalanche :</strong> ${risque}</p>
    `;

    const bouton = document.createElement("button");
    bouton.textContent = "Ajouter au comparateur";
    bouton.addEventListener("click", () => onAjouterComparateur(station.station_id));
    conteneur.appendChild(bouton);

    return conteneur;
}

export function afficherStations(carte, stations, { onAjouterComparateur }) {
    for (const station of stations) {
        if (station.latitude === null || station.longitude === null) continue;

        const marqueur = creerMarqueur(station);
        marqueur.bindPopup(contenuPopup(station, onAjouterComparateur));
        marqueur.addTo(carte);
    }
}
