"""routes/reports.py — Attendance reports & exports."""

from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import (User, UserRole, Course, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus)
from database import db
from datetime import datetime
import csv, io

reports_bp = Blueprint('reports', __name__)


def _attendance_rows(course_id=None, faculty_id=None, student_id=None,
                     date_from=None, date_to=None):
    q = (AttendanceRecord.query
         .join(Session)
         .join(Course, Session.course_id == Course.id)
         .join(User, AttendanceRecord.student_id == User.id))
    if course_id:
        q = q.filter(Session.course_id == course_id)
    if faculty_id:
        q = q.filter(Course.faculty_id == faculty_id)
    if student_id:
        q = q.filter(AttendanceRecord.student_id == student_id)
    if date_from:
        q = q.filter(Session.scheduled_start >= date_from)
    if date_to:
        q = q.filter(Session.scheduled_start <= date_to)
    return q.order_by(Session.scheduled_start.desc()).all()


@reports_bp.get('/summary')
@jwt_required()
def summary():
    role = get_jwt().get('role')
    uid  = int(get_jwt_identity())

    course_id  = request.args.get('course_id', type=int)
    faculty_id = request.args.get('faculty_id', type=int)
    student_id = request.args.get('student_id', type=int)

    # Students only see their own data
    if role == 'student':
        student_id = uid
    elif role == 'faculty':
        faculty_id = uid

    records = _attendance_rows(course_id=course_id, faculty_id=faculty_id,
                                student_id=student_id)
    total   = len(records) or 1
    counts  = {s.value: 0 for s in AttendanceStatus}
    for r in records:
        counts[r.status.value] += 1

    return jsonify(
        total=total,
        present=counts['present'],
        absent=counts['absent'],
        late=counts['late'],
        excused=counts['excused'],
        present_pct=round(counts['present'] / total * 100, 1),
        absent_pct=round(counts['absent']  / total * 100, 1),
    )


@reports_bp.get('/by-course')
@jwt_required()
def by_course():
    role       = get_jwt().get('role')
    uid        = int(get_jwt_identity())
    faculty_id = uid if role == 'faculty' else request.args.get('faculty_id', type=int)

    courses = (Course.query.filter_by(faculty_id=faculty_id, is_active=True).all()
               if faculty_id else Course.query.filter_by(is_active=True).all())
    result = []
    for course in courses:
        total   = (AttendanceRecord.query.join(Session)
                   .filter(Session.course_id == course.id).count()) or 1
        present = (AttendanceRecord.query.join(Session)
                   .filter(Session.course_id == course.id,
                           AttendanceRecord.status == AttendanceStatus.present).count())
        result.append({
            'course': course.to_dict(),
            'total_records': total,
            'present': present,
            'pct': round(present / total * 100, 1),
        })
    return jsonify(result)


@reports_bp.get('/by-student')
@jwt_required()
def by_student():
    role      = get_jwt().get('role')
    course_id = request.args.get('course_id', type=int)
    if role == 'student':
        return jsonify(error='Access denied.'), 403

    students = User.query.filter_by(role=UserRole.student, is_active=True).all()
    result   = []
    for s in students:
        q = AttendanceRecord.query.filter_by(student_id=s.id)
        if course_id:
            q = q.join(Session).filter(Session.course_id == course_id)
        total   = q.count() or 1
        present = q.filter(AttendanceRecord.status == AttendanceStatus.present).count()
        result.append({
            'student': s.to_dict(),
            'total': total,
            'present': present,
            'pct': round(present / total * 100, 1),
        })
    result.sort(key=lambda x: x['pct'])
    return jsonify(result)


@reports_bp.get('/export/csv')
@jwt_required()
def export_csv():
    role = get_jwt().get('role')
    uid  = int(get_jwt_identity())

    course_id  = request.args.get('course_id', type=int)
    student_id = uid if role == 'student' else request.args.get('student_id', type=int)
    faculty_id = uid if role == 'faculty' else None

    records = _attendance_rows(course_id=course_id, faculty_id=faculty_id,
                                student_id=student_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Student ID', 'Student Name', 'Course Code', 'Course Name',
                     'Session Date', 'Status', 'Check-in Time', 'QR Verified', 'GPS Verified'])
    for r in records:
        writer.writerow([
            r.student.user_id if r.student else '',
            r.student.full_name if r.student else '',
            r.session.course.code if r.session and r.session.course else '',
            r.session.course.name if r.session and r.session.course else '',
            r.session.scheduled_start.strftime('%Y-%m-%d %H:%M') if r.session else '',
            r.status.value,
            r.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if r.check_in_time else '',
            r.qr_verified,
            r.gps_verified,
        ])

    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=attendance_report.csv'}
    )
