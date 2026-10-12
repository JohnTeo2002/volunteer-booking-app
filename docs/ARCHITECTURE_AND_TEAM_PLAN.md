# CFG Hackathon: Stack & Team Allocation Output
## Food Bank Volunteer Booking System (5-Hour Build)

---

## SECTION A: ARCHITECTURE RECOMMENDATION

### 1. Frontend: Vite + React + Ant Design + Recharts

**Vite** is a plain React build with no server to configure. **Ant Design** ships the table, modal, form and validation you need — no Tailwind setup to fight.

- ❌ Skip Next.js (routing and server features you won't use)
- ❌ Skip shadcn/ui (you copy and configure components yourself)
- ✅ Vite scaffolds in seconds, Ant Design gives you production-ready components

---

### 2. Backend: FastAPI with Pydantic

FastAPI gives you:
- Auto-generated `/docs` page that doubles as the API contract
- Built-in request validation via Pydantic models
- Type hints that make the code self-documenting

**Why over Express:** Express needs hand-written validation; FastAPI bakes it in.

---

### 3. Database: SQLite (One File, No Hosting)

- **Relational.** The capacity check is a single atomic SQL statement, not application logic.
- **No hosting overhead.** One `.db` file, backed up locally.
- **No setup time.** Zero configuration.

**Trade-off:** Writes are serialized, but this is fine at food-bank scale (not thousands of concurrent bookings).

**Why over Postgres/Firestore:** Postgres and Firestore add hosting setup and managed database overhead you don't have time for.

---

### 4. Authentication: None for Volunteers, ADMIN_TOKEN for Sensitive Endpoints

**Volunteer bookings:** Completely anonymous. No login required.

**Admin endpoints (GET /booking/{id}):** Protected by one environment variable `ADMIN_TOKEN` sent in the header.

**Why this matters:** `GET /booking/{id}` returns names, emails, and phone numbers. Sequential IDs are guessable. Without the token, anyone can scrape volunteer data.

---

### 5. Deployment Architecture

| Component | Host | Reasoning |
|-----------|------|-----------|
| **Frontend** | Netlify (static build) | Free, zero config, works for SPA |
| **Backend** | Railway with persistent volume | Persistent disk for SQLite file; Render free tier sleeps and loses data |
| **Database** | SQLite file on Railway volume at `/data` | No separate host needed |

---

### 6. Data Schema

```
┌─────────────────────────────────┐     ┌──────────────────────────────────────┐
│       volunteer_slots           │     │           bookings                   │
├─────────────────────────────────┤     ├──────────────────────────────────────┤
│ id (PK)                         │     │ id (PK)                              │
│ event_id                        │◄────┼─ slot_id (FK) ─────────────────┐    │
│ date                            │     │ volunteer_name                       │
│ start_time                      │     │ email                                │
│ end_time                        │     │ phone                                │
│ capacity                        │     │ created_at                           │
│ booked (denormalized count)     │     │ UNIQUE(slot_id, email)               │
└─────────────────────────────────┘     └──────────────────────────────────────┘
```

**Note on schema:** The spec includes `event_id` but no events table. For a 5-hour build, **drop the `event_id` column** unless you're demoing multiple food banks. Keep it simple.

#### The Atomic Booking Transaction (CORE OF THE SYSTEM)

This is your data integrity guarantee:

```sql
BEGIN TRANSACTION;

UPDATE volunteer_slots 
  SET booked = booked + 1
  WHERE id = ? AND booked < capacity;
  -- If 0 rows changed: capacity is full, will violate UNIQUE check → rollback

INSERT INTO bookings 
  (slot_id, volunteer_name, email, phone) 
  VALUES (?, ?, ?, ?);
  -- If duplicate (slot_id, email): UNIQUE constraint violated → rollback

COMMIT;
```

**Why this works:**
- The `booked < capacity` check and the increment happen atomically (same transaction)
- If someone takes the last spot, the next person's insert will fail (duplicate email on same slot)
- No race condition. No double-booking.

**The `booked` denormalized field:**
- Stores the live counter so reads don't require `COUNT(*)` queries
- Must be updated in the same transaction as the booking insert
- Keep it correct or the UI lies to users

---

### 7. Why This Stack Wins in 5 Hours

1. **No learning curve.** Every piece is a standard tool the team already knows. Setup is minutes, not hours.

2. **Data integrity in SQL, not code.** The double-booking guarantee lives in one SQL statement. Reliability doesn't depend on complicated framework logic.

3. **Two deployments.** One static frontend (Netlify), one backend with a disk (Railway). Simple to get right, less to debug.

---

### 8. Trade-offs (Honest)

| Trade-off | Impact | Mitigation |
|-----------|--------|-----------|
| **Real-time = polling, not WebSockets** | Counters can be up to 10s stale | Show a "last updated at HH:MM" timestamp so users know data may be old |
| **No volunteer login** | Can't cancel bookings or block bad actors | Add an admin delete endpoint later. For the 5-hour demo, acceptable |
| **SQLite doesn't scale past one server** | Won't work for a national network | Fine for this demo. Migration path: move to Postgres later |
| **No automatic backups** | Data loss if volume mount fails or is deleted | Manually copy `.db` file before demo. Test persistence at hour 3 |
| **Sync FastAPI, not async** | Can't handle thousands of concurrent requests | Async adds `aiosqlite` complexity for no gain at this volume. Upgrade if load matters |
| **Ant Design bundle size is large** | Slightly bigger JS download | Doesn't matter for this app. Render time matters more than bundle size in a hackathon |

---

## SECTION B: WORK BREAKDOWN & TEAM ROLE ALLOCATION

### 9. Role Assignments (4 People, 5 Hours)

#### Person A: Frontend Lead
**Primary responsibility:**
- SlotList table with live remaining capacity counters (polls `GET /slots` every 10 seconds)
- BookingForm modal with form validation and error display

**Secondary responsibility:**
- Dashboard with Recharts utilization chart (built from the same `/slots` data)
- Last thing to build; cut if time runs out

**Unblocked by:** The JSON API contract (hour 1)  
**Unblocks:** Person D's integration tests (hour 2)

---

#### Person B: Backend Lead (CRITICAL PATH)
**Primary responsibility:**
- `schema.sql` and database initialization
- `GET /slots` endpoint (returns available slots with current booking counts)
- `POST /book` with the atomic transaction logic and proper HTTP status codes (409 Conflict, 422 Unprocessable Entity)
- Pydantic models for request/response validation

**Secondary responsibility:**
- `GET /booking/{id}` protected by ADMIN_TOKEN (for admin dashboard)
- Update `.env.example` as new variables are needed

**Why critical path:** If Person B slips, both Person A (needs API working to test forms) and Person D (needs API to test integration) are blocked.

**Unblocks:** Person A at hour 1 (contract), Person C at hour 1 (for test writing), Person D at hour 2 (for integration)

---

#### Person C: QA & Data Integrity Lead
**Primary responsibility:**
- pytest test suite with concurrency test (spin up a 5-spot slot, run 10 concurrent booking attempts, assert exactly 5 succeed)
- Seed script for demo data
- Edge case testing (duplicate email, sold-out slot, invalid phone format)

**Secondary responsibility:**
- End-to-end testing on the deployed URL at hour 3
- Own the demo data story (which slots, which volunteers, what the final state looks like)

**Unblocked by:** The JSON contract (hour 1)  
**Unblocks:** Person D's integration tests at hour 3

---

#### Person D: Integration, Docs, Deployment Lead (Force Multiplier)
**Primary responsibility:**
- README written for a junior developer: setup, `npm install`, Netlify and Railway setup, environment variables, how to test locally
- Deploy frontend to Netlify (hour 2)
- Deploy backend to Railway and verify SQLite persistence (hour 3)

**Secondary responsibility:**
- Floats to whoever is stuck
- If Person B is late on `/book`, pair with them immediately to unblock
- Write a 2-minute demo script so the team nails the presentation

**Unblocked by:** None (can start immediately on README and deployments)  
**Unblocks:** Entire team (deployments enable testing on real URLs)

---

### 10. Parallel Work Streams (What Can Happen at the Same Time)

#### Stream 1: Frontend (Person A)
- Mocks API responses from a fixed JSON sample until hour 3
- Builds UI components independently
- Doesn't depend on backend being ready

#### Stream 2: Backend (Person B)
- Writes API endpoints starting with the booking transaction
- Doesn't wait on anyone; unblocks everyone else
- The critical path

#### Stream 3: Data & Deployment (Person C + Person D)
- Person C writes tests against the agreed JSON contract (from hour 1)
- Person D sets up both deployment environments (Netlify, Railway) in parallel
- Neither blocks Person B

---

### 11. Hour-by-Hour Execution Plan

#### **Hour 1 (10:00 AM – 11:00 AM): Setup & Contract Lock**

**All together (first 10 minutes):**
- Agree on the JSON API contract (write it in a shared doc)
- Copy sample request/response shapes into the repo as `docs/API_CONTRACT.json`
- **Freeze the contract.** No changes after this unless critical

**Person A (Frontend):**
- Vite scaffold: `npm create vite@latest food-bank -- --template react`
- Install Ant Design and Recharts
- Create SlotList table component (static mock data hardcoded for now)
- Mock the polling logic that will call the API later

**Person B (Backend):**
- Create `schema.sql` with the volunteer_slots and bookings tables
- Write seed data (5 slots with varying capacities)
- Implement `GET /slots` endpoint that returns the JSON from the contract
- Write Pydantic models for request/response validation

**Person C (QA):**
- Set up pytest harness
- **Write the concurrency test FIRST** (it will fail until Person B finishes `/book`)
- Outline edge case tests (duplicate email, invalid phone, sold out)

**Person D (Integration/Docs):**
- Create GitHub repo
- Write README skeleton (setup, environment variables, how to run locally)
- Create Netlify and Railway accounts
- Deploy a hello-world FastAPI to Railway to verify the volume mount works

**End of Hour 1 checklist:**
- ✅ Frontend scaffolded with mock SlotList table
- ✅ Backend has GET /slots working
- ✅ Database schema created and seeded
- ✅ Both deployments tested with hello-world
- ✅ API contract written and frozen

---

#### **Hour 2 (11:00 AM – 12:00 PM): Core Feature (Booking)**

**Person B (HIGHEST PRIORITY):**
- Implement `POST /book` with the atomic transaction
- Error handling: 409 Conflict (slot full), 422 Unprocessable Entity (invalid data)
- Test in Postman before 11:45 AM

**Person A (Frontend):**
- BookingForm modal with form validation
- Integrate live counter polling (`GET /slots` every 10 seconds)
- Wire submit button to call the API (still testing against localhost)

**Person C (QA):**
- Run the concurrency test against Person B's `/book` endpoint
- If test passes: green light. If fails: debug with Person B.
- Run edge case tests (duplicate email, bad phone format, sold out)

**Person D (Integration):**
- Deploy the React frontend to Netlify
- Verify the build works and frontend is accessible at a Netlify URL

**If Person B is late on `/book`:**
- Person D drops everything and pairs with Person B to unblock them

**End of Hour 2 checklist:**
- ✅ POST /book working with atomic transaction
- ✅ BookingForm on frontend wired to API
- ✅ Frontend deployed to Netlify
- ✅ Concurrency test passing (or bugs identified and flagged)

---

#### **Hour 3 (12:00 PM – 1:00 PM): Integration & Admin**

**Person A (Frontend):**
- Remove hardcoded mock data
- Wire the frontend to the live API (deployed backend on Railway)
- Add "Last updated" timestamp to the counter

**Person B (Backend):**
- Implement `GET /booking/{id}` protected by ADMIN_TOKEN
- Create an admin endpoint to fetch all bookings (for the admin dashboard if time allows)
- Fix any bugs found by Person C's tests

**Person C (QA):**
- Run full end-to-end test on the deployed frontend and backend (Netlify + Railway)
- Test the admin token protection (verify unauthenticated requests are rejected)
- Verify the SQLite file survives a Railway redeploy (critical!)

**Person D (Integration):**
- Deploy the backend to Railway and confirm SQLite persistence
- Verify frontend can talk to the live backend
- Finish the README with real setup instructions for a clean machine

**End of Hour 3 checklist:**
- ✅ Frontend and backend integrated on deployed URLs
- ✅ SQLite data persists across redeploys
- ✅ Admin token protection working
- ✅ All core features tested end-to-end

---

#### **Hour 4 (1:00 PM – 2:00 PM): Dashboard & Polish**

**Person A (Frontend):**
- Build the Dashboard with Recharts utilization chart (total booked vs capacity over time)
- Polish UI: responsive design, error messages, loading states

**Person B (Backend):**
- Debug any remaining issues from testing
- Optimize queries if slow (unlikely at this data scale)
- Write API documentation in the README

**Person C (QA):**
- Full regression testing on all endpoints
- Test edge cases (network failures, invalid requests)
- Verify demo data is set up correctly

**Person D (Integration):**
- Finish README: add troubleshooting section
- Write a 2-minute demo script for the team

---

#### **Hour 5 (2:00 PM – 3:00 PM): Code Freeze & Demo Rehearsal**

**Code freeze at 2:30 PM.** No new features after this.

**All:**
- Rehearse the demo once (should take exactly 2 minutes)
- Person C backs up the `.db` file
- Person D verifies the README works by following it on a clean machine

**Demo flow (2 minutes):**
1. Show the volunteer slot list (30 seconds)
2. Book 4 volunteers for one slot (the slot has capacity 4) (30 seconds)
3. Try to book a 5th volunteer — see "Slot full" error (30 seconds)
4. Show the admin view (bookings list) with token protection (30 seconds)

**Deployment verification:**
- Both Netlify and Railway are live and stable
- SQLite file is backed up
- No console errors on the deployed URLs

---

### 12. MVP Feature Implementation Order

#### Person B (Backend) Build Order:
1. `schema.sql` + seed data (enables A and C to mock/test)
2. `GET /slots` (unblocks A to test forms)
3. `POST /book` with atomic transaction (core feature, highest priority)
4. `GET /booking/{id}` with ADMIN_TOKEN (nice-to-have, lower priority)

#### Person A (Frontend) Build Order:
1. SlotList table with static mock data (enables demo at hour 1)
2. BookingForm modal with validation (enable booking at hour 2)
3. Live counter polling (works against deployed backend at hour 3)
4. Dashboard chart (nice-to-have, can be swapped for a simple table if time runs out)

#### Person C (QA) Build Order:
1. Test harness setup
2. Concurrency test (writes test first, it fails until B's code lands)
3. Edge case tests (duplicate email, sold out, invalid phone)
4. End-to-end deployed URL tests (hour 3 onward)

#### Person D (Docs) Build Order:
1. README skeleton
2. Deploy pipeline (Netlify + Railway) — test with hello-world
3. README final with real setup instructions
4. Demo script + troubleshooting

---

### 13. Critical Blocking Dependencies

| Blocker | Blocked | When Unblocked | Mitigation |
|---------|---------|-------------------|-----------|
| **JSON API contract** | All (A, C, D need it to start) | Hour 1, 10:15 AM | Agree the contract first, write it down |
| **GET /slots** | Person A can test forms | Hour 1, 10:45 AM | A can mock it if needed; C can write test against contract |
| **POST /book atomic logic** | A can test booking, C can run concurrency test, D can test integration | Hour 2, 11:45 AM | **CRITICAL.** If late, D pairs with B immediately |
| **Deployed frontend URL (Netlify)** | A needs it to test live API integration | Hour 2, 12:00 PM | D handles this; not blocking (A can test localhost first) |
| **Deployed backend + SQLite persistence** | C needs to verify end-to-end on prod | Hour 3, 12:30 PM | **CRITICAL.** If SQLite doesn't persist, the demo data is lost. Test immediately |

**Single biggest dependency:** `POST /book` working and surviving a Railway redeploy. If the booking transaction breaks, the demo fails. If the SQLite file is lost on redeploy, the data is gone.

**Mitigation:**
- Person B owns `/book` first, writes unit tests
- Person C runs the concurrency test hourly
- Person D verifies persistence at hour 3 (redeploy and check data is still there)

---

### 14. Hourly Standup Prompts (Ask Every Hour)

**Person A status:**
- What's your status: on track / slightly behind / blocked?
- What's your next immediate task, and when will it be done?
- Do you need help from anyone, and who specifically?
- Does anything you've changed affect the API contract or the deploy?

**Repeat for B, C, D.**

**Document answers in Slack or a shared doc so you have a record for evaluators.**

---

### 15. Biggest Risk & Mitigation Strategy

#### Biggest Risk
The `/book` transaction or the deployment breaks, and the demo can't show a booking happening live.

#### Most Critical Person
**Person B** (backend). If they get stuck, the whole system stops. Both Person A (forms) and Person D (testing) depend on the API.

**Mitigation:**
- Person C reviews the atomic transaction code at hour 2
- Person D pairs with Person B immediately if they slip
- Person C runs concurrency tests hourly to catch issues early

#### Fallback Plans (If We're Behind)

**If frontend isn't ready by hour 4:**
- Demo the API through Postman/curl + show the database records
- Say plainly: "The backend works; frontend needs polish"

**If backend isn't ready by hour 3:**
- Show the frontend with mock data
- Explain: "The API contract is locked; we're still implementing it"

**Never demo something you haven't tested on the deployed URL.**

#### Person D as Force Multiplier
Person D checks standups every hour. Whoever is stuck gets help within 15 minutes. Person D either:
- Takes a slice of the stuck task and does it so the blocked person can focus
- Pairs with them to unblock faster
- Does D's own (docs/deploy) work so the blocked person isn't waiting on dependencies

---

## Appendix: Implementation Details & Edge Cases

### SQLite Persistence on Railway
**Critical:** Test this at hour 3.

```bash
# After first deploy, add some data
curl -X POST http://your-railway-url/book \
  -H "Content-Type: application/json" \
  -d '{"slot_id": 1, "volunteer_name": "Jane", "email": "jane@example.com", "phone": "555-1234"}'

# Redeploy the backend (or restart the dyno)
# Check if the booking still exists
curl http://your-railway-url/slots

# If the booking is gone, the volume mount isn't working. 
# Fallback: store data in an env variable or use Render's free tier database instead.
```

### ADMIN_TOKEN Validation in FastAPI

```python
from fastapi import Header, HTTPException

@app.get("/booking/{id}")
def get_booking(id: int, admin_token: str = Header(None)):
    if admin_token != os.getenv("ADMIN_TOKEN"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    # ... fetch and return booking
```

### Polling in React (Every 10 Seconds)

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    fetch('/api/slots')
      .then(r => r.json())
      .then(data => setSlots(data));
  }, 10000); // Poll every 10 seconds
  
  return () => clearInterval(interval);
}, []);
```

---

## Before You Demo

- [ ] SQLite data survives a Railway redeploy
- [ ] Netlify frontend connects to Railway backend without CORS errors
- [ ] Concurrency test passes (5 volunteers book the same 5-spot slot)
- [ ] Admin token blocks unauthenticated requests
- [ ] Duplicate email for same slot is rejected
- [ ] README works when followed on a clean machine
- [ ] Demo script takes exactly 2 minutes
- [ ] Backup of the `.db` file exists

---

## Assumptions & Risks

**Verified before hour 1:**
- ❓ Ant Design is still free and hasn't changed API
- ❓ Railway free tier still allows persistent volumes
- ❓ Netlify still has a free tier with instant deploys

**Design decisions not addressed (out of scope for 5-hour build):**
- ❌ Volunteer cancellations (no login, so no way to cancel)
- ❌ Email confirmations (no email integration)
- ❌ Automatic backups (manual only)

**Test persistence at hour 3:** This is critical. If the SQLite file isn't persisted, the whole thing falls apart.

---

## Good luck! 🚀