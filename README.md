# 🏢 Sinhas GmbH — Property Data Management Portal

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

**A full-stack property data management system with a multi-user upload portal and a real-time admin dashboard — powered by Flask, MongoDB Atlas, and Chart.js.**

[Live Demo](https://sinhasrealty.onrender.com) · [GitHub Repo](https://github.com/deba2k5/sinhasrealty)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Deployment (Render)](#-deployment-render)
- [Screenshots](#-screenshots)

---

## 🌐 Overview

**Sinhas GmbH** is a web-based data management platform built for managing Swiss property (apartment) records. It provides two distinct interfaces:

1. **User Portal** (`/`) — A clean, professional SaaS-style interface for data entry teams to upload Excel/CSV files in bulk, run structured ETL jobs, or manually enter individual property records directly into MongoDB.

2. **Admin Dashboard** (`/admin`) — A real-time analytics and data management panel for administrators to view charts, browse all MongoDB collections, search/filter records, and perform inline edits.

---

## ✨ Features

### 📤 User Portal
| Feature | Description |
|---|---|
| **Bulk Upload** | Upload any `.xlsx` or `.csv` file; each sheet becomes a MongoDB collection |
| **Occupancy ETL** | Upload the master `OCCUPANCY` Excel file; auto-parses into structured `cities`, `buildings`, and `apartments` collections |
| **Manual Entry** | Form-based single record insertion with all key property fields matching MongoDB schema |
| **Drag & Drop** | Drag and drop files directly onto the upload zones |

### 🖥️ Admin Dashboard
| Feature | Description |
|---|---|
| **KPI Cards** | Real-time counts — Total Properties, Occupied, Available, Buildings |
| **4 Live Charts** | Occupancy donut, Properties by City bar, System Overview bar, Apartments pie — all via Chart.js |
| **Dynamic Sidebar** | Auto-fetches all MongoDB collections; click any to browse its data |
| **Data Table** | Paginated, searchable table for any collection with configurable row limit |
| **Load All Data** | One-click button to fetch all records from the active collection |
| **Inline Edit** | Click "Edit" on any row to open a field-level modal and save changes to MongoDB |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, Flask 3.0 |
| **Database** | MongoDB Atlas (PyMongo 4.6) |
| **Data Processing** | Pandas 2.2, OpenPyXL 3.1 |
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **Charts** | Chart.js (CDN) |
| **Server (Prod)** | Gunicorn 21.2 |
| **Deployment** | Render (via `render.yaml`) |
| **Fonts** | Google Fonts — Inter |

---

## 📁 Project Structure

```
sinhasgmbh/
│
├── app.py                  # Flask application & all API routes
├── index.html              # User Portal — upload & manual entry UI
├── admin.html              # Admin Dashboard — charts, tables, edit modal
│
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment configuration
├── .env                    # Local environment variables (git-ignored)
├── .gitignore
│
├── migrate_keys.py         # DB migration script (sanitizes field names)
├── import_from_excel.py    # Standalone ETL script (CLI)
├── upload_apartments.py    # CLI uploader for apartment records
├── upload_flat.py          # CLI uploader for flat records
├── analyze_excel.py        # Analysis/inspection utility for sheets
├── test_mongo.py           # MongoDB connection test script
└── test_server.py          # Flask server endpoint test script
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ installed
- A [MongoDB Atlas](https://cloud.mongodb.com) account with a cluster
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/deba2k5/sinhasrealty.git
cd sinhasrealty
```

### 2. Create & Activate a Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=<app>
```

> See [Environment Variables](#-environment-variables) for details.

### 5. Run Locally

```bash
python app.py
```

Open your browser at:
- **User Portal:** `http://localhost:5000/`
- **Admin Dashboard:** `http://localhost:5000/admin`

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | ✅ Yes | Full MongoDB Atlas connection string with credentials |

The app falls back to a default URI if `MONGO_URI` is not set, but it is **strongly recommended** to set it via `.env` for local development and via the hosting provider's environment settings for production.

---

## 📡 API Reference

All API endpoints return JSON.

### Upload Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Bulk upload any Excel or CSV file to MongoDB |
| `POST` | `/upload_occupancy` | ETL upload — parses Occupancy Excel into Cities/Buildings/Apartments |
| `POST` | `/add_city` | Insert a single city record into the `cities` collection |
| `POST` | `/add_property` | Insert a single record into the database |

### Admin / Data Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin` | Serve the Admin Dashboard HTML page |
| `GET` | `/api/collections` | List all MongoDB collection names |
| `GET` | `/api/data/<collection>` | Paginated, searchable data from a collection |
| `POST` | `/api/update/<collection>/<doc_id>` | Update a single document by `_id` |
| `GET` | `/api/stats` | Aggregated stats for KPI cards and charts |
| `GET` | `/download_csv?collection=<name>` | Export any collection as a downloadable CSV |

### `/api/data/<collection>` Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | `1` | Page number |
| `limit` | int | `50` | Records per page (`9999` = load all) |
| `search` | string | `""` | Case-insensitive search across all string fields |

---

## ☁️ Deployment (Render)

The project is pre-configured for [Render](https://render.com) via `render.yaml`.

### Steps

1. **Push to GitHub**

2. **Create a Render Account** at [render.com](https://render.com)

3. **New Web Service** → Connect your GitHub repo `deba2k5/sinhasrealty`

4. Render will auto-detect `render.yaml`. Confirm these settings:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

5. **Add Environment Variable** in the Render dashboard:
   - Key: `MONGO_URI`
   - Value: *(your MongoDB Atlas connection string)*

6. Click **"Deploy"** — your app will be live at:
   ```
   https://sinhasgmbh.onrender.com
   ```

---

## 📊 Data Schema

### Shared Records (migrated)

| Field | Type | Description |
|---|---|---|
| `Apartment Address` | String | Street name of the apartment |
| `City` | String | City name |
| `Floor` | Number | Floor number |
| `POSITION` | String | Unit position (Left / Right / Center) |
| `Apartment SQMT` | Number | Apartment size in square meters |
| `NO OF ROOMS` | Number | Number of rooms (e.g. 3.5) |
| `AWN NO` | Number | Internal AWN reference number |
| `INDIV / SHR` | String | Occupancy type (Family / Sharing / Individual) |
| `Status` | String | Occupancy status (OCCUPIED / AVAILABLE) |

---

## 👤 Author

**Debangshu** — [github.com/deba2k5](https://github.com/deba2k5)

---

## 📄 License

This project is proprietary software developed for **Sinhas GmbH**. All rights reserved.

---

<div align="center">
  Built with ❤️ for Sinhas GmbH using Flask, MongoDB Atlas, and Chart.js
</div>
