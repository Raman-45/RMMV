"""
RMMV Dashboard — Database Seed Data
=====================================
Populates the database with realistic demo data for Madhya Pradesh
water supply infrastructure projects. Idempotent — only seeds when
the database is empty.
"""

from datetime import date

from database.models import db, User, ULB, Project, Activity, SiteEntry


def seed_database(app_db):
    """Insert demo ULBs, users, projects, activities, and site entries.

    Parameters
    ----------
    app_db : SQLAlchemy
        The initialised SQLAlchemy extension instance (unused directly —
        we operate via the imported ``db`` / models, but accepted to
        match the call signature from ``app.py``).
    """

    # Guard: only seed into an empty database
    if User.query.first() is not None:
        return

    # ------------------------------------------------------------------
    # 1. Urban Local Bodies
    # ------------------------------------------------------------------
    ulb_bhopal = ULB(
        name='Bhopal Municipal Corporation',
        district='Bhopal',
        state='Madhya Pradesh',
        code='BMC-MP',
    )
    ulb_indore = ULB(
        name='Indore Municipal Corporation',
        district='Indore',
        state='Madhya Pradesh',
        code='IMC-MP',
    )
    ulb_jabalpur = ULB(
        name='Jabalpur Municipal Corporation',
        district='Jabalpur',
        state='Madhya Pradesh',
        code='JMC-MP',
    )
    db.session.add_all([ulb_bhopal, ulb_indore, ulb_jabalpur])
    db.session.flush()  # Assign IDs before FK references

    # ------------------------------------------------------------------
    # 2. Users
    # ------------------------------------------------------------------
    admin = User(
        username='admin',
        name='Rajesh Kumar (State PMU)',
        email='admin@rmmv.gov.in',
        role='state',
        ulb_id=None,
    )
    admin.set_password('admin123')

    ulb_officer = User(
        username='ulb_officer',
        name='Priya Sharma (ULB Officer)',
        email='priya@bmc.gov.in',
        role='ulb',
        ulb_id=ulb_bhopal.id,
    )
    ulb_officer.set_password('ulb123')

    site_eng = User(
        username='site_eng',
        name='Amit Verma (Site Engineer)',
        email='amit@bmc.gov.in',
        role='site',
        ulb_id=ulb_bhopal.id,
    )
    site_eng.set_password('site123')

    db.session.add_all([admin, ulb_officer, site_eng])
    db.session.flush()

    # ------------------------------------------------------------------
    # 3. Projects (2 per ULB = 6 total)
    # ------------------------------------------------------------------
    projects_data = [
        # --- Bhopal ---
        dict(
            name='Bhopal 24×7 Water Supply — Zone A Pipeline',
            ulb_id=ulb_bhopal.id,
            description='Installation of 45 km DI pipeline for 24×7 water supply in Zone A covering Kolar and Misrod areas.',
            cost=32.5,
            physical_progress=62.0,
            financial_progress=55.0,
            status='active',
            latitude=23.2599,
            longitude=77.4126,
            start_date=date(2024, 4, 1),
            target_date=date(2026, 3, 31),
            contractor='L&T Water & Effluent Treatment Ltd.',
        ),
        dict(
            name='Bhopal Kolar WTP Upgradation (80 MLD)',
            ulb_id=ulb_bhopal.id,
            description='Upgradation of existing Kolar Water Treatment Plant from 40 MLD to 80 MLD capacity.',
            cost=48.0,
            physical_progress=35.0,
            financial_progress=28.0,
            status='delayed',
            latitude=23.1740,
            longitude=77.4520,
            start_date=date(2024, 1, 15),
            target_date=date(2025, 12, 31),
            contractor='SPML Infra Ltd.',
        ),
        # --- Indore ---
        dict(
            name='Indore Smart Water Metering — Phase II',
            ulb_id=ulb_indore.id,
            description='Installation of 1,20,000 smart water meters with IoT-based AMI system across all 85 wards.',
            cost=18.75,
            physical_progress=78.0,
            financial_progress=72.0,
            status='active',
            latitude=22.7196,
            longitude=75.8577,
            start_date=date(2023, 10, 1),
            target_date=date(2025, 9, 30),
            contractor='Itron India Pvt. Ltd.',
        ),
        dict(
            name='Indore Yeshwant Sagar Intake Rehabilitation',
            ulb_id=ulb_indore.id,
            description='Rehabilitation and capacity augmentation of Yeshwant Sagar raw water intake structure and rising main.',
            cost=12.4,
            physical_progress=92.0,
            financial_progress=88.0,
            status='completed',
            latitude=22.6500,
            longitude=75.7700,
            start_date=date(2023, 4, 1),
            target_date=date(2025, 3, 31),
            contractor='VA Tech Wabag Ltd.',
        ),
        # --- Jabalpur ---
        dict(
            name='Jabalpur Narmada Bulk Water Transmission',
            ulb_id=ulb_jabalpur.id,
            description='Construction of 28 km bulk transmission main from Narmada River to Ranital WTP with 3 booster stations.',
            cost=42.0,
            physical_progress=18.0,
            financial_progress=12.0,
            status='critical',
            latitude=23.1815,
            longitude=79.9864,
            start_date=date(2024, 7, 1),
            target_date=date(2027, 6, 30),
            contractor='Megha Engineering & Infrastructures Ltd.',
        ),
        dict(
            name='Jabalpur Ward-Level Distribution Network — South Zone',
            ulb_id=ulb_jabalpur.id,
            description='Replacement of aged CI distribution network with HDPE pipes in 12 southern wards.',
            cost=8.6,
            physical_progress=45.0,
            financial_progress=40.0,
            status='active',
            latitude=23.1550,
            longitude=79.9400,
            start_date=date(2024, 6, 15),
            target_date=date(2026, 6, 14),
            contractor='Tata Projects Ltd.',
        ),
    ]

    project_objects = []
    for pdata in projects_data:
        proj = Project(**pdata)
        db.session.add(proj)
        project_objects.append(proj)

    db.session.flush()

    # ------------------------------------------------------------------
    # 4. Activities (3-4 per project)
    # ------------------------------------------------------------------
    # Template activities with unit / weightage sets
    activity_templates = [
        # (activity_name, unit, weightage)
        ('Excavation & Trenching', 'RMT', 0.20),
        ('Pipe Laying & Jointing', 'RMT', 0.35),
        ('Tank / Structure Construction', 'Nos', 0.30),
        ('Testing & Commissioning', 'Nos', 0.15),
    ]

    # Realistic target quantities per project (indexed by project order)
    qty_sets = [
        [45000, 45000, 8, 8],       # Bhopal Pipeline
        [5000, 3000, 4, 4],         # Bhopal WTP
        [12000, 120000, 200, 200],  # Indore Metering
        [3500, 3500, 2, 2],         # Indore Intake
        [28000, 28000, 3, 3],       # Jabalpur Transmission
        [18000, 18000, 12, 12],     # Jabalpur Distribution
    ]

    all_activities = []
    for idx, proj in enumerate(project_objects):
        progress_fraction = proj.physical_progress / 100.0
        for t_idx, (a_name, unit, weightage) in enumerate(activity_templates):
            target = qty_sets[idx][t_idx]
            # Simulate achieved qty proportional to overall progress (± variance)
            variance = 0.9 + (t_idx * 0.05)  # slight per-activity variance
            achieved = round(target * progress_fraction * variance, 1)
            achieved = min(achieved, target)  # cap at target

            act = Activity(
                project_id=proj.id,
                activity_name=a_name,
                unit=unit,
                target_qty=target,
                achieved_qty=achieved,
                weightage=weightage,
            )
            db.session.add(act)
            all_activities.append(act)

    db.session.flush()

    # ------------------------------------------------------------------
    # 5. Sample Site Entries
    # ------------------------------------------------------------------
    # Create entries for the first project's activities (Bhopal Pipeline)
    bhopal_acts = all_activities[0:4]  # first 4 activities belong to project 1

    entry_specs = [
        # (activity_index, quantity, status, remarks)
        (0, 250.0, 'approved', 'Excavation completed in Sector 12, soil condition stable.'),
        (0, 180.0, 'approved', 'Trenching through rocky terrain near Kolar Road.'),
        (1, 320.0, 'submitted', 'DI K9 pipes laid from Ch. 12+500 to Ch. 15+700.'),
        (1, 150.0, 'submitted', 'Pipe jointing work at road crossing near Misrod.'),
        (2, 1.0, 'draft', 'ESR foundation work started — Ward 45.'),
        (3, 0.5, 'draft', 'Pressure testing of pipeline segment A1–A5 in progress.'),
        (0, 200.0, 'rejected', 'Excavation measurement disputed — re-survey required.'),
    ]

    for act_idx, qty, status, remarks in entry_specs:
        entry = SiteEntry(
            project_id=project_objects[0].id,
            engineer_id=site_eng.id,
            activity_id=bhopal_acts[act_idx].id,
            quantity=qty,
            remarks=remarks,
            status=status,
            reviewed_by=ulb_officer.id if status in ('approved', 'rejected') else None,
            review_remarks='Verified on-site.' if status == 'approved'
                           else ('Measurement mismatch — please re-submit with photos.' if status == 'rejected' else None),
        )
        db.session.add(entry)

    # ------------------------------------------------------------------
    # Commit everything
    # ------------------------------------------------------------------
    db.session.commit()
    print('[SEED] Database seeded successfully with demo data.')
