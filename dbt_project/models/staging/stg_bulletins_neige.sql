-- Parsing des hauteurs de neige et gestion des valeurs manquantes.
-- TODO: extraire hauteur_neige_cm, date_bulletin, état des pistes.

select
    *
from {{ source('raw', 'raw_bulletins_neige') }}
