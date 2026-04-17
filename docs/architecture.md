# CPS (Quick Track Check System) Architecture

This document describes the high-level architecture, module interactions, and the data pipeline of the Quick Track Check Processing System (CPS).

## 1. High-Level Overview

CPS is a full-stack application built to extract structured data from images and PDFs of bank checks. It leverages an AI vision model acting as a sophisticated OCR system combined with robust backend validation to achieve high accuracy.

The system is separated into three discrete tiers:
1. **Frontend (Client)**: Next.js (React) App Router frontend serving an interactive UI.
2. **Backend (API)**: FastAPI (Python) backend handling file processing, AI orchestration, validation, and database interactions.
3. **Storage & Database**: PostgreSQL for structured data and AWS S3 for document blobs.

---

## 2. Component Architecture

### 2.1 Frontend (Next.js)
Located in `src/app`. Built horizontally with React server components and client interactions.

- **UI Framework:** Next.js 16 (App Router), React 19.
- **Styling:** Tailwind CSS v4 and Framer Motion for interactivity.
- **Key Modules:**
  - `src/app/page.tsx`: The primary dashboard where batches of checks are tracked.
  - `src/app/upload/`: Exposes a drag-and-drop React Dropzone interface for check ingestion.
  - `src/app/components/`: Reusable interface parts (modals, loaders, data tables).
  - Internal API routes map directly to external FastAPI backend endpoints using the `NEXT_PUBLIC_API_URL` environment variable.

### 2.2 Backend (FastAPI)
Located in `server/`. Follows a modular monolithic design.

- **`main.py`**: The application entry point defining all API endpoints (Auth, Upload, Extraction, Batch Mgmt, Export).
- **`models.py`**: SQLAlchemy ORM definitions linking Python objects to PostgreSQL tables (`User`, `CheckBatch`, `Check`, `AuditLog`).
- **`database.py`**: Initializes the SQL connection pool and session dependency.
- **`ai_extractor.py`**: Orchestrates Google Gemini (Flash) API interactions. Contains strictly tuned system prompts tailored for MICR code and standard check layout extraction. Includes a rate-limiting queue for the Gemini Free Tier.
- **`pdf_extractor.py` & `table_extractor.py`**: Wraps PyMuPDF to cleanly convert varied document formats (PDF) into standardized, high-DPI image base64 strings needed for the Vision AI.
- **`validators.py`**: Extremely critical component ensuring AI hallucinated routing/account numbers are identified. Validates inputs using banking standard checksum algorithms (e.g., ABA routing checksums).
- **`security.py`**: Handles bcrypt password hashing, and JWT minting and verification.

---

## 3. The Extraction Data Pipeline

1. **Upload Initiation**: User drops a PDF or batch of Images on the UI. The Next.js frontend calls `POST /api/checks/upload` on the backend, generating a tracking `CheckBatch` in the DB.
2. **File Processing**: The FastAPI backend asynchronously processes the uploaded files. PyMuPDF extracts/renders pages at high resolution.
3. **AI Vision Request**: The `ai_extractor.py` converts each high-res page image to Base64 and executes a sequential request to the Google Gemini 1.5 API.
4. **Validation Layer**:
    - The JSON returned from Gemini is parsed.
    - `validators.py` kicks in. It sanitizes text, fixes common OCR confusions (e.g., distinguishing the letter 'O' vs the number '0'), and runs an ABA routing checksum.
    - If the MICR line fails validation, the check's `status` defaults to `needs_review` rather than `approved`.
5. **Storage**: The original check images are stored in AWS S3 (retrieved later via presigned URLs). The validated extracted data is written to the PostgreSQL database under the associated batch ID.
6. **Real-time Feedback**: The frontend progressively polls or listens for completion signals, switching the `Processing...` state to actionable results for the user.

---

## 4. Security & Authentication

- The application uses **JWT (JSON Web Tokens)**.
- Passwords are never stored in plaintext (using `bcrypt`).
- **Role-Based Execution (RBAC)**: Currently distinguishes Standard Users (can upload and review) from Admins (can access all batches and fetch comprehensive audit logs).
- **Audit Logging**: Any destructive action or manual override (changing a check amount, correcting a payee) generates a record in the `audit_logs` table for compliance tracking.
