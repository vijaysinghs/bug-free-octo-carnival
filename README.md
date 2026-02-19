# Personal Profile Database Application

A complete Flask + SQLite application to manage personal data with authentication and encrypted confidential records.

## Features

- User registration/login/logout and profile endpoint.
- CRUD APIs and UI for:
  - Achievements
  - Personal goals (`planned`, `in progress`, `complete`)
  - Expense tracking (`amount`, `date`, `category`, `notes`)
  - Personal notes
  - Confidential details (encrypted at rest)
- Search and filtering support in API + UI.
- SQLite relational schema using SQLAlchemy models.

## Project file structure

```text
.
├── app.py                 # Flask app, models, API routes, encryption logic
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Main web UI
└── static/
    ├── app.js             # Frontend behavior + API calls
    └── styles.css         # Basic styling
```

## Database schema

The app uses SQLAlchemy models and creates tables automatically (`db.create_all()`).

### `user`
- `id` (PK)
- `username` (unique)
- `email` (unique)
- `password_hash`
- `created_at`

### `achievement`
- `id` (PK)
- `title`
- `description`
- `achieved_on`
- `user_id` (FK -> user.id)
- `created_at`

### `goal`
- `id` (PK)
- `title`
- `description`
- `status` (`planned` / `in progress` / `complete`, constrained)
- `target_date`
- `user_id` (FK -> user.id)
- `created_at`

### `expense`
- `id` (PK)
- `amount` (numeric)
- `date`
- `category`
- `notes`
- `user_id` (FK -> user.id)
- `created_at`

### `note`
- `id` (PK)
- `title`
- `content`
- `user_id` (FK -> user.id)
- `created_at`

### `confidential_detail`
- `id` (PK)
- `title`
- `encrypted_value` (**encrypted with Fernet**)
- `user_id` (FK -> user.id)
- `created_at`

## Security notes

- Passwords are hashed with Werkzeug (`generate_password_hash` / `check_password_hash`).
- Confidential detail values are encrypted before being stored in DB using Fernet.
- Set `ENCRYPTION_KEY` in production to a stable Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If `ENCRYPTION_KEY` is not set, a fallback key is derived from `SECRET_KEY`.

## REST API endpoints

### Auth
- `POST /api/register`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/profile`

### Achievements
- `GET /api/achievements?q=...`
- `POST /api/achievements`
- `PUT /api/achievements/<id>`
- `DELETE /api/achievements/<id>`

### Goals
- `GET /api/goals?q=...&status=planned|in progress|complete`
- `POST /api/goals`
- `PUT /api/goals/<id>`
- `DELETE /api/goals/<id>`

### Expenses
- `GET /api/expenses?category=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&min_amount=...&max_amount=...&q=...`
- `POST /api/expenses`
- `PUT /api/expenses/<id>`
- `DELETE /api/expenses/<id>`

### Notes
- `GET /api/notes?q=...`
- `POST /api/notes`
- `PUT /api/notes/<id>`
- `DELETE /api/notes/<id>`

### Confidential details
- `GET /api/confidential-details?q=...`
- `POST /api/confidential-details`
- `PUT /api/confidential-details/<id>`
- `DELETE /api/confidential-details/<id>`

## Run locally

1. Create and activate virtual environment.
2. Install dependencies.
3. Set environment vars (optional but recommended).
4. Start app.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY='change-this-secret'
# Optional: export ENCRYPTION_KEY='paste-fernet-key'
python app.py
```

Open `http://127.0.0.1:5000`.

## Notes for production

- Use PostgreSQL by setting `DATABASE_URL`.
- Run behind HTTPS.
- Use secure cookie flags and a strong random `SECRET_KEY`.
- Use a persistent and protected `ENCRYPTION_KEY`.
