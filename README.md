# Music Subscription App

A cloud-based music subscription web app for the RMIT cloud computing assignment. The backend is a FastAPI service backed by DynamoDB and S3, and the frontend is a static HTML/CSS/JavaScript app that can point at any deployed backend through an API base URL.

## Capabilities

- User registration, login, and logout.
- Song search by title, artist, album, and year.
- Personal music subscriptions stored per user.
- Artist images served through backend-generated S3 presigned URLs.
- Static frontend with configurable backend target via `config.js`, URL query parameter, or `localStorage`.
- Deployment paths for EC2, ECS Fargate, and Lambda with API Gateway.

> Security note: this is a demo/assignment app. Passwords are stored in plaintext and browser session state uses `sessionStorage`; use password hashing and real auth tokens for production.

## Tech Stack

| Area      | Tools                                                  |
| --------- | ------------------------------------------------------ |
| Backend   | Python 3.12, FastAPI, Uvicorn, Pydantic, Boto3, Mangum |
| Frontend  | HTML5, CSS, vanilla JavaScript                         |
| AWS       | DynamoDB, S3, EC2, ECS Fargate, Lambda, API Gateway    |
| Packaging | `uv`, Docker, `requirements.txt` export                |

## Repository Layout

| Path                            | Purpose                                                                 |
| ------------------------------- | ----------------------------------------------------------------------- |
| `app/`                          | FastAPI app, DynamoDB/S3 helpers, routers, schemas                      |
| `frontend/`                     | Static web frontend (`index.html`, `app.js`, `styles.css`, `config.js`) |
| `deploy/`                       | EC2, ECS, Lambda, and API Gateway deployment assets                     |
| `q1_create_login.py`            | Create and seed the `login` table                                       |
| `q2_create_music.py`            | Create the `music` table and indexes                                    |
| `q3_load_music.py`              | Load songs from `2026a2_songs.json`                                     |
| `create_subscriptions_table.py` | Create the `subscriptions` table                                        |
| `q4_S3_images.py`               | Download artist images and upload them to S3                            |
| `deployment_guide.md`           | Full AWS deployment guide                                               |

## Local Development

Install runtime dependencies:

```bash
uv sync --no-dev
```

Configure AWS credentials before using DynamoDB or S3:

```bash
aws configure

# AWS Learner Lab also needs the session token.
export AWS_SESSION_TOKEN=<paste from AWS Details>
```

Run the backend:

```bash
uv run dev
```

Backend URLs:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

Run the frontend:

```bash
cd frontend
python -m http.server 5173
```

Open the frontend against the local backend:

```text
http://127.0.0.1:5173/?apiBase=http://127.0.0.1:8000
```

## Database Initialisation

Run these scripts once, in order:

```bash
python q1_create_login.py
python q2_create_music.py
python q3_load_music.py
python create_subscriptions_table.py
python q4_S3_images.py
```

Expected seed data:

| Table           | Expected count  |
| --------------- | --------------- |
| `login`         | 10 users        |
| `music`         | 137 songs       |
| `subscriptions` | 0 subscriptions |

For a clean rebuild in CloudShell:

```bash
chmod +x reset_music_table.sh
./reset_music_table.sh
```

The reset script drops and recreates the DynamoDB tables, reloads the song data, and prepares the S3 image data.

## DynamoDB Tables

| Table           | Keys                               | Notes                                                                         |
| --------------- | ---------------------------------- | ----------------------------------------------------------------------------- |
| `login`         | `email` (PK)                       | Stores `user_name` and `password`                                             |
| `music`         | `title` (PK), `album` (SK)         | Stores song metadata, image key, lower-case search fields, and search indexes |
| `subscriptions` | `user_email` (PK), `music_id` (SK) | Stores subscribed songs per user, where `music_id` is `{title}#{album}`       |

The `music` table includes `TitleYearIndex`, `TitlePrefixIndex`, and `ArtistYearIndex` to support the query patterns used by the app.

## API Overview

| Method            | Path                                | Description                              |
| ----------------- | ----------------------------------- | ---------------------------------------- |
| `GET`             | `/health`                           | Health check                             |
| `POST`            | `/register`                         | Register a user                          |
| `POST`            | `/login`                            | Authenticate a user                      |
| `GET/POST/DELETE` | `/logout`                           | End session state                        |
| `POST`            | `/songs/search`                     | Search songs with a JSON body            |
| `GET`             | `/songs/search`                     | Search songs with query parameters       |
| `GET`             | `/subscriptions/{email}`            | List a user's subscriptions              |
| `POST`            | `/subscriptions`                    | Add a subscription                       |
| `DELETE`          | `/subscriptions`                    | Remove a subscription with a JSON body   |
| `DELETE`          | `/subscriptions/{email}/{music_id}` | Remove a subscription by path parameters |

Search accepts optional `title`, `artist`, `album`, and `year` fields, but at least one field is required. Text fields are case-insensitive substring matches; `year` is an exact match. Multiple fields are AND-combined first, then supplemented with high-scoring OR matches when too few exact combined matches are found.

## Frontend Configuration

The default API target lives in `frontend/config.js`:

```javascript
window.APP_CONFIG = {
  appName: "Music Subscription",
  apiBaseUrl: "http://127.0.0.1:8000",
};
```

For demos or deployed environments, override the backend without editing files:

```text
http://127.0.0.1:5173/?apiBase=https://api-id.execute-api.us-east-1.amazonaws.com/prod
```

The frontend also supports a persistent browser override:

```javascript
localStorage.setItem(
  "music-subscription-api-base",
  "https://api-id.execute-api.us-east-1.amazonaws.com/prod",
);
```

Common backend targets:

| Backend         | Example API base URL                                        |
| --------------- | ----------------------------------------------------------- |
| EC2 direct      | `http://<EC2_PUBLIC_DNS>`                                   |
| ECS through ALB | `http://<ALB_DNS_NAME>`                                     |
| API Gateway     | `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod` |

## Deployment

The project documents three independently deployable backend options:

| Backend     | Entry point                                             |
| ----------- | ------------------------------------------------------- |
| EC2         | Docker container running the FastAPI app                |
| ECS Fargate | Docker container behind an Application Load Balancer    |
| Lambda      | `lambda_handler.handler` through Mangum and API Gateway |

The frontend is static and can be hosted separately, then pointed at any backend through `apiBase`.

See [deployment_guide.md](deployment_guide.md) for full AWS setup, validation, and teardown steps.

## Dependency Management

This project uses `uv` with `pyproject.toml` and `uv.lock`.

```bash
# Sync runtime dependencies.
uv sync --no-dev

# Refresh lockfile after dependency changes.
uv lock

# Regenerate requirements.txt for Docker and CloudShell.
uv export --no-emit-workspace --no-emit-project --no-hashes --no-annotate --no-dev > requirements.txt
```
