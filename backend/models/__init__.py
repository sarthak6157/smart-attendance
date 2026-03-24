"""
models/__init__.py
All SQLAlchemy ORM models for the Smart Attendance System.
"""

from database import db
from datetime import datetime
import enum


# ─────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin   = 'admin'
    faculty = 'faculty'
    student = 'student'


class AttendanceStatus(str, enum.Enum):
    present  = 'present'
    absent   = 'absent'
    late     = 'late'
    excused  = 'excused'


class SessionStatus(str, enum.Enum):
    scheduled = 'scheduled'
    active    = 'active'
    closed    = 'closed'


# ─────────────────────────────────────────────────────────────────
# Association table: student ↔ course (enrollment)
# ─────────────────────────────────────────────────────────────────

enrollment = db.Table(
    'enrollment',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id',  db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('enrolled_at', db.DateTime, default=datetime.utcnow)
)


# ─────────────────────────────────────────────────────────────────
# User Model
# ─────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.String(64),  unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name     = db.Column(db.String(128), nullable=False)
    email         = db.Column(db.String(128), unique=True, nullable=False)
    role          = db.Column(db.Enum(UserRole), nullable=False)
    department    = db.Column(db.String(128))
    program       = db.Column(db.String(128))
    phone         = db.Column(db.String(32))
    is_active     = db.Column(db.Boolean, default=True)
    first_login   = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - lazy='dynamic' is critical for calling .count() in routes
    taught_courses = db.relationship('Course', backref='faculty', lazy='dynamic',
                                     foreign_keys='Course.faculty_id')
    enrolled_courses = db.relationship('Course', secondary=enrollment,
                                       backref=db.backref('students', lazy='dynamic'),
                                       lazy='dynamic')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic',
                                          foreign_keys='AttendanceRecord.student_id')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role.value,
            'department': self.department,
            'program': self.program,
            'phone': self.phone,
            'is_active': self.is_active,
            'first_login': self.first_login,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# Course Model
# ─────────────────────────────────────────────────────────────────

class Course(db.Model):
    __tablename__ = 'course'

    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(32),  unique=True, nullable=False)
    name          = db.Column(db.String(256), nullable=False)
    description   = db.Column(db.Text)
    credits       = db.Column(db.Integer, default=3)
    semester      = db.Column(db.String(32))
    academic_year = db.Column(db.String(16))
    faculty_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    location_id   = db.Column(db.Integer, db.ForeignKey('location.id'))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    sessions      = db.relationship('Session', backref='course', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.full_name if self.faculty else None,
            'location_id': self.location_id,
            'is_active': self.is_active,
            'student_count': self.students.count(), # Works because of lazy='dynamic' on enrollment
        }


# ─────────────────────────────────────────────────────────────────
# Location Model
# ─────────────────────────────────────────────────────────────────

class Location(db.Model):
    __tablename__ = 'location'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False)
    building    = db.Column(db.String(128))
    room_number = db.Column(db.String(32))
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    radius_m    = db.Column(db.Integer, default=150)
    is_active   = db.Column(db.Boolean, default=True)

    courses     = db.relationship('Course', backref='location', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'building': self.building,
            'room_number': self.room_number,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_m': self.radius_m,
            'is_active': self.is_active,
        }


# ─────────────────────────────────────────────────────────────────
# Session Model
# ─────────────────────────────────────────────────────────────────

class Session(db.Model):
    __tablename__ = 'session'

    id              = db.Column(db.Integer, primary_key=True)
    course_id       = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    faculty_id      = db.Column(db.Integer, db.ForeignKey('user.id'),   nullable=False)
    location_id     = db.Column(db.Integer, db.ForeignKey('location.id'))
    status          = db.Column(db.Enum(SessionStatus), default=SessionStatus.scheduled)
    scheduled_start = db.Column(db.DateTime, nullable=False)
    scheduled_end   = db.Column(db.DateTime, nullable=False)
    actual_start    = db.Column(db.DateTime)
    actual_end      = db.Column(db.DateTime)
    qr_token        = db.Column(db.String(256))
    qr_expires_at   = db.Column(db.DateTime)
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    faculty            = db.relationship('User', foreign_keys=[faculty_id])
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course_name': self.course.name if self.course else None,
            'course_code': self.course.code if self.course else None,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.full_name if self.faculty else None,
            'location_id': self.location_id,
            'status': self.status.value,
            'scheduled_start': self.scheduled_start.isoformat(),
            'scheduled_end': self.scheduled_end.isoformat(),
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'notes': self.notes,
            'present_count': self.attendance_records.filter_by(
                status=AttendanceStatus.present).count(),
            'total_enrolled': self.course.students.count() if self.course else 0,
        }


# ─────────────────────────────────────────────────────────────────
# AttendanceRecord Model
# ─────────────────────────────────────────────────────────────────

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_record'

    id              = db.Column(db.Integer, primary_key=True)
    session_id      = db.Column(db.Integer, db.ForeignKey('session.id'),  nullable=False)
    student_id      = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)
    status          = db.Column(db.Enum(AttendanceStatus), default=AttendanceStatus.absent)
    check_in_time   = db.Column(db.DateTime)
    check_in_lat    = db.Column(db.Float)
    check_in_lng    = db.Column(db.Float)
    qr_verified     = db.Column(db.Boolean, default=False)
    gps_verified    = db.Column(db.Boolean, default=False)
    override_by     = db.Column(db.Integer, db.ForeignKey('user.id'))
    override_reason = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('session_id', 'student_id',
                                          name='uq_session_student'),)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else None,
            'status': self.status.value,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_in_lat': self.check_in_lat,
            'check_in_lng': self.check_in_lng,
            'qr_verified': self.qr_verified,
            'gps_verified': self.gps_verified,
            'override_by': self.override_by,
            'override_reason': self.override_reason,
        }


# ─────────────────────────────────────────────────────────────────
# AuditLog Model
# ─────────────────────────────────────────────────────────────────

class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id          = db.Column(db.Integer, primary_key=True)
    actor_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    action      = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(64))
    entity_id   = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address  = db.Column(db.String(64))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    actor       = db.relationship('User', foreign_keys=[actor_id])

    def to_dict(self):
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'actor_name': self.actor.full_name if self.actor else 'System',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────────
# SystemSettings Model
# ─────────────────────────────────────────────────────────────────

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'

    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(db.Text)
    group = db.Column(db.String(64))

    def to_dict(self):
        return {'key': self.key, 'value': self.value, 'group': self.group}
