"""
Smart Attendance System - Backend (Flask)
"""

from flask import Flask, jsonify  # Moved jsonify to the top
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from database import db
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.faculty import faculty_bp
from routes.student import student_bp
from routes.sessions import sessions_bp
from routes.reports import reports_bp
from routes.settings import settings_bp
from routes.audit import audit_bp
from config import Config
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp,     url_prefix='/api/auth')
    app.register_blueprint(admin_bp,    url_prefix='/api/admin')
    app.register_blueprint(faculty_bp,  url_prefix='/api/faculty')
    app.register_blueprint(student_bp,  url_prefix='/api/student')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')
    app.register_blueprint(reports_bp,  url_prefix='/api/reports')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(audit_bp,    url_prefix='/api/audit')

    # Serve frontend pages at root
    @app.route('/')
    def index():
        return app.send_static_file('login_page_index.html')

    @app.route('/api/programs')
    def programs():
        # Removed local import of jsonify as it is now global
        return jsonify(["BSc Computer Science", "BEng Electronics",
                        "BA Business", "BSc Mathematics", "MEng Software"])

    # Create tables and seed data
    with app.app_context():
        db.create_all()
        from seed import seed_database
        seed_database()

    return app


if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("  Smart Attendance System — Backend Running")
    print("  URL : http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)
