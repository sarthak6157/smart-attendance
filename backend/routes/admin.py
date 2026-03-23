"""routes/admin.py — Admin dashboard & management endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import (User, UserRole, Course, Location, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus, AuditLog, enrollment)
from database import db
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from functools import wraps
import random

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get('role') != 'admin':
            return jsonify(error='Admin access required.'), 403
        return fn(*args, **kwargs)
    return wrapper


# ── KPI Cards ────────────────────────────────────────────────────

@admin_bp.get('/kpi/overall-attendance')
@admin_required
def kpi_overall():
    total   = AttendanceRecord.query.count() or 1
    present = AttendanceRecord.query.filter_by(status=AttendanceStatus.present).count()
    pct     = round(present / total * 100, 1)
    return jsonify(value=pct, label='Overall Attendance %', trend='+2.1%')


@admin_bp.get('/kpi/active-sessions')
@admin_required
def kpi_active():
    count = Session.query.filter_by(status=SessionStatus.active).count()
    return jsonify(value=count, label='Active Sessions Now')


@admin_bp.get('/kpi/absentees-today')
@admin_required
def kpi_absentees():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (AttendanceRecord.query
             .join(Session)
             .filter(Session.scheduled_start >= today_start,
                     AttendanceRecord.status == AttendanceStatus.absent)
             .count())
    return jsonify(value=count, label='Absentees Today')


@admin_bp.get('/kpi/overrides-today')
@admin_required
def kpi_overrides():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (AttendanceRecord.query
             .filter(AttendanceRecord.override_by != None,
                     AttendanceRecord.updated_at >= today_start)
             .count())
    return jsonify(value=count, label='Manual Overrides Today')


# ── Analytics ───────────────────────────────────────────────────

@admin_bp.get('/analytics/trends')
@admin_required
def attendance_trends():
    """Weekly attendance % for the last 8 weeks."""
    weeks = []
    for i in range(7, -1, -1):
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        week_end   = week_start + timedelta(weeks=1)
        total   = (AttendanceRecord.query.join(Session)
                   .filter(Session.scheduled_start >= week_start,
                           Session.scheduled_start < week_end).count()) or 1
        present = (AttendanceRecord.query.join(Session)
                   .filter(Session.scheduled_start >= week_start,
                           Session.scheduled_start < week_end,
                           AttendanceRecord.status == AttendanceStatus.present).count())
        weeks.append({'week': week_start.strftime('W%W'), 'pct': round(present/total*100, 1)})
    return jsonify(weeks)


@admin_bp.get('/analytics/low-attendance')
@admin_required
def low_attendance():
    """Students below 80 % attendance (across all courses)."""
    threshold = float(request.args.get('threshold', 80))
    students  = User.query.filter_by(role=UserRole.student, is_active=True).all()
    at_risk   = []
    for s in students:
        total   = s.attendance_records.count() or 1
        present = s.attendance_records.filter_by(status=AttendanceStatus.present).count()
        pct     = round(present / total * 100, 1)
        if pct < threshold:
            at_risk.append({'id': s.id, 'name': s.full_name,
                            'user_id': s.user_id, 'pct': pct})
    at_risk.sort(key=lambda x: x['pct'])
    return jsonify(at_risk)


# ── Users CRUD ───────────────────────────────────────────────────

@admin_bp.get('/users')
@admin_required
def list_users():
    role = request.args.get('role')
    q    = User.query
    if role:
        q = q.filter_by(role=role)
    users = q.order_by(User.full_name).all()
    return jsonify([u.to_dict() for u in users])


@admin_bp.post('/users')
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    required = ('user_id', 'password', 'full_name', 'email', 'role')
    if not all(data.get(f) for f in required):
        return jsonify(error=f'Fields required: {", ".join(required)}'), 400
    if User.query.filter_by(user_id=data['user_id']).first():
        return jsonify(error='user_id already exists.'), 409
    user = User(
        user_id=data['user_id'],
        password_hash=generate_password_hash(data['password']),
        full_name=data['full_name'],
        email=data['email'],
        role=UserRole(data['role']),
        department=data.get('department'),
        program=data.get('program'),
        phone=data.get('phone'),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@admin_bp.put('/users/<int:uid>')
@admin_required
def update_user(uid):
    user = User.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}
    for field in ('full_name', 'email', 'department', 'program', 'phone', 'is_active'):
        if field in data:
            setattr(user, field, data[field])
    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])
    db.session.commit()
    return jsonify(user.to_dict())


@admin_bp.delete('/users/<int:uid>')
@admin_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    user.is_active = False   # soft delete
    db.session.commit()
    return jsonify(message='User deactivated.')


# ── Courses CRUD ─────────────────────────────────────────────────

@admin_bp.get('/courses')
@admin_required
def list_courses():
    courses = Course.query.filter_by(is_active=True).order_by(Course.code).all()
    return jsonify([c.to_dict() for c in courses])


@admin_bp.post('/courses')
@admin_required
def create_course():
    data = request.get_json(silent=True) or {}
    if not data.get('code') or not data.get('name'):
        return jsonify(error='code and name are required.'), 400
    course = Course(
        code=data['code'], name=data['name'],
        description=data.get('description'),
        credits=data.get('credits', 3),
        semester=data.get('semester'),
        academic_year=data.get('academic_year'),
        faculty_id=data.get('faculty_id'),
        location_id=data.get('location_id'),
    )
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201


@admin_bp.put('/courses/<int:cid>')
@admin_required
def update_course(cid):
    course = Course.query.get_or_404(cid)
    data   = request.get_json(silent=True) or {}
    for field in ('name', 'description', 'credits', 'semester',
                  'academic_year', 'faculty_id', 'location_id', 'is_active'):
        if field in data:
            setattr(course, field, data[field])
    db.session.commit()
    return jsonify(course.to_dict())


@admin_bp.delete('/courses/<int:cid>')
@admin_required
def delete_course(cid):
    course = Course.query.get_or_404(cid)
    course.is_active = False
    db.session.commit()
    return jsonify(message='Course archived.')


# ── Locations CRUD ───────────────────────────────────────────────

@admin_bp.get('/locations')
@admin_required
def list_locations():
    locs = Location.query.filter_by(is_active=True).all()
    return jsonify([l.to_dict() for l in locs])


@admin_bp.post('/locations')
@admin_required
def create_location():
    data = request.get_json(silent=True) or {}
    if not all(data.get(f) for f in ('name', 'latitude', 'longitude')):
        return jsonify(error='name, latitude, longitude required.'), 400
    loc = Location(**{k: data[k] for k in
                      ('name', 'building', 'room_number', 'latitude',
                       'longitude', 'radius_m') if k in data})
    db.session.add(loc)
    db.session.commit()
    return jsonify(loc.to_dict()), 201


@admin_bp.put('/locations/<int:lid>')
@admin_required
def update_location(lid):
    loc  = Location.query.get_or_404(lid)
    data = request.get_json(silent=True) or {}
    for field in ('name', 'building', 'room_number', 'latitude',
                  'longitude', 'radius_m', 'is_active'):
        if field in data:
            setattr(loc, field, data[field])
    db.session.commit()
    return jsonify(loc.to_dict())


# ── Enrollment management ────────────────────────────────────────

@admin_bp.post('/enroll')
@admin_required
def enroll_student():
    data       = request.get_json(silent=True) or {}
    student_id = data.get('student_id')
    course_id  = data.get('course_id')
    if not student_id or not course_id:
        return jsonify(error='student_id and course_id required.'), 400
    student = User.query.filter_by(id=student_id, role=UserRole.student).first_or_404()
    course  = Course.query.get_or_404(course_id)
    if student in course.students:
        return jsonify(error='Already enrolled.'), 409
    course.students.append(student)
    db.session.commit()
    return jsonify(message=f'{student.full_name} enrolled in {course.code}.')


@admin_bp.delete('/enroll')
@admin_required
def unenroll_student():
    data       = request.get_json(silent=True) or {}
    student_id = data.get('student_id')
    course_id  = data.get('course_id')
    student = User.query.get_or_404(student_id)
    course  = Course.query.get_or_404(course_id)
    if student not in course.students:
        return jsonify(error='Not enrolled.'), 404
    course.students.remove(student)
    db.session.commit()
    return jsonify(message='Unenrolled.')
