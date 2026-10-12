# CLAUDE.md: Food Bank Volunteer Booking System

> Source of truth: `docs/ARCHITECTURE_AND_TEAM_PLAN.md`. Where this file and the plan disagree, STOP and ask a human.
> Timeline: the plan is written for 5 hours. Do not expand scope to fill extra time without approval.

---

## 1. Project Vision & High-Level Architecture

**Domain:** Food bank volunteers book a spot in a timed shift. The system must never overbook a slot.

**Personas**
- **Volunteer** (public, anonymous): views slots, books one spot per email per slot. No login.
- **Admin / NGO staff**: holds `ADMIN_TOKEN`. Views bookings, which include PII.
- **Beneficiaries**: not users of this app. Context only.

**Key workflows**
1. Browse slots: `GET /slots`. Frontend polls every 10s and shows "last updated HH:MM".
2. Book: `POST /book` runs the atomic transaction (section 2). Returns 201 or an error.
3. Admin: `GET /booking/{id}` (and a list endpoint only if time allows), header `X-Admin-Token`.
4. Dashboard (Recharts): per-slot booked vs capacity. Last priority, cut first. There is no history table, so do NOT chart "over time" and do NOT add a history table without approval.

**Architecture:** client-server split. React SPA (static, Netlify) calls JSON over HTTP on FastAPI (Railway). FastAPI uses one SQLite file at `/data/app.db` on a persistent volume.

**Layout** (assumed; create as built, keep to it)
```
volunteer-booking-app/
├── CLAUDE.md / GEMINI.md
├── docs/ARCHITECTURE_AND_TEAM_PLAN.md   # read-only for agents
├── docs/API_CONTRACT.json               # frozen after hour 1; create from plan samples
├── backend/
│   ├── app/main.py          # FastAPI app, CORS, exception handlers, routers
│   ├── app/config.py        # the ONLY place env vars are read
│   ├── app/db.py            # ALL SQL lives here: connection, PRAGMAs, booking transaction
│   ├── app/schemas.py       # Pydantic v2 request/response models
│   ├── app/security.py      # ADMIN_TOKEN dependency, rate limiter
│   ├── app/routes/slots.py, bookings.py, admin.py
│   ├── schema.sql           # owner: Person B. Changes need approval
│   ├── seed.py
│   ├── tests/               # pytest. owner: Person C
│   ├── requirements.txt, requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/api/client.ts            # the ONLY file that calls fetch()
│   ├── src/types/api.ts             # mirrors docs/API_CONTRACT.json
│   ├── src/hooks/useSlots.ts        # 10s polling with cleanup
│   ├── src/components/SlotList.tsx, BookingForm.tsx, Dashboard.tsx, AdminBookings.tsx
│   └── .env.example
└── README.md                        # owner: Person D
```

---

## 2. JPMC Security & Engineering Guardrails (STRICT)

Non-negotiable. If a change would break one, stop and report it.

**SQL injection: zero tolerance**
- Parameterized queries only: `conn.execute("... WHERE id = ?", (slot_id,))`.
- Never build SQL with f-strings, `%`, `.format()`, or `+` using any input. Table and column names are hardcoded constants.

**Server-side validation (every endpoint)**
- All bodies and params go through Pydantic v2 models: `Field(...)` constraints plus `field_validator`. Frontend checks are UX only, never trust.
- Trim strings. Reject empty names. Length caps: name ≤ 100, email ≤ 254, phone ≤ 20.
- Phone: one regex, defined once in `schemas.py`.
- Path ids: `Path(gt=0)`. Never return fields that are not in `docs/API_CONTRACT.json`.

**Secrets: zero hardcoded**
- Backend: `os.environ` / `os.getenv`, read in `app/config.py` only.
- Frontend (Vite): `import.meta.env.VITE_*`. `process.env` does NOT exist in browser code.
- NEVER put `ADMIN_TOKEN` in any `VITE_*` var or the bundle. The admin types the token at runtime. Keep it in component state only, never localStorage.
- `.env` and `*.db` go in `.gitignore`. Commit only `.env.example`.
- Never log or print secrets, tokens, or PII (names, emails, phones).
- Fail fast at startup if `ADMIN_TOKEN` is unset or empty.

**Admin auth (`X-Admin-Token`)**
- Dependency in `security.py`. Order of checks, no shortcuts:
  1. `expected = os.getenv("ADMIN_TOKEN")`. If `not expected`, reject. An unset env var must never match a missing header.
  2. Missing header, or `not hmac.compare_digest(token, expected)`, returns 403 `UNAUTHORIZED`.
- Attach the dependency to the admin router. Do not check per function.

**Booking integrity (the core of the system)**
- The plan's `/book` SQL is the rule, with one fix. Do not deviate without approval.
- A full slot is NOT a UNIQUE violation. You MUST check `rowcount` and raise 409 yourself.
- Sketch (illustrative; the real code lives in `app/db.py`):
```python
conn = sqlite3.connect(DB_PATH, isolation_level=None)  # manual transaction control
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("BEGIN IMMEDIATE")                        # serializes writers
try:
    if conn.execute("SELECT 1 FROM volunteer_slots WHERE id = ?", (slot_id,)).fetchone() is None:
        raise SlotNotFound                              # -> 404 SLOT_NOT_FOUND
    cur = conn.execute(
        "UPDATE volunteer_slots SET booked = booked + 1 WHERE id = ? AND booked < capacity",
        (slot_id,))
    if cur.rowcount == 0:
        raise SlotFull                                  # -> 409 SLOT_FULL
    conn.execute(
        "INSERT INTO bookings (slot_id, volunteer_name, email, phone) VALUES (?, ?, ?, ?)",
        (slot_id, name, email, phone))                  # UNIQUE(slot_id, email) -> IntegrityError
    conn.execute("COMMIT")
except sqlite3.IntegrityError:
    conn.execute("ROLLBACK")                            # -> 409 DUPLICATE_BOOKING
    raise
except Exception:
    conn.execute("ROLLBACK")
    raise
```
- `booked` changes ONLY inside this transaction. Never recompute it in app code. `COUNT(*)` is for tests only.
- The concurrency test must use a real file DB (tmp_path), NOT `:memory:`, since threads will not share it.

**CORS**
- `CORSMiddleware` with `allow_origins` from env `CORS_ORIGINS` (comma-separated). Never `"*"` in deployed code.
- Methods: `GET`, `POST` only. Headers: `Content-Type`, `X-Admin-Token`.

**Rate limiting**
- `slowapi` on `POST /book` and `GET /booking/{id}`. Limits are defaults in `config.py`. Tests disable the limiter with an env flag, so the concurrency test is not throttled.

**RBAC (two roles only)**
- `public`: `GET /slots`, `POST /book`.
- `admin`: `X-Admin-Token` required for `GET /booking/{id}` and any list endpoint.

**Standard error envelope (ALL errors, including FastAPI's own 422 and 404)**
```json
{"error": {"code": "SLOT_FULL", "message": "This slot is full.", "details": null}}
```
- Override `RequestValidationError` and `HTTPException` in `main.py` so they produce this envelope. Raise errors as `HTTPException(status, detail={"code": ..., "message": ...})`.
- Codes: VALIDATION_ERROR 422, SLOT_NOT_FOUND 404, BOOKING_NOT_FOUND 404, SLOT_FULL 409, DUPLICATE_BOOKING 409, UNAUTHORIZED 403, RATE_LIMITED 429, INTERNAL_ERROR 500.
- Never return stack traces or raw exception text.

---

## 3. AI Agent Behavior & Execution Boundaries

**Auto-allowed (do without asking)**
- Boilerplate, components, route stubs, and Pydantic models that match the contract.
- Utility functions, seed data matching `schema.sql`, docstrings, README sections.
- Unit and integration tests. Syntax, type, and lint fixes.
- Ant Design UI and Recharts charts built from `/slots` data.

**Requires explicit human approval first (stop and ask)**
- Any change to `schema.sql`: tables, columns, constraints, indexes.
- Any change to `docs/API_CONTRACT.json` (frozen after hour 1).
- Security config: CORS, `ADMIN_TOKEN` logic, rate limits, auth rules, section 2 of this file.
- Core booking logic: the transaction in `app/db.py`, and the `booked` counter.
- Adding dependencies (`requirements*.txt`, `package.json`).
- Deleting files, bookings data, or the `.db` file. Any `git push`, `reset --hard`, or force operation.
- Deployment config (Railway, Netlify, Dockerfile, env var names).

**Out of scope: do not build** (the plan lists these): volunteer cancellation, email confirmations, volunteer login, automatic backups.

**Zero-trust verification (before presenting any code)**
- Confirm every import and package exists in `requirements*.txt` / `package.json`, or in the installed version (`pip show <pkg>`, `npm ls <pkg>`). Never invent a module.
- Check APIs against the installed version, not memory. Known traps:
  - Pydantic v2: `field_validator`, `model_dump()`. NOT `validator` or `.dict()`.
  - Ant Design v5+: `Modal` uses `open`, NOT `visible`.
  - `EmailStr` needs `email-validator`. `TestClient` needs `httpx`. Verify both are installed.
- Never use a deprecated method. If you can't verify an API, write `UNVERIFIED: <what>` in the reply and do not assume it works.

**Stop conditions**
- Two failed attempts at the same fix: stop, and report the exact error output.

**Every task ends with a report:** files changed, tests and lint run with real results, `UNVERIFIED` items.

---

## 4. Codebase Conventions & Styling

**Naming**
- Python: `snake_case` functions, variables, modules. `PascalCase` classes and Pydantic models. `UPPER_SNAKE` constants.
- JS/TS: `camelCase` variables and functions. `PascalCase` component files (`SlotList.tsx`). Hooks named `useX`.
- **API JSON is `snake_case`** (`volunteer_name`, `slot_id`, `booked`). This matches Python and SQL, so no conversion layer. Frontend types mirror it exactly. Never camelCase the payload.
- SQL: `snake_case`, plural table names.

**File organization**
- One component per file. No `utils.py` dumping ground. Put a helper next to its caller unless two files use it.
- No SQL outside `app/db.py`. Route handlers call `db.py` and return schemas.
- No `fetch()` outside `frontend/src/api/client.ts`.

**Types**
- Python: type hints on every signature. Pydantic models at every API boundary. No bare `dict` payloads, no `Any`.
- TypeScript: `"strict": true`. No `any` (use `unknown` and narrow). No `as` casts on API data.

**Async**
- Backend DB routes are sync `def` (plan: sync FastAPI + `sqlite3`). Never mix blocking `sqlite3` into `async def`.
- Frontend uses `async/await`. The plan's `.then` polling snippet is a sketch: convert it, and keep the `clearInterval` cleanup.

**Error handling**
- Backend: one exception handler produces the envelope (section 2). Do not hand-build error JSON in each route.
- Frontend: `client.ts` throws an error carrying the envelope's `code` and `message`. Components show `message` in Ant Design `message` or `Alert`. Never show raw JSON or stack traces.
- Polling failure keeps the last data and shows stale status. It must NOT blank the table.
- Never swallow an error silently.

**Formatting & comments**
- Backend: `ruff format` and `ruff check`. Frontend: the ESLint and Prettier setup that Vite scaffolds.
- Docstrings on public functions. Comments only for the WHY the code cannot show, one line.
- Known limits: `# shortcut: <the limit>, <when to upgrade>`.

---

## 5. Testing & Quality Commands

**Setup**
```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
cd frontend && npm install
```

**Run locally**
```bash
cd backend && uvicorn app.main:app --reload --port 8000   # API; interactive docs at /docs
cd backend && python seed.py                              # demo slots; DB_PATH from env
cd frontend && npm run dev                                # http://localhost:5173
```

**Test**
```bash
cd backend && pytest -q
cd backend && pytest --cov=app --cov-report=term-missing
```

**Lint and build (gate before reporting done)**
```bash
cd backend && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run build
```

**Coverage requirements (critical business logic)**
- Concurrency test: 5-spot slot, 10 concurrent `POST /book`. Assert exactly 5 × 201, 5 × 409, `booked == 5`, and exactly 5 booking rows.
- Every `POST /book` branch has a test: 404, 409 full, 409 duplicate email, 422 each invalid field.
- Admin: missing token, wrong token, and empty `ADMIN_TOKEN` env are all rejected.
- Invariant after every booking test: `booked == COUNT(*) FROM bookings WHERE slot_id = ?`.
- `app/db.py` booking code and `app/security.py` must be 100% line and branch covered.
- A change to critical-path code is not done until its tests pass.

---

## 6. Quick Context Hints

| Task | Open these |
|---|---|
| Schema, `booked` counter | `backend/schema.sql`, plan §6 and Appendix |
| API shapes and status codes | `docs/API_CONTRACT.json` (source of truth), `backend/app/schemas.py` |
| Endpoint build order | plan §12 |
| Atomic booking | `backend/app/db.py`, section 2 of this file, plan §6 |
| Admin auth | `backend/app/security.py`, section 2 of this file (NOT the plan's appendix snippet) |
| Frontend components | `frontend/src/components/`, plan §9 Person A |
| Polling | `frontend/src/hooks/useSlots.ts`, `frontend/src/api/client.ts` |
| Tests | `backend/tests/`, plan §9 Person C |
| Env vars and deploy | `backend/.env.example`, `frontend/.env.example`, `README.md`, plan §5 |
| Demo flow | plan §11 Hour 5 |
| Ownership | plan §9: A frontend, B backend, C QA, D docs/deploy |
