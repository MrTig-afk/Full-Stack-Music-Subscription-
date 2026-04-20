# Cloud Computing - Music Database ETL Pipeline

This project implements a cloud-based infrastructure for managing a music library using **AWS DynamoDB** and **S3**. It includes scripts for schema creation, batch data ingestion, and an automated image processing pipeline.

## 🚀 Project Overview

- **Database:** Amazon DynamoDB (NoSQL)
- **Storage:** Amazon S3 (Object Storage)
- **Language:** Python 3.x
- **SDK:** Boto3

---

## 🛠️ Environment Setup

### 1. Local Configuration

Clone the repository and set up your virtual environment:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows (Git Bash)
# source venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. AWS CLI Configuration

You must have the AWS CLI installed. Use the **DevTeam** credentials provided in our private channel:

```bash
aws configure
```

**Required Settings:**

- **AWS Access Key ID:** [Paste Team Key]
- **AWS Secret Access Key:** [Paste Team Secret]
- **Default region name:** `us-east-1` (Required for consistency)
- **Default output format:** `json`

---

## 📂 Project Structure

| File                 | Description                                                                 |
| :------------------- | :-------------------------------------------------------------------------- |
| `q1_create_login.py` | Creates the `login` table and populates 10 RMIT student entities.           |
| `q2_create_music.py` | Defines the `music` table schema (Title = Partition Key, Album = Sort Key). |
| `q3_load_music.py`   | Batch uploads 137 songs from the JSON dataset to DynamoDB.                  |
| `q4_s3_images.py`    | Downloads artist images and uploads them to the unique S3 bucket.           |
| `2026a2_songs.json`  | The raw source data.                                                        |

---

## ⚡ How to Run

Run the scripts in the following order to ensure dependencies (like table creation) are met:

1. **Initialize Login Table:** `python q1_create_login.py`
2. **Initialize Music Table:** `python q2_create_music.py`
3. **Load Song Data:** `python q3_load_music.py`
4. **Transfer Images:** `python q4_s3_images.py`

---

## 📊 Verification

You can verify the deployment by running:

```bash
# Check DynamoDB item count
aws dynamodb scan --table-name music --select "COUNT"

# List S3 bucket contents
aws s3 ls s3://your-unique-bucket-name/
```

## 🌐 FastAPI Backend

This FastAPI application provides backend APIs for the music subscription system. It connects to AWS DynamoDB and supports user authentication, song search, and subscription management.

---

## 🚀 Features

- User Registration
- User Login & Logout
- Music Search (by title, artist, album, year)
- Subscribe to songs
- Remove subscribed songs
- View user subscriptions

---

## 🔗 API Endpoints

- POST `/register` → Register new user
- POST `/login` → Login user
- GET `/logout` → Logout
- POST `/songs/search` → Search songs
- GET `/subscriptions/{email}` → Get user subscriptions
- POST `/subscriptions` → Add subscription
- DELETE `/subscriptions` → Remove subscription

---

## ⚙️ Setup & Run

### 1. Activate virtual environment

```bash
# Windows
source venv/Scripts/activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn boto3 pydantic
```

### 3. Configure AWS

```bash
aws configure
```

(For AWS Learner Lab, use access key, secret key, and session token.)

### 4. Run FastAPI

```bash
uvicorn app.main:app --reload
```

### 5. Test APIs

Open in browser: <http://127.0.0.1:8000/docs>

🧪 Testing Flow
Register → /register
Login → /login
Search songs → /songs/search
Subscribe → /subscriptions
View subscriptions → /subscriptions/{email}
Remove subscription → /subscriptions (DELETE)
Logout → /logout
