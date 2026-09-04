-- Nettoyage du référentiel stations : normalisation des noms, altitude min/max, massif.
-- TODO: standardiser station_id, gérer les valeurs manquantes.

select
    *
from {{ source('raw', 'raw_stations_referentiel') }}
