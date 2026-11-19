# CiteVerify 🔬
> **Verify the Science. Trust the Evidence.**

CiteVerify is an AI-powered scientific claim and citation verification platform. It allows researchers, academics, students, and fact-checkers to upload research papers or enter scientific claims, extracting individual propositions and verifying them against real-world scientific literature (Semantic Scholar & Crossref APIs) with multi-model AI reasoning and Firebase authentication.

---

## 🌟 Key Features

- **Firebase Authentication:** Seamless Sign In / Sign Up with **Email & Password** and **Google Sign-In** with personalized research profiles.
- **Multi-Format Document Ingestion:** Upload scientific papers in **PDF**, **DOCX**, or **TXT** format.
- **Smart Text & Citation Extraction:** Robust multi-page text extraction with automated fallback mechanisms and structural parsing.
- **Scientific Claim Extraction:** Automatically isolates atomic scientific claims from complex research manuscripts.
- **Real-Time Literature Grounding:** Queries academic research databases (Semantic Scholar & Crossref) to retrieve real-world peer-reviewed evidence.
- **Evidence-Based Verdicts:** Classifies claims into **Supported**, **Contradicted**, or **Inconclusive** with confidence scores and rationales.
- **Document-Specific Isolation:** Ensures every uploaded file receives an isolated verification job ID, unique report generation, and isolated analysis.
- **Modern Interactive Dashboard:** Built with React 19, TypeScript, Tailwind CSS, Lucide icons, and responsive UI components.
- **Unified Startup:** Launch both the FastAPI backend and React frontend with a single Windows PowerShell command.

---

## 🏗️ Architecture

```
CiteVerify/
├── citeverify-backend/          # FastAPI Python Backend
│   ├── app/
│   │   ├── api/routes/          # REST Endpoints (documents, verification, reports, health)
│   │   ├── services/            # Extraction, Gemini AI, Literature Search, Evidence Engine
│   │   ├── models/              # Pydantic schemas & SQLAlchemy ORM models
│   │   └── core/                # Configuration, logging, exception handlers
│   ├── tests/                   # Pytest test suite (30 comprehensive unit & integration tests)
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Backend environment template
│
├── citeverify-frontend/         # React + Vite Frontend
│   └── citeverify_frontend/
│       ├── src/
│       │   ├── lib/             # Firebase Auth context, API client, utilities
│       │   ├── routes/          # Dashboard, verification views, reports
│       │   └── components/      # UI components (Button, Dialog, Avatar, Tabs, etc.)
│       ├── package.json
│       └── .env.example         # Frontend environment template
│
├── package.json                 # Root npm orchestration script
├── start.ps1                    # Unified Windows PowerShell startup script
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (with virtualenv)
- **Node.js 18+** & **npm**
- **Google Gemini API Key**
- **Firebase Project** (for Authentication)

### 1. Clone the Repository
```bash
git clone https://github.com/Sumansd-dev/CiteVerify-Scientific-Claim-and-Citation-Verification-System.git
cd CiteVerify-Scientific-Claim-and-Citation-Verification-System
```

### 2. Configure Environment Variables

**Backend (`citeverify-backend/.env`):**
```env
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
DATABASE_URL=sqlite:///./citeverify.db
```

**Frontend (`citeverify-frontend/citeverify_frontend/.env`):**
```env
VITE_API_BASE_URL=http://127.0.0.1:8000

# Firebase Authentication Configuration
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id_here
VITE_FIREBASE_STORAGE_BUCKET=your_project_id.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id_here
VITE_FIREBASE_APP_ID=your_firebase_app_id_here
```

> **Note:** CiteVerify includes a built-in **Instant Demo Auth Mode** so you can test the application immediately even before configuring Firebase keys.

### 3. Install Dependencies

**Backend:**
```powershell
cd citeverify-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

**Frontend:**
```powershell
cd citeverify-frontend/citeverify_frontend
npm install
cd ../..
```

---

## 💻 Running the Application

### Option A: Unified Startup Script (Recommended)
Run the root PowerShell launcher to boot both the FastAPI backend (`:8000`) and the Vite React frontend (`:5173`) concurrently:
```powershell
.\start.ps1
```
Or via npm:
```bash
npm run dev
```

### Option B: Manual Startup (Two Terminals)

**Terminal 1 — Backend:**
```powershell
cd citeverify-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd citeverify-frontend/citeverify_frontend
npm run dev -- --host 127.0.0.1
```

Open your browser at `http://127.0.0.1:5173`.

---

## 🔐 Firebase Authentication Setup Guide

1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2. In the left navigation, click **Build → Authentication**, then click **Get Started**.
3. Under the **Sign-in method** tab:
   - Enable **Email/Password**.
   - Enable **Google** (set your project support email).
4. Go to **Project Settings** (gear icon) → **General**.
5. Under **Your apps**, click the Web icon (`</>`) to register a web app.
6. Copy the configuration credentials into `citeverify-frontend/citeverify_frontend/.env`.

---

## 🚢 Production Deployment Guide

CiteVerify can be deployed in three production-grade ways:

### 🌟 Option 1: 1-Click Render Cloud Deployment (Recommended)

Render is pre-configured with the included [`render.yaml`](render.yaml) Blueprint. It automatically creates:
- **FastAPI Backend:** Runs Python 3.11 with a persistent SSD disk attached at `/var/data` (preserving SQLite records and uploaded manuscripts across redeploys).
- **React Frontend:** Builds with Node 20 SSR and automatically connects to the backend URL.
- **SSL & Domains:** Automatic free HTTPS certificates on `*.onrender.com`.

**Steps to deploy on Render:**
1. Push your repository to GitHub or GitLab.
2. Go to the [Render Dashboard](https://dashboard.render.com/) and click **New + → Blueprint**.
3. Connect your CiteVerify repository. Render detects [`render.yaml`](render.yaml) automatically.
4. Fill in the required environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
   - `VITE_FIREBASE_*`: *(Optional)* Your Firebase project credentials (leave blank for built-in Demo Auth mode).
5. Click **Apply**. Render will automatically build and launch both services!

---

### 🐳 Option 2: Docker & Docker Compose (Self-Hosted VPS / Cloud Server)

Deploy CiteVerify to any Ubuntu/Debian VPS (DigitalOcean, AWS EC2, Hetzner, Linode) or on-premise server:

1. **Clone the repository on your server:**
   ```bash
   git clone https://github.com/Sudeep-Kumar-Paul/Cite-Verify.git
   cd Cite-Verify
   ```

2. **Configure your environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Set your `GEMINI_API_KEY` and set `VITE_API_BASE_URL` to your public server IP or domain (e.g. `http://your-server-ip:8000` or `https://api.yourdomain.com`).

3. **Build and launch the containers:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify the status:**
   ```bash
   docker compose ps
   docker compose logs -f
   ```
   - Frontend is live on `http://your-server-ip:3000`
   - Backend API is live on `http://your-server-ip:8000` (docs at `/docs`)

---

### ⚡ Option 3: Split Deployment (Vercel Frontend + Render/Railway Backend)

If you prefer deploying the frontend to a global edge CDN:

1. **Deploy Backend (Render or Railway):**
   - Connect `citeverify-backend/` to Render Web Service or Railway.
   - Set Build Command: `pip install -r requirements.txt`
   - Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - Add a persistent disk mounted to `/app/uploads` and set `DATABASE_URL=sqlite:////app/uploads/citeverify.db`.
   - Set `GEMINI_API_KEY=your_key` and `CORS_ORIGINS=https://your-frontend.vercel.app`.
   - Note the assigned backend URL (e.g. `https://citeverify-api.onrender.com`).

2. **Deploy Frontend (Vercel):**
   - Import the repository in [Vercel](https://vercel.com/).
   - Set Root Directory to `citeverify-frontend/citeverify_frontend`.
   - Set Environment Variable:
     - `VITE_API_BASE_URL` = `https://citeverify-api.onrender.com`
   - Deploy!

---

## 🧪 Testing

### Backend Unit & Integration Tests (Pytest)
```powershell
cd citeverify-backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

### Frontend Tests (Vitest)
```powershell
cd citeverify-frontend/citeverify_frontend
npm test
```

---

## 🔒 Security & Privacy

- All user documents and verification reports are processed locally and securely.
- API keys and sensitive credentials remain exclusively on the server backend.
- Uploaded files, virtual environments, and local SQLite databases are strictly excluded from version control via `.gitignore`.

---

## 📄 License
This project is licensed under the MIT License.
