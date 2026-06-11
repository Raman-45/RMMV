"""
ULB Dashboard Blueprint — /ulb
================================
Provides the ULB (Urban Local Body) officer with a scoped view of projects
under their jurisdiction, the ability to review and approve/reject site
entries, and update project progress.

All routes require the 'ulb' role.
"""

import json
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, jsonify, abort, flash, redirect,
    url_for
)
from flask_login import login_required, current_user
from sqlalchemy import desc

from database.models import (
    db, User, ULB, Project, Activity, SiteEntry, AuditLog, MediaFile,
    ProjectBoundary, ProjectAsset, Document, Device
)
from auth.permissions import role_required, get_user_projects

# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
ulb_bp = Blueprint('ulb', __name__, url_prefix='/ulb')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ulb_projects_query():
    """Return a base query scoped to the current ULB officer's ULB."""
    return Project.query.filter_by(ulb_id=current_user.ulb_id)


def _verify_project_ownership(project):
    """Abort 403 if the project does not belong to the officer's ULB."""
    if project.ulb_id != current_user.ulb_id:
        abort(403)


def _create_audit_log(action, entity_type, entity_id,
                      old_value=None, new_value=None):
    """
    Convenience wrapper to insert an AuditLog row and flush.
    Values are serialised to JSON text for storage.
    """
    log = AuditLog(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=json.dumps(old_value) if old_value is not None else None,
        new_value=json.dumps(new_value) if new_value is not None else None,
        ip_address=request.remote_addr,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(log)


def _recalculate_project_progress(project):
    """
    Recalculate the project's physical_progress as the weighted sum of
    activity completion ratios:

        physical_progress = Σ (achieved_qty / target_qty) × weightage × 100

    Each activity's weightage is a fraction (0–1) and the set should
    sum to 1.0 for a given project.
    """
    activities = Activity.query.filter_by(project_id=project.id).all()
    if not activities:
        return

    weighted_sum = 0.0
    for act in activities:
        if act.target_qty and act.target_qty > 0:
            ratio = min((act.achieved_qty or 0) / act.target_qty, 1.0)
        else:
            ratio = 0.0
        weighted_sum += ratio * (act.weightage or 0)

    project.physical_progress = round(weighted_sum * 100, 2)


# ===========================================================================
# DASHBOARD — GET /ulb/
# ===========================================================================
@ulb_bp.route('/')
@login_required
@role_required(['ulb'])
def dashboard():
    """
    ULB officer dashboard.
    Displays projects scoped to the officer's ULB with ULB-specific KPIs.
    """
    projects = _ulb_projects_query().all()

    total_projects = len(projects)
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
    completed_count = sum(1 for p in projects if p.status == 'completed')

    # Pending site entries awaiting review
    project_ids = [p.id for p in projects]
    pending_entries = (
        SiteEntry.query
        .filter(
            SiteEntry.project_id.in_(project_ids),
            SiteEntry.status == 'submitted',
        )
        .order_by(desc(SiteEntry.created_at))
        .limit(10)
        .all()
    ) if project_ids else []

    approved_entries = (
        SiteEntry.query
        .filter(
            SiteEntry.project_id.in_(project_ids),
            SiteEntry.status == 'approved',
        )
        .count()
    ) if project_ids else 0

    pending_reviews = len(pending_entries)
    my_projects_count = total_projects

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

    chart_labels = [p.name for p in projects]
    chart_physical = [float(p.physical_progress or 0) for p in projects]
    chart_financial = [float(p.financial_progress or 0) for p in projects]

    # ULB info for the header
    ulb = ULB.query.get(current_user.ulb_id)

    return render_template(
        'ulb/dashboard.html',
        ulb=ulb,
        projects=projects,
        total_projects=total_projects,
        my_projects_count=my_projects_count,
        avg_physical=avg_physical,
        avg_financial=avg_financial,
        delayed_count=delayed_count,
        critical_count=critical_count,
        completed_count=completed_count,
        pending_reviews=pending_reviews,
        approved_entries=approved_entries,
        pending_entries=pending_entries,
        projects_json=projects_json,
        chart_labels=chart_labels,
        chart_physical=chart_physical,
        chart_financial=chart_financial,
    )


# ===========================================================================
# PROJECT DETAIL — GET /ulb/project/<int:id>
# ===========================================================================
@ulb_bp.route('/project/<int:id>')
@login_required
@role_required(['ulb'])
def project_detail(id):
    """
    Detailed project view — only accessible if the project belongs to the
    officer's ULB. Now includes documents, devices, and GIS data.
    """
    project = Project.query.get_or_404(id)
    _verify_project_ownership(project)

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
# PROJECT GIS DATA API — GET /ulb/project/<int:id>/gis-data
# ===========================================================================
@ulb_bp.route('/project/<int:id>/gis-data')
@login_required
@role_required(['ulb'])
def project_gis_data(id):
    """Returns GeoJSON data for a project's GIS view (ULB-scoped)."""
    project = Project.query.get_or_404(id)
    _verify_project_ownership(project)

    from dashboards.state import _build_gis_response
    return _build_gis_response(project)


# ===========================================================================
# EDIT PROGRESS — POST /ulb/project/<int:id>/edit-progress
# ===========================================================================
@ulb_bp.route('/project/<int:id>/edit-progress', methods=['POST'])
@login_required
@role_required(['ulb'])
def edit_progress(id):
    """
    Accept form data to manually update a project's progress fields.
    Records the change in the audit log with old and new values.

    Expected form fields:
      - physical_progress  (float, 0–100)
      - financial_progress (float, 0–100)
      - status             (active | completed | delayed | critical)
    """
    project = Project.query.get_or_404(id)
    _verify_project_ownership(project)

    # Capture old values for audit trail
    old_values = {
        'physical_progress': float(project.physical_progress or 0),
        'financial_progress': float(project.financial_progress or 0),
        'status': project.status,
    }

    # --- Apply updates -----------------------------------------------------
    new_physical = request.form.get('physical_progress', type=float)
    new_financial = request.form.get('financial_progress', type=float)
    new_status = request.form.get('status', type=str)

    if new_physical is not None:
        project.physical_progress = max(0.0, min(new_physical, 100.0))

    if new_financial is not None:
        project.financial_progress = max(0.0, min(new_financial, 100.0))

    valid_statuses = ('active', 'completed', 'delayed', 'critical')
    if new_status and new_status in valid_statuses:
        project.status = new_status

    # Capture new values
    new_values = {
        'physical_progress': float(project.physical_progress or 0),
        'financial_progress': float(project.financial_progress or 0),
        'status': project.status,
    }

    # --- Audit log ---------------------------------------------------------
    _create_audit_log(
        action='update_progress',
        entity_type='Project',
        entity_id=project.id,
        old_value=old_values,
        new_value=new_values,
    )

    db.session.commit()
    flash('Project progress updated successfully.', 'success')
    return redirect(url_for('ulb.project_detail', id=project.id))


# ===========================================================================
# REVIEW ENTRIES — GET /ulb/review-entries
# ===========================================================================
@ulb_bp.route('/review-entries')
@login_required
@role_required(['ulb'])
def review_entries():
    """
    List site entries for projects under the officer's ULB.
    Default view shows submitted entries, but the UI supports additional
    filtering by project, status, and date range.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Projects available to this ULB officer
    projects = _ulb_projects_query().all()
    project_ids = [p.id for p in projects]

    if project_ids:
        query = SiteEntry.query.filter(SiteEntry.project_id.in_(project_ids))
    else:
        query = SiteEntry.query.filter(SiteEntry.id < 0)

    project_filter = request.args.get('project_id', type=int)
    if project_filter and project_filter in project_ids:
        query = query.filter(SiteEntry.project_id == project_filter)

    status_filter = request.args.get('status', type=str)
    allowed_statuses = ('draft', 'submitted', 'approved', 'rejected')
    if status_filter in allowed_statuses:
        query = query.filter(SiteEntry.status == status_filter)
    else:
        query = query.filter(SiteEntry.status == 'submitted')

    date_from = request.args.get('date_from', type=str)
    if date_from:
        query = query.filter(db.func.date(SiteEntry.created_at) >= date_from)

    date_to = request.args.get('date_to', type=str)
    if date_to:
        query = query.filter(db.func.date(SiteEntry.created_at) <= date_to)

    pagination = (
        query
        .order_by(desc(SiteEntry.created_at))
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        'ulb/review_entries.html',
        projects=projects,
        entries=pagination.items,
        pagination=pagination,
    )


# ===========================================================================
# APPROVE ENTRY — POST /ulb/entry/<int:id>/approve
# ===========================================================================
@ulb_bp.route('/entry/<int:id>/approve', methods=['POST'])
@login_required
@role_required(['ulb'])
def approve_entry(id):
    """
    Approve a submitted site entry.

    Workflow:
      1. Set SiteEntry.status → 'approved', record reviewer.
      2. Add the entry's quantity to the parent Activity.achieved_qty.
      3. Recalculate the project's physical_progress from weighted
         activity completion.
      4. Create an audit-log entry.
    """
    entry = SiteEntry.query.get_or_404(id)

    # Verify the entry's project belongs to this ULB
    project = Project.query.get_or_404(entry.project_id)
    _verify_project_ownership(project)

    if entry.status != 'submitted':
        flash('Only submitted entries can be approved.', 'warning')
        return redirect(url_for('ulb.review_entries'))

    # --- Step 1: Mark approved ---------------------------------------------
    old_status = entry.status
    entry.status = 'approved'
    entry.reviewed_by = current_user.id
    entry.updated_at = datetime.now(timezone.utc)

    # --- Step 2: Update activity achieved quantity -------------------------
    if entry.activity_id:
        activity = Activity.query.get(entry.activity_id)
        if activity:
            old_achieved = float(activity.achieved_qty or 0)
            activity.achieved_qty = old_achieved + float(entry.quantity or 0)

    # --- Step 3: Recalculate project progress ------------------------------
    old_progress = float(project.physical_progress or 0)
    _recalculate_project_progress(project)

    # --- Step 4: Audit log -------------------------------------------------
    _create_audit_log(
        action='approve_entry',
        entity_type='SiteEntry',
        entity_id=entry.id,
        old_value={'status': old_status, 'project_physical': old_progress},
        new_value={
            'status': 'approved',
            'project_physical': float(project.physical_progress or 0),
        },
    )

    db.session.commit()
    flash('Site entry approved successfully.', 'success')
    return redirect(url_for('ulb.review_entries'))


# ===========================================================================
# REJECT ENTRY — POST /ulb/entry/<int:id>/reject
# ===========================================================================
@ulb_bp.route('/entry/<int:id>/reject', methods=['POST'])
@login_required
@role_required(['ulb'])
def reject_entry(id):
    """
    Reject a submitted site entry.
    Requires review_remarks from the form to explain the reason.
    """
    entry = SiteEntry.query.get_or_404(id)

    # Verify the entry's project belongs to this ULB
    project = Project.query.get_or_404(entry.project_id)
    _verify_project_ownership(project)

    if entry.status != 'submitted':
        flash('Only submitted entries can be rejected.', 'warning')
        return redirect(url_for('ulb.review_entries'))

    old_status = entry.status
    review_remarks = request.form.get('review_remarks', '').strip()

    entry.status = 'rejected'
    entry.reviewed_by = current_user.id
    entry.review_remarks = review_remarks
    entry.updated_at = datetime.now(timezone.utc)

    _create_audit_log(
        action='reject_entry',
        entity_type='SiteEntry',
        entity_id=entry.id,
        old_value={'status': old_status},
        new_value={
            'status': 'rejected',
            'review_remarks': review_remarks,
        },
    )

    db.session.commit()
    flash('Site entry rejected.', 'info')
    return redirect(url_for('ulb.review_entries'))
# ===========================================================================
# CREATE PROJECT — GET/POST /ulb/project/create
# ===========================================================================
@ulb_bp.route('/project/create', methods=['GET', 'POST'])
@login_required
@role_required(['ulb'])
def create_project():
    """
    GET:  Render the project creation form (scoped to this ULB).
    POST: Create a new project for this ULB.
    """
    # ULB officer can only create projects for their own ULB
    my_ulb = ULB.query.get(current_user.ulb_id)
    ulbs = [my_ulb]

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        ulb_id = current_user.ulb_id  # Fixed to their ULB
        project_type = request.form.get('project_type', 'water_supply')
        description = request.form.get('description', '').strip()
        contractor = request.form.get('contractor', '').strip()
        cost = request.form.get('cost', 0.0, type=float)
        start_date_str = request.form.get('start_date', '')
        target_date_str = request.form.get('target_date', '')
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        funding_agency = request.form.get('funding_agency', '').strip()

        errors = []
        if not name:
            errors.append('Project name is required.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'ulb/project_form.html',
                project=None,
                ulbs=ulbs,
                edit_mode=False,
            )

        start_date = None
        target_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')

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

        # Activities
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

        boundary_file = request.files.get('boundary_file')
        if boundary_file and boundary_file.filename:
            from dashboards.state import _process_boundary_upload
            _process_boundary_upload(project, boundary_file)

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
        return redirect(url_for('ulb.project_detail', id=project.id))

    return render_template(
        'ulb/project_form.html',
        project=None,
        ulbs=ulbs,
        edit_mode=False,
    )


# ===========================================================================
# EDIT PROJECT — GET/POST /ulb/project/<int:id>/edit
# ===========================================================================
@ulb_bp.route('/project/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['ulb'])
def edit_project(id):
    """Edit an existing project within this ULB."""
    project = Project.query.get_or_404(id)
    _verify_project_ownership(project)
    
    my_ulb = ULB.query.get(current_user.ulb_id)
    ulbs = [my_ulb]

    if request.method == 'POST':
        old_values = {
            'name': project.name,
            'cost': project.cost,
            'status': project.status,
        }

        project.name = request.form.get('name', project.name).strip()
        # Ensure ulb_id stays the same
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

        boundary_file = request.files.get('boundary_file')
        if boundary_file and boundary_file.filename:
            from dashboards.state import _process_boundary_upload
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
        return redirect(url_for('ulb.project_detail', id=project.id))

    return render_template(
        'ulb/project_form.html',
        project=project,
        ulbs=ulbs,
        edit_mode=True,
    )


# ===========================================================================
# CHART DATA API — GET /ulb/api/chart-data
# ===========================================================================
@ulb_bp.route('/api/chart-data')
@login_required
@role_required(['ulb'])
def api_chart_data():
    """
    Returns ULB-specific chart data for Chart.js widgets.

    Response shape:
    {
      "projects": [
        {"name": "Water Supply Ph-1", "physical": 68.5, "financial": 55.0},
        ...
      ],
      "status_distribution": {
        "active": 4, "completed": 2, "delayed": 1, "critical": 0
      },
      "entry_stats": {
        "submitted": 12, "approved": 45, "rejected": 3, "draft": 2
      }
    }
    """
    projects = _ulb_projects_query().all()
    project_ids = [p.id for p in projects]

    # --- Per-project progress ----------------------------------------------
    project_data = [
        {
            'name': p.name,
            'physical': float(p.physical_progress or 0),
            'financial': float(p.financial_progress or 0),
        }
        for p in projects
    ]

    # --- Status distribution -----------------------------------------------
    status_distribution = {}
    for status_val in ('active', 'completed', 'delayed', 'critical'):
        status_distribution[status_val] = sum(
            1 for p in projects if p.status == status_val
        )

    # --- Entry stats -------------------------------------------------------
    entry_stats = {}
    for entry_status in ('draft', 'submitted', 'approved', 'rejected'):
        if project_ids:
            entry_stats[entry_status] = (
                SiteEntry.query
                .filter(
                    SiteEntry.project_id.in_(project_ids),
                    SiteEntry.status == entry_status,
                )
                .count()
            )
        else:
            entry_stats[entry_status] = 0

    return jsonify({
        'projects': project_data,
        'status_distribution': status_distribution,
        'entry_stats': entry_stats,
    })
