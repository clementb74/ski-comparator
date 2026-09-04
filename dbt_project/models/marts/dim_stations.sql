-- Dimension station : nom, massif, altitude, coordonnées, taille du domaine.
-- altitude_m est un point unique (village/centre station, source OSM) ;
-- altitude_min/altitude_max (fourchette du domaine skiable) seront ajoutés
-- quand la source bulletins neige sera branchée (souvent publiée dessus).

select
    station_id,
    nom_station,
    massif,
    altitude_m,
    latitude,
    longitude
from {{ ref('stg_stations_referentiel') }}
