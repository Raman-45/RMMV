"""
RMMV Dashboard — Auth Permissions
===================================
Reusable decorators and helper functions for role-based access control.
"""

from functools import wraps

from flask import abort
from flask_login import current_user

from database.models import Project


def role_required(roles):
    """Decorator that restricts a route to users whose ``role`` is in *roles*.

    Parameters
    ----------
    roles : list[str]
        Allowed role strings, e.g. ``['state', 'ulb']``.

    Usage
    -----
    ::

        @app.route('/admin')
        @login_required          # ensure user is authenticated first
        @role_required(['state'])
        def admin_panel():
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_user_projects(user):
    """Return a filtered SQLAlchemy query of projects visible to *user*.

    - **state** users see all projects.
    - **ulb** and **site** users see only projects belonging to their ULB.

    Parameters
    ----------
    user : User
        The currently authenticated user.

    Returns
    -------
    flask_sqlalchemy.BaseQuery
        A query object (not yet executed) that can be further filtered,
        paginated, or iterated.
    """
    if user.role == 'state':
        return Project.query
    else:
        # Both 'ulb' and 'site' are scoped to their own ULB
        return Project.query.filter_by(ulb_id=user.ulb_id)
