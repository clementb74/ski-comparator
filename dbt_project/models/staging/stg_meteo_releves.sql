-- Nettoyage et typage des relevés météo bruts.
-- TODO: normaliser les unités (cm, °C), typer les dates, dédupliquer.

select
    *
from {{ source('raw', 'raw_meteo_releves') }}
