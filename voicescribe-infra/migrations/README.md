# Alembic shared template

Questa directory contiene la base condivisa per migrazioni DB nei microservizi.

- `alembic.ini`: configurazione base.
- `env.py`: template con `DATABASE_URL` da variabile ambiente.
- `versions/`: migrazioni condivise di bootstrap.

Ogni microservizio con accesso DB puo copiare questa struttura e adattarla al proprio repository.
