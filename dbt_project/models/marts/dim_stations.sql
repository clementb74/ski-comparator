-- Dimension station : nom, massif, altitude, coordonnées, taille du domaine.

select
    station_id,
    nom_station,
    massif,
    altitude_min,
    altitude_max,
    latitude,
    longitude
from {{ ref('stg_stations_referentiel') }}
