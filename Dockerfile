FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dépendances seules d'abord, depuis le lockfile : cette couche reste en cache
# tant que pyproject.toml et uv.lock ne changent pas.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

# Puis le paquet oceens, installé (non éditable) dans /app/.venv
COPY src src
RUN uv sync --locked --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH"

# Le paquet est installé dans .venv, pas cloné : database.py ne peut pas en
# déduire la racine du dépôt. La base reste donc dans /app/database, à monter
# comme volume pour persister la base SQLite entre les redémarrages.
ENV LOCAL_DATABASE_DIR=/app/database

# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.

CMD ["uvicorn", "oceens.main:app", "--host", "0.0.0.0", "--port", "8000"]
