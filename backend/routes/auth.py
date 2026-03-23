"""routes/auth.py — Authentication endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (create_access_token, jwt_required,
                                 get_jwt_identity, get_jwt)
from werkzeug.security import check_password_hash
from models import User, AuditLog
from database import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    user_id  = (data.get('userId') or '').strip()
    password = data.get('password') or ''

    if not user_id or not password:
        return jsonify(error='User ID and password are required.'), 400

    user = User.query.filter_by(user_id=user_id, is_active=True).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error='Invalid credentials.'), 401

    token = create_access_token(identity=str(user.id),
                                 additional_claims={'role': user.role.value,
                                                    'user_id': user.user_id})

    # Determine redirect based on role & first_login
    role_routes = {
        'admin':   '/admin_dashboard.html',
        'faculty': '/faculty_dashboard.html',
        'student': '/enrollment_page.html' if user.first_login else '/student_dashboard.html',
    }

    # Audit
    db.session.add(AuditLog(
        actor_id=user.id, action='LOGIN', entity_type='user', entity_id=user.id,
        description=f'{user.user_id} signed in', ip_address=request.remote_addr))
    db.session.commit()

    return jsonify(
        access_token=token,
        role=user.role.value,
        full_name=user.full_name,
        first_login=user.first_login,
        redirect=role_routes.get(user.role.value, '/'),
    ), 200


@auth_bp.post('/logout')
@jwt_required()
def logout():
    uid = int(get_jwt_identity())
    db.session.add(AuditLog(
        actor_id=uid, action='LOGOUT', entity_type='user', entity_id=uid,
        description='User signed out', ip_address=request.remote_addr))
    db.session.commit()
    return jsonify(message='Logged out.'), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    return jsonify(user.to_dict()), 200


@auth_bp.post('/change-password')
@jwt_required()
def change_password():
    from werkzeug.security import generate_password_hash
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}
    old  = data.get('old_password', '')
    new  = data.get('new_password', '')

    if not check_password_hash(user.password_hash, old):
        return jsonify(error='Current password is incorrect.'), 403
    if len(new) < 6:
        return jsonify(error='New password must be at least 6 characters.'), 400

    user.password_hash = generate_password_hash(new)
    user.first_login   = False
    db.session.commit()
    return jsonify(message='Password changed successfully.'), 200
