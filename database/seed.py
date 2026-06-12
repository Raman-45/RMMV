"""
RMMV Database Seed
==================
Populates the database with realistic sample data for the Tamil Nadu 
Remote Monitoring, Measurement & Verification dashboard.
Includes ULBs (Implementing Agencies), Users, Projects, Activities,
and full GIS Project Digital Twin data (ProjectBoundary, ProjectAsset, Device).
"""

import json
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash

def seed_database(db):
    from database.models import (
        User, ULB, Project, Activity, SiteEntry, AuditLog, 
        ProjectBoundary, ProjectAsset, Device, MediaFile
    )

    # Only seed if database is empty
    if User.query.first() is not None:
        return

    print("Seeding database...")

    # --- 1. Implementing Agencies (ULBs / Statutory Bodies) -------------------
    ulb_chennai = ULB(
        name='GCC', district='Chennai',
        code='GCC-TN', state='Tamil Nadu', agency_type='Municipal Corporation'
    )
    ulb_kancheepuram = ULB(
        name='Kancheepuram Municipal Corporation', district='Kancheepuram',
        code='KMC-TN', state='Tamil Nadu', agency_type='Municipal Corporation'
    )
    ulb_cmwssb = ULB(
        name='CMWSSB', district='Chennai',
        code='CMWSSB-TN', state='Tamil Nadu', agency_type='Statutory Body'
    )
    
    db.session.add_all([ulb_chennai, ulb_kancheepuram, ulb_cmwssb])
    db.session.commit()

    # --- 2. Users ------------------------------------------------------------
    admin = User(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        role='state',
        name='Mr. Rajesh Kumar (State PMU)',
        email='rajeshkumar.pmu@tn.gov.in'
    )
    ulb_officer = User(
        username='ulb_officer',
        password_hash=generate_password_hash('ulb123'),
        role='ulb',
        ulb_id=ulb_chennai.id,
        name='Priya Sharma (Agency Officer)',
        email='priya.gcc@tn.gov.in'
    )
    site_eng = User(
        username='site_eng',
        password_hash=generate_password_hash('site123'),
        role='site',
        ulb_id=ulb_kancheepuram.id,
        name='Amit Verma (Site Engineer)',
        email='amit.site@tn.gov.in'
    )

    db.session.add_all([admin, ulb_officer, site_eng])
    db.session.commit()

    # --- 3. Projects ---------------------------------------------------------
    p1 = Project(
        name='Kancheepuram UGSS Package 1',
        ulb_id=ulb_kancheepuram.id,
        project_type='sewerage',
        cost=254.0,
        physical_progress=38.40,
        financial_progress=36.45,
        status='active',
        latitude=12.8342,
        longitude=79.7036,
        contractor='M/s Saravana Engineering & VVV Construction',
        funding_agency='World Bank',
        start_date=date(2024, 9, 1),
        target_date=date(2027, 9, 30),
        description='Progress as on 25 April 2026'
    )
    p2 = Project(
        name='kancheepuram UGSS package 2',
        ulb_id=ulb_kancheepuram.id,
        project_type='sewerage',
        cost=None,
        physical_progress=None,
        financial_progress=None,
        status='active',
        latitude=12.8355,
        longitude=79.7080,
        contractor=None,
        funding_agency='World Bank',
        start_date=None,
        target_date=None
    )
    p3 = Project(
        name='Kancheepuram WSIS Package 1',
        ulb_id=ulb_kancheepuram.id,
        project_type='water_supply',
        cost=None,
        physical_progress=None,
        financial_progress=None,
        status='active',
        latitude=12.8320,
        longitude=79.7010,
        contractor=None,
        funding_agency='World Bank',
        start_date=None,
        target_date=None
    )
    p4 = Project(
        name='kancheepuram WSIS Package 2',
        ulb_id=ulb_kancheepuram.id,
        project_type='water_supply',
        cost=None,
        physical_progress=None,
        financial_progress=None,
        status='active',
        latitude=12.8290,
        longitude=79.7055,
        contractor=None,
        funding_agency='World Bank',
        start_date=None,
        target_date=None
    )
    p5 = Project(
        name='Madhavaram UGSS',
        ulb_id=ulb_cmwssb.id,
        project_type='sewerage',
        cost=None,
        physical_progress=None,
        financial_progress=None,
        status='active',
        latitude=13.1482,
        longitude=80.2310,
        contractor=None,
        funding_agency='KfW',
        start_date=None,
        target_date=None
    )
    p6 = Project(
        name='kodungaiyur Biominning Plant',
        ulb_id=ulb_chennai.id,
        project_type='solid_waste',
        cost=None,
        physical_progress=None,
        financial_progress=None,
        status='active',
        latitude=13.1310,
        longitude=80.2560,
        contractor=None,
        funding_agency='KfW',
        start_date=None,
        target_date=None
    )
    projects = [p1, p2, p3, p4, p5, p6]
    db.session.add_all(projects)
    db.session.commit()

    # --- 4. Activities -------------------------------------------------------
    # --- Only real activities for Kancheepuram UGSS Package 1 (p1) ---
    p1_activities = [
        Activity(
            project_id=p1.id,
            activity_name='Sewer Line Laying (170.702 km)',
            unit='KM',
            target_qty=170.702,
            achieved_qty=79.300,
            weightage=0.30
        ),
        Activity(
            project_id=p1.id,
            activity_name='Machine Hole Erection (7,437 Nos)',
            unit='Nos',
            target_qty=7437.0,
            achieved_qty=4202.0,
            weightage=0.15
        ),
        Activity(
            project_id=p1.id,
            activity_name='House Service Connection (15,652 Nos)',
            unit='Nos',
            target_qty=15652.0,
            achieved_qty=4908.0,
            weightage=0.15
        ),
        Activity(
            project_id=p1.id,
            activity_name='Pumping Main (14.10 km)',
            unit='KM',
            target_qty=14.10,
            achieved_qty=2.141,
            weightage=0.10
        ),
        Activity(
            project_id=p1.id,
            activity_name='Pumping Stations (5 Nos)',
            unit='Nos',
            target_qty=5.0,
            achieved_qty=5.0,
            weightage=0.10
        ),
        Activity(
            project_id=p1.id,
            activity_name='Lifting Stations (7 Nos — LS-5A to LS-7C)',
            unit='Nos',
            target_qty=7.0,
            achieved_qty=6.0,
            weightage=0.10
        ),
        Activity(
            project_id=p1.id,
            activity_name='Road Restoration (194.54 km)',
            unit='KM',
            target_qty=194.54,
            achieved_qty=66.33,
            weightage=0.10
        ),
    ]
    db.session.add_all(p1_activities)
    db.session.commit()

    # --- 5. Project Boundaries (GeoJSON) -------------------------------------
    def make_polygon(center_lat, center_lng, radius_deg=0.02):
        return {
            "type": "Polygon",
            "coordinates": [[
                [center_lng - radius_deg, center_lat - radius_deg],
                [center_lng + radius_deg, center_lat - radius_deg],
                [center_lng + radius_deg, center_lat + radius_deg],
                [center_lng - radius_deg, center_lat + radius_deg],
                [center_lng - radius_deg, center_lat - radius_deg]
            ]]
        }

    for proj in projects:
        boundary = ProjectBoundary(
            project_id=proj.id,
            geojson=json.dumps(make_polygon(proj.latitude, proj.longitude)),
            boundary_type='polygon'
        )
        db.session.add(boundary)

    db.session.commit()

    # --- 6. Project Assets (GIS Features) — Only for Kancheepuram UGSS Package 1 (p1) ---
    assets_p1 = [
        ProjectAsset(
            project_id=p1.id,
            asset_type='pipeline',
            name='Main Trunk Pipeline (Zone A)',
            geojson=json.dumps({
                "type": "LineString",
                "coordinates": [
                    [79.695, 12.830], [79.700, 12.832], [79.7036, 12.8342], [79.710, 12.836]
                ]
            }),
            status='installation',
            properties_json=json.dumps({"diameter": "600mm", "material": "DI K9", "length": "3.5km"}),
            description='Primary transmission main'
        ),
        ProjectAsset(
            project_id=p1.id,
            asset_type='oht',
            name='Kancheepuram OHT',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [79.700, 12.832]
            }),
            status='completed',
            properties_json=json.dumps({"capacity": "15 Lakh Litres", "type": "Overhead Tank"}),
            description='Distribution reservoir'
        ),
        ProjectAsset(
            project_id=p1.id,
            asset_type='pump_house',
            name='Kancheepuram Pumping Station',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [79.710, 12.836]
            }),
            status='testing',
            properties_json=json.dumps({"capacity": "500 HP", "pumps": 3}),
            description='Main booster pumping station'
        )
    ]
    
    db.session.add_all(assets_p1)
    db.session.commit()

    # --- 7. Devices — Only for Kancheepuram UGSS Package 1 (p1) ---
    dev1 = Device(
        project_id=p1.id,
        device_type='drone',
        name='DJI Mavic 3 Enterprise - RMMV1',
        serial_number='DJI-M3E-001',
        status='active',
        latitude=12.8342,
        longitude=79.7036,
        last_sync=datetime.now(timezone.utc),
        metadata_json=json.dumps({"firmware": "v1.0.4", "battery": "82%"})
    )
    dev2 = Device(
        project_id=p1.id,
        device_type='cctv',
        name='Site Cam - Kancheepuram OHT',
        serial_number='CCTV-HIK-042',
        status='active',
        latitude=12.8320,
        longitude=79.7000,
        last_sync=datetime.now(timezone.utc),
        metadata_json=json.dumps({"resolution": "4K", "network": "4G"})
    )
    
    db.session.add_all([dev1, dev2])
    db.session.commit()

    print("Database seeding completed.")
