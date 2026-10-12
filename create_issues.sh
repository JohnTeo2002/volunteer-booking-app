#!/usr/bin/env bash
# Creates the 25 hackathon issues in the current repo, in order, so issue numbers match the "#N" references.
# Needs: gh auth login done, run from inside the repo (or add -R OWNER/REPO to gh issue create).
set -euo pipefail

ASSIGN_A="${ASSIGN_A:-JohnTeo2002}"
ASSIGN_B="${ASSIGN_B:-JohnTeo2002}"
ASSIGN_C="${ASSIGN_C:-JohnTeo2002}"
ASSIGN_D="${ASSIGN_D:-JohnTeo2002}"

for label in backend frontend database testing integration high-priority medium-priority low-priority; do
  gh label create "$label" --force >/dev/null
done

issue() { # args: title, labels, assignee, body
  url=$(gh issue create --title "$1" --label "$2" --assignee "$3" --body "$4")
  echo "$url  $1"
}

issue "Create repo skeleton and ignore rules" "integration,high-priority" "$ASSIGN_D" "What: Create the folder layout from CLAUDE.md section 1 (backend, frontend, docs). Add .gitignore excluding .env, *.db, .venv and node_modules. Set branch protection on main.
Acceptance criteria:
- Empty .env.example files exist in backend and frontend.
- All four people can clone and push.
Depends on: none
Unblocks: #2, #3, #5, #6, #9, #18"

issue "Write and freeze docs/API_CONTRACT.json" "integration,high-priority" "$ASSIGN_D" "What: Write the request and response JSON for GET /slots, POST /book and GET /booking/{id}, plus the error envelope and error codes. Use snake_case.
Acceptance criteria:
- Every endpoint has a sample request, success response and each error code.
- Person A and Person B both sign off in a comment.
- Frozen afterwards. Changes need human approval.
Depends on: #1
Unblocks: #4, #5, #6"

issue "Write schema.sql and DB connection setup" "database,high-priority" "$ASSIGN_B" "What: Create both tables with UNIQUE(slot_id, email) and CHECK(booked <= capacity). In app/db.py, add the connection helper with foreign_keys = ON.
Acceptance criteria:
- schema.sql creates both tables on an empty DB file.
- Inserting a duplicate (slot_id, email) fails.
- All SQL is parameterized.
Notes: schema changes need human approval after this.
Depends on: #1
Unblocks: #7, #8, #9, #16"

issue "Build Pydantic v2 request and response models" "backend,high-priority" "$ASSIGN_B" "What: Write app/schemas.py with the booking request model. Trim strings and reject empty names. Length caps: name 100, email 254, phone 20. One phone regex. Path ids use Path(gt=0).
Acceptance criteria:
- Models match the contract field for field.
- email-validator is installed and confirmed.
- Invalid input raises a validation error.
Depends on: #2
Unblocks: #7, #8"

issue "Add config, app entry point, error envelope and CORS" "backend,high-priority" "$ASSIGN_D" "What: Write app/config.py (the only place env vars are read) and app/main.py. FastAPI 422, 404 and HTTPException responses all use the standard error envelope. CORS origins come from CORS_ORIGINS, methods GET and POST only.
Acceptance criteria:
- A bad request returns the error envelope, not FastAPI's default shape.
- No wildcard CORS origin.
- The app fails at startup if ADMIN_TOKEN is unset or empty.
- No stack traces reach the client.
Depends on: #1, #2
Unblocks: #7, #8, #15"

issue "Scaffold frontend and API client" "frontend,high-priority" "$ASSIGN_A" "What: Scaffold Vite, React and TypeScript with strict mode. Install Ant Design and Recharts. Write src/types/api.ts mirroring the contract. Write src/api/client.ts, the only file that calls fetch(); it throws an error carrying the envelope code and message.
Acceptance criteria:
- npm run lint and npm run build pass.
- No any types and no casts on API data.
- VITE_API_URL is read from .env, and .env.example is committed.
Depends on: #1, #2
Unblocks: #12, #13, #19"

issue "Build GET /slots endpoint" "backend,high-priority" "$ASSIGN_B" "What: List slots with booked and remaining capacity. Optional event_id and date filters. Sync def route; SQL lives in app/db.py.
Acceptance criteria:
- Response matches the contract.
- Filters work.
- The response contains no PII.
Depends on: #3, #4, #5
Unblocks: #20"

issue "Build POST /book atomic booking" "backend,high-priority" "$ASSIGN_B" "What: Implement the transaction from CLAUDE.md section 2: BEGIN IMMEDIATE, check the slot exists, conditional UPDATE, check rowcount, then INSERT. Map errors to 404, 409 SLOT_FULL and 409 DUPLICATE_BOOKING. Return 201.
Acceptance criteria:
- A full slot returns 409 SLOT_FULL, checked via rowcount.
- A duplicate email on the same slot returns 409 DUPLICATE_BOOKING and rolls back.
- booked changes only inside this transaction.
- The concurrency test in #10 passes.
Notes: do not deviate without approval. If not done by hour 2, Person D pairs with Person B.
Depends on: #3, #4, #5
Unblocks: #11, #20"

issue "Set up test harness and seed.py" "testing,high-priority" "$ASSIGN_C" "What: Set up pytest with a file-based tmp_path DB, TestClient (needs httpx), and an env flag that disables the rate limiter. Write seed.py with demo slots.
Acceptance criteria:
- pytest -q runs.
- seed.py reads DB_PATH from the environment.
- Tests never use :memory: databases.
Depends on: #1, #3
Unblocks: #10, #11"

issue "Write concurrency test for POST /book" "testing,high-priority" "$ASSIGN_C" "What: A slot with 5 spots receives 10 concurrent POST /book requests.
Acceptance criteria:
- Exactly 5 responses are 201 and 5 are 409.
- booked equals 5 and exactly 5 booking rows exist.
Notes: write before #8 lands; it stays red until then.
Depends on: #9
Unblocks: gates the merge of #8"

issue "Write POST /book branch tests" "testing,high-priority" "$ASSIGN_C" "What: Test 404, 409 full, 409 duplicate email, and 422 for each invalid field.
Acceptance criteria:
- After every test, booked equals COUNT of bookings for that slot.
- Booking code in app/db.py has 100 percent line and branch coverage.
Depends on: #8, #9"

issue "Build SlotList table with mock data" "frontend,high-priority" "$ASSIGN_A" "What: Ant Design Table with date, time, remaining spots and a Book button. The button is disabled when the slot is full. Use static mock data that matches the contract.
Acceptance criteria:
- Renders mock slots.
- Full slots show Full and a disabled button.
Depends on: #6
Unblocks: #14"

issue "Build useSlots polling hook" "frontend,high-priority" "$ASSIGN_A" "What: Poll every 10 seconds with async/await and clearInterval cleanup. Show a last updated HH:MM time.
Acceptance criteria:
- A failed poll keeps the old data and shows a stale notice; it never blanks the table.
- Polling stops on unmount.
Depends on: #6
Unblocks: #20"

issue "Build BookingForm modal" "frontend,high-priority" "$ASSIGN_A" "What: Ant Design Modal (use open, not visible) with name, email and phone. Client-side validation is for UX only. On error, show the envelope message.
Acceptance criteria:
- Submit shows loading, then success.
- Slot full and already booked messages show clearly.
- No raw JSON is shown.
Depends on: #12
Unblocks: #20"

issue "Add admin auth dependency and rate limiting" "backend,high-priority" "$ASSIGN_C" "What: security.py checks X-Admin-Token with hmac.compare_digest and rejects when ADMIN_TOKEN is empty. Attach to the admin router. Add slowapi limits on POST /book and GET /booking/{id}. Person B reviews before merge.
Acceptance criteria:
- Missing token, wrong token and empty ADMIN_TOKEN all return 403 UNAUTHORIZED.
- Over-limit requests return 429 RATE_LIMITED.
Notes: adding slowapi needs human approval.
Depends on: #5
Unblocks: #16, #17"

issue "Build GET /booking/{id} admin endpoint" "backend,medium-priority" "$ASSIGN_B" "What: Return one booking behind the admin dependency.
Acceptance criteria:
- Unknown id returns 404.
- Output contains only fields from the contract.
Depends on: #3, #15
Unblocks: #17, #22"

issue "Write admin and security tests" "testing,medium-priority" "$ASSIGN_C" "What: Test all rejection paths for the admin token, plus the rate limit.
Acceptance criteria:
- security.py has 100 percent line and branch coverage.
- No token or PII appears in test logs.
Depends on: #15, #16"

issue "Deploy backend to Railway with persistent volume" "integration,high-priority" "$ASSIGN_D" "What: Deploy a hello-world FastAPI app first, with a volume mounted at /data. Set DB_PATH, ADMIN_TOKEN and CORS_ORIGINS. Redeploy real code after #8.
Acceptance criteria:
- A test row survives a redeploy.
- /docs loads on the public URL.
Notes: deployment config changes need human approval.
Depends on: #1
Unblocks: #19, #23, #24"

issue "Deploy frontend to Netlify" "integration,high-priority" "$ASSIGN_D" "What: Deploy the static build with VITE_API_URL set to the Railway URL. Add the Netlify origin to CORS_ORIGINS.
Acceptance criteria:
- The deployed page loads and calls the backend with no CORS error.
- ADMIN_TOKEN is not in any VITE_ variable.
Depends on: #6, #18
Unblocks: #20, #24"

issue "Wire frontend to live API" "frontend,high-priority" "$ASSIGN_A" "What: Replace mock data with useSlots and client.ts.
Acceptance criteria:
- A volunteer can book a slot on the deployed site.
- The counter drops within 10 seconds.
Depends on: #7, #8, #13, #14, #19
Unblocks: #21, #22, #23"

issue "Build dashboard chart (booked vs capacity)" "frontend,low-priority" "$ASSIGN_A" "What: Recharts bar chart of booked vs capacity per slot, built from GET /slots.
Acceptance criteria:
- Chart renders live data.
- No over-time chart and no history table.
Notes: cut first if short on time. Fallback is a plain table.
Depends on: #20"

issue "Build AdminBookings view (stretch)" "frontend,low-priority" "$ASSIGN_A" "What: A form where the admin types the token and a booking id.
Acceptance criteria:
- The token lives only in component state, never in localStorage.
- A 403 shows a clear message.
Notes: cut second. Fallback is the sqlite3 CLI.
Depends on: #16, #20"

issue "Run end-to-end check on deployed URL and back up DB" "testing,high-priority" "$ASSIGN_C" "What: Run a manual checklist on production: book, fill a slot, try a duplicate, try an invalid phone. Seed demo data. Copy the .db file as a backup.
Acceptance criteria:
- Checklist results are posted in this issue.
- A backup file exists.
Depends on: #18, #20
Unblocks: #25"

issue "Write README for junior developers" "integration,medium-priority" "$ASSIGN_D" "What: Cover setup, run, test, deploy and env vars. Add a plain-language how-it-works paragraph for NGO staff.
Acceptance criteria:
- A teammate follows it on a clean machine and gets the app running.
Depends on: #18, #19"

issue "Write demo script, rehearse and freeze code" "integration,medium-priority" "$ASSIGN_D" "What: Write the 2-minute demo script. Announce the code freeze at the start of hour 5. Run one rehearsal.
Acceptance criteria:
- The rehearsal runs on the deployed URL.
- No merges after the freeze.
Depends on: #23"

echo "Done. Check with: gh issue list --state all"
