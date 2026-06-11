"""
RMMV Dashboard — Authentication Routes
========================================
Blueprint ``auth_bp`` handles login, logout, and session management.
URL prefix: ``/auth``
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from database.models import User, AuditLog

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ===========================================================================
# Login
# ===========================================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Display the login form (GET) or authenticate the user (POST).

    On successful login the user is redirected to the dashboard that
    matches their role:

    - ``state`` → ``/state``
    - ``ulb``   → ``/ulb``
    - ``site``  → ``/site``
    """

    # Already logged-in users go straight to their dashboard
    if current_user.is_authenticated:
        return _redirect_to_dashboard(current_user.role)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Contact the administrator.', 'warning')
            return render_template('login.html')

        # Check if the selected role matches the user's actual role
        selected_role = request.form.get('role')
        if selected_role and selected_role != user.role:
            flash('Invalid credentials for the selected role.', 'danger')
            return render_template('login.html')

        # Authenticate & create session
        login_user(user, remember=True)

        # Audit trail
        AuditLog.log_action(
            user_id=user.id,
            action='login',
            entity_type='User',
            entity_id=user.id,
            ip_address=request.remote_addr,
        )

        flash(f'Welcome back, {user.name}!', 'success')

        # Honour ?next= if present, otherwise go to role dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return _redirect_to_dashboard(user.role)

    # GET — render the login form
    return render_template('login.html')


# ===========================================================================
# Logout
# ===========================================================================
@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user and redirect to the login page."""

    AuditLog.log_action(
        user_id=current_user.id,
        action='logout',
        entity_type='User',
        entity_id=current_user.id,
        ip_address=request.remote_addr,
    )

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ===========================================================================
# Helpers
# ===========================================================================
def _redirect_to_dashboard(role: str):
    """Return a redirect response to the dashboard matching *role*."""
    destinations = {
        'state': 'state.dashboard',
        'ulb':   'ulb.dashboard',
        'site':  'site.dashboard',
    }
    endpoint = destinations.get(role, 'auth.login')
    return redirect(url_for(endpoint))
