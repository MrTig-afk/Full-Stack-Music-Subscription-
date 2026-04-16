# Cloud Computing - Music Database ETL Pipeline

This project implements a cloud-based infrastructure for managing a music library using **AWS DynamoDB** and **S3**. It includes scripts for schema creation, batch data ingestion, and an automated image processing pipeline.

## 🚀 Project Overview
* **Database:** Amazon DynamoDB (NoSQL)
* **Storage:** Amazon S3 (Object Storage)
* **Language:** Python 3.x
* **SDK:** Boto3

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
* **AWS Access Key ID:** [Paste Team Key]
* **AWS Secret Access Key:** [Paste Team Secret]
* **Default region name:** `us-east-1` (Required for consistency)
* **Default output format:** `json`

---

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `q1_create_login.py` | Creates the `login` table and populates 10 RMIT student entities. |
| `q2_create_music.py` | Defines the `music` table schema (Title = Partition Key, Album = Sort Key). |
| `q3_load_music.py` | Batch uploads 137 songs from the JSON dataset to DynamoDB. |
| `q4_s3_images.py` | Downloads artist images and uploads them to the unique S3 bucket. |
| `2026a2_songs.json` | The raw source data. |

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