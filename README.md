# 🏦 CPS — Cheque Printing System

A full-stack **Zonal OCR** web application that automatically extracts structured financial data from bank cheque PDFs. Upload one or more cheques, get structured JSON back instantly — no cloud Vision APIs, no machine learning.

**Live Demo**: [cps.vercel.app](https://cps.vercel.app) *(replace with your actual Vercel URL)*

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [How the OCR Works](#how-the-ocr-works)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Output Schema](#output-schema)

---

## ✨ Features

- 📄 **Batch PDF Processing** — Upload and process multiple cheques at once
- 🔍 **Zonal OCR Extraction** — Coordinate-based precision extraction (no ML required)
- 🏦 **MICR Line Parsing** — Extracts Routing Number and Account Number from the MICR footer
- 🌙 **Dark / Light Mode** — Toggle with persistent preference (saved to localStorage)
- 📊 **CSV Export** — Download all extracted records as a spreadsheet
- ⚡ **Real-time Feedback** — Animated upload queue and live results table
- 🖱️ **Drag & Drop** — Drop PDF files directly onto the upload zone
- ☁️ **Cloud Deployed** — Runs on Vercel with a hybrid Next.js + Python runtime

---

## 🛠️ Tech Stack

### Frontend
| Package | Version | Purpose |
|---|---|---|
| [Next.js](https://nextjs.org/) | 16.1.6 | React Framework (App Router) |
| [React](https://react.dev/) | 19.2.3 | UI Runtime |
| [TypeScript](https://www.typescriptlang.org/) | ^5 | Static Typing |
| [Tailwind CSS](https://tailwindcss.com/) | v4 | Utility-first Styling |
| [Framer Motion](https://www.framer.com/motion/) | ^12 | Animations & Transitions |
| [next-themes](https://github.com/pacocoursey/next-themes) | ^0.4.6 | Dark/Light Mode |
| [react-dropzone](https://react-dropzone.js.org/) | ^15 | Drag & Drop File Upload |
| [lucide-react](https://lucide.dev/) | ^0.575 | Icon Library |

### Backend
| Package | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/) | 3.x | Extraction Runtime |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | >=0.11.0 | PDF Parsing & Zone Cropping |
| [Flask](https://flask.palletsprojects.com/) | >=3.0.0 | HTTP Handler (Vercel Serverless) |
| [flask-cors](https://flask-cors.readthedocs.io/) | >=4.0.0 | Cross-Origin Resource Sharing |

### Infrastructure
| Service | Purpose |
|---|---|
| [Vercel](https://vercel.com/) | Hosting (Next.js + Python multi-runtime) |
| [GitHub](https://github.com/Itskainos/cps) | Version Control |

---

## 📁 Project Structure

```
CPS/
├── api/
│   └── extract.py              # 🐍 Python OCR engine (CLI + Flask dual-mode)
│
├── src/
│   └── app/
│       ├── api/
│       │   └── extract-bridge/ # 🌉 Local dev Node→Python bridge
│       │       └── route.ts
│       ├── components/
│       │   └── ThemeProvider.tsx  # Dark/Light mode provider
│       ├── globals.css            # CSS variables (dark/light themes)
│       ├── layout.tsx             # Root layout (fonts, ThemeProvider)
│       └── page.tsx               # Main UI page
│
├── cheques/                       # 📂 Sample cheque PDF files
│
├── vercel.json                    # ☁️  Vercel build + routing config
├── requirements.txt               # 🐍 Python dependencies
├── next.config.ts                 # Dev rewrites + React Compiler
├── package.json
├── tsconfig.json
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) >= 18
- [Python](https://www.python.org/downloads/) >= 3.9
- [Git](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/Itskainos/cps.git
cd cps
```

### 2. Install Node.js Dependencies

```bash
npm install
```

### 3. Install Python Dependencies

```bash
pip install pdfplumber
```

> **Note**: You do **not** need to install Flask locally. It is only required on the Vercel cloud runtime and is installed automatically from `requirements.txt` during deployment.

### 4. Start the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🔬 How the OCR Works

The engine uses **Coordinate-Based Zonal Extraction** — a fast, deterministic approach that does not rely on machine learning or cloud APIs.

### Pipeline

```
PDF Upload
    │
    ▼
pdfplumber.open(pdf)
    │
    ▼
For each page:
    ├─ Crop zone: page.crop((x0, y0, x1, y1))
    ├─ Extract text: cropped.extract_text()
    └─ Clean & normalize
    │
    ▼
JSON Array Output
```

### Defined Extraction Zones

Each field has a bounding box `(x0, y0, x1, y1)` in PDF coordinate space (points), calibrated for the **Stellar Bank** standard cheque template:

| Field | x0 | y0 | x1 | y1 | Description |
|---|---|---|---|---|---|
| `Cheque_No` | 480 | 5 | 570 | 30 | Top-right cheque number |
| `Date` | 480 | 30 | 580 | 50 | Date field |
| `Payee` | 18 | 80 | 500 | 110 | "Pay to the Order of" field |
| `Amount` | 530 | 75 | 605 | 100 | Numeric amount box |
| `Memo` | 50 | 135 | 300 | 160 | Memo/notes line |
| `Bank` | 200 | 15 | 412 | 45 | Bank name header |
| `Routing_No` | 250 | 250 | 345 | 275 | ⚠️ MICR Line — Routing |
| `Account_No` | 345 | 250 | 450 | 275 | ⚠️ MICR Line — Account |

### Text Cleaning Rules

| Field | Cleaning Applied |
|---|---|
| `Cheque_No` | Strip all non-numeric characters |
| `Amount` | Remove `$`, `*`, and any non-digit characters except `.` |
| `Payee` | Truncate at first `$` symbol or newline |
| `Routing_No` | Keep digits only (removes MICR glyphs `⑆ ⑈`) |
| `Account_No` | Keep digits only |

---

## 📡 API Reference

### `POST /api/extract`

Extracts cheque data from an uploaded PDF file.

**Request**

```
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `File` | ✅ | The cheque PDF to process |

**Response — Success** `200 OK`

```json
[
  {
    "Date":       "2/16/2026",
    "Cheque_No":  "1190005",
    "Payee":      "JOHN DOE",
    "Amount":     "10.05",
    "Memo":       "Invoice #42",
    "Bank":       "Stellar Bank",
    "Routing_No": "102301164",
    "Account_No": "2017237191"
  }
]
```

> Returns an array — one object per page if the PDF contains multiple cheques.

**Response — Error** `400 / 500`

```json
{ "error": "No file uploaded" }
```

---

## ☁️ Deployment

### Vercel (Recommended)

The project uses a **hybrid multi-runtime** deployment on Vercel, declared in `vercel.json`:

```json
{
  "builds": [
    { "src": "package.json",    "use": "@vercel/next"   },
    { "src": "api/extract.py",  "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/extract", "dest": "/api/extract.py", "methods": ["POST", "OPTIONS"] },
    { "src": "/(.*)",        "dest": "/$1" }
  ]
}
```

**Steps:**
1. Push to GitHub
2. Import the repository at [vercel.com/new](https://vercel.com/new)
3. Keep all settings at their defaults
4. Click **Deploy**

Vercel automatically installs Python dependencies from `requirements.txt`.

### Local vs Production Routing

| Environment | How `/api/extract` is served |
|---|---|
| **`npm run dev`** | Via `next.config.ts` rewrite → `src/app/api/extract-bridge/route.ts` → Python CLI subprocess |
| **Vercel Production** | Via `vercel.json` → `api/extract.py` (Flask Python Serverless Function) |

---

## ⚙️ Configuration

### Adjusting OCR Zones

To support a different cheque template, edit the `ZONES` dictionary in `api/extract.py`:

```python
ZONES = {
    "Cheque_No":  (x0, y0, x1, y1),
    "Date":       (x0, y0, x1, y1),
    "Payee":      (x0, y0, x1, y1),
    # ... etc
}
```

**Tip**: Use `pdfplumber`'s debug visualizer to find the exact coordinates:

```python
import pdfplumber

with pdfplumber.open("your_cheque.pdf") as pdf:
    page = pdf.pages[0]
    im = page.to_image()
    im.draw_rects(page.extract_words())
    im.save("debug.png")
```

---

## 📤 Output Schema

Every extracted cheque record follows this schema:

| Field | Type | Example | Notes |
|---|---|---|---|
| `Date` | `string` | `"2/16/2026"` | As printed on cheque |
| `Cheque_No` | `string` | `"1190005"` | Digits only |
| `Payee` | `string` | `"JOHN DOE"` | Truncated at `$` |
| `Amount` | `string` | `"10.05"` | Stripped of `$` and `*` |
| `Memo` | `string` | `"Invoice #42"` | May be empty |
| `Bank` | `string` | `"Stellar Bank"` | Bank name |
| `Routing_No` | `string` | `"102301164"` | 9-digit ABA routing number |
| `Account_No` | `string` | `"2017237191"` | Bank account number |

---

## 📄 License

MIT © 2026 Jimmy Sherpa (Itskainos)
