-- Historique d'enneigement par station et par saison, à partir des bulletins neige.
-- TODO: agréger par station_id + saison, calculer les tendances.

select
    *
from {{ ref('stg_bulletins_neige') }}
