-- Table de faits : enneigement et météo quotidiens par station.
-- Combine relevés météo/avalanche (int_stations_meteo_joined) et bulletins
-- neige (int_enneigement_historique) sur station_id — avant ce fix, cette
-- table ne contenait que la météo, jamais les données d'enneigement.

select
    meteo.* exclude (meteo_ingested_at, stations_ingested_at),
    neige.* exclude (station_id, ingested_at),
    stations_ingested_at,
    meteo_ingested_at,
    neige.ingested_at as neige_ingested_at
from {{ ref('int_stations_meteo_joined') }} as meteo
left join {{ ref('int_enneigement_historique') }} as neige
    on meteo.station_id = neige.station_id
