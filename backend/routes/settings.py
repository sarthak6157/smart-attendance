"""routes/settings.py — System settings endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import SystemSettings
from database import db
from functools import wraps

settings_bp = Blueprint('settings', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get('role') != 'admin':
            return jsonify(error='Admin access required.'), 403
        return fn(*args, **kwargs)
    return wrapper


def _settings_as_dict(group=None):
    q = SystemSettings.query
    if group:
        q = q.filter_by(group=group)
    return {s.key: s.value for s in q.all()}


@settings_bp.get('/attendance')
@jwt_required()
def get_attendance_settings():
    return jsonify(_settings_as_dict('attendance'))


@settings_bp.get('/notifications')
@jwt_required()
def get_notification_settings():
    return jsonify(_settings_as_dict('notifications'))


@settings_bp.get('/')
@jwt_required()
def get_all_settings():
    return jsonify(_settings_as_dict())


@settings_bp.post('/')
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}
    for key, value in data.items():
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            # Infer group from key prefix
            group = 'general'
            if key in ('min_attendance_percent', 'at_risk_threshold',
                       'late_grace_period_min', 'allow_manual_override'):
                group = 'attendance'
            elif key in ('qr_rotation_seconds',):
                group = 'qr'
            elif key in ('geofence_radius_m',):
                group = 'gps'
            elif key in ('email_notifications', 'sms_notifications'):
                group = 'notifications'
            db.session.add(SystemSettings(key=key, value=str(value), group=group))
    db.session.commit()
    return jsonify(message='Settings saved.', settings=_settings_as_dict())


@settings_bp.put('/<string:key>')
@admin_required
def update_single_setting(key):
    data    = request.get_json(silent=True) or {}
    setting = SystemSettings.query.filter_by(key=key).first()
    if not setting:
        return jsonify(error=f'Setting "{key}" not found.'), 404
    setting.value = str(data.get('value', ''))
    db.session.commit()
    return jsonify(setting.to_dict())
