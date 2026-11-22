# Frontdesk – Customer Support Ticket Management System

## Project Overview

Frontdesk is a web-based Customer Support Ticket Management System developed using Python Flask and PostgreSQL.

The system helps support teams create, manage, assign, and track customer complaints and service requests through a centralized dashboard.

## Technologies Used

- **Frontend:** HTML, CSS, Bootstrap
- **Backend:** Python Flask
- **Database:** PostgreSQL
- **Authentication:** Flask-Login
- **ORM:** Flask-SQLAlchemy

## Features

1. User login and authentication.
2. Dashboard displaying ticket statistics.
3. Create and view customer support tickets.
4. Ticket priorities: Urgent, Medium, and Small.
5. Ticket status management.
6. Assign tickets using the Take This Ticket feature.
7. Public replies and private internal notes.
8. Ticket activity and audit history.
9. SLA target information based on ticket priority.
10. PostgreSQL database integration.

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd FRONTDESK
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
DB_USER=postgres
DB_PASSWORD=YOUR_DATABASE_PASSWORD
DB_HOST=localhost
DB_PORT=5432
DB_NAME=frontdesk_db
SECRET_KEY=YOUR_SECRET_KEY
```

Use your own PostgreSQL credentials. Do not upload the `.env` file to GitHub.

### 6. Create the PostgreSQL database

Create a database named:

```sql
CREATE DATABASE frontdesk_db;
```

### 7. Run the application

```bash
python app.py
```

Open the application in your browser:

http://127.0.0.1:5000

## Current Limitations and Future Improvements

- SLA information currently displays target response and resolution times based on priority. Full working-hour calculations, holiday exclusions, and automatic pause/resume handling are not implemented.
- Automatic customer email notifications are not implemented.
- Automatic ticket closure after customer inactivity is not implemented.
- Reopening rules and time-based restrictions can be enhanced.
- Audit history is implemented at the application level; database-level immutable audit protection is not implemented.
- Additional security controls, testing, and production deployment configuration can be improved.

## Conclusion

Frontdesk provides a basic centralized platform for managing customer support tickets, tracking their status, assigning responsibilities, and maintaining communication and activity records. It can be extended with advanced SLA automation, notifications, and additional administrative features.