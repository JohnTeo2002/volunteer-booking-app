# Railway deployment: persistent-volume smoke test

This procedure is for Issue #21. It deploys a small FastAPI smoke app first, verifies persistent SQLite storage, then switches the same Railway service to the real application. Issue #8 is closed, so the real-app stage can follow once the smoke test passes.

## 1. Create the Railway service

1. In Railway, create a project and deploy this GitHub repository.
2. Ensure Railway builds using the repository-root `Dockerfile` (Railway detects it automatically). Configure build and deploy settings in the Railway service dashboard; this guide intentionally does not use legacy `railway.toml` Config-as-Code because Railway documents that new services cannot opt into that mechanism.
3. In **Settings → Deploy**, set the health check path to `/health` and the health check timeout to 120 seconds.
4. In the service's **Settings → Volumes**, add a volume mounted at exactly `/data`.
5. In **Variables**, set:
   - `DB_PATH=/data/app.db`
   - `ADMIN_TOKEN=<a long random secret>`
   - `CORS_ORIGINS=http://localhost:5173,https://<your-frontend-domain>`
6. In **Settings → Networking**, generate a public domain.

Do not use a wildcard CORS origin. Keep `ADMIN_TOKEN` only in Railway's server-side variables; do not expose it as a Vite variable.

## 2. Verify the smoke app

Open these paths on the generated public domain:

- `/` should return a hello-world JSON message.
- `/health` should return `{"status":"ok"}`.
- `/docs` should load FastAPI's Swagger UI.

Call `POST /persistence-test` once with the header `X-Admin-Token: <your ADMIN_TOKEN>`. This protected smoke-only endpoint seeds five demo slot rows into the database configured by `DB_PATH`. The response reports `inserted_rows` and `total_slots`. Calling it again is safe; the seed script does not duplicate rows. Do not send the token in a URL or expose it in frontend code.

Call `GET /persistence-test` and confirm it reports five slots.

## 3. Redeploy the real application

After the smoke test passes, change the final `CMD` in the root `Dockerfile` from:

```dockerfile
CMD ["sh", "-c", "uvicorn app.railway_smoke:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

to:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Commit and push that change so Railway deploys the real app. Keep the volume mounted at `/data` and keep `DB_PATH=/data/app.db` unchanged.

In the Railway dashboard, change the health check path from `/health` to `/slots`, because the real application does not expose the smoke app's `/health` path.

After the redeploy:

- `/docs` should still load.
- `/slots` should return the five seeded slot rows. This verifies that the SQLite data survived deployment replacement.
- Railway's configured health check should pass against `/slots`.

The smoke app and its `/persistence-test` endpoints are temporary deployment checks. The final Dockerfile command should run `app.main:app`, not `app.railway_smoke:app`.

## Validation limitation

A repository change alone cannot prove Railway volume persistence. The public domain, mounted volume, server-side variables, successful first deployment, and successful redeploy must be verified in the Railway project UI.
