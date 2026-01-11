# Fix-It AI - AI-Powered Home Repair Triage Platform

A lead-generation platform that uses Google Gemini AI to analyze home repair issues from photos or descriptions and connect homeowners with local professionals.

## 🚀 Features

- **AI Image Analysis**: Upload photos of home repair issues for instant diagnosis
- **Text-Only Mode**: Describe issues without photos for quick estimates
- **Lead Capture**: Collect user information for professional matching
- **Admin Dashboard**: View and manage leads (`?admin=true`)
- **Canadian Market**: Optimized for Vancouver with postal code support

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLite, Google Gemini AI
- **Frontend**: React, Vite, Tailwind CSS, Axios
- **Deployment**: Render (Backend), Cloudflare/Vercel (Frontend)

## 📦 Project Structure

```
home-repair-mvp/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── gunicorn_conf.py     # Production server config
│   ├── .env                 # Environment variables (not in git)
│   └── leads.db             # SQLite database (not in git)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── main.jsx         # Entry point
│   │   └── index.css        # Tailwind styles
│   ├── package.json
│   └── vite.config.js
└── .gitignore
```

## 🏃 Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create .env with GEMINI_API_KEY=your_key_here
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🌐 Production Deployment

### Backend (Render)
1. Connect GitHub repo to Render
2. Create new Web Service
3. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn main:app -c gunicorn_conf.py`
4. Environment Variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key

### Frontend (Cloudflare Pages / Vercel)
1. Connect GitHub repo
2. Settings:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Root Directory: `frontend`
3. Environment Variables:
   - `VITE_API_URL`: Your Render backend URL (e.g., `https://your-app.onrender.com`)

## 🔑 Environment Variables

### Backend (.env)
```
GEMINI_API_KEY=your_google_gemini_api_key
```

### Frontend
```
VITE_API_URL=https://your-backend-url.onrender.com
```

## 📊 Admin Dashboard

Access the admin dashboard by adding `?admin=true` to the URL:
- Local: `http://localhost:5173/?admin=true`
- Production: `https://your-frontend.com/?admin=true`

API endpoint: `GET /leads?admin_key=secret123`

## 📄 License

MIT License - Feel free to use for your own projects!
