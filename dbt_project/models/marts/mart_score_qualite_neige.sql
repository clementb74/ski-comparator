-- Score de qualité neige calculé (enneigement, fraîcheur, météo à venir).
-- TODO: définir la formule de pondération (voir docs/SPEC.md section 8).

select
    station_id,
    -- score placeholder, à remplacer par la vraie formule
    0 as score_qualite_neige
from {{ ref('dim_stations') }}
