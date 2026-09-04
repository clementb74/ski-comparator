-- Nettoyage du référentiel stations : normalisation des noms, altitude min/max, massif.
-- Filtré sur le périmètre pilote (seeds/perimetre_stations.csv) pour rester extensible :
-- ajouter une station = ajouter une ligne au CSV, sans toucher au code.
-- TODO: standardiser station_id, gérer les valeurs manquantes.

select
    raw.*
from {{ source('raw', 'raw_stations_referentiel') }} as raw
inner join {{ ref('perimetre_stations') }} as perimetre
    on raw.station_id = perimetre.station_id
where perimetre.actif = true
