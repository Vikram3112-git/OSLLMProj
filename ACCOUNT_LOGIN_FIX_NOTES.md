# OSLLM Account Login Fix — 24 October 2026

## Fix applied

- Fixed the HTTP middleware body replay in `server.py`. Previously, the `receive_body()` callback returned the same `http.request` message indefinitely. During Starlette response cleanup, this could raise `RuntimeError: Unexpected message received: http.request`, especially for streamed responses. The middleware now replays the inspected request body exactly once and then signals `http.disconnect`.
- Kept the authenticated account checks for API calls and payload `student` identity checks.
- Redesigned the login / create-account screen with a dark teal gradient, two-panel desktop layout, responsive mobile layout, improved input states, stronger primary action, and clearer account privacy copy.
- Preserved the existing API routes and login/register JavaScript IDs so the existing authentication flow remains wired up.

## Run on Ubuntu

```bash
cd ~/Desktop/OSLLM
chmod +x run.sh
./run.sh
```

Open `http://localhost:8501` if the browser does not open automatically.

## Notes

- The `@app.on_event("startup")` deprecation warning is not the cause of the reported HTTP exception; it can be migrated to a lifespan handler separately.
- The Hugging Face unauthenticated warning affects rate limits/download speed, not the HTTP request exception.
- `python -m py_compile server.py` and `node --check web/app.js` pass in the build environment. Run the app locally to validate against the installed Python package versions and model environment.
