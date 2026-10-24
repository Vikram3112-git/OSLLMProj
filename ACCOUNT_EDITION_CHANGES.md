# OSLLM Account Edition — Changes and Setup

This package keeps the existing OSLLM FastAPI + plain-JavaScript interface, Ollama model integration, OS knowledge base, Learn, Practice, Progress, and Chat features, and adds/fixes account-based personalization.

## Changes included

1. **Visible login and registration page**: the app shows a login/create-account screen when there is no valid session. Registration asks for username, email, and a password of at least 8 characters; login accepts username or email.
2. **Password storage**: passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, never as plaintext.
3. **Session tokens**: authenticated API calls use a bearer token; the database stores a hash of the token and sessions expire after 30 days. Logging out revokes the server session.
4. **Per-account saved conversations**: chats are stored by username on the server, and only the authenticated account can list, save, or delete its chats.
5. **Private preferences and memory**: users can set display name, explanation level, response style, goals, and a private memory note. Relevant notes are added to the AI context for that account.
6. **Private documents**: uploaded PDF, Markdown, and text documents are text-extracted and stored under that account. Document search is scoped by username; upload/delete do not modify the shared course index.
7. **Account-isolated learning progress**: the authenticated username is used for progress operations, and client-supplied identity mismatches are rejected by the API middleware.
8. **Database migration correction**: fixed the SQLite `memory_notes` migration default so older account databases missing that column can upgrade correctly.
9. **Clean package**: runtime databases and Python bytecode caches are excluded, so the app creates fresh local databases on first launch rather than shipping another user's local state.

## Linux setup

Open Terminal in the extracted `OSLLM` folder and run:

```bash
chmod +x run.sh
./run.sh
```

The launcher checks/starts Ollama, downloads its configured model if missing, prepares the Python environment and knowledge index, then starts the FastAPI server. First launch may take a while and download several GB. Open `http://localhost:8501` after the launcher says the server is ready.

If you already have a virtual environment and want to launch only the web server after dependencies and the Ollama model/index are prepared:

```bash
source venv/bin/activate
python server.py
```

Open `http://localhost:8501`.

## First login

1. Click **Create account**.
2. Enter a username (3–32 letters/numbers/underscore/dot/hyphen), a valid email, and a password of at least 8 characters.
3. Create the account; the app signs you in.
4. Use **Preferences** to set AI style, goals, and private memory. Use **My files** for your own documents.

## Important limits and deployment security

- This is a local Ollama application. The host computer must be on, Ollama must be running, and the model must be available.
- Password hashing and per-account authorization are implemented, but this should still be treated as a local/personal-use build until production deployment protections are added: HTTPS, rate limiting, CSRF/origin strategy where applicable, backups, secure secret/session management, request-size limits at a reverse proxy, and a security review.
- SQLite files live in `data/` and contain account/session records, private documents, chats, and learning progress. Keep that directory private and back it up securely.
- Private document retrieval currently uses lexical/text overlap, not a dedicated per-user vector database. Scanned PDFs may require OCR.
- This is not a hosted cloud AI service. The AI runs through the local Ollama service on the host.

## Troubleshooting

- If the browser continues showing an already-authenticated session from an older copy, click **Log out** first or open the app in a private/incognito window. A fresh browser session with no OSLLM token should show the login page.
- If port 8501 is busy, stop the older OSLLM server with `Ctrl+C` before launching the new copy.
- If the browser still serves an older interface, verify that the terminal is running `server.py` from this extracted folder, then hard-refresh the page with `Ctrl+Shift+R`.
