-- Table de faits : enneigement et météo quotidiens par station.

select
    *
from {{ ref('int_stations_meteo_joined') }}
