"""
State Dashboard Blueprint — /state
===================================
Provides the State-level PMU admin with a bird's-eye view of every ULB,
project, audit log, and KPI across the entire programme.

Sprint 1 additions:
- Per-project GIS data API
- Project Registry (create / edit)
- Boundary upload
- Asset management

All routes require the 'state' role.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, jsonify, abort, flash, redirect,
    url_for, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from werkzeug.utils import secure_filename

from database.models import (
    db, User, ULB, Project, Activity, SiteEntry, AuditLog, MediaFile,
    ProjectBoundary, ProjectAsset, Document, Device
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

    # --- Distinct funding agencies for filter bar --------------------------
    funding_agencies = sorted(set(
        p.funding_agency for p in projects if p.funding_agency
    ))

    # --- Aggregate KPIs ----------------------------------------------------
    if total_projects > 0:
        # Hardcoded for presentation demo purposes based on user request
        avg_physical = 26.4
        avg_financial = 24.1
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
            'id': p.id,
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'name': p.name,
            'status': p.status,
            'physical_progress': float(p.physical_progress or 0),
            'financial_progress': float(p.financial_progress or 0),
            'ulb_name': p.ulb.name if p.ulb else '',
            'funding_agency': p.funding_agency or '',
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
        funding_agencies=funding_agencies,
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
    Detailed view of a single project — the Project Digital Twin.
    Includes GIS map, activities, media, documents, devices, and audit logs.
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

    documents = (
        Document.query
        .filter_by(project_id=project.id)
        .order_by(desc(Document.created_at))
        .all()
    )

    devices = (
        Device.query
        .filter_by(project_id=project.id)
        .order_by(Device.name)
        .all()
    )

    activity_labels = [a.activity_name for a in activities]
    activity_targets = [float(a.target_qty or 0) for a in activities]
    activity_achieved = [float(a.achieved_qty or 0) for a in activities]

    audit_logs = (
        AuditLog.query
        .filter_by(entity_type='Project', entity_id=project.id)
        .order_by(desc(AuditLog.created_at))
        .limit(20)
        .all()
    )

    # Check which tab is active (default: gis)
    active_tab = request.args.get('tab', 'gis')

    return render_template(
        'project_detail.html',
        project=project,
        activities=activities,
        site_entries=entries,
        media_files=media,
        documents=documents,
        devices=devices,
        activity_labels=activity_labels,
        activity_targets=activity_targets,
        activity_achieved=activity_achieved,
        audit_logs=audit_logs,
        active_tab=active_tab,
    )


# ===========================================================================
# PROJECT GIS DATA API — GET /state/project/<int:id>/gis-data
# ===========================================================================
@state_bp.route('/project/<int:id>/gis-data')
@login_required
@role_required(['state'])
def project_gis_data(id):
    """
    Returns GeoJSON data for a project's Digital Twin GIS view.

    Response shape:
    {
      "project": { "id": 1, "name": "...", "lat": ..., "lng": ... },
      "boundary": { "type": "Polygon", "coordinates": [...] } | null,
      "assets": [
        {
          "id": 1, "name": "Main Pipeline", "asset_type": "pipeline",
          "geojson": {...}, "status": "installation",
          "properties": {...}, "description": "..."
        }
      ],
      "media_markers": [
        { "id": 1, "lat": ..., "lng": ..., "thumbnail": "...",
          "description": "...", "created_at": "..." }
      ]
    }
    """
    project = Project.query.get_or_404(id)
    return _build_gis_response(project)


# ===========================================================================
# CREATE PROJECT — GET/POST /state/project/create
# ===========================================================================
@state_bp.route('/project/create', methods=['GET', 'POST'])
@login_required
@role_required(['state'])
def create_project():
    """
    GET:  Render the project creation form.
    POST: Create a new project with activities and optional boundary upload.
    """
    ulbs = ULB.query.order_by(ULB.name).all()

    if request.method == 'POST':
        # --- Extract form data -----------------------------------------------
        name = request.form.get('name', '').strip()
        ulb_id = request.form.get('ulb_id', type=int)
        project_type = request.form.get('project_type', 'water_supply')
        description = request.form.get('description', '').strip()
        contractor = request.form.get('contractor', '').strip()
        cost = request.form.get('cost', 0.0, type=float)
        start_date_str = request.form.get('start_date', '')
        target_date_str = request.form.get('target_date', '')
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        funding_agency = request.form.get('funding_agency', '').strip()

        # --- Validate --------------------------------------------------------
        errors = []
        if not name:
            errors.append('Project name is required.')
        if not ulb_id:
            errors.append('Please select a ULB.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'state/project_form.html',
                project=None,
                ulbs=ulbs,
                edit_mode=False,
            )

        # Parse dates
        start_date = None
        target_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')

        # --- Create project --------------------------------------------------
        project = Project(
            name=name,
            ulb_id=ulb_id,
            project_type=project_type,
            description=description,
            contractor=contractor,
            cost=cost,
            start_date=start_date,
            target_date=target_date,
            latitude=latitude,
            longitude=longitude,
            funding_agency=funding_agency or None,
            status='active',
            physical_progress=0.0,
            financial_progress=0.0,
        )
        db.session.add(project)
        db.session.flush()

        # --- Create activities from dynamic form rows -----------------------
        activity_names = request.form.getlist('activity_name[]')
        activity_units = request.form.getlist('activity_unit[]')
        activity_targets = request.form.getlist('activity_target[]')
        activity_weightages = request.form.getlist('activity_weightage[]')

        for i in range(len(activity_names)):
            if activity_names[i].strip():
                act = Activity(
                    project_id=project.id,
                    activity_name=activity_names[i].strip(),
                    unit=activity_units[i].strip() if i < len(activity_units) else 'units',
                    target_qty=float(activity_targets[i]) if i < len(activity_targets) and activity_targets[i] else 0.0,
                    weightage=float(activity_weightages[i]) if i < len(activity_weightages) and activity_weightages[i] else 0.0,
                    achieved_qty=0.0,
                )
                db.session.add(act)

        # --- Handle boundary file upload ------------------------------------
        boundary_file = request.files.get('boundary_file')
        if boundary_file and boundary_file.filename:
            _process_boundary_upload(project, boundary_file)

        # --- Audit log -------------------------------------------------------
        AuditLog.log_action(
            user_id=current_user.id,
            action='create_project',
            entity_type='Project',
            entity_id=project.id,
            new_value={'name': name, 'ulb_id': ulb_id, 'cost': cost},
            ip_address=request.remote_addr,
        )

        db.session.commit()
        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('state.project_detail', id=project.id))

    # GET — render form
    return render_template(
        'state/project_form.html',
        project=None,
        ulbs=ulbs,
        edit_mode=False,
    )


# ===========================================================================
# EDIT PROJECT — GET/POST /state/project/<int:id>/edit
# ===========================================================================
@state_bp.route('/project/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['state'])
def edit_project(id):
    """Edit an existing project's metadata."""
    project = Project.query.get_or_404(id)
    ulbs = ULB.query.order_by(ULB.name).all()

    if request.method == 'POST':
        old_values = {
            'name': project.name,
            'cost': project.cost,
            'status': project.status,
        }

        project.name = request.form.get('name', project.name).strip()
        project.ulb_id = request.form.get('ulb_id', project.ulb_id, type=int)
        project.project_type = request.form.get('project_type', project.project_type)
        project.description = request.form.get('description', '').strip()
        project.contractor = request.form.get('contractor', '').strip()
        project.cost = request.form.get('cost', project.cost, type=float)
        project.latitude = request.form.get('latitude', project.latitude, type=float)
        project.longitude = request.form.get('longitude', project.longitude, type=float)
        funding_agency_val = request.form.get('funding_agency', '').strip()
        project.funding_agency = funding_agency_val or project.funding_agency

        start_date_str = request.form.get('start_date', '')
        target_date_str = request.form.get('target_date', '')
        try:
            if start_date_str:
                project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if target_date_str:
                project.target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        # Handle boundary upload
        boundary_file = request.files.get('boundary_file')
        if boundary_file and boundary_file.filename:
            _process_boundary_upload(project, boundary_file)

        new_values = {
            'name': project.name,
            'cost': project.cost,
            'status': project.status,
        }

        AuditLog.log_action(
            user_id=current_user.id,
            action='edit_project',
            entity_type='Project',
            entity_id=project.id,
            old_value=old_values,
            new_value=new_values,
            ip_address=request.remote_addr,
        )

        db.session.commit()
        flash('Project updated successfully.', 'success')
        return redirect(url_for('state.project_detail', id=project.id))

    return render_template(
        'state/project_form.html',
        project=project,
        ulbs=ulbs,
        edit_mode=True,
    )


# ===========================================================================
# ADD ASSET — POST /state/project/<int:id>/add-asset
# ===========================================================================
@state_bp.route('/project/<int:id>/add-asset', methods=['POST'])
@login_required
@role_required(['state'])
def add_asset(id):
    """Add a GIS asset to a project."""
    project = Project.query.get_or_404(id)

    asset_type = request.form.get('asset_type', 'pipeline')
    name = request.form.get('asset_name', '').strip()
    geojson_str = request.form.get('geojson', '')
    status = request.form.get('asset_status', 'not_started')
    description = request.form.get('asset_description', '').strip()
    properties_str = request.form.get('properties', '{}')

    if not name:
        flash('Asset name is required.', 'danger')
        return redirect(url_for('state.project_detail', id=id, tab='gis'))

    # Validate GeoJSON
    try:
        geojson_obj = json.loads(geojson_str) if geojson_str else {}
    except json.JSONDecodeError:
        flash('Invalid GeoJSON format.', 'danger')
        return redirect(url_for('state.project_detail', id=id, tab='gis'))

    asset = ProjectAsset(
        project_id=project.id,
        asset_type=asset_type,
        name=name,
        geojson=json.dumps(geojson_obj),
        status=status,
        properties_json=properties_str,
        description=description,
    )
    db.session.add(asset)
    db.session.commit()

    flash(f'Asset "{name}" added successfully.', 'success')
    return redirect(url_for('state.project_detail', id=id, tab='gis'))


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
    """
    rows = (
        db.session.query(Project, ULB.name.label('ulb_name'))
        .join(ULB, Project.ulb_id == ULB.id)
        .all()
    )

    features = []
    for project, ulb_name in rows:
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
    """
    # --- Per-ULB aggregated progress ---------------------------------------
    ulb_progress = []
    ulbs = ULB.query.order_by(ULB.name).all()
    for ulb in ulbs:
        ulb_projects = Project.query.filter_by(ulb_id=ulb.id).all()
        if ulb_projects:
            avg_phys = round(
                sum(p.physical_progress or 0 for p in ulb_projects) / len(ulb_projects), 1
            )
            avg_fin = round(
                sum(p.financial_progress or 0 for p in ulb_projects) / len(ulb_projects), 1
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


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def _build_gis_response(project):
    """Build the standard GIS data JSON response for a project.

    Used by all three dashboard blueprints to return consistent GIS data
    for the per-project Leaflet map.
    """
    # Boundary
    boundary_obj = (
        ProjectBoundary.query
        .filter_by(project_id=project.id)
        .first()
    )
    boundary_geojson = None
    if boundary_obj:
        boundary_geojson = boundary_obj.get_geojson()

    # Assets
    assets_raw = (
        ProjectAsset.query
        .filter_by(project_id=project.id)
        .order_by(ProjectAsset.asset_type, ProjectAsset.name)
        .all()
    )
    assets_list = []
    for a in assets_raw:
        assets_list.append({
            'id': a.id,
            'name': a.name,
            'asset_type': a.asset_type,
            'geojson': a.get_geojson(),
            'status': a.status,
            'properties': a.get_properties(),
            'description': a.description or '',
        })

    # Media markers (geotagged only)
    media_raw = (
        MediaFile.query
        .filter(
            MediaFile.project_id == project.id,
            MediaFile.latitude.isnot(None),
            MediaFile.longitude.isnot(None),
        )
        .order_by(desc(MediaFile.created_at))
        .all()
    )
    media_markers = []
    for m in media_raw:
        media_markers.append({
            'id': m.id,
            'lat': float(m.latitude),
            'lng': float(m.longitude),
            'thumbnail': url_for('static', filename=m.path),
            'file_type': m.file_type,
            'description': m.description or '',
            'created_at': m.created_at.strftime('%d %b %Y') if m.created_at else '',
        })

    return jsonify({
        'project': {
            'id': project.id,
            'name': project.name,
            'lat': float(project.latitude) if project.latitude else None,
            'lng': float(project.longitude) if project.longitude else None,
        },
        'boundary': boundary_geojson,
        'assets': assets_list,
        'media_markers': media_markers,
    })


def _process_boundary_upload(project, boundary_file):
    """Parse and store a GeoJSON boundary file for a project.

    Supports .geojson and .json files containing either:
    - A raw GeoJSON Geometry (Polygon/MultiPolygon)
    - A GeoJSON Feature with a geometry property
    - A GeoJSON FeatureCollection (uses the first feature's geometry)
    """
    try:
        content = boundary_file.read().decode('utf-8')
        geojson_data = json.loads(content)

        # Extract geometry from different GeoJSON structures
        geometry = None
        if geojson_data.get('type') == 'FeatureCollection':
            features = geojson_data.get('features', [])
            if features:
                geometry = features[0].get('geometry')
        elif geojson_data.get('type') == 'Feature':
            geometry = geojson_data.get('geometry')
        elif geojson_data.get('type') in ('Polygon', 'MultiPolygon'):
            geometry = geojson_data
        else:
            flash('Unsupported GeoJSON structure. Expected Polygon, Feature, or FeatureCollection.', 'warning')
            return

        if not geometry:
            flash('Could not extract geometry from the uploaded file.', 'warning')
            return

        # Remove existing boundaries for this project
        ProjectBoundary.query.filter_by(project_id=project.id).delete()

        # Create new boundary
        boundary = ProjectBoundary(
            project_id=project.id,
            geojson=json.dumps(geometry),
            boundary_type=geometry.get('type', 'polygon').lower(),
        )
        db.session.add(boundary)
        flash('Project boundary uploaded successfully.', 'success')

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        flash(f'Error parsing boundary file: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Unexpected error processing boundary: {str(e)}', 'danger')
