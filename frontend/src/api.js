import { API_BASE_URL } from "./config.js";

async function appelerApi(chemin, params = {}) {
    const url = new URL(`${API_BASE_URL}${chemin}`);
    for (const [cle, valeur] of Object.entries(params)) {
        if (valeur === undefined || valeur === null) continue;
        if (Array.isArray(valeur)) {
            valeur.forEach((v) => url.searchParams.append(cle, v));
        } else {
            url.searchParams.set(cle, valeur);
        }
    }

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Erreur API ${response.status} sur ${chemin}`);
    }
    return response.json();
}

export function listerStations(filtres = {}) {
    return appelerApi("/stations", filtres);
}

export function comparerStations(ids) {
    return appelerApi("/stations/comparer", { ids });
}
