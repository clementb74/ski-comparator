-- Score de qualité neige (0-100) : enneigement (50%) + fraîcheur de la
-- dernière chute (25%) + ouverture du domaine (25%). Le risque avalanche
-- (BRA) est exposé à part (niveau_risque_avalanche) : ce n'est pas un
-- critère de "qualité neige" mais un risque à signaler séparément.
--
-- NULL si aucune donnée d'enneigement (station hors-saison) plutôt qu'un
-- score arbitraire, pour ne pas confondre "mauvaises conditions" et
-- "pas de donnée" — voir CLAUDE.md.
--
-- Seuils de normalisation choisis arbitrairement pour ce premier jet, faute
-- de saison active pour les calibrer sur de vraies données (100cm de base =
-- plein score enneigement, 40 pistes ouvertes = plein score ouverture,
-- chute le jour même = pleine fraîcheur, dégressif jusqu'à 0 sur 10 jours) :
-- à recalibrer une fois des données réelles disponibles (novembre 2026).

with faits as (

    select
        station_id,
        base_snow_depth,
        open_trails,
        try_to_date(last_snowfall_date) as last_snowfall_date,
        risque_maxi as niveau_risque_avalanche
    from {{ ref('fct_enneigement_quotidien') }}

)

select
    station_id,
    niveau_risque_avalanche,
    case
        when base_snow_depth is null then null
        else
            least(base_snow_depth / 100.0, 1.0) * 50
            + greatest(
                1 - coalesce(datediff('day', last_snowfall_date, current_date()), 999) / 10.0, 0
            ) * 25
            + least(coalesce(open_trails, 0) / 40.0, 1.0) * 25
    end as score_qualite_neige
from faits
