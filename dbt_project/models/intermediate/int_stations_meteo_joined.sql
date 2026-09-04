-- Jointure stations x relevés météo par zone géographique / massif.
-- TODO: définir la clé de jointure (massif ou proximité géographique).

select
    stations.*,
    meteo.*
from {{ ref('stg_stations_referentiel') }} as stations
left join {{ ref('stg_meteo_releves') }} as meteo
    on stations.massif = meteo.zone_massif
