import os
from datetime import timedelta

# Resolve the base directory for local SQLite storage
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # ── Database Configuration ─────────────────────────────────────
    # This checks for 'DATABASE_URL' (provided by Render/Postgres).
    # If not found, it falls back to your local SQLite file.
    # FIXED: Handles the 'postgres://' vs 'postgresql://' prefix issue common on some hosts.
    uri = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "attendance.db")}')
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Security & JWT ───────────────────────────────────────────
    # In production, ALWAYS set these as environment variables in Render
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret-change-in-prod')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'flask-secret-dev')
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ── Application Logic Settings ───────────────────────────────
    QR_ROTATION_SECONDS = int(os.environ.get('QR_ROTATION_SECONDS', 60))
    DEFAULT_GEOFENCE_RADIUS_M = int(os.environ.get('GEOFENCE_RADIUS_M', 150))
    MIN_ATTENDANCE_PERCENT = int(os.environ.get('MIN_ATTENDANCE_PERCENT', 75))
    AT_RISK_THRESHOLD = int(os.environ.get('AT_RISK_THRESHOLD', 80))

    # ── Debug Mode ───────────────────────────────────────────────
    # Automatically turns off debug mode in production
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
