# k6 Load Testing — Tier 1 Bronze

Stress test the shorten.it API with 50 concurrent users using [k6](https://k6.io/).

## Install k6

**Windows (winget):**
```bash
winget install k6 --source winget
```

**Windows (choco):**
```bash
choco install k6
```

**macOS:**
```bash
brew install k6
```

**Linux:**
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

## Prerequisites

Make sure the Flask backend is running:
```bash
uv run run.py          # starts on http://localhost:5000
```

And that the database is seeded:
```bash
uv run scripts/init_db.py
```

## Running the Tests

### 1. Smoke test (sanity check)

Run this first to make sure all endpoints respond:
```bash
k6 run "k6 testing/smoke_test.js"
```

### 2. Full load test (50 concurrent users, 30 seconds)

```bash
k6 run "k6 testing/load_test.js"
```

To target a different host:
```bash
k6 run -e BASE_URL=http://your-server:5000 "k6 testing/load_test.js"
```

## What Gets Tested

Each of the 50 virtual users runs this loop for 30 seconds:

| Endpoint               | Method | Purpose                    |
|------------------------|--------|----------------------------|
| `/users`               | GET    | List users                 |
| `/users`               | POST   | Create user                |
| `/users/:id`           | GET    | Get user by ID             |
| `/users/:id`           | PUT    | Update user                |
| `/users?page&per_page` | GET    | Paginated list             |
| `/urls`                | GET    | List URLs                  |
| `/urls`                | POST   | Create short URL           |
| `/urls/:id`            | GET    | Get URL by ID              |
| `/urls/:id`            | PUT    | Update URL                 |
| `/urls?is_active`      | GET    | Filter active URLs         |
| `/events`              | GET    | List events                |
| `/events`              | POST   | Create click event         |
| `/events?event_type`   | GET    | Filter events by type      |
| `/events?url_id`       | GET    | Filter events by URL       |
| `/urls/:id`            | DELETE | Cleanup created URL        |
| `/users/:id`           | DELETE | Cleanup created user       |

## Reading the Output

k6 prints a summary table after each run. Key metrics to document:

- **http_req_duration (p95)** — 95th percentile response time (your baseline)
- **http_reqs** — total requests made
- **errors** — custom error rate (non-expected status codes)
- **iterations** — how many full loops completed

### Example output to screenshot:
```
     scenarios: (100.00%) 1 scenario, 50 max VUs, 1m0s max duration
                load_test: 50 looping VUs for 30s

     ✓ GET /users status 200
     ✓ POST /users status 201
     ...

     http_req_duration..........: avg=45ms  min=3ms  med=30ms  max=500ms  p(90)=120ms  p(95)=180ms
     http_reqs..................: 12500  416/s
     errors.....................: 0.50%  ✓ 62  ✗ 12438
     iterations.................: 800   26/s
```

**For the hackathon submission, screenshot the full terminal output showing the 50 VUs and the p95 line.**
