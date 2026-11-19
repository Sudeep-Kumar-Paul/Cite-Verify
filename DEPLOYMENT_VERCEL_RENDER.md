# Deploying CiteVerify: Frontend on Vercel & Backend on Render

CiteVerify is structured as a full-stack monorepo:
- **Backend:** FastAPI (Python 3.11) $\rightarrow$ Deployed on **Render**
- **Frontend:** React 19 + TanStack Start + Vite $\rightarrow$ Deployed on **Vercel**

---

## Part 1: Deploy Backend to Render (Free & Simple)

### Option A: Using Render Blueprint (Recommended, 1-Click)
1. Go to [dashboard.render.com](https://dashboard.render.com) and log in.
2. Click **New +** $\rightarrow$ **Blueprint**.
3. Connect your repository: `Sudeep-Kumar-Paul/Cite-Verify` (branch `main`).
4. Render will read `render.yaml` automatically and configure the `citeverify-backend` service.
5. In the environment variables prompt, enter your Gemini API key:
   - `GEMINI_API_KEY`: *(Your Google AI Studio Gemini API Key starting with AIzaSy...)*
6. Click **Apply**.
7. Once deployed, Render will provide your backend URL (e.g. `https://citeverify-backend-xxxx.onrender.com`).
   - Test it: visit `https://<your-render-url>/health` $\rightarrow$ should return `{"status":"healthy",...}`.

### Option B: Manual Web Service Setup
1. On Render, click **New +** $\rightarrow$ **Web Service**.
2. Connect `Sudeep-Kumar-Paul/Cite-Verify`.
3. Configure:
   - **Name:** `citeverify-backend`
   - **Region:** Any (e.g., Oregon or Frankfurt)
   - **Branch:** `main`
   - **Root Directory:** `citeverify-backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.10`
   - `GEMINI_API_KEY`: *(Your Gemini API key)*
   - `GEMINI_MODEL`: `gemini-3.8-flash`
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
5. Click **Create Web Service**.
6. Copy your public Render URL (e.g., `https://citeverify-backend.onrender.com`).

---

## Part 2: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and log in.
2. Click **Add New…** $\rightarrow$ **Project**.
3. Import `Sudeep-Kumar-Paul/Cite-Verify`.
4. In the Project Configuration:
   - **Framework Preset:** Other (or Vite) — Vercel will automatically use TanStack Start + Nitro output.
   - **Root Directory:** Click **Edit** and select:
     ```text
     citeverify-frontend/citeverify_frontend
     ```
   - **Build Command:** `npm run build` (Default)
   - **Output Directory:** `.vercel/output` (Default, handled automatically by Nitro)
5. Under **Environment Variables**, add:
   - `VITE_API_URL`: `https://<your-render-backend-url>.onrender.com` *(Paste your Render URL from Part 1)*
   - *(Optional Firebase overrides if needed; built-in fallbacks are already bundled)*:
     - `VITE_FIREBASE_API_KEY`
     - `VITE_FIREBASE_AUTH_DOMAIN`
     - `VITE_FIREBASE_PROJECT_ID`
6. Click **Deploy**.

---

## Part 3: Authorize Vercel Domain in Firebase

1. Open your [Firebase Console](https://console.firebase.google.com).
2. Go to your project (`gen-lang-client-0405702773`) $\rightarrow$ **Authentication** $\rightarrow$ **Settings** $\rightarrow$ **Authorized domains**.
3. Click **Add domain** and enter your Vercel domain (e.g., `cite-verify.vercel.app`).
4. Save changes.

---

## Summary of Architecture
- **CORS:** The backend automatically whitelists all `https://*.vercel.app` domains by default.
- **SSR & Edge:** Vercel automatically deploys Nitro SSR functions to Vercel Functions and assets to the Global Edge CDN.
- **Port Binding:** Render binds to dynamic `$PORT` automatically via `python main.py`.
