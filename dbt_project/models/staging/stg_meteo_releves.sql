-- Nettoyage et typage des relevés météo bruts (bulletins BRA par massif).
-- TODO: normaliser les unités (cm, °C), typer les dates, dédupliquer.

select
    *,
    nom_massif_bra as zone_massif
from {{ source('raw', 'raw_meteo_releves') }}
