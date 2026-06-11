"""
Site Engineer Dashboard Blueprint — /site
==========================================
Provides the Site engineer with tools to submit daily work entries,
upload geo-tagged media, and track the status of previous submissions.

All routes require the 'site' role.
"""

import json
import os
import uuid
from datetime import datetime, date, timezone

from flask import (
    Blueprint, render_template, request, jsonify, abort, flash, redirect,
    url_for, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from database.models import (
    db, User, ULB, Project, Activity, SiteEntry, AuditLog, MediaFile,
    ProjectBoundary, ProjectAsset, Document, Device
)
from auth.permissions import role_required, get_user_projects

# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
site_bp = Blueprint('site', __name__, url_prefix='/site')

# Allowed file extensions for media uploads
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _site_projects():
    """Return projects visible to the current site engineer (same ULB)."""
    return Project.query.filter_by(ulb_id=current_user.ulb_id).all()


def _create_audit_log(action, entity_type, entity_id,
                      old_value=None, new_value=None):
    """Insert an AuditLog record for the current user."""
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


def _allowed_file(filename):
    """Check whether the upload has an allowed extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _detect_file_type(filename):
    """Return 'image' or 'video' based on file extension."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    return 'image'


# ===========================================================================
# DASHBOARD — GET /site/
# ===========================================================================
@site_bp.route('/')
@login_required
@role_required(['site'])
def dashboard():
    """
    Site engineer landing page.
    Shows quick stats: today's submissions, pending entries, and
    approved/rejected counts.
    """
    projects = _site_projects()
    project_ids = [p.id for p in projects]

    today = date.today()

    # --- Quick KPIs --------------------------------------------------------
    if project_ids:
        base_query = SiteEntry.query.filter(
            SiteEntry.engineer_id == current_user.id
        )

        # Entries submitted today
        today_count = (
            base_query
            .filter(db.func.date(SiteEntry.created_at) == today)
            .count()
        )

        submitted_count = base_query.filter(
            SiteEntry.status == 'submitted'
        ).count()

        approved_count = base_query.filter(
            SiteEntry.status == 'approved'
        ).count()

        rejected_count = base_query.filter(
            SiteEntry.status == 'rejected'
        ).count()

        draft_count = base_query.filter(
            SiteEntry.status == 'draft'
        ).count()
    else:
        today_count = submitted_count = approved_count = 0
        rejected_count = draft_count = 0

    # Recent entries for the dashboard widget
    recent_entries = (
        SiteEntry.query
        .filter_by(engineer_id=current_user.id)
        .order_by(desc(SiteEntry.created_at))
        .limit(10)
        .all()
    )

    return render_template(
        'site/dashboard.html',
        projects=projects,
        pending_count=submitted_count,
        submitted_today=today_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        draft_count=draft_count,
        recent_entries=recent_entries,
        now=datetime.now(timezone.utc),
    )


# ===========================================================================
# SUBMIT ENTRY — GET/POST /site/submit-entry
# ===========================================================================
@site_bp.route('/submit-entry', methods=['GET', 'POST'])
@login_required
@role_required(['site'])
def submit_entry():
    """
    GET:  Render the entry-submission form with project/activity selectors.
    POST: Create a new SiteEntry with status='submitted'.

    Expected form fields (POST):
      - project_id   (int, required)
      - activity_id  (int, required)
      - quantity     (float, required)
      - remarks      (str, optional)
      - latitude     (float, optional — from GPS capture)
      - longitude    (float, optional — from GPS capture)
    """
    projects = _site_projects()

    # Build a mapping of project_id → activities for the template
    activities_by_project = {}
    for proj in projects:
        activities_by_project[proj.id] = (
            Activity.query
            .filter_by(project_id=proj.id)
            .order_by(Activity.id)
            .all()
        )
    activities = [a for acts in activities_by_project.values() for a in acts]

    if request.method == 'POST':
        # --- Validate inputs -----------------------------------------------
        project_id = request.form.get('project_id', type=int)
        activity_id = request.form.get('activity_id', type=int)
        quantity = request.form.get('quantity', type=float)
        remarks = request.form.get('remarks', '').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)

        # Basic validation
        errors = []
        if not project_id:
            errors.append('Please select a project.')
        if not activity_id:
            errors.append('Please select an activity.')
        if quantity is None or quantity <= 0:
            errors.append('Quantity must be a positive number.')

        # Verify project belongs to user's ULB
        if project_id:
            project = Project.query.get(project_id)
            if not project or project.ulb_id != current_user.ulb_id:
                errors.append('Invalid project selection.')

        # Verify activity belongs to the selected project
        if activity_id and project_id:
            activity = Activity.query.get(activity_id)
            if not activity or activity.project_id != project_id:
                errors.append('Invalid activity selection.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'site/submit_entry.html',
                projects=projects,
                activities_by_project=activities_by_project,
            )

        # --- Create the entry ----------------------------------------------
        now = datetime.now(timezone.utc)
        entry = SiteEntry(
            project_id=project_id,
            engineer_id=current_user.id,
            activity_id=activity_id,
            quantity=quantity,
            remarks=remarks,
            status='submitted',
            created_at=now,
            updated_at=now,
        )
        db.session.add(entry)
        db.session.flush()  # get entry.id for audit log

        # --- Audit log -----------------------------------------------------
        _create_audit_log(
            action='submit_entry',
            entity_type='SiteEntry',
            entity_id=entry.id,
            new_value={
                'project_id': project_id,
                'activity_id': activity_id,
                'quantity': quantity,
                'remarks': remarks,
                'latitude': latitude,
                'longitude': longitude,
            },
        )

        db.session.commit()
        flash('Site entry submitted successfully!', 'success')
        return redirect(url_for('site.dashboard'))

    # GET — render the form
    return render_template(
        'site/submit_entry.html',
        projects=projects,
        activities_by_project=activities_by_project,
    )


# ===========================================================================
# UPLOAD MEDIA — GET/POST /site/upload-media
# ===========================================================================
@site_bp.route('/upload-media', methods=['GET', 'POST'])
@login_required
@role_required(['site'])
def upload_media():
    """
    GET:  Render the media upload form.
    POST: Save the uploaded file and create a MediaFile record.

    Expected form fields (POST):
      - project_id   (int, required)
      - file         (file upload, required)
      - description  (str, optional)
      - latitude     (float, optional)
      - longitude    (float, optional)
    """
    projects = _site_projects()

    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        description = request.form.get('description', '').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)

        # --- Validate -----------------------------------------------------
        errors = []
        if not project_id:
            errors.append('Please select a project.')
        else:
            project = Project.query.get(project_id)
            if not project or project.ulb_id != current_user.ulb_id:
                errors.append('Invalid project selection.')

        uploaded_file = request.files.get('media_file')
        if not uploaded_file or uploaded_file.filename == '':
            errors.append('Please select a file to upload.')
        elif not _allowed_file(uploaded_file.filename):
            errors.append(
                'File type not allowed. Accepted: '
                + ', '.join(sorted(ALLOWED_EXTENSIONS))
            )

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'site/upload_media.html',
                projects=projects,
            )

        # --- Save file to disk --------------------------------------------
        original_filename = secure_filename(uploaded_file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{file_ext}"

        upload_dir = os.path.join(
            current_app.root_path, 'static', 'uploads', str(project_id)
        )
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, unique_name)
        uploaded_file.save(file_path)

        # Relative path stored in DB (for serving via static files)
        relative_path = f"uploads/{project_id}/{unique_name}"

        # --- Create MediaFile record --------------------------------------
        file_type = _detect_file_type(original_filename)

        media = MediaFile(
            project_id=project_id,
            uploaded_by=current_user.id,
            file_type=file_type,
            filename=unique_name,
            original_filename=original_filename,
            path=relative_path,
            latitude=latitude,
            longitude=longitude,
            description=description,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(media)
        db.session.flush()

        # --- Audit log ----------------------------------------------------
        _create_audit_log(
            action='upload_media',
            entity_type='MediaFile',
            entity_id=media.id,
            new_value={
                'project_id': project_id,
                'file_type': file_type,
                'filename': unique_name,
                'original_filename': original_filename,
            },
        )

        db.session.commit()
        flash('Media uploaded successfully!', 'success')
        return redirect(url_for('site.dashboard'))

    # GET — render the form
    return render_template(
        'site/upload_media.html',
        projects=projects,
    )


# ===========================================================================
# MY ENTRIES — GET /site/my-entries
# ===========================================================================
@site_bp.route('/my-entries')
@login_required
@role_required(['site'])
def my_entries():
    """
    Paginated list of all SiteEntry records created by the current user.

    Status badge colours:
      draft    → grey
      submitted → blue
      approved  → green
      rejected  → red
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Optional status filter
    status_filter = request.args.get('status', type=str)
    query = SiteEntry.query.filter_by(engineer_id=current_user.id)

    valid_statuses = ('draft', 'submitted', 'approved', 'rejected')
    if status_filter and status_filter in valid_statuses:
        query = query.filter(SiteEntry.status == status_filter)

    pagination = (
        query
        .order_by(desc(SiteEntry.created_at))
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        'site/my_entries.html',
        entries=pagination.items,
        pagination=pagination,
        selected_status=status_filter,
    )


# ===========================================================================
# LOCATION API — GET /site/api/location
# ===========================================================================
@site_bp.route('/api/location')
@login_required
@role_required(['site'])
def api_location():
    """
    Accept lat/lng query parameters and return them as JSON.

    In a production environment this would integrate with a reverse-geocoding
    service (e.g. Nominatim, Google Maps) to resolve the coordinates into a
    human-readable address.  For now it echoes the coordinates back.

    Query params:
      ?lat=<float>&lng=<float>

    Response:
    {
      "lat": 23.2599,
      "lng": 77.4126,
      "address": "23.2599°N, 77.4126°E",
      "status": "ok"
    }
    """
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)

    if lat is None or lng is None:
        return jsonify({
            'status': 'error',
            'message': 'lat and lng query parameters are required.',
        }), 400

    # Echo coordinates with a formatted address placeholder
    hemisphere_ns = 'N' if lat >= 0 else 'S'
    hemisphere_ew = 'E' if lng >= 0 else 'W'
    address = f"{abs(lat):.4f}°{hemisphere_ns}, {abs(lng):.4f}°{hemisphere_ew}"

    return jsonify({
        'lat': lat,
        'lng': lng,
        'address': address,
        'status': 'ok',
    })


# ===========================================================================
# PROJECT GIS DATA API — GET /site/project/<int:id>/gis-data
# ===========================================================================
@site_bp.route('/project/<int:id>/gis-data')
@login_required
@role_required(['site'])
def project_gis_data(id):
    """Returns GeoJSON data for a project's GIS view (Site-scoped)."""
    project = Project.query.get_or_404(id)
    if project.ulb_id != current_user.ulb_id:
        abort(403)

    from dashboards.state import _build_gis_response
    return _build_gis_response(project)


# ===========================================================================
# MY MEDIA — GET /site/my-media
# ===========================================================================
@site_bp.route('/my-media')
@login_required
@role_required(['site'])
def my_media():
    """List all media files uploaded by the current site engineer."""
    media_files = (
        MediaFile.query
        .filter_by(uploaded_by=current_user.id)
        .order_by(desc(MediaFile.created_at))
        .all()
    )
    return render_template('site/my_media.html', media_files=media_files)


# ===========================================================================
# DELETE MEDIA — POST /site/media/<int:id>/delete
# ===========================================================================
@site_bp.route('/media/<int:id>/delete', methods=['POST'])
@login_required
@role_required(['site'])
def delete_media(id):
    """Delete a media file uploaded by the current site engineer."""
    media = MediaFile.query.get_or_404(id)

    # Only allow deletion of own uploads
    if media.uploaded_by != current_user.id:
        flash('You can only delete your own uploads.', 'danger')
        return redirect(url_for('site.my_media'))

    # Delete file from disk
    file_path = os.path.join(current_app.root_path, 'static', media.path)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Audit log
    _create_audit_log(
        action='delete_media',
        entity_type='MediaFile',
        entity_id=media.id,
        old_value={
            'filename': media.original_filename,
            'project_id': media.project_id,
        },
    )

    # Delete from database
    db.session.delete(media)
    db.session.commit()

    flash('Media deleted successfully.', 'success')
    return redirect(url_for('site.my_media'))
