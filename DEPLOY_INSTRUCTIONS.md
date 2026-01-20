# Fix-It AI - Deployment Instructions

## Overview

This guide covers deploying Fix-It AI to Render (Backend + Database) and optionally Cloudflare Pages (Frontend Widget).

---

## 1. Environment Variables

### Backend (Render Web Service)

Set these environment variables in your Render dashboard under **Environment**:

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI API key for Gemini 2.0 Flash | `AIzaSy...` |
| `DATABASE_URL` | Auto-set by Render when you attach a PostgreSQL database | `postgresql://user:pass@host:5432/dbname` |
| `ADMIN_KEY` | (Optional) Key for admin endpoints | `your-secret-admin-key` |

### How to get GEMINI_API_KEY:
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key and add it to Render

---

## 2. Render Setup

### Step 1: Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **PostgreSQL**
3. Name: `fixit-db`
4. Region: Choose closest to your users
5. Plan: **Free** (for MVP)
6. Click **Create Database**
7. Copy the **Internal Database URL** (you'll need this for the web service)

### Step 2: Create Web Service (Backend)

1. Click **New** → **Web Service**
2. Connect your GitHub repo: `andreasdweber/AI-Home-Repair-Triage-Platform`
3. Configure:
   - **Name**: `fixit-ai-backend`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `home-repair-mvp/backend`
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**: 
     ```
     gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
     ```
   - **Plan**: **Free** (for MVP)

4. Add Environment Variables:
   - `GEMINI_API_KEY` = your Google AI key
   - `DATABASE_URL` = paste the Internal Database URL from Step 1

5. Click **Create Web Service**

### Step 3: Deploy Frontend (Optional - for production widget)

For production, build the frontend and host it:

**Option A: Render Static Site**
1. Click **New** → **Static Site**
2. Connect same repo
3. Root Directory: `home-repair-mvp/frontend`
4. Build Command: `npm install && npm run build`
5. Publish Directory: `dist`
6. Add env: `VITE_API_URL=https://your-backend.onrender.com`

**Option B: Cloudflare Pages**
1. Connect repo to Cloudflare Pages
2. Build settings same as above
3. Faster global CDN

---

## 3. Build Commands Reference

### Backend Build Command (Render)
```bash
pip install -r requirements.txt && alembic upgrade head
```

### Backend Start Command (Render)
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### Frontend Build Command
```bash
npm install && npm run build
```

---

## 4. Git Commands

### Push all changes to main branch:

```bash
# Navigate to project root
cd home-repair-mvp

# Check status
git status

# Stage all changes
git add .

# Commit with descriptive message
git commit -m "Deploy: Complete Fix-It AI refactor with chat widget"

# Push to main (triggers Render auto-deploy)
git push origin main
```

### If you need to force push (use with caution):
```bash
git push origin main --force
```

### Check deployment status:
After pushing, go to your Render dashboard to watch the deployment logs.

---

## 5. Post-Deployment Verification

### Test Backend Health:
```bash
curl https://your-backend.onrender.com/
```

Expected response:
```json
{"status": "ok", "version": "2.0.0"}
```

### Test Chat Endpoint:
```bash
curl -X POST https://your-backend.onrender.com/chat \
  -F "session_id=test-1" \
  -F "text=My sink is leaking"
```

### Test from Demo Page:
1. Update `demo_site.html` with production URLs
2. Open in browser
3. Click the chat widget
4. Send a test message

---

## 6. Embedding the Widget (Production)

Once deployed, embed the widget on any site:

```html
<!-- Add to your HTML -->
<div id="fixit-widget"></div>
<script type="module" src="https://your-frontend.onrender.com/assets/main.js"></script>
```

Or with custom configuration:
```html
<div id="fixit-widget"></div>
<script type="module">
  import { mountWidget } from 'https://your-frontend.onrender.com/assets/main.js';
  mountWidget('fixit-widget', {
    apiUrl: 'https://your-backend.onrender.com'
  });
</script>
```

---

## 7. Troubleshooting

### "Module not found" errors during build
- Check that `requirements.txt` includes all dependencies
- Verify `Root Directory` is set to `home-repair-mvp/backend`

### Database connection errors
- Ensure `DATABASE_URL` env var is set
- Check that the PostgreSQL database is in the same region
- Use **Internal Database URL** (not External) for web services

### Alembic migration fails
- Run locally first: `alembic upgrade head`
- Check `alembic/env.py` imports the models correctly

### CORS errors in browser
- Backend allows all origins by default (`allow_origins=["*"]`)
- For production, restrict to your domain

### Widget not loading
- Check browser console for errors
- Verify `VITE_API_URL` points to your backend
- Ensure HTTPS is used for both frontend and backend

---

## 8. Quick Reference

| Service | Local URL | Production URL |
|---------|-----------|----------------|
| Backend | http://localhost:8000 | https://your-app.onrender.com |
| Frontend | http://localhost:5173 | https://your-frontend.onrender.com |
| Database | sqlite:///./fixit.db | PostgreSQL on Render |

---

## Need Help?

- Render Docs: https://render.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
- Vite Docs: https://vitejs.dev
