"""
seed.py — Populates the database with demo data on first run.
Matches the test credentials shown in login_page.html.
"""

from database import db
from models import (User, UserRole, Course, Location, Session, SessionStatus,
                    AttendanceRecord, AttendanceStatus, AuditLog, SystemSettings,
                    enrollment)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random


def seed_database():
    """Only seeds if the users table is empty."""
    if User.query.first():
        return
    print("  → Seeding demo data …")

    # ── Users ────────────────────────────────────────────────────
    users_data = [
        dict(user_id='admin1',      password='admin123',    full_name='Alex Admin',
             email='admin@uni.edu', role=UserRole.admin,    department='IT'),
        dict(user_id='faculty1',    password='teach123',    full_name='Dr. Alex Nguyen',
             email='faculty1@uni.edu', role=UserRole.faculty, department='Computer Science'),
        dict(user_id='faculty2',    password='teach456',    full_name='Prof. Maria Santos',
             email='faculty2@uni.edu', role=UserRole.faculty, department='Mathematics'),
        dict(user_id='student1',    password='password123', full_name='Jordan Smith',
             email='s1@uni.edu',  role=UserRole.student, program='BSc Computer Science'),
        dict(user_id='student2',    password='password123', full_name='Priya Patel',
             email='s2@uni.edu',  role=UserRole.student, program='BSc Computer Science'),
        dict(user_id='student3',    password='password123', full_name='Chris Lee',
             email='s3@uni.edu',  role=UserRole.student, program='BEng Electronics'),
        dict(user_id='student4',    password='password123', full_name='Amara Osei',
             email='s4@uni.edu',  role=UserRole.student, program='BSc Mathematics'),
        dict(user_id='student5',    password='password123', full_name='Lucas Müller',
             email='s5@uni.edu',  role=UserRole.student, program='BSc Computer Science'),
        dict(user_id='student_new', password='welcome123',  full_name='New Student',
             email='snew@uni.edu', role=UserRole.student, program='BSc Computer Science',
             first_login=True),
    ]

    created_users = {}
    for u in users_data:
        pwd = u.pop('password')
        first_login = u.pop('first_login', False)
        # Standardize: explicitly pass first_login to the User model
        user = User(**u,
                    password_hash=generate_password_hash(pwd),
                    first_login=first_login)
        db.session.add(user)
        # Store for reference in foreign keys
        db.session.flush() 
        created_users[u['user_id']] = user

    # ── Locations ────────────────────────────────────────────────
    locs_data = [
        dict(name='Main Lecture Hall A', building='Science Block', room_number='SB-101',
             latitude=28.3670, longitude=77.3220, radius_m=100),
        dict(name='Computer Lab 1',      building='IT Block',      room_number='IT-201',
             latitude=28.3675, longitude=77.3225, radius_m=80),
        dict(name='Seminar Room B',      building='Arts Block',    room_number='AB-302',
             latitude=28.3665, longitude=77.3215, radius_m=75),
        dict(name='Engineering Workshop', building='Eng Block',    room_number='EB-105',
             latitude=28.3680, longitude=77.3230, radius_m=120),
    ]
    locs = []
    for l in locs_data:
        loc = Location(**l)
        db.session.add(loc)
        locs.append(loc)
    db.session.flush()

    # ── Courses ──────────────────────────────────────────────────
    f1 = created_users['faculty1']
    f2 = created_users['faculty2']
    courses_data = [
        dict(code='CS301', name='Data Structures & Algorithms',
             description='Fundamental algorithms and data structures.',
             credits=4, semester='Semester 1', academic_year='2024-25',
             faculty_id=f1.id, location_id=locs[1].id),
        dict(code='CS302', name='Operating Systems',
             description='Process management, memory, filesystems.',
             credits=3, semester='Semester 1', academic_year='2024-25',
             faculty_id=f1.id, location_id=locs[0].id),
        dict(code='MA201', name='Discrete Mathematics',
             description='Logic, sets, combinatorics, graph theory.',
             credits=3, semester='Semester 1', academic_year='2024-25',
             faculty_id=f2.id, location_id=locs[2].id),
        dict(code='EE201', name='Circuit Analysis',
             description='Kirchhoff laws, AC/DC analysis.',
             credits=4, semester='Semester 1', academic_year='2024-25',
             faculty_id=f2.id, location_id=locs[3].id),
    ]
    courses = []
    for c in courses_data:
        course = Course(**c)
        db.session.add(course)
        courses.append(course)
    db.session.flush()

    # ── Enrolments ───────────────────────────────────────────────
    students_list = [created_users[f'student{i}'] for i in range(1, 6)]
    # Use standard relationship append logic
    for student in students_list[:4]:
        courses[0].students.append(student)
        courses[2].students.append(student)
    for student in students_list[2:]:
        courses[3].students.append(student)
    for student in students_list[:3]:
        courses[1].students.append(student)
    db.session.flush()

    # ── Sessions ─────────────────────────────────────────────────
    now = datetime.utcnow()
    sessions_created = []

    def make_session(course, faculty_id, loc_id, start_offset_h, duration_h=1.5, status=None):
        start = now + timedelta(hours=start_offset_h)
        end   = start + timedelta(hours=duration_h)
        s = Session(
            course_id=course.id,
            faculty_id=faculty_id,
            location_id=loc_id,
            scheduled_start=start,
            scheduled_end=end,
            status=status or (SessionStatus.active if start_offset_h < 0 and end > now
                              else (SessionStatus.closed if end < now else SessionStatus.scheduled)),
            actual_start=start if start < now else None,
            actual_end=end if end < now else None,
        )
        db.session.add(s)
        return s

    # Past sessions
    for i in range(1, 8):
        s = make_session(courses[0], f1.id, locs[1].id, -(i * 48))
        sessions_created.append(s)
    for i in range(1, 6):
        s = make_session(courses[1], f1.id, locs[0].id, -(i * 72))
        sessions_created.append(s)
    for i in range(1, 5):
        s = make_session(courses[2], f2.id, locs[2].id, -(i * 48))
        sessions_created.append(s)

    # Active session now
    active = make_session(courses[0], f1.id, locs[1].id, -0.5, status=SessionStatus.active)
    sessions_created.append(active)

    # Future sessions
    make_session(courses[1], f1.id, locs[0].id, 24)
    make_session(courses[2], f2.id, locs[2].id, 48)
    db.session.flush()

    # ── Attendance Records ───────────────────────────────────────
    enrolled_map = {
        courses[0].id: students_list[:4],
        courses[1].id: students_list[:3],
        courses[2].id: students_list,
        courses[3].id: students_list[2:],
    }
    statuses = [AttendanceStatus.present, AttendanceStatus.present,
                AttendanceStatus.present, AttendanceStatus.absent, AttendanceStatus.late]

    for sess in sessions_created:
        if sess.status == SessionStatus.scheduled:
            continue
        enrolled = enrolled_map.get(sess.course_id, students_list[:4])
        for student in enrolled:
            pick = random.choice(statuses)
            rec = AttendanceRecord(
                session_id=sess.id,
                student_id=student.id,
                status=pick,
                check_in_time=sess.actual_start + timedelta(minutes=random.randint(0, 15))
                              if pick in (AttendanceStatus.present, AttendanceStatus.late) else None,
                check_in_lat=locs[1].latitude  + random.uniform(-0.0005, 0.0005),
                check_in_lng=locs[1].longitude + random.uniform(-0.0005, 0.0005),
                qr_verified=(pick == AttendanceStatus.present),
                gps_verified=(pick != AttendanceStatus.absent),
            )
            db.session.add(rec)

    # ── System Settings ─────────────────────────────────────────
    defaults = [
        ('min_attendance_percent', '75', 'attendance'),
        ('at_risk_threshold', '80',      'attendance'),
        ('qr_rotation_seconds', '60',    'qr'),
        ('geofence_radius_m', '150',     'gps'),
        ('late_grace_period_min', '10',  'attendance'),
        ('allow_manual_override', 'true','attendance'),
        ('email_notifications', 'true',  'notifications'),
        ('sms_notifications', 'false',   'notifications'),
        ('institution_name', 'My University', 'general'),
        ('academic_year', '2024-25',     'general'),
    ]
    for key, val, grp in defaults:
        db.session.add(SystemSettings(key=key, value=val, group=grp))

    # ── Audit Logs ───────────────────────────────────────────────
    admin_user = created_users['admin1']
    for entry in [
        (admin_user.id, 'USER_CREATED',  'user',   f1.id,     'Created faculty account faculty1'),
        (admin_user.id, 'COURSE_CREATED','course', courses[0].id, 'Created course CS301'),
        (f1.id,   'SESSION_STARTED','session',active.id, 'Started session for CS301'),
    ]:
        db.session.add(AuditLog(actor_id=entry[0], action=entry[1],
                                entity_type=entry[2], entity_id=entry[3],
                                description=entry[4], ip_address='127.0.0.1'))

    db.session.commit()
    print("  ✓ Demo data seeded successfully.")
