# Smart Attendance System — Backend

A full-featured Flask REST API backend for the **Hybrid QR + GPS Attendance** system.

---

## Quick Start (one command)

```bash
python start.py
```

`start.py` will:
1. Check Python ≥ 3.9
2. Create a `venv/` virtual environment
3. Install all dependencies
4. Seed the database with demo data
5. Launch Flask at **http://localhost:5000**

Then open **http://localhost:5000** in your browser — it serves the frontend directly.

---

## Folder Layout

```
backend/
├── app.py               # Flask app factory + entry point
├── config.py            # All configuration variables
├── database.py          # SQLAlchemy db instance
├── seed.py              # Demo data seeder (runs once on first launch)
├── start.py             # One-click launcher (creates venv + installs deps)
├── requirements.txt     # Python dependencies
├── models/
│   └── __init__.py      # All ORM models (User, Course, Session, …)
├── routes/
│   ├── auth.py          # POST /api/auth/login  (login / logout / me)
│   ├── admin.py         # GET|POST|PUT|DELETE /api/admin/…
│   ├── faculty.py       # GET /api/faculty/…
│   ├── student.py       # GET|POST /api/student/…
│   ├── sessions.py      # Full session lifecycle + QR + GPS check-in
│   ├── reports.py       # Attendance reports + CSV export
│   ├── settings.py      # GET|POST /api/settings/…
│   └── audit.py         # GET /api/audit/logs
└── attendance.db        # SQLite file (auto-created on first run)
```

Place the **frontend/** folder next to **backend/** so Flask can serve it:

```
project/
├── backend/     ← this folder
└── frontend/    ← your HTML/CSS files
```

---

## Demo Credentials

| Role    | User ID       | Password     | Redirects to           |
|---------|---------------|--------------|------------------------|
| Admin   | `admin1`      | `admin123`   | Admin Dashboard        |
| Faculty | `faculty1`    | `teach123`   | Faculty Dashboard      |
| Student | `student1`    | `password123`| Student Dashboard      |
| New Std | `student_new` | `welcome123` | Enrollment Page        |

---

## API Reference

### Authentication

| Method | Endpoint                    | Description                  |
|--------|-----------------------------|------------------------------|
| POST   | `/api/auth/login`           | Login → returns JWT token    |
| POST   | `/api/auth/logout`          | Logout (audited)             |
| GET    | `/api/auth/me`              | Current user profile         |
| POST   | `/api/auth/change-password` | Change password              |

**Login request body:**
```json
{ "userId": "admin1", "password": "admin123" }
```

**Login response:**
```json
{
  "access_token": "eyJ...",
  "role": "admin",
  "full_name": "Alex Admin",
  "first_login": false,
  "redirect": "/admin_dashboard.html"
}
```

All protected endpoints require the header:
```
Authorization: Bearer <access_token>
```

---

### Admin Endpoints

| Method | Endpoint                            | Description                    |
|--------|-------------------------------------|--------------------------------|
| GET    | `/api/admin/kpi/overall-attendance` | Overall attendance %           |
| GET    | `/api/admin/kpi/active-sessions`    | Active session count           |
| GET    | `/api/admin/kpi/absentees-today`    | Today's absentees              |
| GET    | `/api/admin/kpi/overrides-today`    | Manual overrides today         |
| GET    | `/api/admin/analytics/trends`       | Weekly attendance trend (8wks) |
| GET    | `/api/admin/analytics/low-attendance` | At-risk students list        |
| GET    | `/api/admin/users`                  | List all users (`?role=`)      |
| POST   | `/api/admin/users`                  | Create user                    |
| PUT    | `/api/admin/users/<id>`             | Update user                    |
| DELETE | `/api/admin/users/<id>`             | Deactivate user (soft-delete)  |
| GET    | `/api/admin/courses`                | List courses                   |
| POST   | `/api/admin/courses`                | Create course                  |
| PUT    | `/api/admin/courses/<id>`           | Update course                  |
| DELETE | `/api/admin/courses/<id>`           | Archive course                 |
| GET    | `/api/admin/locations`              | List locations                 |
| POST   | `/api/admin/locations`              | Create location                |
| PUT    | `/api/admin/locations/<id>`         | Update location                |
| POST   | `/api/admin/enroll`                 | Enroll student in course       |
| DELETE | `/api/admin/enroll`                 | Unenroll student               |

---

### Sessions & Attendance

| Method | Endpoint                          | Description                      |
|--------|-----------------------------------|----------------------------------|
| GET    | `/api/sessions/`                  | List sessions (role-filtered)    |
| POST   | `/api/sessions/`                  | Create session (faculty/admin)   |
| POST   | `/api/sessions/<id>/start`        | Start session → generates QR     |
| POST   | `/api/sessions/<id>/close`        | Close session                    |
| GET    | `/api/sessions/<id>/qr`           | Get current QR token (rotates)   |
| POST   | `/api/sessions/<id>/checkin`      | Student check-in (QR + GPS)      |
| GET    | `/api/sessions/<id>/attendance`   | Full attendance list for session |

**Check-in request body:**
```json
{
  "qr_token": "abc123...",
  "latitude": 28.3670,
  "longitude": 77.3220
}
```

---

### Faculty

| Method | Endpoint                              | Description                |
|--------|---------------------------------------|----------------------------|
| GET    | `/api/faculty/dashboard`              | Dashboard summary + stats  |
| GET    | `/api/faculty/my-courses`             | Faculty's active courses   |
| GET    | `/api/faculty/courses/<id>/students`  | Students + attendance %    |
| GET    | `/api/faculty/at-risk`                | At-risk students list      |
| POST   | `/api/faculty/attendance/override`    | Override attendance status |

---

### Student

| Method | Endpoint                          | Description               |
|--------|-----------------------------------|---------------------------|
| GET    | `/api/student/dashboard`          | Dashboard + course stats  |
| GET    | `/api/student/attendance-history` | Attendance history        |
| GET    | `/api/student/active-sessions`    | Active sessions to join   |
| POST   | `/api/student/enroll`             | Self-enroll in a course   |

---

### Reports

| Method | Endpoint                  | Description                    |
|--------|---------------------------|--------------------------------|
| GET    | `/api/reports/summary`    | Overall attendance summary     |
| GET    | `/api/reports/by-course`  | Attendance breakdown by course |
| GET    | `/api/reports/by-student` | Attendance breakdown by student|
| GET    | `/api/reports/export/csv` | Download CSV report            |

---

### Settings

| Method | Endpoint                       | Description                  |
|--------|--------------------------------|------------------------------|
| GET    | `/api/settings/`               | All settings                 |
| GET    | `/api/settings/attendance`     | Attendance settings          |
| GET    | `/api/settings/notifications`  | Notification settings        |
| POST   | `/api/settings/`               | Bulk update settings (admin) |
| PUT    | `/api/settings/<key>`          | Update single setting (admin)|

---

### Audit

| Method | Endpoint           | Description                        |
|--------|--------------------|------------------------------------|
| GET    | `/api/audit/logs`  | Paginated audit log (admin only)   |
| POST   | `/api/audit/log`   | Write a frontend audit event       |

---

### Other

| Method | Endpoint       | Description        |
|--------|----------------|--------------------|
| GET    | `/api/programs`| List of programs   |

---

## Environment Variables

| Variable              | Default                | Description                     |
|-----------------------|------------------------|---------------------------------|
| `DATABASE_URL`        | `sqlite:///attendance.db` | SQLAlchemy database URL      |
| `JWT_SECRET_KEY`      | `dev-secret-…`         | JWT signing key (change in prod)|
| `QR_ROTATION_SECONDS` | `60`                   | QR code rotation interval       |
| `GEOFENCE_RADIUS_M`   | `150`                  | Default GPS geofence radius (m) |
| `MIN_ATTENDANCE_PERCENT` | `75`               | Minimum attendance threshold    |
| `AT_RISK_THRESHOLD`   | `80`                   | At-risk alert threshold         |

---

## Production Notes

- Replace `sqlite:///attendance.db` with PostgreSQL for multi-server deployments.
- Set a strong `JWT_SECRET_KEY` and `SECRET_KEY` from environment variables.
- Use **gunicorn** or **uWSGI** instead of the Flask dev server.
- Serve the frontend via Nginx (reverse-proxy `/api` to Flask).
