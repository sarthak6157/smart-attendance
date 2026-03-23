"""routes/faculty.py — Faculty dashboard endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from models import (User, UserRole, Course, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus)
from database import db
from functools import wraps

faculty_bp = Blueprint('faculty', __name__)


def faculty_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        role = get_jwt().get('role')
        if role not in ('faculty', 'admin'):
            return jsonify(error='Faculty access required.'), 403
        return fn(*args, **kwargs)
    return wrapper


@faculty_bp.get('/dashboard')
@faculty_required
def dashboard():
    uid     = int(get_jwt_identity())
    faculty = User.query.get_or_404(uid)
    courses = Course.query.filter_by(faculty_id=uid, is_active=True).all()

    # Summary stats
    course_ids = [c.id for c in courses]
    total_sessions = Session.query.filter(Session.course_id.in_(course_ids)).count()
    active_sessions = Session.query.filter(
        Session.course_id.in_(course_ids),
        Session.status == SessionStatus.active).count()

    total_records = (AttendanceRecord.query
                     .join(Session)
                     .filter(Session.course_id.in_(course_ids)).count()) or 1
    present = (AttendanceRecord.query
               .join(Session)
               .filter(Session.course_id.in_(course_ids),
                       AttendanceRecord.status == AttendanceStatus.present).count())

    return jsonify(
        faculty=faculty.to_dict(),
        courses=[c.to_dict() for c in courses],
        stats={
            'total_courses': len(courses),
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'overall_attendance_pct': round(present / total_records * 100, 1),
        }
    )


@faculty_bp.get('/my-courses')
@faculty_required
def my_courses():
    uid     = int(get_jwt_identity())
    courses = Course.query.filter_by(faculty_id=uid, is_active=True).all()
    return jsonify([c.to_dict() for c in courses])


@faculty_bp.get('/courses/<int:cid>/students')
@faculty_required
def course_students(cid):
    course   = Course.query.get_or_404(cid)
    students = course.students.all()
    result   = []
    for s in students:
        total   = (AttendanceRecord.query
                   .join(Session)
                   .filter(Session.course_id == cid,
                           AttendanceRecord.student_id == s.id).count()) or 1
        present = (AttendanceRecord.query
                   .join(Session)
                   .filter(Session.course_id == cid,
                           AttendanceRecord.student_id == s.id,
                           AttendanceRecord.status == AttendanceStatus.present).count())
        info = s.to_dict()
        info['attendance_pct'] = round(present / total * 100, 1)
        result.append(info)
    return jsonify(result)


@faculty_bp.get('/at-risk')
@faculty_required
def at_risk_students():
    uid       = int(get_jwt_identity())
    threshold = float(request.args.get('threshold', 75))
    courses   = Course.query.filter_by(faculty_id=uid, is_active=True).all()
    at_risk   = []

    for course in courses:
        for student in course.students.all():
            total   = (AttendanceRecord.query
                       .join(Session)
                       .filter(Session.course_id == course.id,
                               AttendanceRecord.student_id == student.id).count()) or 1
            present = (AttendanceRecord.query
                       .join(Session)
                       .filter(Session.course_id == course.id,
                               AttendanceRecord.student_id == student.id,
                               AttendanceRecord.status == AttendanceStatus.present).count())
            pct = round(present / total * 100, 1)
            if pct < threshold:
                at_risk.append({
                    'student': student.to_dict(),
                    'course': course.to_dict(),
                    'attendance_pct': pct,
                    'sessions_missed': total - present,
                })

    at_risk.sort(key=lambda x: x['attendance_pct'])
    return jsonify(at_risk)


@faculty_bp.post('/attendance/override')
@faculty_required
def override_attendance():
    uid  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    record = AttendanceRecord.query.get_or_404(data.get('record_id'))
    record.status          = AttendanceStatus(data.get('status', 'present'))
    record.override_by     = uid
    record.override_reason = data.get('reason', '')
    db.session.commit()
    return jsonify(record.to_dict())
