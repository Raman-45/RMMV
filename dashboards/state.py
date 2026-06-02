"""
State Dashboard Blueprint — /state
===================================
Provides the State-level PMU admin with a bird's-eye view of every ULB,
project, audit log, and KPI across the entire programme.

All routes require the 'state' role.
"""

from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, abort, flash, redirect,
    url_for
)
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from database.models import (
    db, User, ULB, Project, Activity, SiteEntry, AuditLog, MediaFile
)
from auth.permissions import role_required, get_user_projects

# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
state_bp = Blueprint('state', __name__, url_prefix='/state')


# ===========================================================================
# DASHBOARD — GET /state/
# ===========================================================================
@state_bp.route('/')
@login_required
@role_required(['state'])
def dashboard():
    """
    Main State dashboard.
    Computes aggregate KPIs across all ULBs and projects and renders the
    overview page with summary cards, charts, and a project map.
    """
    # --- Fetch core data ---------------------------------------------------
    ulbs = ULB.query.all()
    projects = Project.query.all()

    total_projects = len(projects)
    total_ulbs = len(ulbs)

    # --- Aggregate KPIs ----------------------------------------------------
    if total_projects > 0:
        avg_physical = round(
            sum(p.physical_progress or 0 for p in projects) / total_projects, 1
        )
        avg_financial = round(
            sum(p.financial_progress or 0 for p in projects) / total_projects, 1
        )
    else:
        avg_physical = 0.0
        avg_financial = 0.0

    delayed_count = sum(1 for p in projects if p.status == 'delayed')
    critical_count = sum(1 for p in projects if p.status == 'critical')
    alerts_count = delayed_count + critical_count

    # Status distribution for quick-glance chart
    status_counts = {
        'active': sum(1 for p in projects if p.status == 'active'),
        'completed': sum(1 for p in projects if p.status == 'completed'),
        'delayed': delayed_count,
        'critical': critical_count,
    }

    # Recent audit-log entries (last 10 for the dashboard widget)
    recent_logs = (
        AuditLog.query
        .order_by(desc(AuditLog.created_at))
        .limit(10)
        .all()
    )

    projects_json = [
        {
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'name': p.name,
            'status': p.status,
            'physical_progress': float(p.physical_progress or 0),
            'financial_progress': float(p.financial_progress or 0),
            'ulb_name': p.ulb.name if p.ulb else '',
        }
        for p in projects if p.latitude is not None and p.longitude is not None
    ]

    chart_labels = [ulb.name for ulb in ulbs]
    chart_physical = []
    chart_financial = []
    for ulb in ulbs:
        ulb_projects = Project.query.filter_by(ulb_id=ulb.id).all()
        if ulb_projects:
            chart_physical.append(
                round(sum(p.physical_progress or 0 for p in ulb_projects) / len(ulb_projects), 1)
            )
            chart_financial.append(
                round(sum(p.financial_progress or 0 for p in ulb_projects) / len(ulb_projects), 1)
            )
        else:
            chart_physical.append(0.0)
            chart_financial.append(0.0)

    return render_template(
        'state/dashboard.html',
        ulbs=ulbs,
        projects=projects,
        total_projects=total_projects,
        total_ulbs=total_ulbs,
        avg_physical=avg_physical,
        avg_financial=avg_financial,
        delayed_count=delayed_count,
        critical_count=critical_count,
        alerts_count=alerts_count,
        status_counts=status_counts,
        recent_logs=recent_logs,
        projects_json=projects_json,
        chart_labels=chart_labels,
        chart_physical=chart_physical,
        chart_financial=chart_financial,
    )


# ===========================================================================
# PROJECTS LIST — GET /state/projects
# ===========================================================================
@state_bp.route('/projects')
@login_required
@role_required(['state'])
def projects():
    """
    Paginated, filterable list of all projects.
    Supports query-string filters:
      ?ulb_id=<int>   — filter by ULB
      ?status=<str>   — filter by project status
      ?page=<int>     — pagination (20 per page)
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Start building the query
    query = Project.query

    # --- Optional filters --------------------------------------------------
    ulb_filter = request.args.get('ulb_id', type=int)
    if ulb_filter:
        query = query.filter(Project.ulb_id == ulb_filter)

    status_filter = request.args.get('status', type=str)
    if status_filter and status_filter in ('active', 'completed', 'delayed', 'critical'):
        query = query.filter(Project.status == status_filter)

    # --- Paginate ----------------------------------------------------------
    pagination = query.order_by(Project.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # All ULBs for the filter dropdown
    ulbs = ULB.query.order_by(ULB.name).all()

    return render_template(
        'state/projects.html',
        projects=pagination.items,
        pagination=pagination,
        ulbs=ulbs,
        selected_ulb=ulb_filter,
        selected_status=status_filter,
    )


# ===========================================================================
# PROJECT DETAIL — GET /state/project/<int:id>
# ===========================================================================
@state_bp.route('/project/<int:id>')
@login_required
@role_required(['state'])
def project_detail(id):
    """
    Detailed view of a single project including its activities, site entries,
    and uploaded media.
    """
    project = Project.query.get_or_404(id)

    activities = (
        Activity.query
        .filter_by(project_id=project.id)
        .order_by(Activity.id)
        .all()
    )

    entries = (
        SiteEntry.query
        .filter_by(project_id=project.id)
        .order_by(desc(SiteEntry.created_at))
        .all()
    )

    media = (
        MediaFile.query
        .filter_by(project_id=project.id)
        .order_by(desc(MediaFile.created_at))
        .all()
    )

    activity_labels = [a.activity_name for a in activities]
    activity_targets = [float(a.target_qty or 0) for a in activities]
    activity_achieved = [float(a.achieved_qty or 0) for a in activities]

    audit_logs = (
        AuditLog.query
        .filter_by(entity_type='Project', entity_id=project.id)
        .order_by(desc(AuditLog.created_at))
        .limit(15)
        .all()
    )

    return render_template(
        'project_detail.html',
        project=project,
        activities=activities,
        site_entries=entries,
        media_files=media,
        activity_labels=activity_labels,
        activity_targets=activity_targets,
        activity_achieved=activity_achieved,
        audit_logs=audit_logs,
    )


# ===========================================================================
# AUDIT LOGS — GET /state/audit-logs
# ===========================================================================
@state_bp.route('/audit-logs')
@login_required
@role_required(['state'])
def audit_logs():
    """
    Paginated audit-log viewer. State admins can review every action
    recorded across the system.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = AuditLog.query

    user_filter = request.args.get('user_id', type=int)
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)

    action_filter = request.args.get('action', type=str)
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    date_from = request.args.get('date_from', type=str)
    if date_from:
        query = query.filter(db.func.date(AuditLog.created_at) >= date_from)

    date_to = request.args.get('date_to', type=str)
    if date_to:
        query = query.filter(db.func.date(AuditLog.created_at) <= date_to)

    users = User.query.order_by(User.name).all()
    action_types = [row.action for row in (
        AuditLog.query.with_entities(AuditLog.action)
        .distinct()
        .order_by(AuditLog.action)
        .all()
    )]

    pagination = (
        query
        .order_by(desc(AuditLog.created_at))
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        'state/audit_logs.html',
        logs=pagination.items,
        pagination=pagination,
        users=users,
        action_types=action_types,
    )


# ===========================================================================
# MAP DATA API — GET /state/api/map-data
# ===========================================================================
@state_bp.route('/api/map-data')
@login_required
@role_required(['state'])
def api_map_data():
    """
    Returns a JSON array of all projects with geographic coordinates for
    the Leaflet map on the State dashboard.

    Response shape:
    [
      {
        "id": 1,
        "name": "Project Alpha",
        "lat": 23.2599,
        "lng": 77.4126,
        "status": "active",
        "physical_progress": 45.0,
        "financial_progress": 38.5,
        "ulb_name": "Bhopal MC"
      },
      ...
    ]
    """
    # Join Project → ULB so we can include the ULB name in one query
    rows = (
        db.session.query(Project, ULB.name.label('ulb_name'))
        .join(ULB, Project.ulb_id == ULB.id)
        .all()
    )

    features = []
    for project, ulb_name in rows:
        # Skip projects without coordinates
        if project.latitude is None or project.longitude is None:
            continue
        features.append({
            'id': project.id,
            'name': project.name,
            'lat': float(project.latitude),
            'lng': float(project.longitude),
            'status': project.status,
            'physical_progress': float(project.physical_progress or 0),
            'financial_progress': float(project.financial_progress or 0),
            'ulb_name': ulb_name,
        })

    return jsonify(features)


# ===========================================================================
# CHART DATA API — GET /state/api/chart-data
# ===========================================================================
@state_bp.route('/api/chart-data')
@login_required
@role_required(['state'])
def api_chart_data():
    """
    Returns aggregated data consumed by Chart.js on the State dashboard.

    Response shape:
    {
      "ulb_progress": [
        {"ulb": "Bhopal MC", "physical": 52.3, "financial": 48.1},
        ...
      ],
      "status_distribution": {
        "active": 12, "completed": 5, "delayed": 3, "critical": 1
      },
      "top_delayed": [
        {"id": 7, "name": "Road Widening Ph-2", "physical_progress": 18.0},
        ...
      ]
    }
    """
    # --- Per-ULB aggregated progress ---------------------------------------
    ulb_progress = []
    ulbs = ULB.query.order_by(ULB.name).all()
    for ulb in ulbs:
        projects = Project.query.filter_by(ulb_id=ulb.id).all()
        if projects:
            avg_phys = round(
                sum(p.physical_progress or 0 for p in projects) / len(projects), 1
            )
            avg_fin = round(
                sum(p.financial_progress or 0 for p in projects) / len(projects), 1
            )
        else:
            avg_phys = 0.0
            avg_fin = 0.0
        ulb_progress.append({
            'ulb': ulb.name,
            'physical': avg_phys,
            'financial': avg_fin,
        })

    # --- Project status distribution ---------------------------------------
    status_distribution = {}
    for status_val in ('active', 'completed', 'delayed', 'critical'):
        status_distribution[status_val] = (
            Project.query.filter_by(status=status_val).count()
        )

    # --- Top 10 delayed / critical projects --------------------------------
    top_delayed = (
        Project.query
        .filter(Project.status.in_(['delayed', 'critical']))
        .order_by(Project.physical_progress.asc())
        .limit(10)
        .all()
    )
    top_delayed_list = [
        {
            'id': p.id,
            'name': p.name,
            'physical_progress': float(p.physical_progress or 0),
        }
        for p in top_delayed
    ]

    return jsonify({
        'ulb_progress': ulb_progress,
        'status_distribution': status_distribution,
        'top_delayed': top_delayed_list,
    })
