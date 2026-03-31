---
title: CPS Backend
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🏦 CPS — Quick Track Check System

A full-stack AI-powered web application that automatically extracts structured financial data from business banking checks (PDFs and Images). Upload one or more checks, and leverage OpenAI's Vision models for high-accuracy data extraction, robust MICR validation, and full audit logging.

**Live Demo**: [cps.vercel.app](https://cps-mu.vercel.app/)

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [How the AI Extraction Works](#how-the-ai-extraction-works)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Output Schema](#output-schema)

---

## ✨ Features

- 📄 **Batch PDF & Image Processing** — Upload and process multiple checks at once.
- 🧠 **AI-Powered OCR Extraction** — High-accuracy extraction using OpenAI's GPT-4o-mini vision capabilities.
- 🏦 **MICR Line Parsing & Validation** — Accurately identifies Routing and Account Numbers with fallback checksum validation.
- 🛡️ **Role-Based Authentication** — Secure login and user management system (Admin / Standard roles) using JWT.
- 📝 **Audit Logging** — Tracks all manual reviews, edits, and status changes for compliance.
- ☁️ **AWS S3 Integration** — Secure cloud storage for check images using presigned URLs, with local filesystem fallback.
- 🌙 **Dark / Light Mode** — Toggle with persistent preference (saved to localStorage).
- 📊 **CSV & Excel Export** — Download all approved records as spreadsheets tailored for accounting software.
- ⚡ **Real-time Feedback** — Animated upload queue and live dashboard interactions.

---

## 🛠️ Tech Stack

### Frontend
| Package | Version | Purpose |
|---|---|---|
| [Next.js](https://nextjs.org/) | 16.1.6 | React Framework (App Router) |
| [React](https://react.dev/) | 19.x | UI Runtime |
| [TypeScript](https://www.typescriptlang.org/) | ^5 | Static Typing |
| [Tailwind CSS](https://tailwindcss.com/) | v4 | Utility-first Styling |
| [Framer Motion](https://www.framer.com/motion/) | ^12 | Animations & Transitions |

### Backend
| Package | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/) | 3.x | API & Extraction Runtime |
| [FastAPI](https://fastapi.tiangolo.com/) | >=0.100.0 | High-performance Python Web Framework |
| [SQLAlchemy](https://www.sqlalchemy.org/) | >=2.0.0 | ORM for PostgreSQL Document Tracking |
| [OpenAI](https://github.com/openai/openai-python) | >=1.30.0 | AI Vision Extraction via GPT-4o-mini |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | >=1.23.0 | PDF Processing & Image Conversion |
| [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) | - | AWS S3 Integration |

### Infrastructure
| Service | Purpose |
|---|---|
| [Vercel](https://vercel.com/) | Frontend Hosting |
| [Railway](https://railway.app/) | Backend API Hosting & PostgreSQL Database |
| [AWS S3](https://aws.amazon.com/s3/) | Secure Document Storage for Check Images |

---

## 📁 Project Structure

```
CPS/
├── src/                       
│   └── app/                   # ⚛️ Next.js Frontend App Router
│       ├── api/               # Next.js Serverless API Routes
│       ├── components/        # React UI Components
│       ├── globals.css        # Global Styles
│       ├── layout.tsx         # Root Layout
│       └── page.tsx           # Main Dashboard View
│
├── server/                    # 🐍 FastAPI Backend Application
│   ├── main.py                # Application Entrypoint & API Routes
│   ├── models.py              # SQLAlchemy Database Models
│   ├── database.py            # PostgreSQL Connection & Session Setup
│   ├── ai_extractor.py        # OpenAI Vision integration & Prompting
│   ├── validators.py          # MICR Checksum & Data Validators
│   ├── security.py            # JWT Authentication & Password Hashing
│   └── export.py              # Excel/CSV Generation
│
├── vercel.json                # Vercel Deployment Configuration
├── railway.json               # Railway Deployment Configuration
├── package.json               # Node.js Dependencies
└── requirements.txt           # Python Dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) >= 20.9.0
- [Python](https://www.python.org/downloads/) >= 3.9
- PostgreSQL Database (Local or Cloud)
- OpenAI API Key
- AWS S3 Bucket (Optional, falls back to local uploads)

### 1. Clone the Repository

```bash
git clone https://github.com/Itskainos/cps.git
cd cps
```

### 2. Frontend Setup

```bash
npm install
npm run dev
```

### 3. Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
touch .env.local
```

Add the following to your `.env.local`:
```env
DATABASE_URL=postgresql://user:password@localhost/dbname
OPENAI_API_KEY=sk-your-openai-api-key
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
JWT_SECRET=your-secure-jwt-secret
```

Start the backend server (Windows):
```bash
start_backend.bat
```
Alternatively, run it manually:
```bash
uvicorn server.main:app --reload --port 8000
```

---

## 🧠 How the AI Extraction Works

The system utilizes a hybrid approach: PDF parsing combined with OpenAI's Vision capabilities.

### Pipeline
1. **Upload**: A PDF or Image is uploaded via the Next.js frontend to the FastAPI backend.
2. **Preprocessing**: PyMuPDF converts PDF pages into high-resolution JPEGs (zoomed 2x for OCR quality).
3. **AI Vision**: The image is encoded to Base64 and sent to `gpt-4o-mini` with a strict extraction system prompt.
4. **Validation**: The extracted Routing Number and Account variables are rigorously tested against banking checksum algorithms.
5. **Storage**: Images are securely uploaded to AWS S3 (generating presigned URLs) and parsed data is stored in the PostgreSQL database.

---

## 📡 API Reference

### Important Endpoints

- `POST /api/auth/login` - Authenticate and receive JWT.
- `POST /api/checks/upload` - Create a new upload batch.
- `POST /api/checks/extract` - Upload single check, perform AI OCR, and attach to Batch.
- `GET /api/checks/batches` - Retrieve paginated batches for the Dashboard.
- `PATCH /api/checks/{check_id}` - Manual review overrides and Approval.
- `GET /api/audit` - Fetch a global history of all changes (Admin only).
- `GET /api/checks/export` - Export approved checks to Excel.

---

## ☁️ Deployment

The project separates the Next.js frontend and the FastAPI backend for flexibility and scalability.

### 1. Backend (Railway)
1. Provide a **PostgreSQL Database** in Railway.
2. Link the GitHub repository and specify the source directory.
3. Add all required Environment Variables (`DATABASE_URL`, `OPENAI_API_KEY`, AWS Keys, etc.).
4. Add a shared volume mounted to `/data` if needed (for local upload fallback).

### 2. Frontend (Vercel)
1. Import the repository at [vercel.com/new](https://vercel.com/new).
2. Add the Environment Variable:
   - `NEXT_PUBLIC_API_URL`: Points to your deployed Railway backend (e.g., `https://cps-backend.up.railway.app`).
3. Click **Deploy**.

---

## 📤 Output Schema

Every extracted check record maps to this structure:

| Field | Type | Description |
|---|---|---|
| `store_name` | `string` | The associated store or location |
| `check_date` | `string` | ISO Date `YYYY-MM-DD` |
| `check_number` | `string` | Digits only from top-right corner |
| `payee_name` | `string` | "Pay to the Order of" entity |
| `amount` | `float` | Check numeric amount |
| `memo` | `string` | Memo / Notes line |
| `bank_name` | `string` | Issuing Bank name |
| `routing_number` | `string` | 9-digit ABA routing number |
| `account_number` | `string` | Bank account number |
| `confidence_score` | `float` | AI OCR confidence rating (0.0 - 1.0) |

---

## 📄 License

MIT © 2026 Jimmy Sherpa (Itskainos) & Quick Track Inc.
