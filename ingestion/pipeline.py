"""Point d'entrée du pipeline d'ingestion PySpark.

Orchestre la collecte des sources (météo, référentiel stations, bulletins neige)
et l'écriture en couche bronze (MongoDB).

TODO: initialiser une SparkSession, appeler les modules sources/, écrire dans MongoDB.
"""


def run() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    run()
