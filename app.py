"""
RMMV Dashboard — Application Entry Point
==========================================
Remote Monitoring, Measurement & Verification (RMMV) Dashboard
for government infrastructure project oversight.

Creates and configures the Flask application, registers blueprints,
initialises extensions, seeds the database, and starts the dev server.
"""

import os
from datetime import datetime, timezone

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

from config import Config
from database.models import db, User
from database.seed import seed_database


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app(config_class=Config):
    """Create and configure the Flask application.

    Parameters
    ----------
    config_class : class
        Configuration class to use (default: ``Config`` from config.py).

    Returns
    -------
    Flask
        The fully configured application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Ensure required directories exist -----------------------------------
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # --- Initialise extensions -----------------------------------------------
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        """Flask-Login callback: load a User by primary key."""
        return User.query.get(int(user_id))

    # --- Register blueprints -------------------------------------------------
    from auth.routes import auth_bp
    from dashboards.state import state_bp
    from dashboards.ulb import ulb_bp
    from dashboards.site import site_bp

    app.register_blueprint(auth_bp)     # /auth
    app.register_blueprint(state_bp)    # /state
    app.register_blueprint(ulb_bp)      # /ulb
    app.register_blueprint(site_bp)     # /site

    # --- Root route -----------------------------------------------------------
    @app.route('/')
    def index():
        """Redirect to the appropriate dashboard or the login page."""
        if current_user.is_authenticated:
            role_map = {
                'state': 'state.dashboard',
                'ulb':   'ulb.dashboard',
                'site':  'site.dashboard',
            }
            endpoint = role_map.get(current_user.role, 'auth.login')
            return redirect(url_for(endpoint))
        return redirect(url_for('auth.login'))

    # --- Template context processors ----------------------------------------
    @app.context_processor
    def inject_globals():
        """Make common values available in every Jinja template."""
        return {
            'current_year': datetime.now(timezone.utc).year,
            'app_name': 'RMMV Dashboard',
        }

    # --- Database creation & seeding -----------------------------------------
    with app.app_context():
        db.create_all()
        seed_database(db)

    return app


# ===========================================================================
# Development server
# ===========================================================================
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
