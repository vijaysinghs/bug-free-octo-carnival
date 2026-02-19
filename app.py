"""Personal Profile Database Application.

Features:
- Session-based authentication.
- CRUD APIs for achievements, goals, expenses, notes, confidential details.
- Search/filter support per module.
- Confidential details encrypted at rest using Fernet.
"""
from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, jsonify, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///profile.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


def _load_fernet() -> Fernet:
    """Build the encryption utility from ENCRYPTION_KEY or SECRET_KEY."""
    key_from_env = os.environ.get("ENCRYPTION_KEY")
    if key_from_env:
        return Fernet(key_from_env.encode())

    digest = hashlib.sha256(app.config["SECRET_KEY"].encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


fernet = _load_fernet()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    achievements = db.relationship("Achievement", backref="user", cascade="all, delete-orphan")
    goals = db.relationship("Goal", backref="user", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="user", cascade="all, delete-orphan")
    notes = db.relationship("Note", backref="user", cascade="all, delete-orphan")
    confidential_details = db.relationship("ConfidentialDetail", backref="user", cascade="all, delete-orphan")


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    achieved_on = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Goal(db.Model):
    __table_args__ = (
        CheckConstraint("status IN ('planned', 'in progress', 'complete')", name="goal_status_check"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planned")
    target_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ConfidentialDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    encrypted_value = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def current_user() -> User | None:
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


def require_auth() -> User:
    user = current_user()
    if not user:
        raise PermissionError("Authentication required")
    return user


def parse_date(raw: str | None):
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.errorhandler(PermissionError)
def handle_permission(_: PermissionError):
    return json_error("Unauthorized", 401)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/register")
def register():
    payload = request.get_json(force=True)
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not username or not email or len(password) < 8:
        return json_error("username, email and password(min 8 chars) are required")

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return json_error("username or email already exists", 409)

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    return jsonify({"message": "registered", "user": {"id": user.id, "username": user.username, "email": user.email}}), 201


@app.post("/api/login")
def login():
    payload = request.get_json(force=True)
    username_or_email = payload.get("username", "").strip()
    password = payload.get("password", "")

    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email.lower())).first()
    if not user or not check_password_hash(user.password_hash, password):
        return json_error("invalid credentials", 401)

    session["user_id"] = user.id
    return jsonify({"message": "logged in", "user": {"id": user.id, "username": user.username, "email": user.email}})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "logged out"})


@app.get("/api/profile")
def profile():
    user = require_auth()
    return jsonify({"id": user.id, "username": user.username, "email": user.email, "created_at": user.created_at.isoformat()})


@app.get("/api/achievements")
def list_achievements():
    user = require_auth()
    q = request.args.get("q", "").strip()
    query = Achievement.query.filter_by(user_id=user.id)
    if q:
        query = query.filter((Achievement.title.ilike(f"%{q}%")) | (Achievement.description.ilike(f"%{q}%")))
    items = query.order_by(Achievement.created_at.desc()).all()
    return jsonify([
        {"id": a.id, "title": a.title, "description": a.description, "achieved_on": a.achieved_on.isoformat() if a.achieved_on else None}
        for a in items
    ])


@app.post("/api/achievements")
def create_achievement():
    user = require_auth()
    payload = request.get_json(force=True)
    item = Achievement(
        title=payload.get("title", "").strip(),
        description=payload.get("description", "").strip(),
        achieved_on=parse_date(payload.get("achieved_on")),
        user_id=user.id,
    )
    if not item.title or not item.description:
        return json_error("title and description are required")
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id}), 201


@app.put("/api/achievements/<int:item_id>")
def update_achievement(item_id: int):
    user = require_auth()
    item = Achievement.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    payload = request.get_json(force=True)
    item.title = payload.get("title", item.title).strip()
    item.description = payload.get("description", item.description).strip()
    item.achieved_on = parse_date(payload.get("achieved_on")) if "achieved_on" in payload else item.achieved_on
    db.session.commit()
    return jsonify({"message": "updated"})


@app.delete("/api/achievements/<int:item_id>")
def delete_achievement(item_id: int):
    user = require_auth()
    item = Achievement.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


@app.get("/api/goals")
def list_goals():
    user = require_auth()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Goal.query.filter_by(user_id=user.id)
    if q:
        query = query.filter((Goal.title.ilike(f"%{q}%")) | (Goal.description.ilike(f"%{q}%")))
    if status:
        query = query.filter(Goal.status == status)
    items = query.order_by(Goal.created_at.desc()).all()
    return jsonify([
        {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "status": g.status,
            "target_date": g.target_date.isoformat() if g.target_date else None,
        }
        for g in items
    ])


@app.post("/api/goals")
def create_goal():
    user = require_auth()
    payload = request.get_json(force=True)
    status = payload.get("status", "planned")
    if status not in {"planned", "in progress", "complete"}:
        return json_error("invalid status")
    item = Goal(
        title=payload.get("title", "").strip(),
        description=payload.get("description", "").strip(),
        status=status,
        target_date=parse_date(payload.get("target_date")),
        user_id=user.id,
    )
    if not item.title or not item.description:
        return json_error("title and description are required")
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id}), 201


@app.put("/api/goals/<int:item_id>")
def update_goal(item_id: int):
    user = require_auth()
    item = Goal.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    payload = request.get_json(force=True)
    if "status" in payload and payload["status"] not in {"planned", "in progress", "complete"}:
        return json_error("invalid status")
    item.title = payload.get("title", item.title).strip()
    item.description = payload.get("description", item.description).strip()
    item.status = payload.get("status", item.status)
    item.target_date = parse_date(payload.get("target_date")) if "target_date" in payload else item.target_date
    db.session.commit()
    return jsonify({"message": "updated"})


@app.delete("/api/goals/<int:item_id>")
def delete_goal(item_id: int):
    user = require_auth()
    item = Goal.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


@app.get("/api/expenses")
def list_expenses():
    user = require_auth()
    query = Expense.query.filter_by(user_id=user.id)
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()
    start = parse_date(request.args.get("start_date")) if request.args.get("start_date") else None
    end = parse_date(request.args.get("end_date")) if request.args.get("end_date") else None

    if category:
        query = query.filter(Expense.category == category)
    if q:
        query = query.filter(Expense.notes.ilike(f"%{q}%"))
    if start:
        query = query.filter(Expense.date >= start)
    if end:
        query = query.filter(Expense.date <= end)

    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    if min_amount:
        query = query.filter(Expense.amount >= Decimal(min_amount))
    if max_amount:
        query = query.filter(Expense.amount <= Decimal(max_amount))

    items = query.order_by(Expense.date.desc()).all()
    return jsonify([
        {
            "id": e.id,
            "amount": float(e.amount),
            "date": e.date.isoformat(),
            "category": e.category,
            "notes": e.notes,
        }
        for e in items
    ])


@app.post("/api/expenses")
def create_expense():
    user = require_auth()
    payload = request.get_json(force=True)
    try:
        amount = Decimal(str(payload.get("amount", "")))
    except (InvalidOperation, ValueError):
        return json_error("invalid amount")

    item = Expense(
        amount=amount,
        date=parse_date(payload.get("date")) or datetime.utcnow().date(),
        category=payload.get("category", "").strip(),
        notes=payload.get("notes", "").strip(),
        user_id=user.id,
    )
    if not item.category:
        return json_error("category required")
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id}), 201


@app.put("/api/expenses/<int:item_id>")
def update_expense(item_id: int):
    user = require_auth()
    item = Expense.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    payload = request.get_json(force=True)
    if "amount" in payload:
        try:
            item.amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError):
            return json_error("invalid amount")
    item.date = parse_date(payload.get("date")) if "date" in payload else item.date
    item.category = payload.get("category", item.category).strip()
    item.notes = payload.get("notes", item.notes)
    db.session.commit()
    return jsonify({"message": "updated"})


@app.delete("/api/expenses/<int:item_id>")
def delete_expense(item_id: int):
    user = require_auth()
    item = Expense.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


@app.get("/api/notes")
def list_notes():
    user = require_auth()
    q = request.args.get("q", "").strip()
    query = Note.query.filter_by(user_id=user.id)
    if q:
        query = query.filter((Note.title.ilike(f"%{q}%")) | (Note.content.ilike(f"%{q}%")))
    items = query.order_by(Note.created_at.desc()).all()
    return jsonify([{"id": n.id, "title": n.title, "content": n.content} for n in items])


@app.post("/api/notes")
def create_note():
    user = require_auth()
    payload = request.get_json(force=True)
    item = Note(
        title=payload.get("title", "").strip(),
        content=payload.get("content", "").strip(),
        user_id=user.id,
    )
    if not item.title or not item.content:
        return json_error("title and content are required")
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id}), 201


@app.put("/api/notes/<int:item_id>")
def update_note(item_id: int):
    user = require_auth()
    item = Note.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    payload = request.get_json(force=True)
    item.title = payload.get("title", item.title).strip()
    item.content = payload.get("content", item.content).strip()
    db.session.commit()
    return jsonify({"message": "updated"})


@app.delete("/api/notes/<int:item_id>")
def delete_note(item_id: int):
    user = require_auth()
    item = Note.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


@app.get("/api/confidential-details")
def list_confidential_details():
    user = require_auth()
    q = request.args.get("q", "").strip()
    query = ConfidentialDetail.query.filter_by(user_id=user.id)
    if q:
        query = query.filter(ConfidentialDetail.title.ilike(f"%{q}%"))
    items = query.order_by(ConfidentialDetail.created_at.desc()).all()

    response = []
    for c in items:
        try:
            decrypted = fernet.decrypt(c.encrypted_value.encode()).decode()
        except InvalidToken:
            decrypted = "[decryption failed: invalid key]"
        response.append({"id": c.id, "title": c.title, "value": decrypted})
    return jsonify(response)


@app.post("/api/confidential-details")
def create_confidential_detail():
    user = require_auth()
    payload = request.get_json(force=True)
    title = payload.get("title", "").strip()
    value = payload.get("value", "")
    if not title or not value:
        return json_error("title and value are required")
    encrypted = fernet.encrypt(value.encode()).decode()
    item = ConfidentialDetail(title=title, encrypted_value=encrypted, user_id=user.id)
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id}), 201


@app.put("/api/confidential-details/<int:item_id>")
def update_confidential_detail(item_id: int):
    user = require_auth()
    item = ConfidentialDetail.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    payload = request.get_json(force=True)
    if "title" in payload:
        item.title = payload["title"].strip()
    if "value" in payload:
        item.encrypted_value = fernet.encrypt(payload["value"].encode()).decode()
    db.session.commit()
    return jsonify({"message": "updated"})


@app.delete("/api/confidential-details/<int:item_id>")
def delete_confidential_detail(item_id: int):
    user = require_auth()
    item = ConfidentialDetail.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


@app.cli.command("init-db")
def init_db_command():
    """Create all database tables."""
    db.create_all()
    print("Database initialized")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
