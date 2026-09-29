import { comparerStations } from "./api.js";

const selection = new Set();

function formaterCellule(valeur, suffixe = "") {
    return valeur === null || valeur === undefined ? "—" : `${valeur}${suffixe}`;
}

async function render(conteneur) {
    if (selection.size === 0) {
        conteneur.innerHTML = "<p>Ajoutez des stations depuis la carte pour les comparer.</p>";
        return;
    }

    const stations = await comparerStations([...selection]);

    const lignes = stations
        .map(
            (s) => `
        <tr>
            <td>${s.nom_station}</td>
            <td>${s.massif}</td>
            <td>${formaterCellule(s.altitude_m ? Math.round(s.altitude_m) : null, " m")}</td>
            <td>${formaterCellule(s.score_qualite_neige?.toFixed?.(1))}</td>
            <td>${formaterCellule(s.niveau_risque_avalanche)}</td>
            <td><button data-station-id="${s.station_id}" class="retirer">Retirer</button></td>
        </tr>`
        )
        .join("");

    conteneur.innerHTML = `
        <table class="tableau-comparateur">
            <thead>
                <tr>
                    <th>Station</th><th>Massif</th><th>Altitude</th>
                    <th>Score neige</th><th>Risque avalanche</th><th></th>
                </tr>
            </thead>
            <tbody>${lignes}</tbody>
        </table>
    `;

    conteneur.querySelectorAll("button.retirer").forEach((bouton) => {
        bouton.addEventListener("click", () => {
            retirer(bouton.dataset.stationId);
            render(conteneur);
        });
    });
}

export function ajouter(stationId, conteneur) {
    selection.add(stationId);
    render(conteneur);
}

export function retirer(stationId) {
    selection.delete(stationId);
}

export function initComparateur(conteneur) {
    render(conteneur);
    return {
        ajouter: (stationId) => ajouter(stationId, conteneur),
    };
}
