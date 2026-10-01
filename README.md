# OcéEns II

Course evaluation platform built for the EPF engineering school.

## Overview

**OcéEns II** lets program managers, facilitators, campus directors and administrators create and manage evaluation surveys for EPF's various programs, and lets students answer them. Responses can be exported, visualized, and summarized by an LLM. The interface uses EPF's official visual identity.

### Tech stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth 2.0 / MSAL, Microsoft Graph |
| **Database** | SQLite (via SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Logging** | Python standard `logging` module, via Uvicorn handlers |
| **Exports** | Pandas (CSV) |
| **Free-text summaries** | Separate daemon calling an LLM (`requests-cache`, `markdown-it-py`) |

---

## Roles

- `student`: answers the surveys they are enrolled in.
- `program_manager:<code>`: manages surveys for their program(s).
- `facilitator:<code>`: facilitates surveys for their program(s).
- `campus_manager:<campus>`: campus-wide scope.
- `admin`: general administration.

A user can hold several roles, each with its own scope (program codes or campuses separated by `;`).

---

## Main pages and routes

| Route | Description |
|-------|-------------|
| `/` | Home page, authentication hub. |
| `/login`, `/auth/callback`, `/logout` | Microsoft Entra ID authentication flow. |
| `/dev/login` | Development login: user picker page on `GET`, login on `POST` (only with `AUTH_MODE=dev`, see [Development mode authentication](#development-mode-authentication)). |
| `/dashboard/student` | Student dashboard. |
| `/dashboard/program-manager` | Program manager dashboard. |
| `/dashboard/facilitator` | Facilitator dashboard. |
| `/dashboard/campus-manager` | Campus director dashboard. |
| `/dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by year / semester / program. Available to the `campus_manager` and `program_manager` roles, scoped to each one's perimeter. |
| `/dashboard/admin` | Administrator dashboard. |
| `/dashboard/survey-create` | Survey creation / configuration. |
| `/api/surveys/{survey_id}` | Questionnaire (answering the survey). |
| `/api/surveys/{survey_id}/status` | Change a survey's status. |
| `/api/surveys/{survey_id}/students` | Manage students enrolled in a survey. |
| `/api/surveys/{survey_id}/export` | CSV export of responses. |
| `/api/surveys/{survey_id}/visualisation` | Response visualization. Accepts `?teacher=<name>` to open pre-filtered on a teacher. |
| `/api/surveys/{survey_id}/generate-summaries` | Start LLM summary generation. |
| `/api/surveys/{survey_id}/destroy-summaries` | Delete generated summaries. |
| `/api/users/{user_id}/role` | Change a user's role. |
| `/backend/prompts` | List of LLM prompts (admin only). |
| `/backend/prompts/new` | Prompt creation form. |
| `/backend/prompts/{id}/edit` | Prompt edit form. |
| `/api/prompts` | Create a prompt (POST, form). |
| `/api/prompts/{id}` | Update a prompt (PUT, fetch). Blocked if the prompt is referenced in `summaries`. |
| `/api/prompts/{id}/delete` | Delete a prompt (POST, form). Blocked if the prompt is referenced in `summaries`. |

---

## Installation and startup

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs Python 3.12 (pinned in `.python-version`) if needed (or Docker)
- A `.env` file: `cp .env.example .env` (see [Configuration](#configuration))

### First run (fresh clone)

```bash
cp .env.example .env     # Windows PowerShell: Copy-Item .env.example .env
```

`.env.example` ships with `AUTH_MODE=dev`, so the app starts with **no Entra credentials and no LLM key**. Then start it with Docker Compose or Uvicorn below, open http://localhost:8000 and sign in through `/dev/login`. The database is created and seeded on first startup. To check your setup, follow [docs/smoke-test.md](docs/smoke-test.md).

### With Docker Compose (recommended)

```bash
docker compose up --build
```

`docker compose up` fails if `.env` does not exist (`env_file: .env`): create it first, as in [First run](#first-run-fresh-clone).

The SQLite database is persisted in a local directory, `./database/` by default. To point elsewhere, set `LOCAL_DATABASE_DIR` in `.env` or in the environment:

```env
LOCAL_DATABASE_DIR=/path/to/database
```

Without Compose:

```bash
docker build -t oceens .
docker run -p 8000:8000 --env-file .env -v oceens_db:/app/database oceens
```

> The `Dockerfile` installs the `oceens` package from `uv.lock` and runs Uvicorn **without** `--reload`: the source code is copied into the image, so a code change requires a rebuild (`docker compose up --build`). For live reload, run Uvicorn locally with `--reload` instead.

> The SQLite database is persisted in the `oceens_db` Docker volume (`/app/database`).
> The `.env` file is never copied into the image: it is passed via `--env-file` at launch.

### Without Docker (manual installation)

### Steps

1. **Clone the project**

   ```bash
   git clone <repo-url>
   cd OceENS
   ```

2. **Create your `.env`** (`cp .env.example .env`)

3. **Install the project and its dependencies**

   ```bash
   uv sync --locked
   ```

   `uv sync` creates `.venv` with Python 3.12 and installs the `oceens` package (from `src/oceens/`) with the exact versions in `uv.lock`.

   The commands below call the binaries by path, which also works on Windows where `Activate.ps1` is blocked by default: replace `.venv/bin/` with `.venv\Scripts\` (and add `.exe`).

4. **Database**
   Nothing to do: `database/` is created on first startup and `seed_all_if_necessary()` seeds an empty database. To reuse an existing database, place `db_oceens.db` in `database/` (or in `LOCAL_DATABASE_DIR`).

5. **Start the application**:

   ```bash
   .venv/bin/uvicorn oceens.main:app --port 8000   # add --reload to follow code changes
   ```

   `.venv/bin/python -m oceens.main` also works (Uvicorn on `0.0.0.0:8000`). In production, `launch.sh` starts the application and the summaries daemon in separate `screen` sessions.

6. **(Optional) Start the LLM summaries daemon**:

   ```bash
   .venv/bin/oceens-summaries
   ```

   This process runs in a loop, writes to the database and contacts an external LLM service: only run it when needed.

   > Setting the environment variable `RUN_SUMMARIES_DAEMON=1` in `.env`
   > makes Uvicorn automatically start the daemon as a separate process on startup
   > (and stop it on shutdown). Use this in production with Docker.
   > Note: `launch.sh` (without Docker) already manages the daemon in its own `screen` session.

7. Open your browser at **http://localhost:8000**.

---

## Logging

Application logs use Python's standard `logging` module and the `uvicorn`
logger. This lets messages from the application, `auth.py` and `seed.py` reuse
the format, colors and handlers already configured by the server.

Levels are used according to severity:

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed information useful during development and seeding. |
| `INFO` | Startup, shutdown and normal application operations. |
| `WARNING` | Expected resource missing or non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | Required configuration missing, preventing startup. |

Example:

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Operation completed")

try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

New diagnostics should use the appropriate logger rather than `print()`. The
application level is currently set to `DEBUG` in `core/dependencies.py`.
Application logs go through the Uvicorn handler, usually written to `stderr`;
with a separate redirection, use for example `2> error.log` to capture them.

---

## Configuration

`cp .env.example .env`: the file at the project root is read by the application and by `docker-compose.yaml`. [`.env.example`](.env.example) is the reference and documents each variable; it ships with `AUTH_MODE=dev`. Every variable the code reads:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_MODE` | `entra` | `entra` or `dev`; any other value stops the app. See [Development mode authentication](#development-mode-authentication). |
| `DEV_LOGIN_KEY` | unset | `dev` only: key required by every login. Open login if unset. |
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | unset | Required when `AUTH_MODE=entra` (the app exits at startup without them); not needed in `dev`. |
| `REDIRECT_URI` | `https://localhost/auth/callback` | Entra redirect URL, e.g. `http://localhost:8000/auth/callback`. |
| `ALLOWED_DOMAINS` | `epf.fr,epfedu.fr` | Allowed email domains, comma-separated. Set it explicitly with `AUTH_MODE=entra`. |
| `SECRET_KEY` | random in `dev` | Signs session cookies. Required when `AUTH_MODE=entra`. |
| `LOCAL_DATABASE_DIR` | `./database` | Directory holding `db_oceens.db`. |
| `RUN_SUMMARIES_DAEMON` | off | `1`/`true`/`yes`/`on`: Uvicorn starts the summaries daemon. |
| `LLM_API_KEY` | unset | Key of the default LLM provider (Ollama EPF). Other providers use their own `*_API_KEY` / `LLM_*` variable (see below). |

**The app runs without an LLM key.** Only summary generation is unavailable until a key is set. For EPF's Ollama, get a key from https://locallm.mde.epf.fr.

`SECRET_KEY` signs session cookies: anyone who knows it can forge an admin session. It is **required unless `AUTH_MODE=dev`**: if it is missing or empty, the application logs a critical error and exits at startup (exit code 1). Generate it with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

> [!CAUTION]
> Never commit the `.env` file. It is already listed in `.gitignore`, as are `*.db` files (`database/db_oceens.db`, `cache_llm.db`).

---

## LLM providers (free-text summaries)

Free-text summaries are generated by an LLM. The provider is
**configurable from the interface** (`/backend/providers`, admin only),
without touching the code. The default provider is **Ollama EPF**
(`https://locallm.mde.epf.fr/ollama`), created automatically on first
startup.

### Supported API types

| `api_type` | Covers |
|------------|--------|
| `ollama`    | Ollama servers (local, EPF, third-party) |
| `openai`    | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Claude API (Anthropic) |

### Security principle: no keys in the database

The SQLite database is not encrypted and ends up in backups. **No API key is
therefore stored in it.** The `llm_providers` table only holds the *name* of
the environment variable (`api_key_env`, e.g. `OPENAI_API_KEY`); the value
stays in `.env` and is only resolved at call time. This name is validated
against an allowlist (`LLM_*` or `*_API_KEY`) to prevent pointing at a system
secret (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…).

### Adding a new provider

1. **Add the key to `.env`** with a compliant name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the summaries daemon** (`.env` variables are only read at
   startup):

   ```bash
   .venv/bin/oceens-summaries
   ```

3. **Create the provider** in `/backend/providers` → *+ Nouveau fournisseur*
   (new provider): enter the name, API type, base URL, env variable name
   (`OPENAI_API_KEY`) and a default model. The **"key present / missing"**
   indicator confirms the variable is loaded. The **Tester** (Test) button
   checks that the URL and key respond, then sends a one-token generation
   to confirm the account can actually generate (see below).

4. **Link a prompt** to the provider: in `/backend/prompts`, a `<select>`
   lets you choose a prompt's provider. A prompt without a provider
   (`provider_id` NULL) automatically falls back to Ollama EPF.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted
> (so as not to break those prompts' configuration).

### Exhausted credit and other provider errors

Each provider reports failures in a different format: exhausted credit is a
`429 insufficient_quota` at OpenAI, but a `400 "Your credit balance is too
low"` at Anthropic. `services/llm_client.py` normalizes these responses into
categories (`quota`, `rate_limit`, `auth`, `model`, `server`) and derives a
readable message from them, for example (shown in French in the app):

> ⚠️ Crédit ou quota épuisé chez le fournisseur : la clé est valide mais le
> compte ne peut plus générer. Rechargez le compte ou choisissez un autre
> fournisseur. (fournisseur OpenAI, modèle gpt-4o-mini, HTTP 429)
>
> *(Credit or quota exhausted at the provider: the key is valid but the
> account can no longer generate. Top up the account or choose another
> provider.)*

This message is written to `Summary.metadata_text` instead of the raw JSON, so
it is visible directly in the interface when a summary fails. The provider's
raw response stays in the daemon logs for diagnosis.

> [!IMPORTANT]
> The **Tester** (Test) button does not just list models: at both OpenAI and
> Anthropic, `GET /v1/models` still responds perfectly with a zero balance.
> A one-token generation ping (negligible cost) is therefore sent afterwards.
> It is the only way to detect exhausted credit **before** launching a
> summaries campaign.

---

## Summary costs

The cost of each summary is **measured, not estimated**. At generation time,
the daemon records the token counts returned by the provider
(`Summary.input_tokens`, `output_tokens`, `model_used`): this is the only
chance to capture them, as no API lets you request them afterwards. The amount
is then obtained by combining these counts with the price table.

> [!NOTE]
> This section replaces the old `llm-utils/token-counting/` scripts, which
> counted the tokens of the **repository source code** and multiplied them by a
> hard-coded rate. That measurement said nothing about the application's actual
> spending. Tracking now covers the calls that are actually billed.

### Price table — `/backend/llm/prices`

Prices live in the database (`llm_model_prices` table), in **dollars per
million tokens**, as published by providers. They can be edited from the
admin area: no release is needed to follow a price change or to cover a
locally added provider.

Pre-filled at startup (`seed_model_prices`, idempotent: a manually corrected
price is never overwritten):

| Model | Input $/M | Output $/M |
| --- | ---: | ---: |
| `claude-opus-5` | 5.00 | 25.00 |
| `claude-sonnet-5` | 3.00 | 15.00 |
| `claude-haiku-4-5` | 1.00 | 5.00 |
| `gemma4:26b` (Ollama EPF, self-hosted) | 0.00 | 0.00 |

Prices for other providers (OpenAI, Mistral, Groq…) **must be entered**: they
are not guessed. A provider-specific price takes precedence over a generic
price with the same model name.

### Where to view

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Overall cost, broken down by survey and by model (admin) |
| 💰 button on a survey row | Cost of that survey's summaries |

### What is not priced

A summary cannot be priced when its counts are missing (generated before this
feature, or a provider that doesn't expose them) or when its model has no
recorded price. It is then **counted separately**, never estimated or rounded
down to zero: an invented amount would be more harmful than a missing one,
since it would be displayed with the authority of a real amount. Screens
explicitly indicate when a total is partial.

This is distinct from a **zero** cost: self-hosted models really cost $0.00,
which is not the same information as "unknown".

> [!IMPORTANT]
> Tracking starts when the feature goes live: summaries generated before then
> have no counts in the database and cannot be priced retroactively.

---

## Project structure

```
OceENS/
├── pyproject.toml                # Project metadata, pinned dependencies, `oceens-summaries` entry point
├── uv.lock                       # Locked dependency versions (uv)
├── .python-version               # Python interpreter version (3.12)
├── launch.sh                     # Launch script (production, without Docker)
├── Dockerfile                    # Application Docker image
├── .dockerignore                 # Files excluded from the Docker build
├── .env                          # Environment variables (⚠️ not committed)
├── .gitignore                    # Files and folders ignored by Git
│
├── database/                     # Folder containing the database (ignored by Git)
│   └── db_oceens.db
│
├── llm-utils/                    # LLM tools outside the application
│   └── README.md                 # (cost tracking moved into the app, see above)
│
└── src/oceens/                   # The `oceens` package; paths below are relative to it
├── __init__.py
├── main.py                       # FastAPI factory, middlewares and router assembly
├── sondage_loader.py             # Loads a full survey for export
├── survey_loader_from_xlsx.py    # Imports surveys from an Excel file
├── summaries_generator_daemon.py # Asynchronous LLM summary processing (separate process)
│
├── core/                         # Low-level access and security
│   ├── auth.py                   #   Microsoft Entra ID authentication (login, logout, callback) and development login
│   ├── database.py               #   SQLite engine and SessionDep dependency
│   ├── security.py               #   Roles, scopes, access control
│   ├── dependencies.py           #   Shared Jinja templates and logger
│   └── seed.py                   #   Initial data and program synchronization
│
├── models/                       # SQLModel schema, one file per table
│   ├── __init__.py               #   Re-exports all classes (see its docstring)
│   └── User.py, Survey.py, ...
│
├── routers/                      # Routes split by business domain
│   ├── pages.py                  #   Home page and per-role dashboards
│   ├── surveys.py                #   Surveys: CRUD, status, export, visualization
│   ├── students.py               #   Student enrollment in a survey
│   ├── users.py                  #   User role management
│   ├── summaries.py              #   Triggering LLM summaries
│   ├── prompts.py                #   Prompt administration
│   ├── survey_templates.py       #   Survey template administration
│   ├── sections_questions.py     #   Section and question administration
│   └── llm/                      #   LLM administration (URLs unchanged)
│       ├── _access.py            #     Shared access control for LLM screens
│       ├── providers.py          #     LLM providers (CRUD + connection test)
│       ├── prices.py             #     Per-model price table
│       └── costs.py              #     Overall cost and per-survey cost
│
├── services/                     # Business logic
│   ├── helpers.py                # Navigation, statistics, filters, sorting
│   ├── visualisation_data.py     # Aggregations and visualization context
│   ├── llm_client.py             # Multi-provider LLM client (ollama/openai/anthropic)
│   ├── llm_costs.py              # Summary costs (measured tokens × price table)
│   └── export_csv.py             # CSV export of responses
│
├── templates/                    # HTML templates (Jinja2)
│   ├── index.html                     # Home / login page
│   ├── dashboard/
│   │   ├── admin.html
│   │   ├── student.html
│   │   ├── program_manager.html
│   │   ├── facilitator.html
│   │   ├── campus_manager.html
│   │   ├── teachers-analytics.html       # Teacher satisfaction (campus_manager, program_manager)
│   │   ├── survey.html                   # Answering a survey
│   │   ├── survey_create.html            # Survey creation
│   │   └── visualisation.html            # Response visualization
│   ├── backend/                       # Administration pages (admin only)
│   │   ├── prompts.html               # List of LLM prompts
│   │   ├── prompt_form.html           # Shared create/edit form
│   │   └── llm/                       # LLM screens (providers, prices, costs)
│   │       ├── providers.html
│   │       ├── provider_form.html
│   │       ├── prices.html            # Editable price table
│   │       └── costs.html             # Overall and per-survey cost
│   └── template_parts/                # Fragments reused across dashboards
│       ├── part_site_header.html
│       ├── part_dashboard_navigation.html
│       ├── part_theme_switcher.html
│       └── ...
│
├── static/
│   ├── css/                      # admin.css, student.css, program_manager.css, survey.css,
│   │                              # survey_create.css, visualisation.css, prompt_form.css,
│   │                              # llm_backend.css (LLM screens), theme.css, site_header.css,
│   │                              # dashboard_navigation.css, responsive.css
│   ├── js/
│   │   └── survey.js
│   └── img/
│
└── import/                       # Seed data: program list and demo answers (CSV)
```

---

## Authentication (OAuth 2.0)

The authentication flow relies on **Microsoft Entra ID** via the MSAL library:

```
1. User clicks "Sign in"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to the Microsoft login page

2. User authenticates with Microsoft
   → Microsoft redirects to /auth/callback with a code + state

3. The server exchanges the code for an access token
   → Retrieves user info via Microsoft Graph
   → Looks up the database for the user's role(s) and scope
   → Creates the session {name, email, roles}
   → Redirects to the matching dashboard

4. On logout (/logout)
   → Deletes the session and cookies
   → Signs out on the Microsoft side
   → Returns to the home page
```

Authentication alone authorizes no business action: each route then checks the role and scope (program or campus) via `require_roles()` and the associated helpers.

---

## Development mode authentication

To work on a fork without an Azure app, the **development login** lets you sign in as any user, without proof of identity. It must **never** be used in production.

| Variable | Purpose |
|----------|---------|
| `AUTH_MODE` | `entra` (default) or `dev`, case- and whitespace-insensitive. Any other value stops the application at startup. In `dev`, the `ENTRA_*` variables are not needed. |
| `DEV_LOGIN_KEY` | Optional, `dev` mode only. If set, every login must provide it (`key` field), otherwise `401`. If not set, login is open. Ignored (with a warning) in `entra`. |
| `SECRET_KEY` | Optional in `dev`: if missing, a random key is drawn at each startup (with a warning) and sessions are lost on restart. Required in `entra`. |
| `ALLOWED_DOMAINS` | Also applies in `dev` (`403` for another domain); defaults to `epf.fr,epfedu.fr` in this mode. |

In `dev` mode, the session cookie is no longer restricted to HTTPS (`http://localhost` works), `/login` redirects to `/dev/login`, `/auth/callback` does not exist, and `/logout` clears the session then returns to `/`. A warning is logged at startup. A red, non-dismissible banner appears at the top of every page that includes the shared header: it shows the signed-in address, offers « Changer d'utilisateur » (switch user, `/dev/login`), and states « accès ouvert à tous » (open to everyone) when `DEV_LOGIN_KEY` is not set.

`POST /dev/login` expects a form with `email`, `name` (optional) and `key` (if `DEV_LOGIN_KEY` is set). The user is fetched or created as on return from Entra: an unknown email becomes a new student. Without `name`, the display name is built from the email (`bob.leponge@epfedu.fr` → "Bob Leponge"). A new login replaces the session: that is how you switch users.

In a browser, `GET /dev/login` shows the list of database users, grouped by role name without scope (a user with no role appears under `student`, a user with several roles under each of them). One click signs in as the chosen user; a free-text field lets you use another address, with an optional name. If `DEV_LOGIN_KEY` is set, a single key field appears and is used for every login on the page; the key is never stored in the session. Return to this page to switch users.

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=my-key .venv/bin/uvicorn oceens.main:app

# Sign in as the seed admin; -c saves the session cookie
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for subsequent requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

> [!WARNING]
> `dev` mode does not require `SECRET_KEY`. Without it, the key is random and unknown; but if a known `SECRET_KEY` is set (shared, copied from an example…), anyone who knows it can forge a session cookie and bypass `DEV_LOGIN_KEY`: `dev` mode accepts this, since it is only meant for local use.

---

## Notable features

### Teacher analytics

The `/dashboard/teachers/analytics` route (`campus_manager`, `program_manager`) aggregates the satisfaction score per `(teacher, survey)` from `QCU_Satisfaction` responses that have an `Answer.teacher` (ME sections). The teacher list is sorted with `teacher_sort_key()`, case- and accent-insensitive, and can be filtered by school year, semester, program and teacher.

### Teacher filter in the visualization

A client-side selector filters the visualization without reloading: only the chosen teacher's modules remain visible, and the Campus and Program sections are hidden. The page reads `?teacher=<name>` on load to pre-filter itself; links from the analytics page pass this parameter, so clicking a teacher's score opens their view directly.

### Surveys imported from Excel

Surveys loaded by `survey_loader_from_xlsx.py` have no `QCU_Attendance` question: `services/visualisation_data.py` then uses `satisfaction_responses_count` as a fallback denominator for the teacher score. Teacher names are normalized with `.title()` both at import and at aggregation, to merge case variants (`"GADEMER Antoine"` and `"Gademer Antoine"` = a single entry). Questions are sorted by `question_id` in the template, which guarantees charts come before free-text answers regardless of insertion order.

### Campus director scope

The `campus_manager` dashboard only shows closed surveys with at least one respondent. The questionnaire link and QR code are hidden there (`can_view_survey_link=False`): this role views results without distributing surveys. The `{% if can_view_survey_link | default(true) %}` guard leaves the other dashboards unchanged.

### Orphan student cleanup

When a survey is deleted, students who are no longer attached to **any other**
survey are also deleted, to avoid accumulating unused accounts
(`services/helpers.py`, `_delete_orphan_students`). A safeguard protects users
with a privileged role (`admin`, `program_manager`, `facilitator`,
`campus_manager`): a teacher or manager who answered a survey is never deleted.

### Adding a user by email

The "Utilisateurs" (Users) tab of the admin dashboard offers a
**« + Ajouter un utilisateur »** (add user) button: an email is enough to
create the account, with the `student` role by default (`POST /api/users`,
admin only). The email is validated (format + allowed domain) and duplicates
are rejected.

---

## Deployment checklist

- [ ] `.env` created with real Azure credentials and a dedicated `SECRET_KEY` (required unless `AUTH_MODE=dev`, otherwise the application refuses to start)
- [ ] `AUTH_MODE` unset or `entra`
- [ ] Valid SSL certificate (Let's Encrypt or equivalent)
- [ ] `https_only=True` in the SessionMiddleware (automatic unless `AUTH_MODE=dev`)
- [ ] Database present (`database/db_oceens.db`) or Docker volume mounted
- [ ] Environment variables secured, including `LLM_API_KEY`
- [ ] **Docker Compose**: `.env` loaded via `env_file`, never copied into the image; `LOCAL_DATABASE_DIR` pointing to the right database directory
- [ ] Summaries daemon (`oceens-summaries`) running if LLM summaries are used

---

## Validation before contributing

The repository has no automated test suite or CI. Before proposing a change, follow the checks in [docs/smoke-test.md](docs/smoke-test.md).

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**OcéEns Team** — EPF
