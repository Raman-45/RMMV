"""
RMMV Dashboard — Database Models
==================================
Defines all SQLAlchemy ORM models for the application.
The shared `db` instance is created here and imported by app.py.

Models
------
- User            — Authentication & role-based identity (state / ulb / site)
- ULB             — Urban Local Body (municipality)
- Project         — Infrastructure project tied to a ULB
- Activity        — Line-item work activity within a project
- SiteEntry       — Daily quantity entry submitted by a site engineer
- AuditLog        — Immutable record of every data-changing action
- MediaFile       — Geo-tagged photo / video evidence for a project
- ProjectBoundary — GeoJSON polygon/multipolygon for project area
- ProjectAsset    — GIS features (pipelines, tanks, pump houses) within a project
- Document        — Non-media file uploads (PDFs, DWGs, reports)
- Device          — Monitoring devices registered to projects
"""

from datetime import datetime, timezone
import json

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Shared SQLAlchemy instance — imported by app.py and all blueprints
# ---------------------------------------------------------------------------
db = SQLAlchemy()


# ===========================================================================
# User
# ===========================================================================
class User(UserMixin, db.Model):
    """Application user with role-based access control.

    Roles
    -----
    state : PMU administrator — sees all ULBs and projects.
    ulb   : ULB officer — sees only their own ULB's projects.
    site  : Site engineer — submits daily entries & media for assigned ULB.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='site')  # state | ulb | site
    ulb_id = db.Column(db.Integer, db.ForeignKey('ulbs.id'), nullable=True)
    name = db.Column(db.String(150), nullable=False, default='')
    email = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # --- Relationships -------------------------------------------------------
    ulb = db.relationship('ULB', back_populates='users')
    site_entries = db.relationship('SiteEntry', foreign_keys='SiteEntry.engineer_id',
                                   back_populates='engineer', lazy='dynamic')
    reviewed_entries = db.relationship('SiteEntry', foreign_keys='SiteEntry.reviewed_by',
                                       back_populates='reviewer', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')
    uploaded_media = db.relationship('MediaFile', back_populates='uploader', lazy='dynamic')
    uploaded_documents = db.relationship('Document', back_populates='uploader', lazy='dynamic')

    # --- Password helpers ----------------------------------------------------
    def set_password(self, password: str) -> None:
        """Hash and store *password*."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return ``True`` if *password* matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f'<User {self.username} ({self.role})>'


# ===========================================================================
# ULB (Urban Local Body)
# ===========================================================================
class ULB(db.Model):
    """Implementing Agency — Municipal Corporation, Statutory Body, or SPV."""

    __tablename__ = 'ulbs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    district = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False, default='Tamil Nadu')
    code = db.Column(db.String(20), nullable=True, unique=True)
    agency_type = db.Column(db.String(50), nullable=False, default='Municipal Corporation')
    # agency_type: Municipal Corporation | Statutory Body | SPV | Municipality

    # --- Relationships -------------------------------------------------------
    users = db.relationship('User', back_populates='ulb', lazy='dynamic')
    projects = db.relationship('Project', back_populates='ulb', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<ULB {self.name}>'


# ===========================================================================
# Project
# ===========================================================================
class Project(db.Model):
    """Infrastructure project linked to a single ULB."""

    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    ulb_id = db.Column(db.Integer, db.ForeignKey('ulbs.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_type = db.Column(db.String(50), nullable=False, default='water_supply')
    # project_type: water_supply | sewerage | drainage | solid_waste | other
    cost = db.Column(db.Float, nullable=False, default=0.0)  # in Crores (₹)
    physical_progress = db.Column(db.Float, nullable=False, default=0.0)  # 0–100
    financial_progress = db.Column(db.Float, nullable=False, default=0.0)  # 0–100
    status = db.Column(db.String(20), nullable=False, default='active')  # active | completed | delayed | critical
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    contractor = db.Column(db.String(200), nullable=True)
    funding_agency = db.Column(db.String(100), nullable=True)  # World Bank | KfW | ADB | AMRUT | State Fund

    # --- Relationships -------------------------------------------------------
    ulb = db.relationship('ULB', back_populates='projects')
    activities = db.relationship('Activity', back_populates='project',
                                 lazy='dynamic', cascade='all, delete-orphan')
    entries = db.relationship('SiteEntry', back_populates='project',
                              lazy='dynamic', cascade='all, delete-orphan')
    media_files = db.relationship('MediaFile', back_populates='project',
                                  lazy='dynamic', cascade='all, delete-orphan')
    boundaries = db.relationship('ProjectBoundary', back_populates='project',
                                  lazy='dynamic', cascade='all, delete-orphan')
    assets = db.relationship('ProjectAsset', back_populates='project',
                              lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Document', back_populates='project',
                                 lazy='dynamic', cascade='all, delete-orphan')
    devices = db.relationship('Device', back_populates='project',
                               lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Project {self.name} [{self.status}]>'


# ===========================================================================
# Activity
# ===========================================================================
class Activity(db.Model):
    """Line-item work activity within a project.

    ``weightage`` values across all activities in a project should sum to 1.0.
    """

    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    activity_name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(50), nullable=False, default='units')
    target_qty = db.Column(db.Float, nullable=False, default=0.0)
    achieved_qty = db.Column(db.Float, nullable=False, default=0.0)
    weightage = db.Column(db.Float, nullable=False, default=0.0)  # fraction, e.g. 0.25

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='activities')
    site_entries = db.relationship('SiteEntry', back_populates='activity', lazy='dynamic')

    @property
    def progress_pct(self) -> float:
        """Return percentage completion for this activity."""
        if self.target_qty == 0:
            return 0.0
        return min(round((self.achieved_qty / self.target_qty) * 100, 2), 100.0)

    def __repr__(self) -> str:
        return f'<Activity {self.activity_name} ({self.progress_pct}%)>'


# ===========================================================================
# SiteEntry
# ===========================================================================
class SiteEntry(db.Model):
    """Daily quantity entry submitted by a site engineer.

    Workflow statuses: draft → submitted → approved / rejected
    """

    __tablename__ = 'site_entries'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    engineer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft | submitted | approved | rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='entries')
    engineer = db.relationship('User', foreign_keys=[engineer_id], back_populates='site_entries')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], back_populates='reviewed_entries')
    activity = db.relationship('Activity', back_populates='site_entries')

    def __repr__(self) -> str:
        return f'<SiteEntry #{self.id} [{self.status}]>'


# ===========================================================================
# AuditLog
# ===========================================================================
class AuditLog(db.Model):
    """Immutable audit trail for every state-changing action in the system."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    old_value = db.Column(db.Text, nullable=True)   # JSON-serialised
    new_value = db.Column(db.Text, nullable=True)   # JSON-serialised
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    user = db.relationship('User', back_populates='audit_logs')

    # --- Helper classmethod --------------------------------------------------
    @classmethod
    def log_action(cls, user_id, action, entity_type, entity_id,
                   old_value=None, new_value=None, ip_address=None):
        """Create and persist an audit log entry.

        Parameters
        ----------
        user_id : int | None
            The ID of the acting user (``None`` for system events).
        action : str
            Short verb phrase, e.g. ``"approved_entry"``, ``"login"``.
        entity_type : str
            Model name affected, e.g. ``"SiteEntry"``, ``"Project"``.
        entity_id : int | None
            Primary key of the affected entity.
        old_value : dict | str | None
            Previous state (will be JSON-serialised).
        new_value : dict | str | None
            New state (will be JSON-serialised).
        ip_address : str | None
            Client IP address.
        """
        entry = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=json.dumps(old_value) if old_value is not None else None,
            new_value=json.dumps(new_value) if new_value is not None else None,
            ip_address=ip_address,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    def __repr__(self) -> str:
        return f'<AuditLog {self.action} by user={self.user_id}>'


# ===========================================================================
# MediaFile
# ===========================================================================
class MediaFile(db.Model):
    """Geo-tagged photo or video evidence linked to a project."""

    __tablename__ = 'media_files'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_type = db.Column(db.String(10), nullable=False, default='image')  # image | video
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='media_files')
    uploader = db.relationship('User', back_populates='uploaded_media')

    def __repr__(self) -> str:
        return f'<MediaFile {self.original_filename} ({self.file_type})>'


# ===========================================================================
# ProjectBoundary
# ===========================================================================
class ProjectBoundary(db.Model):
    """GeoJSON polygon/multipolygon defining a project's geographic area."""

    __tablename__ = 'project_boundaries'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    geojson = db.Column(db.Text, nullable=False)  # Full GeoJSON geometry object
    boundary_type = db.Column(db.String(20), nullable=False, default='polygon')
    # boundary_type: polygon | multipolygon | circle
    area_sqm = db.Column(db.Float, nullable=True)  # Computed area in sq meters
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='boundaries')

    def get_geojson(self):
        """Return parsed GeoJSON dict."""
        try:
            return json.loads(self.geojson)
        except (json.JSONDecodeError, TypeError):
            return None

    def __repr__(self) -> str:
        return f'<ProjectBoundary project={self.project_id} ({self.boundary_type})>'


# ===========================================================================
# ProjectAsset
# ===========================================================================
class ProjectAsset(db.Model):
    """GIS feature within a project — pipelines, tanks, pump houses, etc.

    Stores geometry as GeoJSON and tracks construction status independently.

    Asset Types
    -----------
    pipeline    — Linear water/sewage pipeline (LineString)
    stp         — Sewage Treatment Plant (Point/Polygon)
    wtp         — Water Treatment Plant (Point/Polygon)
    oht         — Overhead Tank (Point)
    pump_house  — Pump House / Booster Station (Point)
    valve       — Valve Chamber (Point)
    meter       — Flow/Pressure Meter (Point)
    manhole     — Manhole / Inspection Chamber (Point)

    Construction Status
    -------------------
    not_started → excavation → installation → testing → completed
    """

    __tablename__ = 'project_assets'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    asset_type = db.Column(db.String(30), nullable=False)
    # asset_type: pipeline | stp | wtp | oht | pump_house | valve | meter | manhole
    name = db.Column(db.String(200), nullable=False)
    geojson = db.Column(db.Text, nullable=False)  # GeoJSON geometry (Point/LineString/Polygon)
    status = db.Column(db.String(20), nullable=False, default='not_started')
    # status: not_started | excavation | installation | testing | completed
    properties_json = db.Column(db.Text, nullable=True)  # JSON — diameter, material, capacity, etc.
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='assets')

    def get_geojson(self):
        """Return parsed GeoJSON geometry dict."""
        try:
            return json.loads(self.geojson)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_properties(self):
        """Return parsed properties dict."""
        try:
            return json.loads(self.properties_json) if self.properties_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self) -> str:
        return f'<ProjectAsset {self.name} ({self.asset_type}) [{self.status}]>'


# ===========================================================================
# Document
# ===========================================================================
class Document(db.Model):
    """Non-media file upload — PDFs, DWGs, survey reports, specifications."""

    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doc_type = db.Column(db.String(30), nullable=False, default='report')
    # doc_type: report | drawing | survey | specification | approval | other
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='documents')
    uploader = db.relationship('User', back_populates='uploaded_documents')

    def __repr__(self) -> str:
        return f'<Document {self.original_filename} ({self.doc_type})>'


# ===========================================================================
# Device
# ===========================================================================
class Device(db.Model):
    """Monitoring device registered to a project.

    Device Types
    ------------
    drone | cctv | flow_meter | pressure_meter | level_sensor | mobile
    """

    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    device_type = db.Column(db.String(30), nullable=False)
    # device_type: drone | cctv | flow_meter | pressure_meter | level_sensor | mobile
    name = db.Column(db.String(200), nullable=False)
    serial_number = db.Column(db.String(100), nullable=True, unique=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    # status: active | offline | maintenance
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)  # JSON — model, firmware, battery, etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relationships -------------------------------------------------------
    project = db.relationship('Project', back_populates='devices')

    def get_metadata(self):
        """Return parsed metadata dict."""
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self) -> str:
        return f'<Device {self.name} ({self.device_type}) [{self.status}]>'
