import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Database ──────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "attendance.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ───────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ── QR Code ───────────────────────────────────────────────────
    QR_ROTATION_SECONDS = int(os.environ.get('QR_ROTATION_SECONDS', 60))

    # ── GPS Geofence ──────────────────────────────────────────────
    DEFAULT_GEOFENCE_RADIUS_M = int(os.environ.get('GEOFENCE_RADIUS_M', 150))

    # ── Attendance thresholds ────────────────────────────────────
    MIN_ATTENDANCE_PERCENT = int(os.environ.get('MIN_ATTENDANCE_PERCENT', 75))
    AT_RISK_THRESHOLD = int(os.environ.get('AT_RISK_THRESHOLD', 80))

    # ── General ───────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'flask-secret-dev')
    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
