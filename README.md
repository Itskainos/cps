# Cheque Printing System (CPS) - Zonal OCR

This is a premium web implementation of the Cheque Printing System, featuring high-accuracy coordinate-based OCR for extracting critical bank details from cheques.

## 🚀 Features

- **Zonal OCR Extraction**: Uses precise (x0, top, x1, bottom) coordinates to capture:
  - Payee Name (Stops before currency symbols)
  - Numeric Amount (Auto-sanitized)
  - **MICR Line**: Accurate Routing and Account number capture, ignoring special glyphs.
  - Cheque Number & Bank Details.
- **Premium UI**: Built with Next.js 15, Tailwind CSS v4, and Framer Motion for a state-of-the-art experience.
- **Vercel Native**: Dual-stack architecture with a React frontend and Python backend API.

## 🛠️ Project Structure

- `api/extract.py`: Python handler using `pdfplumber` for coordinate-based scanning.
- `src/app/page.tsx`: Premium React frontend with animated upload and data tables.
- `requirements.txt`: Python dependencies for the Vercel serverless environment.

## 📦 Local Development

1. **Install JS dependencies:**
   ```bash
   npm install
   ```

2. **(Optional) Install Python dependencies for testing extraction scripts:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

## ☁️ Deployment on Vercel

1. **Push to GitHub**:
   - Create a new repository on GitHub.
   - Run the following commands in your terminal:
     ```bash
     git remote add origin <your-repo-url>
     git branch -M main
     git push -u origin main
     ```

2. **Connect to Vercel**:
   - Go to [Vercel](https://vercel.com/new).
   - Select the repository you just pushed.
   - Vercel will automatically detect the Next.js frontend and the Python API.
   - **Click Deploy.**

## 🔍 How it Works

Unlike standard OCR which scans text linearly, this system uses **Zonal Mapping**. We have calibrated the exact coordinates for fields based on common bank templates (like Stellar Bank), ensuring that the MICR line at the bottom is captured even when traditional text extraction fails.
