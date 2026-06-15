# Deploying Atlas to a public URL

Target topology (all have free tiers): **Neon** (Postgres + pgvector) · **Render**
(FastAPI API + ARQ worker + Redis) · **Vercel** (React frontend). End state:
`https://<you>.vercel.app` → talks to `https://atlas-api-<you>.onrender.com`.

Total time: ~30–40 min. You'll need GitHub (push this repo) + the three accounts.

---

## 0. Push the repo to GitHub
```bash
cd "TalentBank Tech Hackathon"
gh repo create atlas-career-os --private --source=. --push   # or create on github.com and `git push`
```

## 1. Neon — database (≈5 min)
1. Create a project at https://neon.tech → pick **Singapore (ap-southeast-1)** region.
2. In the SQL editor run: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Copy the connection string. Convert the driver prefix for async:
   `postgresql://…` → **`postgresql+asyncpg://…`** (keep `?sslmode=require` → change to `?ssl=require` for asyncpg, or drop it; asyncpg uses SSL automatically on Neon).
   Save this as **`DATABASE_URL`**.

## 2. Render — API + worker + Redis (≈15 min)
Render reads [`render.yaml`](../render.yaml) (Blueprint).
1. https://render.com → **New → Blueprint** → connect the GitHub repo. It detects `render.yaml` (web `atlas-api`, worker `atlas-worker`, `atlas-redis`).
2. Set the env vars it marks `sync:false`:
   - `DATABASE_URL` = your Neon async URL (on **both** `atlas-api` and `atlas-worker`)
   - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` = your Azure values
   - `CORS_ORIGINS` = your Vercel URL (add after step 3; redeploy) e.g. `https://atlas-career-os.vercel.app`
   - `USE_MOCK_LLM` = `false` (live) — or `true` to demo without Azure
   - `SECRET_KEY` auto-generates; `REDIS_URL` auto-wires from `atlas-redis`.
3. Deploy. The `preDeployCommand` runs `python -m app.scripts.init_db` (creates the schema + pgvector). Health check: `/health`.
4. **Seed the demo data once** (Render shell on `atlas-api`, or locally with `DATABASE_URL` pointed at Neon):
   ```bash
   python -m app.scripts.seed
   ```
5. Note the API URL, e.g. `https://atlas-api-xxxx.onrender.com`.

> Free Render web services sleep after inactivity (~50s cold start). Fine for judging; upgrade to keep warm for the live finale.

## 3. Vercel — frontend (≈10 min)
1. https://vercel.com → **Add New → Project** → import the repo.
2. **Root Directory: `frontend`** (important). Framework: Vite (auto). [`vercel.json`](../frontend/vercel.json) handles the SPA rewrite.
3. Environment variable:
   - `VITE_API_BASE_URL` = `https://atlas-api-xxxx.onrender.com/api/v1`  (your Render API URL + `/api/v1`)
4. Deploy → you get `https://atlas-career-os.vercel.app`.
5. Go back to Render `atlas-api` → set `CORS_ORIGINS` to that Vercel URL → redeploy.

## 4. Verify
- Open the Vercel URL → landing page loads.
- Click **Explore the demo** → log in with a demo account (password `demo1234`):
  `aisyah@demo.atlas` (candidate) · `daniel@demo.atlas` (employer) · `dr.tan@demo.atlas` (university) · `admin@demo.atlas` (admin).
- This Vercel URL is your **Intent Form "clickable prototype / live demo URL."**

---

## Alternative: Azure (matches your Azure OpenAI)
- **DB:** Azure Database for PostgreSQL Flexible Server → enable the `vector` extension (`azure.extensions`), set `DATABASE_URL`.
- **API + worker:** Azure Container Apps (or App Service for Containers) from `backend/Dockerfile`; one container runs `uvicorn`, another runs `arq app.workers.arq_settings.WorkerSettings`. Azure Cache for Redis for `REDIS_URL`.
- **Frontend:** Azure Static Web Apps from `frontend/` (build `npm run build`, output `dist`).
- Set the same env vars as above. Everything else is identical.

## One-command local demo (no accounts needed)
```bash
docker compose up        # → frontend http://localhost:5173, API http://localhost:8000/docs
```
This brings up Postgres+pgvector, Redis, API (auto-runs init_db + seed), worker, and the frontend.
