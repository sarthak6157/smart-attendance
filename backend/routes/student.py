"""routes/student.py — Student dashboard endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (User, UserRole, Course, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus, enrollment)
from database import db

student_bp = Blueprint('student', __name__)


@student_bp.get('/dashboard')
@jwt_required()
def dashboard():
    uid     = int(get_jwt_identity())
    student = User.query.get_or_404(uid)
    courses = student.enrolled_courses.filter_by(is_active=True).all()

    course_stats = []
    for course in courses:
        total   = (AttendanceRecord.query
                   .join(Session)
                   .filter(Session.course_id == course.id,
                           AttendanceRecord.student_id == uid).count()) or 1
        present = (AttendanceRecord.query
                   .join(Session)
                   .filter(Session.course_id == course.id,
                           AttendanceRecord.student_id == uid,
                           AttendanceRecord.status == AttendanceStatus.present).count())
        course_stats.append({
            'course': course.to_dict(),
            'attendance_pct': round(present / total * 100, 1),
            'sessions_attended': present,
            'sessions_total': total,
        })

    # Overall
    all_total   = student.attendance_records.count() or 1
    all_present = student.attendance_records.filter_by(
        status=AttendanceStatus.present).count()

    # Upcoming sessions
    from datetime import datetime
    upcoming = (Session.query
                .filter(Session.course_id.in_([c.id for c in courses]),
                        Session.scheduled_start > datetime.utcnow(),
                        Session.status == SessionStatus.scheduled)
                .order_by(Session.scheduled_start)
                .limit(5).all())

    return jsonify(
        student=student.to_dict(),
        course_stats=course_stats,
        overall_pct=round(all_present / all_total * 100, 1),
        upcoming_sessions=[s.to_dict() for s in upcoming],
    )


@student_bp.get('/attendance-history')
@jwt_required()
def attendance_history():
    uid     = int(get_jwt_identity())
    course_id = request.args.get('course_id', type=int)
    q = (AttendanceRecord.query
         .join(Session)
         .filter(AttendanceRecord.student_id == uid))
    if course_id:
        q = q.filter(Session.course_id == course_id)
    records = q.order_by(Session.scheduled_start.desc()).limit(100).all()
    return jsonify([r.to_dict() for r in records])


@student_bp.get('/active-sessions')
@jwt_required()
def active_sessions():
    """Active sessions the student can check in to."""
    uid     = int(get_jwt_identity())
    student = User.query.get_or_404(uid)
    cids    = [c.id for c in student.enrolled_courses.all()]
    active  = (Session.query
               .filter(Session.course_id.in_(cids),
                       Session.status == SessionStatus.active)
               .all())
    return jsonify([s.to_dict() for s in active])


@student_bp.post('/enroll')
@jwt_required()
def self_enroll():
    uid     = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}
    course_id = data.get('course_id')
    if not course_id:
        return jsonify(error='course_id required.'), 400
    student = User.query.get_or_404(uid)
    course  = Course.query.get_or_404(course_id)
    if student in course.students:
        return jsonify(error='Already enrolled.'), 409
    course.students.append(student)
    student.first_login = False
    db.session.commit()
    return jsonify(message=f'Enrolled in {course.code} — {course.name}.')
