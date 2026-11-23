
import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)

from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text, update
from sqlalchemy.engine import URL
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "frontdesk-secret-key")

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME")
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------- DATABASE MODELS ----------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="agent", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(30), default="Open")
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    waiting_since = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    message_body = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- COMMON FUNCTIONS ----------------

def record_audit(ticket_id, action, details):
    log = AuditLog(
        ticket_id=ticket_id,
        actor_id=current_user.id,
        action=action,
        details=details
    )
    db.session.add(log)


# ---------------- LOGIN ----------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def home():
    return """
    <h1>Welcome to Frontdesk!</h1>
    <h2>Customer Support Ticket Management System</h2>
    <p>PostgreSQL Connected Successfully!</p>
    <a href="/login">Login</a>
    """


@app.route("/setup", methods=["GET", "POST"])
def setup():

    if User.query.count() > 0:
        return "Admin account already created. Please log in."

    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or len(password) < 8:
            flash("Enter valid details. Password must be at least 8 characters.")
            return redirect(url_for("setup"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin"
        )

        db.session.add(user)
        db.session.commit()

        flash("Admin account created successfully!")
        return redirect(url_for("login"))

    return """
    <h2>Create Frontdesk Admin Account</h2>
    <form method="POST">
        <p>Username: <input name="username" required></p>
        <p>Email: <input type="email" name="email" required></p>
        <p>Password: <input type="password" name="password" minlength="8" required></p>
        <button type="submit">Create Admin</button>
    </form>
    """


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    total_tickets = Ticket.query.count()

    open_tickets = Ticket.query.filter_by(status="Open").count()

    in_progress_tickets = Ticket.query.filter_by(
        status="In Progress"
    ).count()

    waiting_tickets = Ticket.query.filter_by(
        status="Waiting for Customer"
    ).count()

    resolved_tickets = Ticket.query.filter_by(
        status="Resolved"
    ).count()

    return render_template(
        "dashboard.html",
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        waiting_tickets=waiting_tickets,
        resolved_tickets=resolved_tickets
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- TICKET LIST ----------------

@app.route("/tickets")
@login_required
def tickets():

    all_tickets = Ticket.query.order_by(
        Ticket.created_at.desc()
    ).all()

    return render_template("tickets.html", tickets=all_tickets)


# ---------------- CREATE TICKET ----------------

@app.route("/tickets/create", methods=["POST"])
@login_required
def create_ticket():

    customer_name = request.form.get("customer_name", "").strip()
    customer_email = request.form.get("customer_email", "").strip()
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "Medium")

    if not all([
        customer_name,
        customer_email,
        subject,
        description
    ]):
        flash("Please fill in all ticket details.")
        return redirect(url_for("tickets"))

    if priority not in ["Urgent", "Medium", "Small"]:
        flash("Invalid ticket priority.")
        return redirect(url_for("tickets"))

    ticket = Ticket(
        ticket_number="FD-" + uuid.uuid4().hex[:8].upper(),
        customer_name=customer_name,
        customer_email=customer_email,
        subject=subject,
        description=description,
        priority=priority,
        status="Open"
    )

    db.session.add(ticket)
    db.session.flush()

    record_audit(
        ticket.id,
        "Ticket Created",
        "Ticket created with priority: " + priority
    )

    db.session.commit()

    flash("Ticket created successfully!")
    return redirect(url_for("tickets"))


# ---------------- TICKET DETAILS ----------------

@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):

    ticket = db.get_or_404(Ticket, ticket_id)

    agents = User.query.order_by(User.username).all()

    # This is an agent-only page. Internal notes are not
    # exposed through any customer-facing route or API.
    messages = Message.query.filter_by(
        ticket_id=ticket.id
    ).order_by(Message.created_at.asc()).all()

    audit_logs = AuditLog.query.filter_by(
        ticket_id=ticket.id
    ).order_by(AuditLog.created_at.desc()).all()

    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        agents=agents,
        messages=messages,
        audit_logs=audit_logs
    )


# ---------------- TAKE UNASSIGNED TICKET ----------------

@app.route("/tickets/<int:ticket_id>/take", methods=["POST"])
@login_required
def take_ticket(ticket_id):

    # One atomic database update ensures only one agent
    # can take an unassigned ticket successfully.
    result = db.session.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.assigned_to.is_(None),
            Ticket.status.notin_(["Resolved", "Closed"])
        )
        .values(
            assigned_to=current_user.id,
            updated_at=datetime.utcnow()
        )
    )

    if result.rowcount == 1:
        record_audit(
            ticket_id,
            "Ticket Taken",
            current_user.username + " took the ticket."
        )
        db.session.commit()
        flash("Ticket assigned to you successfully.")
    else:
        db.session.rollback()
        flash("This ticket is already assigned or cannot be taken.")

    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


# ---------------- UPDATE TICKET ----------------

@app.route("/tickets/<int:ticket_id>/update", methods=["POST"])
@login_required
def update_ticket(ticket_id):

    # Lock the ticket row while updating it to avoid
    # simultaneous conflicting assignment changes.
    ticket = Ticket.query.filter_by(
        id=ticket_id
    ).with_for_update().first_or_404()

    new_priority = request.form.get("priority")
    new_status = request.form.get("status")
    assigned_value = request.form.get("assigned_to", "").strip()

    if new_priority not in ["Urgent", "Medium", "Small"]:
        flash("Invalid priority.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    allowed_statuses = [
        "Open", "In Progress", "Waiting Customer",
        "Resolved", "Closed"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid status.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    if assigned_value:
        try:
            new_assigned_to = int(assigned_value)
        except ValueError:
            flash("Invalid agent selection.")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))

        selected_agent = db.session.get(User, new_assigned_to)

        if not selected_agent:
            flash("Selected agent does not exist.")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    else:
        new_assigned_to = None

    # Do not allow another user to overwrite an existing
    # agent's assignment through the assignment form.
    if (
        ticket.assigned_to is not None
        and ticket.assigned_to != current_user.id
        and new_assigned_to != ticket.assigned_to
    ):
        flash("This ticket is assigned to another agent.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    if ticket.priority != new_priority:
        old_priority = ticket.priority
        ticket.priority = new_priority

        record_audit(
            ticket.id,
            "Priority Changed",
            old_priority + " changed to " + new_priority
        )

    if ticket.status != new_status:
        old_status = ticket.status
        ticket.status = new_status

        if new_status == "Waiting Customer":
            ticket.waiting_since = datetime.utcnow()
        elif old_status == "Waiting Customer":
            ticket.waiting_since = None

        if new_status == "Resolved":
            ticket.resolved_at = datetime.utcnow()
        elif old_status == "Resolved":
            ticket.resolved_at = None

        record_audit(
            ticket.id,
            "Status Changed",
            old_status + " changed to " + new_status
        )

    if ticket.assigned_to != new_assigned_to:
        old_agent = (
            db.session.get(User, ticket.assigned_to)
            if ticket.assigned_to else None
        )
        new_agent = (
            db.session.get(User, new_assigned_to)
            if new_assigned_to else None
        )

        old_name = old_agent.username if old_agent else "Unassigned"
        new_name = new_agent.username if new_agent else "Unassigned"

        ticket.assigned_to = new_assigned_to

        record_audit(
            ticket.id,
            "Assignment Changed",
            old_name + " changed to " + new_name
        )

    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Ticket updated successfully.")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


# ---------------- ADD MESSAGE ----------------

@app.route("/tickets/<int:ticket_id>/message", methods=["POST"])
@login_required
def add_message(ticket_id):

    ticket = db.get_or_404(Ticket, ticket_id)

    message_body = request.form.get("message_body", "").strip()
    message_type = request.form.get("message_type", "")

    if not message_body:
        flash("Message cannot be empty.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    if message_type not in ["public", "internal"]:
        flash("Invalid message type.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    message = Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        message_body=message_body,
        message_type=message_type
    )

    db.session.add(message)
    db.session.flush()

    if message_type == "internal":
        audit_details = "A private internal note was added."
        action_name = "Internal Note Added"
    else:
        audit_details = "A public customer reply was added."
        action_name = "Public Reply Added"

    record_audit(ticket.id, action_name, audit_details)

    db.session.commit()

    flash("Message added successfully.")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


# ---------------- DATABASE CHECK ----------------

@app.route("/database-check")
@login_required
def database_check():

    with db.engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return "PostgreSQL database connection is working!"


# ---------------- START APPLICATION ----------------

with app.app_context():
    db.create_all()

print("Frontdesk database tables are ready!")

if __name__ == "__main__":
    app.run(debug=True)