# shorten.it Runbook

> For your 3 AM self. Don't think. Follow the steps.

## Quick Health Check

```bash
docker compose -f docker-compose.gold.yml ps
curl -s http://localhost/health/ready | python -m json.tool
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## When an Alert Fires

### ServiceDown / App Instance Down

App is unreachable or an instance crashed.

1. `docker compose -f docker-compose.gold.yml ps` — find what's down
2. Check logs: `docker compose -f docker-compose.gold.yml logs --tail=50 app-1 app-2 app-3 app-4`
3. Restart the broken instance: `docker compose -f docker-compose.gold.yml restart app-<N>`
4. If everything is down: `docker compose -f docker-compose.gold.yml down && docker compose -f docker-compose.gold.yml up -d`

### High Error Rate (>10% 5xx)

1. Check Loki in Grafana: `{service=~"app-.*"} |= "ERROR"`
2. Check DB connections: `docker compose -f docker-compose.gold.yml exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"`
3. If a single instance is misbehaving, restart it
4. If recent code change caused it, rollback (see below)

### Postgres Down

**This breaks everything.**

1. `docker compose -f docker-compose.gold.yml restart db`
2. Wait ~25s, then: `docker compose -f docker-compose.gold.yml exec db pg_isready -U postgres`
3. If DB is back but apps aren't recovering: `docker compose -f docker-compose.gold.yml restart app-1 app-2 app-3 app-4`

### Redis Down

**App still works** — just slower (cache falls back to DB).

1. `docker compose -f docker-compose.gold.yml restart redis`
2. Verify: `docker compose -f docker-compose.gold.yml exec redis redis-cli ping`

### High CPU / Low Disk

1. Find the culprit: `docker stats --no-stream`
2. Disk full? `docker system prune -f` and truncate logs: `truncate -s 0 logs/app-*/app-*.log`

### Loki / Promtail Down

**Users aren't affected** — but you lose log visibility.

1. `docker compose -f docker-compose.gold.yml restart loki promtail`

---

## Rollback a Bad Deploy

```bash
git log --oneline -5                          # find last good commit
git checkout <commit-hash>
docker compose -f docker-compose.gold.yml build && docker compose -f docker-compose.gold.yml up -d
```

---

## Escalation

- **Critical** (ServiceDown, Postgres down, high error rate): Fix now. If not resolved in 15 min, escalate.
- **Warning** (high CPU, low disk, Redis down): Fix within 30 min.
- Critical alerts go to **email + Discord**. Warnings go to **email only**.

---

## After Every Incident

1. Run the quick health check above
2. Write down: what happened, what fixed it, how to prevent it
3. Update this runbook if needed
