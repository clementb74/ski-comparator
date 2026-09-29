import { listerStations } from "./api.js";
import { initCarte, afficherStations } from "./map.js";
import { initComparateur } from "./comparateur.js";

async function main() {
    const carte = initCarte();
    const comparateur = initComparateur(document.getElementById("comparateur"));

    const stations = await listerStations();
    afficherStations(carte, stations, {
        onAjouterComparateur: comparateur.ajouter,
    });
}

main().catch((erreur) => {
    console.error(erreur);
    document.getElementById("map").textContent =
        "Impossible de charger les stations (API indisponible ?)";
});
