# Music Subscription App

A cloud-based music subscription web application built on AWS. Users can log in, search for songs, and manage personal subscriptions. The FastAPI backend connects to DynamoDB and S3; the frontend is a static HTML/JS/CSS app.

**Tech stack:** Python 3.12, FastAPI, Boto3, Uvicorn, Mangum | HTML5, Vanilla JS | DynamoDB, S3, EC2, ECS Fargate, Lambda + API Gateway

---

## Local Development

### Install dependencies

```bash
uv sync --no-dev
```

### Configure AWS credentials

```bash
aws configure
# For Learner Lab, also set AWS_SESSION_TOKEN:
export AWS_SESSION_TOKEN=<paste from AWS Details>
```

### Run backend

```bash
uv run dev
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/docs  (Swagger UI)
```

### Run frontend

```bash
cd frontend && python -m http.server 5173
# → http://127.0.0.1:5173/?apiBase=http://127.0.0.1:8000
```

---

## Database Initialisation

Run these scripts once in order. The reset script handles teardown and re-runs all four cleanly.

```bash
python q1_create_login.py           # login table + 10 seed users
python q2_create_music.py           # music table + indexes
python q3_load_music.py             # load 137 songs from 2026a2_songs.json
python create_subscriptions_table.py
python q4_S3_images.py              # download artist images → upload to S3
```

**Full reset (CloudShell):**

```bash
chmod +x reset_music_table.sh && ./reset_music_table.sh
```

Drops and recreates all three tables, then reruns all four DDL scripts. Expected final counts: `login: 10`, `music: 137`, `subscriptions: 0`.

---

## DynamoDB Schema

### `login`

| Key          | Type   |
| ------------ | ------ |
| `email` (PK) | String |

Attributes: `user_name`, `password`. Billing: PAY_PER_REQUEST.

### `music`

| Key          | Type   |
| ------------ | ------ |
| `title` (PK) | String |
| `album` (SK) | String |

Attributes: `artist`, `year`, `img_url`, `music_id`, `title_lower`, `artist_lower`, `album_lower`, `first_char`.

Indexes:

| Index              | Type | Keys                                | Purpose                                                       |
| ------------------ | ---- | ----------------------------------- | ------------------------------------------------------------- |
| `TitleYearIndex`   | LSI  | PK: `title`, SK: `year`             | Title + year range queries                                    |
| `TitlePrefixIndex` | GSI  | PK: `first_char`, SK: `title_lower` | Efficient prefix-based title search (majority access pattern) |
| `ArtistYearIndex`  | GSI  | PK: `artist`, SK: `year`            | Artist and artist + year queries (demo patterns)              |

Billing: PAY_PER_REQUEST.

### `subscriptions`

| Key               | Type                         |
| ----------------- | ---------------------------- |
| `user_email` (PK) | String                       |
| `music_id` (SK)   | String — `"{title}#{album}"` |

Billing: PAY_PER_REQUEST.

---

## API Endpoints

| Method            | Path                                | Description                       |
| ----------------- | ----------------------------------- | --------------------------------- |
| `GET`             | `/health`                           | Health check                      |
| `POST`            | `/register`                         | Register new user                 |
| `POST`            | `/login`                            | Authenticate user                 |
| `GET/POST/DELETE` | `/logout`                           | End session                       |
| `POST`            | `/songs/search`                     | Search songs (JSON body)          |
| `GET`             | `/songs/search`                     | Search songs (query params)       |
| `GET`             | `/subscriptions/{email}`            | List user subscriptions           |
| `POST`            | `/subscriptions`                    | Add subscription                  |
| `DELETE`          | `/subscriptions`                    | Remove subscription (JSON body)   |
| `DELETE`          | `/subscriptions/{email}/{music_id}` | Remove subscription (path params) |

All search fields (`title`, `artist`, `album`, `year`) are optional but at least one is required. Title, artist, and album use case-insensitive substring matching. Multiple fields are AND-combined by default; if AND returns fewer than 3 results, top OR matches are appended.

---

## Deployment

Three independent backend deployments are supported, each fully functional and independently validated:

| Backend     | Entry point                                       | Frontend hosting  |
| ----------- | ------------------------------------------------- | ----------------- |
| EC2         | Docker container on port 80                       | S3 static website |
| ECS Fargate | Docker container via ALB                          | S3 static website |
| Lambda      | `lambda_handler.handler` (Mangum) via API Gateway | S3 static website |

See **[deployment_guide.md](deployment_guide.md)** for step-by-step instructions covering all three backends, the Docker build/push workflow, API Gateway setup, and teardown.

---

## Dependency Management

This project uses `uv` with `pyproject.toml` and `uv.lock`.

```bash
# Sync environment
uv sync --no-dev

# After editing pyproject.toml
uv lock

# Regenerate requirements.txt (used by Docker and CloudShell)
uv export --no-emit-workspace --no-emit-project --no-hashes --no-annotate --no-dev > requirements.txt
```
