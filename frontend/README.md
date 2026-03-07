# Frontend (No Backend Changes)

This frontend is a standalone `HTML + Tailwind + JS` app that proxies API requests to your existing FastAPI backend.

## Run

1. Start backend first (default `http://127.0.0.1:8000`).
2. In another terminal:

```bash
cd frontend
node server.mjs
```

3. Open:

- `http://127.0.0.1:5173`

## Optional env vars

```bash
FRONTEND_PORT=5173 BACKEND_ORIGIN=http://127.0.0.1:8000 node server.mjs
```

## Notes

- No change to backend code is required.
- Streaming chat works via `fetch` + `ReadableStream`.
- Session (`user_id`, `thread_id`) is stored in browser `localStorage`.
