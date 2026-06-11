"""
RMMV Database Seed
==================
Populates the database with realistic sample data for the Tamil Nadu 
Remote Monitoring, Measurement & Verification dashboard.
Includes ULBs (Implementing Agencies), Users, Projects, Activities,
and full GIS Project Digital Twin data (ProjectBoundary, ProjectAsset, Device).
"""

import json
from datetime import datetime, date, timedelta, timezone
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
        name='Greater Chennai Corporation', district='Chennai',
        code='GCC-TN', state='Tamil Nadu', agency_type='Municipal Corporation'
    )
    ulb_kancheepuram = ULB(
        name='Kancheepuram Municipal Corporation', district='Kancheepuram',
        code='KMC-TN', state='Tamil Nadu', agency_type='Municipal Corporation'
    )
    ulb_madurai = ULB(
        name='Madurai Municipal Corporation', district='Madurai',
        code='MMC-TN', state='Tamil Nadu', agency_type='Municipal Corporation'
    )
    ulb_twad = ULB(
        name='TWAD Board', district='State-wide',
        code='TWAD-TN', state='Tamil Nadu', agency_type='Statutory Body'
    )
    ulb_cmwssb = ULB(
        name='CMWSSB', district='Chennai',
        code='CMWSSB-TN', state='Tamil Nadu', agency_type='Statutory Body'
    )
    
    db.session.add_all([ulb_chennai, ulb_kancheepuram, ulb_madurai, ulb_twad, ulb_cmwssb])
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
        name='Kancheepuram UGSS',
        ulb_id=ulb_kancheepuram.id,
        project_type='Sewerage',
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
        name='Kancheepuram STP',
        ulb_id=ulb_kancheepuram.id,
        project_type='Sewerage',
        cost=48.0,
        physical_progress=35.0,
        financial_progress=28.0,
        status='delayed',
        latitude=13.0120,
        longitude=80.2340,
        contractor='SPML',
        funding_agency='World Bank',
        start_date=date(2024, 6, 1),
        target_date=date(2025, 12, 31)
    )
    p3 = Project(
        name='Kancheepuram WSIS',
        ulb_id=ulb_kancheepuram.id,
        project_type='water_supply',
        cost=18.75,
        physical_progress=78.0,
        financial_progress=72.0,
        status='active',
        latitude=11.0168,
        longitude=76.9558,
        contractor='Itron',
        funding_agency='World Bank',
        start_date=date(2025, 3, 10),
        target_date=date(2026, 6, 30)
    )
    p4 = Project(
        name='Kancheepuram Intakes',
        ulb_id=ulb_kancheepuram.id,
        project_type='water_supply',
        cost=12.4,
        physical_progress=92.0,
        financial_progress=88.0,
        status='completed',
        latitude=10.9800,
        longitude=76.9200,
        contractor='VA Tech Wabag',
        funding_agency='World Bank',
        start_date=date(2023, 11, 1),
        target_date=date(2025, 2, 28)
    )
    p5 = Project(
        name='Madhavaram UGSS',
        ulb_id=ulb_cmwssb.id,
        project_type='Sewerage',
        cost=686.54,
        physical_progress=38.0,
        financial_progress=32.0,
        status='active',
        latitude=13.1482,
        longitude=80.2310,
        contractor='L&T Construction',
        funding_agency='KfW',
        start_date=date(2024, 3, 1),
        target_date=date(2027, 4, 30)
    )
    p6 = Project(
        name='Kodungaiyur Biomining Plant',
        ulb_id=ulb_chennai.id,
        project_type='Solid Waste Management',
        cost=641.0,
        physical_progress=33.0,
        financial_progress=28.0,
        status='active',
        latitude=13.1310,
        longitude=80.2560,
        contractor='Ramky Enviro Engineers',
        funding_agency='KfW',
        start_date=date(2023, 6, 1),
        target_date=date(2027, 12, 31)
    )
    projects = [p1, p2, p3, p4, p5, p6]
    db.session.add_all(projects)
    db.session.commit()

    # --- 4. Activities -------------------------------------------------------
    # --- 4a. Real activities for Kancheepuram UGSS (p1) from progress report ---
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
            activity_name='Manhole Erection (7,437 Nos)',
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

    # --- 4b. Generic activities for other projects ---
    for proj in [p2, p3, p4, p5, p6]:
        act1 = Activity(
            project_id=proj.id,
            activity_name='Excavation & Trenching',
            unit='RMT',
            target_qty=10000.0,
            achieved_qty=10000.0 * (proj.physical_progress / 100),
            weightage=0.20
        )
        act2 = Activity(
            project_id=proj.id,
            activity_name='Pipe Laying & Jointing',
            unit='RMT',
            target_qty=10000.0,
            achieved_qty=10000.0 * (proj.physical_progress / 100),
            weightage=0.35
        )
        act3 = Activity(
            project_id=proj.id,
            activity_name='Tank / Structure Construction',
            unit='Nos',
            target_qty=5.0,
            achieved_qty=5.0 * (proj.physical_progress / 100),
            weightage=0.30
        )
        act4 = Activity(
            project_id=proj.id,
            activity_name='Testing & Commissioning',
            unit='Nos',
            target_qty=5.0,
            achieved_qty=5.0 * (proj.physical_progress / 100),
            weightage=0.15
        )
        db.session.add_all([act1, act2, act3, act4])
    
    db.session.commit()

    # --- 5. Project Boundaries (GeoJSON) -------------------------------------
    def make_polygon(center_lat, center_lng, radius_deg=0.02):
        # A simple box around the center for demo purposes
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

    # --- 6. Project Assets (GIS Features) ------------------------------------
    # Add assets to P1 (Chennai Pipeline)
    assets_p1 = [
        ProjectAsset(
            project_id=p1.id,
            asset_type='pipeline',
            name='Main Trunk Pipeline (Zone A)',
            geojson=json.dumps({
                "type": "LineString",
                "coordinates": [
                    [80.2600, 13.0750], [80.2650, 13.0800], [80.2707, 13.0827], [80.2800, 13.0850]
                ]
            }),
            status='installation',
            properties_json=json.dumps({"diameter": "600mm", "material": "DI K9", "length": "3.5km"}),
            description='Primary transmission main'
        ),
        ProjectAsset(
            project_id=p1.id,
            asset_type='oht',
            name='Velachery OHT',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [80.2600, 13.0750]
            }),
            status='completed',
            properties_json=json.dumps({"capacity": "15 Lakh Litres", "type": "Overhead Tank"}),
            description='Distribution reservoir'
        ),
        ProjectAsset(
            project_id=p1.id,
            asset_type='pump_house',
            name='Zone A Booster Station',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [80.2800, 13.0850]
            }),
            status='testing',
            properties_json=json.dumps({"capacity": "500 HP", "pumps": 3}),
            description='Main booster pumping station'
        )
    ]
    
    # Add a WTP to P2
    assets_p2 = [
        ProjectAsset(
            project_id=p2.id,
            asset_type='wtp',
            name='Chembarambakkam WTP Module 2',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [80.2340, 13.0120]
            }),
            status='excavation',
            properties_json=json.dumps({"capacity": "80 MLD", "technology": "Rapid Sand Filtration"}),
            description='Water treatment plant expansion'
        )
    ]

    # Add meters to P3
    assets_p3 = [
        ProjectAsset(
            project_id=p3.id,
            asset_type='meter',
            name='Bulk Flow Meter - RS Puram',
            geojson=json.dumps({
                "type": "Point",
                "coordinates": [76.9558, 11.0168]
            }),
            status='completed',
            properties_json=json.dumps({"size": "400mm", "type": "Electromagnetic"}),
            description='Smart flow meter on main feeder'
        )
    ]

    db.session.add_all(assets_p1 + assets_p2 + assets_p3)
    db.session.commit()

    # --- 7. Devices ----------------------------------------------------------
    dev1 = Device(
        project_id=p1.id,
        device_type='drone',
        name='DJI Mavic 3 Enterprise - RMMV1',
        serial_number='DJI-M3E-001',
        status='active',
        latitude=13.0827,
        longitude=80.2707,
        last_sync=datetime.now(timezone.utc),
        metadata_json=json.dumps({"firmware": "v1.0.4", "battery": "82%"})
    )
    dev2 = Device(
        project_id=p1.id,
        device_type='cctv',
        name='Site Cam - Velachery OHT',
        serial_number='CCTV-HIK-042',
        status='active',
        latitude=13.0750,
        longitude=80.2600,
        last_sync=datetime.now(timezone.utc) - timedelta(minutes=5),
        metadata_json=json.dumps({"resolution": "4K", "network": "4G"})
    )
    
    db.session.add_all([dev1, dev2])
    db.session.commit()

    print("Database seeding completed.")
