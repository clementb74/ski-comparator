"""Récupération des prévisions et relevés météo (API Météo France / data.gouv.fr).

TODO: implémenter l'appel API et le mapping vers le schéma bronze.
"""


def fetch_previsions(zone_massif: str) -> list[dict]:
    """Récupère les prévisions météo pour une zone de massif donnée."""
    raise NotImplementedError


def fetch_releves(zone_massif: str) -> list[dict]:
    """Récupère les relevés météo historiques pour une zone de massif donnée."""
    raise NotImplementedError
