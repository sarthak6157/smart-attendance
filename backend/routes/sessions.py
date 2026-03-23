"""routes/sessions.py — Session management + QR/GPS attendance."""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import (User, Course, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus, Location, AuditLog)
from database import db
from datetime import datetime, timedelta
import secrets, math

sessions_bp = Blueprint('sessions', __name__)


# ── Helpers ──────────────────────────────────────────────────────

def haversine_distance(lat1, lng1, lat2, lng2):
    """Return distance in metres between two GPS coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a    = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def refresh_qr(session: Session):
    rotation = current_app.config.get('QR_ROTATION_SECONDS', 60)
    session.qr_token      = secrets.token_urlsafe(24)
    session.qr_expires_at = datetime.utcnow() + timedelta(seconds=rotation)
    db.session.commit()
    return session


# ── Session CRUD ─────────────────────────────────────────────────

@sessions_bp.get('/')
@jwt_required()
def list_sessions():
    uid  = int(get_jwt_identity())
    role = get_jwt().get('role')
    q    = Session.query

    if role == 'faculty':
        q = q.filter_by(faculty_id=uid)
    elif role == 'student':
        # sessions for courses the student is enrolled in
        user    = User.query.get(uid)
        cids    = [c.id for c in user.enrolled_courses.all()]
        q       = q.filter(Session.course_id.in_(cids))

    status = request.args.get('status')
    if status:
        q = q.filter_by(status=SessionStatus(status))

    sessions = q.order_by(Session.scheduled_start.desc()).limit(50).all()
    return jsonify([s.to_dict() for s in sessions])


@sessions_bp.post('/')
@jwt_required()
def create_session():
    uid  = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role not in ('faculty', 'admin'):
        return jsonify(error='Not authorised.'), 403

    data = request.get_json(silent=True) or {}
    required = ('course_id', 'scheduled_start', 'scheduled_end')
    if not all(data.get(f) for f in required):
        return jsonify(error=f'Required: {", ".join(required)}'), 400

    sess = Session(
        course_id=data['course_id'],
        faculty_id=uid,
        location_id=data.get('location_id'),
        scheduled_start=datetime.fromisoformat(data['scheduled_start']),
        scheduled_end=datetime.fromisoformat(data['scheduled_end']),
        notes=data.get('notes', ''),
        status=SessionStatus.scheduled,
    )
    db.session.add(sess)
    db.session.commit()
    return jsonify(sess.to_dict()), 201


@sessions_bp.post('/<int:sid>/start')
@jwt_required()
def start_session(sid):
    role = get_jwt().get('role')
    if role not in ('faculty', 'admin'):
        return jsonify(error='Not authorised.'), 403

    sess = Session.query.get_or_404(sid)
    if sess.status != SessionStatus.scheduled:
        return jsonify(error='Session is not in scheduled state.'), 409

    sess.status       = SessionStatus.active
    sess.actual_start = datetime.utcnow()
    refresh_qr(sess)
    db.session.commit()
    return jsonify(sess.to_dict())


@sessions_bp.post('/<int:sid>/close')
@jwt_required()
def close_session(sid):
    role = get_jwt().get('role')
    if role not in ('faculty', 'admin'):
        return jsonify(error='Not authorised.'), 403

    sess = Session.query.get_or_404(sid)
    if sess.status != SessionStatus.active:
        return jsonify(error='Session is not active.'), 409

    sess.status     = SessionStatus.closed
    sess.actual_end = datetime.utcnow()
    sess.qr_token   = None
    db.session.commit()
    return jsonify(sess.to_dict())


# ── QR Code ──────────────────────────────────────────────────────

@sessions_bp.get('/<int:sid>/qr')
@jwt_required()
def get_qr(sid):
    """Return the current QR token. Rotates automatically if expired."""
    role = get_jwt().get('role')
    if role not in ('faculty', 'admin'):
        return jsonify(error='Not authorised.'), 403

    sess = Session.query.get_or_404(sid)
    if sess.status != SessionStatus.active:
        return jsonify(error='Session is not active.'), 409

    now = datetime.utcnow()
    if not sess.qr_token or (sess.qr_expires_at and sess.qr_expires_at <= now):
        refresh_qr(sess)

    return jsonify(
        session_id=sess.id,
        qr_token=sess.qr_token,
        expires_at=sess.qr_expires_at.isoformat(),
        rotation_seconds=current_app.config.get('QR_ROTATION_SECONDS', 60),
    )


# ── Check-in (student) ──────────────────────────────────────────

@sessions_bp.post('/<int:sid>/checkin')
@jwt_required()
def check_in(sid):
    """Student submits QR token + GPS coordinates to mark attendance."""
    uid  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    sess = Session.query.get_or_404(sid)
    if sess.status != SessionStatus.active:
        return jsonify(error='Session is not active.'), 409

    # Verify student is enrolled
    student = User.query.get_or_404(uid)
    course  = sess.course
    if not course.students.filter_by(id=uid).first():
        return jsonify(error='You are not enrolled in this course.'), 403

    now = datetime.utcnow()

    # ── QR verification ──────────────────────────────────────────
    qr_ok = False
    submitted_token = data.get('qr_token', '')
    if (submitted_token and sess.qr_token and
            submitted_token == sess.qr_token and
            sess.qr_expires_at and sess.qr_expires_at > now):
        qr_ok = True

    # ── GPS verification ─────────────────────────────────────────
    gps_ok = False
    student_lat = data.get('latitude')
    student_lng = data.get('longitude')
    if student_lat is not None and student_lng is not None and sess.location:
        loc  = sess.location
        dist = haversine_distance(student_lat, student_lng, loc.latitude, loc.longitude)
        gps_ok = dist <= loc.radius_m

    if not qr_ok and not gps_ok:
        return jsonify(error='Attendance verification failed (invalid QR and GPS out of range).'), 422

    # Determine status
    grace = timedelta(minutes=10)
    if sess.actual_start and now > sess.actual_start + grace:
        status = AttendanceStatus.late
    else:
        status = AttendanceStatus.present

    # Upsert record
    record = (AttendanceRecord.query
              .filter_by(session_id=sid, student_id=uid).first())
    if not record:
        record = AttendanceRecord(session_id=sid, student_id=uid)
        db.session.add(record)

    record.status        = status
    record.check_in_time = now
    record.check_in_lat  = student_lat
    record.check_in_lng  = student_lng
    record.qr_verified   = qr_ok
    record.gps_verified  = gps_ok
    db.session.commit()

    return jsonify(record.to_dict()), 200


# ── Attendance list for a session ─────────────────────────────────

@sessions_bp.get('/<int:sid>/attendance')
@jwt_required()
def session_attendance(sid):
    role = get_jwt().get('role')
    if role not in ('faculty', 'admin'):
        return jsonify(error='Not authorised.'), 403

    sess    = Session.query.get_or_404(sid)
    records = sess.attendance_records.all()
    return jsonify({
        'session': sess.to_dict(),
        'records': [r.to_dict() for r in records],
    })
