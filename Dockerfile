# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# tesseract-ocr is needed for MICR fallback
# libgl1-mesa-glx and libglib2.0-0 are needed for OpenCV
# gcc is needed for some python packages
RUN apt-get update && apt-get install -y \
    gcc \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server directory and other necessary files
COPY server/ ./server/
COPY public/ ./public/
COPY .env.local* ./

# Hugging Face Spaces default port is 7860
EXPOSE 7860

# Command to run the application
# We use 0.0.0.0 to bind to all interfaces for HF Spaces
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
