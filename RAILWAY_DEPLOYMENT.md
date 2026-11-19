# Deploying CiteVerify to Railway

CiteVerify is organized as a full-stack monorepo with a FastAPI backend and a React (TanStack Router + Vite) frontend.

---

## 1. Create a Project on Railway

1. Go to [railway.com](https://railway.com) and log in.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select `Sudeep-Kumar-Paul/Cite-Verify`.

---

## 2. Service 1: Backend (`citeverify-backend`)

1. In Railway project settings for this service:
   - **Name:** `citeverify-backend`
   - **Root Directory:** `/citeverify-backend`
2. Under **Variables**, add:
   - `GEMINI_API_KEY`: *(Your Google AI Studio Gemini API Key)*
   - `GEMINI_MODEL`: `gemini-3.8-flash`
   - `CORS_ORIGINS`: `https://<your-frontend-service>.up.railway.app,http://localhost:5173` *(or `*`)*
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
   - *(Optional)* If using PostgreSQL: Click **+ New** → **Database** → **Add PostgreSQL**, then connect it to this service (Railway automatically sets `DATABASE_URL`).
   - *(Optional)* If using SQLite: Under service settings, add a **Persistent Volume** mounted at `/citeverify-backend/uploads`.
3. Under **Networking**, click **Generate Domain** (e.g. `citeverify-backend-production.up.railway.app`).

---

## 3. Service 2: Frontend (`citeverify-frontend`)

1. In the same Railway project, click **+ New** → **GitHub Repo** → select `Sudeep-Kumar-Paul/Cite-Verify` again.
2. In Railway settings for this second service:
   - **Name:** `citeverify-frontend`
   - **Root Directory:** `/citeverify-frontend/citeverify_frontend`
3. Under **Variables**, add:
   - `VITE_API_BASE_URL`: `https://citeverify-backend-production.up.railway.app` *(The domain generated in Step 2.3)*
   - `VITE_FIREBASE_API_KEY`: *(Your Firebase API key)*
   - `VITE_FIREBASE_AUTH_DOMAIN`: *(Your Firebase auth domain)*
   - `VITE_FIREBASE_PROJECT_ID`: *(Your Firebase project ID)*
   - `VITE_FIREBASE_STORAGE_BUCKET`: *(Your Firebase storage bucket)*
   - `VITE_FIREBASE_MESSAGING_SENDER_ID`: *(Your Firebase sender ID)*
   - `VITE_FIREBASE_APP_ID`: *(Your Firebase app ID)*
4. Under **Networking**, click **Generate Domain** (e.g. `citeverify-production.up.railway.app`).

---

## 4. Authorize Frontend Domain in Firebase

1. Open your [Firebase Console](https://console.firebase.google.com).
2. Go to **Authentication** → **Settings** tab → **Authorized domains**.
3. Click **Add domain** and enter your Railway frontend domain:
   ```
   citeverify-production.up.railway.app
   ```
4. Save changes.

---

## Architecture Summary
- **Backend Build:** Handled automatically via Nixpacks using `citeverify-backend/Procfile` & `requirements.txt`.
- **Frontend Build:** Handled automatically via `npm run build` and served via `vite preview` on dynamic `$PORT`.
- **CORS & Authentication:** Safely configured with auto-recovery and fallback support.
