"""routes/audit.py — Audit log endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import AuditLog
from database import db
from datetime import datetime
from functools import wraps

audit_bp = Blueprint('audit', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get('role') != 'admin':
            return jsonify(error='Admin access required.'), 403
        return fn(*args, **kwargs)
    return wrapper


@audit_bp.get('/logs')
@admin_required
def get_logs():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action   = request.args.get('action')
    actor_id = request.args.get('actor_id', type=int)
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')

    q = AuditLog.query

    if action:
        q = q.filter(AuditLog.action.ilike(f'%{action}%'))
    if actor_id:
        q = q.filter_by(actor_id=actor_id)
    if date_from:
        try:
            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    paginated = (q.order_by(AuditLog.created_at.desc())
                  .paginate(page=page, per_page=per_page, error_out=False))

    return jsonify(
        logs=[log.to_dict() for log in paginated.items],
        total=paginated.total,
        page=paginated.page,
        pages=paginated.pages,
        per_page=per_page,
    )


@audit_bp.post('/log')
@jwt_required()
def write_log():
    """Allow frontend to push a client-side audit event."""
    from flask_jwt_extended import get_jwt_identity
    uid  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    db.session.add(AuditLog(
        actor_id=uid,
        action=data.get('action', 'FRONTEND_EVENT'),
        entity_type=data.get('entity_type'),
        entity_id=data.get('entity_id'),
        description=data.get('description', ''),
        ip_address=request.remote_addr,
    ))
    db.session.commit()
    return jsonify(message='Logged.'), 201
