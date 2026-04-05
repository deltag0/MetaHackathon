# Error Handling

Documents how the app handles 404s and 500s — all error responses are JSON, never HTML or stack traces.

---

## HTTP Error Responses

| Status | Scenario | Response body |
|---|---|---|
| 400 | Missing required field | `{"error": "url is required"}` |
| 400 | Invalid URL scheme | `{"error": "url must start with http:// or https://"}` |
| 404 | Route does not exist | `{"error": "not found"}` |
| 404 | Resource not found | `{"error": "not found"}` |
| 405 | Wrong HTTP method | `{"error": "method not allowed"}` |
| 500 | Unhandled server exception | `{"error": "internal server error"}` |

---

## 404 — Not Found

Registered via Flask's `@app.errorhandler(404)`. Triggered when:
- A route does not exist
- A resource (short code, user, URL) is not found in the database

```bash
curl -s http://localhost:5000/doesnotexist | jq
# {"error": "not found"}
```

---

## 405 — Method Not Allowed

Registered via Flask's `@app.errorhandler(405)`. Triggered when the route exists but the HTTP method is wrong.

```bash
curl -s -X POST http://localhost:5000/health | jq
# {"error": "method not allowed"}
```

---

## 500 — Internal Server Error

Registered via Flask's `@app.errorhandler(500)`. Triggered on any unhandled exception. The stack trace is logged server-side but never exposed to the client.

```bash
# The server logs the full traceback internally.
# The client always sees:
# {"error": "internal server error"}
```
