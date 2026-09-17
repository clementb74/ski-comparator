-- Jointure stations x relevés météo, via le mapping station -> massif BRA
-- (dbt_project/seeds/stations_massif_bra.csv). `stations.massif` (toujours
-- "Alpes du Nord" pour le périmètre pilote) n'est pas une clé de jointure
-- utilisable ; le massif BRA fin (Vanoise, Chablais, ...) l'est.

select
    stations.* exclude (ingested_at),
    stations.ingested_at as stations_ingested_at,
    meteo.* exclude (ingested_at),
    meteo.ingested_at as meteo_ingested_at
from {{ ref('stg_stations_referentiel') }} as stations
left join {{ ref('stations_massif_bra') }} as mapping
    on stations.station_id = mapping.station_id
left join {{ ref('stg_meteo_releves') }} as meteo
    on mapping.nom_massif_bra = meteo.zone_massif
