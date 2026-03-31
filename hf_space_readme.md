---
title: CPS Backend
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🏦 CPS — Quick Track Check System (Backend API)

This is the FastAPI backend for the CPS project. 
It is configured to run as a Docker Space on Hugging Face.

## 🚀 Deployment Instructions

1. **Create Space**: [huggingface.co/new-space](https://huggingface.co/new-space)
2. **Settings**:
   - SDK: **Docker**
   - Hardware: **CPU Basic** (Free)
3. **Secrets**: Add the following secrets in the Space Settings:
   - `DATABASE_URL` (From Neon)
   - `OPENAI_API_KEY`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `S3_BUCKET_NAME`
   - `JWT_SECRET` (Pick a random string)

4. **Update Frontend**: 
   Once the Space is running, copy the "Direct URL" (e.g., `https://[username]-[space-name].hf.space`) and update your **Vercel** environment variable `NEXT_PUBLIC_API_URL`.
