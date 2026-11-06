"""
==============================================================================
SAINIK SAHAYAK — Digital Welfare Assistance & Grievance Guidance Platform
Academic Engineering Project | Refined Public-Service UI/UX Architecture
==============================================================================
"""

import os
import sqlite3
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sainik-sahayak-prototype-secret-key-2026'
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sainik_sahayak.db')

# ============================================================================
# DATABASE UTILITIES (Preserved SQLite/MySQL compatible layer)
# ============================================================================
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone_number TEXT,
        beneficiary_category TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schemes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_code TEXT UNIQUE NOT NULL,
        scheme_name TEXT NOT NULL,
        category TEXT NOT NULL,
        purpose TEXT NOT NULL,
        short_description TEXT NOT NULL,
        detailed_benefit TEXT NOT NULL,
        eligibility_conditions TEXT NOT NULL,
        application_process TEXT NOT NULL,
        official_source_name TEXT NOT NULL,
        official_portal_url TEXT NOT NULL,
        last_verified TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheme_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_id INTEGER NOT NULL,
        document_name TEXT NOT NULL,
        is_mandatory INTEGER DEFAULT 1,
        notes TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prototype_grievances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference_number TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        guest_name TEXT,
        guest_email TEXT,
        category TEXT NOT NULL,
        issue_summary TEXT NOT NULL,
        detailed_description TEXT NOT NULL,
        status TEXT DEFAULT 'Submitted',
        official_recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_schemes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        scheme_id INTEGER NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, scheme_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (scheme_id) REFERENCES schemes(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM schemes")
    if cursor.fetchone()[0] == 0:
        verified_schemes = [
            (
                'KSB-EDU-01',
                'Financial Assistance for Education of Children of ESM (RMDF)',
                'Dependent of Ex-serviceman',
                'Education',
                'Monthly scholarship support for dependent school and college-going children of low-income ex-servicemen.',
                '₹1,000 per month per child (Class 1 to Graduation/Post-Graduation), up to a maximum of two dependent children.',
                'Applicable for wards of Ex-Servicemen / Widows up to the rank of Havildar/equivalent in Navy/Air Force. Student must have passed the previous academic examination.',
                'Apply online through the Kendriya Sainik Board (KSB) portal. Applications are routed through the respective Zila Sainik Board (ZSB).',
                'Kendriya Sainik Board (RMDF)',
                'https://ksb.gov.in',
                '2026-01-15'
            ),
            (
                'KSB-MARR-02',
                'Daughter Marriage Financial Grant (RMDF)',
                'Ex-serviceman / Veteran',
                'Marriage Assistance',
                'One-time financial assistance to assist eligible non-commissioned veterans and war widows with daughter marriage expenses.',
                'One-time grant of ₹50,000 for the marriage of up to two daughters.',
                'Eligible for Ex-Servicemen and widows up to the rank of Havildar/equivalent. Marriage must be solemnized within the applicable financial window.',
                'Submit an online application on the KSB portal with marriage certificate and discharge book within 1 year of marriage.',
                'Kendriya Sainik Board (RMDF)',
                'https://ksb.gov.in',
                '2026-01-15'
            ),
            (
                'KSB-PENURY-03',
                'Penury Grant for Non-Pensioner Ex-Servicemen (RMDF)',
                'Ex-serviceman / Veteran',
                'Financial Relief',
                'Monthly subsistence grant to senior aged ex-servicemen or widows who are not in receipt of any official service pension.',
                '₹4,000 per month payable on regular life certificate verification.',
                'Ex-Serviceman / Widow aged 65 years and above, non-pensioner, rank up to Havildar, in indigent financial circumstances.',
                'Apply online through KSB with certification from Zila Sainik Welfare Office (ZSWO) confirming non-pensioner status.',
                'Kendriya Sainik Board (RMDF)',
                'https://ksb.gov.in',
                '2026-01-15'
            ),
            (
                'DESW-PMSS-04',
                'Prime Minister Scholarship Scheme (PMSS)',
                'Dependent of Ex-serviceman',
                'Education',
                'Merit scholarship for dependent wards and widows of ESM pursuing recognized technical/professional degree courses.',
                '₹2,500 per month for boys (₹30,000/yr) and ₹3,000 per month for girls (₹36,000/yr) paid annually.',
                'Wards of deceased/ex-service personnel below officer rank. Minimum 60% marks in 10+2/MEQ. Professional courses must be AICTE/UGC approved.',
                'Submit online through the KSB portal with a bonafide certificate from the university/institution.',
                'Department of Ex-Servicemen Welfare (DESW)',
                'https://desw.gov.in',
                '2026-02-01'
            ),
            (
                'ECHS-MED-05',
                'Ex-Servicemen Contributory Health Scheme (ECHS)',
                'Ex-serviceman / Veteran',
                'Healthcare',
                'Cashless healthcare for ex-servicemen pensioners and their eligible dependents across polyclinics & empaneled hospitals.',
                'Cashless out-patient and in-patient treatment across designated polyclinics, military hospitals, and empaneled private hospitals.',
                'Armed forces personnel receiving service/disability pension and their verified dependent family members.',
                'Apply for 64-KB ECHS Smart Card via the central ECHS online portal with PPO and Service Discharge book.',
                'Department of Ex-Servicemen Welfare',
                'https://echs.gov.in',
                '2026-01-20'
            )
        ]

        cursor.executemany("""
        INSERT INTO schemes (
            scheme_code, scheme_name, category, purpose, short_description,
            detailed_benefit, eligibility_conditions, application_process,
            official_source_name, official_portal_url, last_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, verified_schemes)

        docs = [
            (1, 'Discharge Book / Service Certificate copy', 1, 'Showing personal details, family particulars, and rank'),
            (1, 'Marksheet of previous class passed', 1, 'Attested by school or college principal'),
            (1, 'Bonafide Certificate from Current Institution', 1, 'Confirming regular student enrollment'),
            (1, 'First page of Bank Passbook (cancelled cheque)', 1, 'Clear IFSC code and applicant account name'),
            (2, 'Discharge Book of ESM', 1, 'Pages showing service record and dependent details'),
            (2, 'Official Marriage Certificate', 1, 'Issued by Registrar of Marriages / Municipal Authority'),
            (2, 'Age Proof of the Daughter', 1, '10th certificate or official birth certificate'),
            (3, 'Discharge Certificate', 1, 'Confirming date of enrollment and discharge'),
            (3, 'Age Proof confirming 65+ years', 1, 'Voter ID or official birth record'),
            (3, 'Non-Pensioner Certificate from ZSWO', 1, 'Signed by Zila Sainik Welfare Officer'),
            (4, 'Bonafide Student Certificate', 1, 'Signed by Dean / Principal of AICTE/UGC college'),
            (4, 'Minimum Education Qualification Marksheet (10+2/Diploma)', 1, 'Minimum 60% aggregate'),
            (5, 'Pension Payment Order (PPO)', 1, 'Original or digitally authenticated copy'),
            (5, 'Discharge Book', 1, 'All pages containing service records')
        ]
        cursor.executemany("""
        INSERT INTO scheme_documents (scheme_id, document_name, is_mandatory, notes)
        VALUES (?, ?, ?, ?)
        """, docs)

        admin_pass_hash = generate_password_hash('Admin@Sainik2026')
        cursor.execute("""
        INSERT INTO users (full_name, email, password_hash, beneficiary_category, role)
        VALUES (?, ?, ?, ?, ?)
        """, ('Sainik Sahayak Review Desk', 'admin@sainiksahayak.internal', admin_pass_hash, 'Ex-serviceman / Veteran', 'admin'))

    conn.commit()
    conn.close()

# ============================================================================
# ASSET BOOTSTRAPPER (Injects refined CSS and Jinja2 templates)
# ============================================================================
def setup_frontend_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tpl_dir = os.path.join(base_dir, 'templates')
    css_dir = os.path.join(base_dir, 'static', 'css')
    os.makedirs(tpl_dir, exist_ok=True)
    os.makedirs(css_dir, exist_ok=True)

    # 1. REFINED PUBLIC-SERVICE DESIGN SYSTEM (styles.css)
    css_content = """/* ==========================================================================
   SAINIK SAHAYAK — REFINED PUBLIC SERVICE DESIGN SYSTEM
   Palette: Navy #17365D | Olive #687B55 | Canvas #F5F6F3 | Surface #FFFFFF
   ========================================================================== */

:root {
  --primary-navy: #17365D;
  --primary-navy-dark: #0f243f;
  --secondary-olive: #687B55;
  --secondary-olive-dark: #4e5e40;
  --canvas-bg: #F5F6F3;
  --surface-white: #FFFFFF;
  --text-main: #202B36;
  --text-muted: #65717D;
  --border-subtle: #E1E5E8;
  --border-strong: #C8CED4;
  --accent-gold: #C49A50;
  --state-danger: #a63232;
  --state-success: #2e6930;
  --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --max-width: 1280px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --shadow-subtle: 0 1px 3px rgba(0, 0, 0, 0.05);
  --shadow-card: 0 1px 4px rgba(32, 43, 54, 0.06);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-family);
  background-color: var(--canvas-bg);
  color: var(--text-main);
  line-height: 1.55;
  font-size: 16px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
}

/* Prototype Disclaimer Banner */
.notice-bar {
  background-color: #202B36;
  color: #F5F6F3;
  font-size: 0.8125rem;
  padding: 8px 16px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  letter-spacing: 0.01em;
}

.notice-bar strong {
  color: var(--accent-gold);
}

/* Header & Navigation Bar */
.site-header {
  background-color: var(--surface-white);
  border-bottom: 2px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.nav-container {
  max-width: var(--max-width);
  width: 92%;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 76px;
  padding: 8px 0;
}

.brand {
  display: flex;
  align-items: center;
  text-decoration: none;
  gap: 14px;
  flex-shrink: 0;
}

.brand-icon {
  width: 42px;
  height: 42px;
  background-color: var(--primary-navy);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.15rem;
  border-radius: var(--radius-sm);
  border-left: 4px solid var(--secondary-olive);
}

.brand-text-block {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--primary-navy);
  letter-spacing: -0.015em;
  line-height: 1.2;
}

.brand-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.05em;
  margin-top: 2px;
}

.nav-wrapper {
  display: flex;
  align-items: center;
  gap: 28px;
}

.nav-links {
  display: flex;
  gap: 22px;
  list-style: none;
  align-items: center;
}

.nav-links a {
  text-decoration: none;
  color: var(--text-main);
  font-size: 0.9375rem;
  font-weight: 500;
  padding: 8px 2px;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
}

.nav-links a:hover {
  color: var(--primary-navy);
  border-bottom-color: var(--secondary-olive);
}

.nav-links a.active {
  color: var(--primary-navy);
  font-weight: 600;
  border-bottom-color: var(--primary-navy);
}

.auth-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Mobile Navigation Hamburger */
.mobile-nav-toggle {
  display: none;
  background: none;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  cursor: pointer;
}

.mobile-nav-toggle span {
  display: block;
  width: 22px;
  height: 2px;
  background-color: var(--primary-navy);
  margin: 4px 0;
  transition: 0.2s;
}

/* Main Layout Wrapper */
.main-wrapper {
  flex: 1;
  max-width: var(--max-width);
  width: 92%;
  margin: 0 auto;
  padding: 36px 0 64px;
}

/* High-Contrast Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  font-size: 0.9375rem;
  font-weight: 600;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-decoration: none;
  border: 1px solid transparent;
  line-height: 1.25;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
}

.btn-primary {
  background-color: var(--primary-navy) !important;
  color: #ffffff !important;
  border-color: var(--primary-navy) !important;
}

.btn-primary:hover, .btn-primary:focus {
  background-color: var(--primary-navy-dark) !important;
  border-color: var(--primary-navy-dark) !important;
  color: #ffffff !important;
}

.btn-secondary {
  background-color: var(--surface-white) !important;
  color: var(--primary-navy) !important;
  border: 1px solid var(--border-strong) !important;
}

.btn-secondary:hover, .btn-secondary:focus {
  background-color: #f1f4f8 !important;
  border-color: var(--primary-navy) !important;
  color: var(--primary-navy-dark) !important;
}

.btn-olive {
  background-color: var(--secondary-olive) !important;
  color: #ffffff !important;
  border-color: var(--secondary-olive) !important;
}

.btn-olive:hover, .btn-olive:focus {
  background-color: var(--secondary-olive-dark) !important;
  border-color: var(--secondary-olive-dark) !important;
  color: #ffffff !important;
}

.btn-logout {
  background-color: transparent !important;
  color: var(--primary-navy) !important;
  border: 1px solid var(--border-strong) !important;
}

.btn-logout:hover {
  background-color: #fdf2f2 !important;
  color: var(--state-danger) !important;
  border-color: var(--state-danger) !important;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 0.85rem;
}

/* Alerts / Notifications */
.alert {
  padding: 14px 18px;
  border-radius: var(--radius-sm);
  margin-bottom: 24px;
  font-size: 0.9375rem;
  border: 1px solid transparent;
}

.alert-success {
  background-color: #edf7ed;
  color: var(--state-success);
  border-color: #c8e6c9;
}

.alert-error {
  background-color: #fdf2f2;
  color: var(--state-danger);
  border-color: #f5c6cb;
}

.alert-info {
  background-color: #eef3f8;
  color: var(--primary-navy);
  border-color: #c7d8e8;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 4px 9px;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 3px;
  background-color: #eef3f8;
  color: var(--primary-navy);
  letter-spacing: 0.02em;
}

.badge-olive {
  background-color: #f1f4ed;
  color: var(--secondary-olive-dark);
}

/* Hero Section */
.hero-box {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 44px 44px;
  margin-bottom: 40px;
  border-left: 6px solid var(--primary-navy);
  box-shadow: var(--shadow-card);
}

.hero-heading {
  font-size: 2.25rem;
  color: var(--primary-navy);
  margin: 12px 0 14px;
  line-height: 1.25;
  font-weight: 700;
  max-width: 960px;
}

.hero-desc {
  font-size: 1.125rem;
  color: var(--text-muted);
  max-width: 860px;
  margin-bottom: 28px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

/* Service Grid (4 Core Columns) */
.section-header {
  margin-bottom: 22px;
}

.section-title {
  font-size: 1.45rem;
  color: var(--primary-navy);
  font-weight: 700;
}

.section-subtitle {
  color: var(--text-muted);
  font-size: 0.95rem;
  margin-top: 2px;
}

.service-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.card {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: var(--shadow-card);
}

.card h3 {
  font-size: 1.15rem;
  color: var(--primary-navy);
  margin: 10px 0 8px;
  line-height: 1.3;
}

.card p {
  color: var(--text-muted);
  font-size: 0.925rem;
  line-height: 1.55;
  margin-bottom: 20px;
  flex: 1;
}

/* Process Section */
.process-box {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 36px 40px;
  margin-bottom: 36px;
  box-shadow: var(--shadow-card);
}

.process-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
  margin-top: 24px;
}

.process-step {
  border-top: 3px solid var(--secondary-olive);
  padding-top: 16px;
}

.process-step-num {
  font-weight: 700;
  color: var(--secondary-olive);
  font-size: 0.8125rem;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}

.process-step-title {
  font-weight: 700;
  color: var(--primary-navy);
  font-size: 1.05rem;
  margin-bottom: 6px;
}

.process-step p {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.5;
}

/* Scheme Cards */
.scheme-card {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 26px;
  margin-bottom: 18px;
  box-shadow: var(--shadow-card);
}

.scheme-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.scheme-benefit-box {
  background-color: var(--canvas-bg);
  padding: 14px 18px;
  border-radius: var(--radius-sm);
  font-size: 0.9375rem;
  margin: 14px 0 16px;
  border-left: 3px solid var(--secondary-olive);
}

.scheme-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

/* Forms */
.form-panel {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 34px 38px;
  box-shadow: var(--shadow-card);
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 0.925rem;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 6px;
}

.form-control, .form-select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  color: var(--text-main);
  background-color: #ffffff;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-control:focus, .form-select:focus {
  border-color: var(--primary-navy);
  box-shadow: 0 0 0 2px rgba(23, 54, 93, 0.15);
}

/* Checklist Module */
.checklist-item {
  background-color: var(--surface-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  margin-bottom: 10px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.checklist-item:hover {
  border-color: var(--border-strong);
  background-color: #fafbfc;
}

.checklist-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin-top: 3px;
  cursor: pointer;
  flex-shrink: 0;
}

.progress-bar-bg {
  width: 100%;
  background-color: var(--border-subtle);
  height: 10px;
  border-radius: 5px;
  overflow: hidden;
  margin: 12px 0 20px;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--secondary-olive);
  width: 0%;
  transition: width 0.3s ease;
}

/* Tables */
.table-responsive {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background-color: #ffffff;
  font-size: 0.9rem;
  text-align: left;
}

.data-table th {
  background-color: var(--canvas-bg);
  padding: 12px 14px;
  font-weight: 600;
  color: var(--primary-navy);
  border-bottom: 2px solid var(--border-subtle);
  white-space: nowrap;
}

.data-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}

/* Footer */
.site-footer {
  background-color: #17222C;
  color: #CDD5DD;
  border-top: 4px solid var(--secondary-olive);
  padding: 44px 0 24px;
  margin-top: auto;
  font-size: 0.875rem;
}

.footer-grid {
  max-width: var(--max-width);
  width: 92%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 40px;
  margin-bottom: 32px;
}

.footer-col h4 {
  color: #ffffff;
  margin-bottom: 14px;
  font-size: 1rem;
}

.footer-col p {
  line-height: 1.6;
}

.footer-col a {
  color: #ADB9C5;
  text-decoration: none;
  display: block;
  margin-bottom: 9px;
  transition: color 0.15s;
}

.footer-col a:hover {
  color: #ffffff;
  text-decoration: underline;
}

.footer-bottom {
  max-width: var(--max-width);
  width: 92%;
  margin: 0 auto;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 20px;
  text-align: center;
  font-size: 0.8rem;
  color: #8C98A4;
}

/* Responsive Media Queries */
@media (max-width: 1100px) {
  .service-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 960px) {
  .nav-wrapper {
    display: none;
    position: absolute;
    top: 76px;
    left: 0;
    right: 0;
    background-color: #ffffff;
    flex-direction: column;
    padding: 20px;
    border-bottom: 2px solid var(--border-subtle);
    box-shadow: 0 4px 8px rgba(0,0,0,0.06);
    gap: 16px;
  }
  .nav-wrapper.is-open {
    display: flex;
  }
  .nav-links {
    flex-direction: column;
    width: 100%;
    align-items: flex-start;
    gap: 12px;
  }
  .auth-nav {
    width: 100%;
    flex-direction: column;
    gap: 10px;
  }
  .auth-nav .btn {
    width: 100%;
  }
  .mobile-nav-toggle {
    display: block;
  }
  .process-grid {
    grid-template-columns: 1fr;
  }
  .footer-grid {
    grid-template-columns: 1fr;
    gap: 28px;
  }
}

@media (max-width: 600px) {
  .service-grid {
    grid-template-columns: 1fr;
  }
  .hero-box {
    padding: 28px 20px;
  }
  .hero-heading {
    font-size: 1.65rem;
  }
  .hero-actions {
    flex-direction: column;
  }
  .hero-actions .btn {
    width: 100%;
  }
}
"""
    with open(os.path.join(css_dir, 'styles.css'), 'w', encoding='utf-8') as f:
        f.write(css_content)

    # 2. TEMPLATES DEFINITIONS
    templates = {}

    # Base layout
    templates['base.html'] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Sainik Sahayak — Defense Welfare Assistance & Grievance Guidance{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
  <div class="notice-bar">
    <strong>INDEPENDENT ACADEMIC PROTOTYPE:</strong> Non-governmental guidance model. Official eligibility and grievance processing remain strictly under the jurisdiction of the Ministry of Defence, KSB, and DESW.
  </div>

  <header class="site-header">
    <div class="nav-container">
      <a href="{{ url_for('index') }}" class="brand">
        <div class="brand-icon">SS</div>
        <div class="brand-text-block">
          <span class="brand-name">Sainik Sahayak</span>
          <span class="brand-sub">Welfare & Redressal Support</span>
        </div>
      </a>

      <button class="mobile-nav-toggle" id="mobileNavToggle" aria-label="Toggle navigation">
        <span></span><span></span><span></span>
      </button>

      <div class="nav-wrapper" id="navWrapper">
        <ul class="nav-links">
          <li><a href="{{ url_for('index') }}" class="{% if request.endpoint == 'index' %}active{% endif %}">Home</a></li>
          <li><a href="{{ url_for('schemes_list') }}" class="{% if request.endpoint in ['schemes_list', 'scheme_detail'] %}active{% endif %}">Welfare Schemes</a></li>
          <li><a href="{{ url_for('scheme_finder') }}" class="{% if request.endpoint == 'scheme_finder' %}active{% endif %}">Find My Scheme</a></li>
          <li><a href="{{ url_for('checklist') }}" class="{% if request.endpoint == 'checklist' %}active{% endif %}">Document Checklist</a></li>
          <li><a href="{{ url_for('grievance') }}" class="{% if request.endpoint in ['grievance', 'track_grievance'] %}active{% endif %}">Grievance Support</a></li>
          <li><a href="{{ url_for('about') }}" class="{% if request.endpoint == 'about' %}active{% endif %}">About Us</a></li>
        </ul>

        <div class="auth-nav">
          {% if session.get('user_id') %}
            {% if session.get('role') == 'admin' %}
              <a href="{{ url_for('admin_desk') }}" class="btn btn-secondary btn-sm">Admin Desk</a>
            {% else %}
              <a href="{{ url_for('dashboard') }}" class="btn btn-secondary btn-sm">My Dashboard</a>
            {% endif %}
            <a href="{{ url_for('logout') }}" class="btn btn-logout btn-sm">Logout</a>
          {% else %}
            <a href="{{ url_for('login') }}" class="btn btn-secondary btn-sm">Sign In</a>
            <a href="{{ url_for('register') }}" class="btn btn-primary btn-sm">Register</a>
          {% endif %}
        </div>
      </div>
    </div>
  </header>

  <main class="main-wrapper">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="alert alert-{{ category }}" role="alert">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>

  <footer class="site-footer">
    <div class="footer-grid">
      <div class="footer-col">
        <h4>Sainik Sahayak Digital Model</h4>
        <p>A digital public service system engineered to assist serving personnel, ex-servicemen, and their families in discovering verified welfare schemes and navigating official grievance avenues.</p>
        <p style="margin-top: 10px; font-size: 0.8rem; color: #8C98A4;">Data grounded in published policies from Kendriya Sainik Board (KSB) and Department of Ex-Servicemen Welfare (DESW).</p>
      </div>
      <div class="footer-col">
        <h4>Official Direct Portals</h4>
        <a href="https://ksb.gov.in" target="_blank" rel="noopener">Kendriya Sainik Board (KSB)</a>
        <a href="https://desw.gov.in" target="_blank" rel="noopener">Dept of Ex-Servicemen Welfare</a>
        <a href="https://pgportal.gov.in" target="_blank" rel="noopener">CPGRAMS Redressal Portal</a>
        <a href="https://echs.gov.in" target="_blank" rel="noopener">ECHS Cashless Healthcare</a>
      </div>
      <div class="footer-col">
        <h4>Prototype Resources</h4>
        <a href="{{ url_for('about') }}">About the Project</a>
        <a href="{{ url_for('checklist') }}">Document Readiness Tool</a>
        <a href="{{ url_for('grievance') }}">Official Redressal Channels</a>
      </div>
    </div>
    <div class="footer-bottom">
      &copy; 2026 Sainik Sahayak Academic Engineering Project. Strictly Non-Commercial.
    </div>
  </footer>

  <script>
    const navBtn = document.getElementById('mobileNavToggle');
    const navWrap = document.getElementById('navWrapper');
    if (navBtn && navWrap) {
      navBtn.addEventListener('click', () => {
        navWrap.classList.toggle('is-open');
      });
    }
  </script>
</body>
</html>
"""

    # Index page
    templates['index.html'] = """{% extends "base.html" %}
{% block content %}
<section class="hero-box">
  <span class="badge badge-olive">Serving Soldiers &bull; Veterans &bull; Families</span>
  <h1 class="hero-heading">Support, Guidance and Welfare Assistance — All in One Place.</h1>
  <p class="hero-desc">
    Sainik Sahayak helps serving personnel, veterans, and military families discover verified welfare assistance schemes, prepare required documents, and navigate appropriate grievance redressal paths.
  </p>
  <div class="hero-actions">
    <a href="{{ url_for('schemes_list') }}" class="btn btn-primary">Find Welfare Schemes</a>
    <a href="{{ url_for('grievance') }}" class="btn btn-secondary">Get Grievance Guidance</a>
    <a href="{{ url_for('scheme_finder') }}" class="btn btn-olive">Smart Scheme Finder</a>
  </div>
</section>

<div class="section-header">
  <h2 class="section-title">Core Platform Services</h2>
  <p class="section-subtitle">Dedicated welfare and grievance guidance structured for the armed forces community.</p>
</div>

<div class="service-grid">
  <div class="card">
    <div>
      <span class="badge">Directory</span>
      <h3>Explore Welfare Schemes</h3>
      <p>Browse verified financial, educational, and medical grants provided via Kendriya Sainik Board (RMDF) and DESW.</p>
    </div>
    <a href="{{ url_for('schemes_list') }}" class="btn btn-secondary btn-sm">Browse Directory &rarr;</a>
  </div>

  <div class="card">
    <div>
      <span class="badge badge-olive">Advisory Tool</span>
      <h3>Find My Scheme</h3>
      <p>Answer three basic questions about your service rank or dependent status to receive targeted scheme recommendations.</p>
    </div>
    <a href="{{ url_for('scheme_finder') }}" class="btn btn-secondary btn-sm">Start Scheme Finder &rarr;</a>
  </div>

  <div class="card">
    <div>
      <span class="badge">Preparation</span>
      <h3>Document Checklist</h3>
      <p>Review the exact paperwork required before applying. Completely private with zero personal document uploads.</p>
    </div>
    <a href="{{ url_for('checklist') }}" class="btn btn-secondary btn-sm">Check Readiness &rarr;</a>
  </div>

  <div class="card">
    <div>
      <span class="badge">Redressal</span>
      <h3>Grievance Support</h3>
      <p>Learn how to properly route pension, healthcare, or service record concerns through CPGRAMS or DESW cells.</p>
    </div>
    <a href="{{ url_for('grievance') }}" class="btn btn-secondary btn-sm">View Redressal Steps &rarr;</a>
  </div>
</div>

<section class="process-box">
  <div class="section-header">
    <h2 class="section-title">How Sainik Sahayak Works</h2>
    <p class="section-subtitle">Three structured steps to access welfare information without confusion.</p>
  </div>

  <div class="process-grid">
    <div class="process-step">
      <div class="process-step-num">STEP 01</div>
      <div class="process-step-title">Select Beneficiary Category</div>
      <p>Identify whether you are a serving soldier, ex-serviceman, or family dependent to focus only on applicable assistance.</p>
    </div>
    <div class="process-step">
      <div class="process-step-num">STEP 02</div>
      <div class="process-step-title">Review Eligibility &amp; Papers</div>
      <p>Check the verified criteria and required paperwork before visiting the Zila Sainik Board or applying online.</p>
    </div>
    <div class="process-step">
      <div class="process-step-num">STEP 03</div>
      <div class="process-step-title">Apply via Official Portals</div>
      <p>Proceed with confidence using authentic government links to KSB, DESW, or CPGRAMS for submission.</p>
    </div>
  </div>
</section>
{% endblock %}
"""

    # Schemes List
    templates['schemes.html'] = """{% extends "base.html" %}
{% block title %}Welfare Schemes Directory — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header">
  <h1 class="section-title">Welfare Schemes Directory</h1>
  <p class="section-subtitle">Verified support initiatives from Kendriya Sainik Board (KSB) and Department of Ex-Servicemen Welfare (DESW).</p>
</div>

<form method="GET" action="{{ url_for('schemes_list') }}" style="background: #ffffff; padding: 22px 26px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); margin-bottom: 28px; box-shadow: var(--shadow-card);">
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) 100px; gap: 16px; align-items: end;">
    <div>
      <label class="form-label">Beneficiary Category</label>
      <select name="category" class="form-select">
        <option value="All">All Categories</option>
        <option value="Ex-serviceman / Veteran" {% if selected_category == 'Ex-serviceman / Veteran' %}selected{% endif %}>Ex-serviceman / Veteran</option>
        <option value="Dependent of Ex-serviceman" {% if selected_category == 'Dependent of Ex-serviceman' %}selected{% endif %}>Dependent of Ex-serviceman</option>
        <option value="Serving Soldier" {% if selected_category == 'Serving Soldier' %}selected{% endif %}>Serving Soldier</option>
      </select>
    </div>

    <div>
      <label class="form-label">Assistance Purpose</label>
      <select name="purpose" class="form-select">
        <option value="All">All Purposes</option>
        <option value="Education" {% if selected_purpose == 'Education' %}selected{% endif %}>Education</option>
        <option value="Financial Relief" {% if selected_purpose == 'Financial Relief' %}selected{% endif %}>Financial Relief</option>
        <option value="Marriage Assistance" {% if selected_purpose == 'Marriage Assistance' %}selected{% endif %}>Marriage Assistance</option>
        <option value="Healthcare" {% if selected_purpose == 'Healthcare' %}selected{% endif %}>Healthcare</option>
      </select>
    </div>

    <div>
      <label class="form-label">Keyword Search</label>
      <input type="text" name="q" value="{{ query }}" placeholder="e.g. Marriage, RMDF" class="form-control">
    </div>

    <button type="submit" class="btn btn-primary" style="height: 42px;">Filter</button>
  </div>
</form>

<div>
  {% for sch in schemes %}
    <article class="scheme-card">
      <div class="scheme-card-header">
        <div>
          <span class="badge">{{ sch['purpose'] }}</span>
          <span class="badge badge-olive" style="margin-left: 6px;">{{ sch['category'] }}</span>
          <h2 style="font-size: 1.3rem; color: var(--primary-navy); margin-top: 8px;">{{ sch['scheme_name'] }}</h2>
        </div>
        <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600; white-space: nowrap;">Code: {{ sch['scheme_code'] }}</span>
      </div>

      <p style="color: var(--text-main); font-size: 0.95rem; line-height: 1.6;">{{ sch['short_description'] }}</p>

      <div class="scheme-benefit-box">
        <strong>Verified Assistance:</strong> {{ sch['detailed_benefit'] }}
      </div>

      <div class="scheme-card-footer">
        <span style="font-size: 0.825rem; color: var(--text-muted);">
          Source: <strong>{{ sch['official_source_name'] }}</strong> &bull; Verified: {{ sch['last_verified'] }}
        </span>
        <div style="display: flex; gap: 8px;">
          <a href="{{ url_for('checklist', scheme_id=sch['id']) }}" class="btn btn-secondary btn-sm">Checklist</a>
          <a href="{{ url_for('scheme_detail', scheme_id=sch['id']) }}" class="btn btn-primary btn-sm">Full Details &rarr;</a>
        </div>
      </div>
    </article>
  {% else %}
    <div style="background: #ffffff; padding: 44px; text-align: center; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
      <h3 style="color: var(--primary-navy); margin-bottom: 6px;">No Schemes Match Your Filter</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem;">Try selecting "All Categories" or clearing the keyword query.</p>
      <a href="{{ url_for('schemes_list') }}" class="btn btn-secondary btn-sm" style="margin-top: 14px;">Reset Filters</a>
    </div>
  {% endfor %}
</div>
{% endblock %}
"""

    # Scheme Detail
    templates['scheme_detail.html'] = """{% extends "base.html" %}
{% block title %}{{ scheme['scheme_name'] }} — Sainik Sahayak{% endblock %}
{% block content %}
<div style="margin-bottom: 18px;">
  <a href="{{ url_for('schemes_list') }}" style="color: var(--primary-navy); font-size: 0.9rem; text-decoration: none; font-weight: 600;">&larr; Back to Schemes Directory</a>
</div>

<article style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 36px 40px; box-shadow: var(--shadow-card);">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 20px;">
    <div>
      <span class="badge">{{ scheme['purpose'] }}</span>
      <span class="badge badge-olive" style="margin-left: 6px;">{{ scheme['category'] }}</span>
      <h1 style="color: var(--primary-navy); font-size: 1.85rem; margin-top: 10px; line-height: 1.3;">{{ scheme['scheme_name'] }}</h1>
      <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">Official Scheme Code: {{ scheme['scheme_code'] }}</p>
    </div>
    {% if session.get('user_id') %}
      <form method="POST" action="{{ url_for('toggle_save', scheme_id=scheme['id']) }}">
        <button type="submit" class="btn btn-secondary btn-sm">
          {{ 'Saved Scheme' if is_saved else 'Bookmark Scheme' }}
        </button>
      </form>
    {% endif %}
  </div>

  <section style="margin: 26px 0;">
    <h3 style="color: var(--primary-navy); font-size: 1.15rem; margin-bottom: 8px;">Official Financial / Welfare Benefit</h3>
    <div class="scheme-benefit-box" style="margin: 0; font-size: 1rem;">
      {{ scheme['detailed_benefit'] }}
    </div>
  </section>

  <section style="margin: 26px 0;">
    <h3 style="color: var(--primary-navy); font-size: 1.15rem; margin-bottom: 8px;">Eligibility Criteria</h3>
    <p style="color: var(--text-main); font-size: 0.975rem; line-height: 1.65;">{{ scheme['eligibility_conditions'] }}</p>
  </section>

  <section style="margin: 26px 0;">
    <h3 style="color: var(--primary-navy); font-size: 1.15rem; margin-bottom: 12px;">Required Supporting Documents</h3>
    <ul style="margin-left: 20px; font-size: 0.95rem; line-height: 1.8;">
      {% for doc in documents %}
        <li><strong>{{ doc['document_name'] }}</strong>{% if doc['notes'] %} <span style="color: var(--text-muted);">— {{ doc['notes'] }}</span>{% endif %}</li>
      {% endfor %}
    </ul>
    <div style="margin-top: 16px;">
      <a href="{{ url_for('checklist', scheme_id=scheme['id']) }}" class="btn btn-secondary btn-sm">Open Readiness Checklist</a>
    </div>
  </section>

  <section style="margin: 26px 0;">
    <h3 style="color: var(--primary-navy); font-size: 1.15rem; margin-bottom: 8px;">Application Process</h3>
    <p style="color: var(--text-main); font-size: 0.975rem; line-height: 1.65;">{{ scheme['application_process'] }}</p>
  </section>

  <div style="background: var(--canvas-bg); padding: 20px 24px; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; margin-top: 30px;">
    <div>
      <div style="font-weight: 600; color: var(--primary-navy);">Official Source: {{ scheme['official_source_name'] }}</div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">Last verified on {{ scheme['last_verified'] }}</div>
    </div>
    <a href="{{ scheme['official_portal_url'] }}" target="_blank" rel="noopener" class="btn btn-primary">Visit Official Application Portal &rarr;</a>
  </div>
</article>
{% endblock %}
"""

    # Smart Scheme Finder
    templates['finder.html'] = """{% extends "base.html" %}
{% block title %}Smart Scheme Finder — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header">
  <h1 class="section-title">Smart Scheme Finder</h1>
  <p class="section-subtitle">Answer three quick questions to narrow down potentially relevant welfare programs.</p>
</div>

<div class="form-panel" style="max-width: 820px; margin: 0 auto 36px;">
  <form method="POST" action="{{ url_for('scheme_finder') }}">
    <div class="form-group">
      <label class="form-label">1. What is your beneficiary category?</label>
      <select name="category" class="form-select" required>
        <option value="Ex-serviceman / Veteran" {% if answers.get('category') == 'Ex-serviceman / Veteran' %}selected{% endif %}>Ex-serviceman / Veteran</option>
        <option value="Dependent of Ex-serviceman" {% if answers.get('category') == 'Dependent of Ex-serviceman' %}selected{% endif %}>Dependent / Child / Widow of ESM</option>
        <option value="Serving Soldier" {% if answers.get('category') == 'Serving Soldier' %}selected{% endif %}>Serving Soldier</option>
        <option value="Family Member of Serving Soldier" {% if answers.get('category') == 'Family Member of Serving Soldier' %}selected{% endif %}>Family Member of Serving Personnel</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">2. What type of assistance are you looking for?</label>
      <select name="purpose" class="form-select" required>
        <option value="Any">Any Category of Assistance</option>
        <option value="Education" {% if answers.get('purpose') == 'Education' %}selected{% endif %}>Education &amp; Children Scholarship</option>
        <option value="Marriage Assistance" {% if answers.get('purpose') == 'Marriage Assistance' %}selected{% endif %}>Daughter Marriage Grant</option>
        <option value="Financial Relief" {% if answers.get('purpose') == 'Financial Relief' %}selected{% endif %}>Subsistence / Penury Financial Relief</option>
        <option value="Healthcare" {% if answers.get('purpose') == 'Healthcare' %}selected{% endif %}>Medical &amp; Healthcare Support</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">3. What is your relevant service or pension status?</label>
      <select name="pension_status" class="form-select">
        <option value="Regular Pensioner" {% if answers.get('pension_status') == 'Regular Pensioner' %}selected{% endif %}>Regular Service Pensioner</option>
        <option value="Non-Pensioner" {% if answers.get('pension_status') == 'Non-Pensioner' %}selected{% endif %}>Non-Pensioner / Indigent Veteran</option>
        <option value="Not Applicable" {% if answers.get('pension_status') == 'Not Applicable' %}selected{% endif %}>Serving / Not Applicable</option>
      </select>
    </div>

    <button type="submit" class="btn btn-primary" style="width: 100%; height: 44px; margin-top: 8px;">Show Potentially Relevant Schemes</button>
  </form>
</div>

{% if results is not none %}
  <div style="max-width: 820px; margin: 0 auto;">
    <div class="section-header">
      <h2 class="section-title">Suggested Schemes Based on Your Answers</h2>
      <p class="section-subtitle">These suggestions are informational only. Final eligibility is determined by the relevant government authority.</p>
    </div>

    {% for sch in results %}
      <div class="scheme-card">
        <div class="scheme-card-header">
          <div>
            <span class="badge">{{ sch['purpose'] }}</span>
            <span class="badge badge-olive" style="margin-left: 6px;">{{ sch['category'] }}</span>
            <h3 style="color: var(--primary-navy); margin-top: 6px;">{{ sch['scheme_name'] }}</h3>
          </div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">Ref: {{ sch['scheme_code'] }}</span>
        </div>
        <p style="font-size: 0.95rem; color: var(--text-main); margin-bottom: 12px;">{{ sch['short_description'] }}</p>
        <div class="scheme-benefit-box" style="margin-bottom: 14px;">
          <strong>Benefit:</strong> {{ sch['detailed_benefit'] }}
        </div>
        <a href="{{ url_for('scheme_detail', scheme_id=sch['id']) }}" class="btn btn-secondary btn-sm">Review Requirements &rarr;</a>
      </div>
    {% else %}
      <div style="background: #ffffff; padding: 36px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); text-align: center;">
        No specific scheme directly matched that combination. Try selecting "Any Category of Assistance" or explore the full directory.
      </div>
    {% endfor %}
  </div>
{% endif %}
{% endblock %}
"""

    # Document Checklist
    templates['checklist.html'] = """{% extends "base.html" %}
{% block title %}Document Readiness Checklist — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header">
  <h1 class="section-title">Document Readiness Checklist</h1>
  <p class="section-subtitle">Verify that you have all necessary certificates ready before visiting the Zila Sainik Board or applying online.</p>
</div>

<div style="background: #f0f4ec; border-left: 4px solid var(--secondary-olive); padding: 14px 18px; border-radius: var(--radius-sm); font-size: 0.9rem; margin-bottom: 28px;">
  <strong>Privacy Protected:</strong> Sainik Sahayak runs this checklist entirely in your browser. Do not upload Aadhaar cards, military service books, or bank credentials.
</div>

<div style="display: grid; grid-template-columns: 340px 1fr; gap: 28px; align-items: start;">
  <!-- Scheme selection sidebar -->
  <div style="background: #ffffff; padding: 22px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); box-shadow: var(--shadow-card); position: sticky; top: 96px;">
    <h3 style="font-size: 1.05rem; color: var(--primary-navy); margin-bottom: 14px;">Select Welfare Scheme</h3>
    <div style="display: flex; flex-direction: column; gap: 8px;">
      {% for s in all_schemes %}
        <a href="{{ url_for('checklist', scheme_id=s['id']) }}"
           style="display: block; padding: 10px 12px; border-radius: var(--radius-sm); text-decoration: none; font-size: 0.9rem; line-height: 1.4; border: 1px solid {% if selected_scheme and selected_scheme['id'] == s['id'] %}var(--primary-navy){% else %}var(--border-subtle){% endif %}; background: {% if selected_scheme and selected_scheme['id'] == s['id'] %}#eef3f8{% else %}#ffffff{% endif %}; color: var(--text-main);">
          {{ s['scheme_name'] }}
        </a>
      {% endfor %}
    </div>
  </div>

  <!-- Checklist body -->
  <div style="background: #ffffff; padding: 30px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); box-shadow: var(--shadow-card);">
    {% if selected_scheme %}
      <span class="badge">{{ selected_scheme['scheme_code'] }}</span>
      <h2 style="color: var(--primary-navy); font-size: 1.45rem; margin: 8px 0 16px;">{{ selected_scheme['scheme_name'] }}</h2>

      <div style="display: flex; justify-content: space-between; font-size: 0.925rem; font-weight: 600;">
        <span>Readiness Progress</span>
        <span id="readiness-label">0% Ready (0/{{ documents|length }})</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="readiness-bar"></div>
      </div>

      <div id="items-box">
        {% for doc in documents %}
          <label class="checklist-item">
            <input type="checkbox" class="doc-chk" onchange="recalc()">
            <div>
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-main);">{{ doc['document_name'] }}</div>
              {% if doc['notes'] %}
                <div style="font-size: 0.825rem; color: var(--text-muted); margin-top: 2px;">{{ doc['notes'] }}</div>
              {% endif %}
            </div>
          </label>
        {% endfor %}
      </div>

      <div id="advice-box" style="margin-top: 22px; padding: 14px 18px; background: #fdfaf3; border: 1px solid #ebd9b8; border-radius: var(--radius-sm); font-size: 0.9rem;">
        Tick the documents you have in your possession to evaluate your application readiness.
      </div>
    {% else %}
      <div style="text-align: center; color: var(--text-muted); padding: 50px 20px;">
        <h3 style="color: var(--primary-navy); margin-bottom: 8px;">Select a Scheme</h3>
        <p>Choose any scheme from the left column to view its verified document requirements.</p>
      </div>
    {% endif %}
  </div>
</div>

<script>
function recalc() {
  const chks = document.querySelectorAll('.doc-chk');
  if(!chks.length) return;
  let count = 0;
  chks.forEach(c => { if(c.checked) count++; });
  const pct = Math.round((count / chks.length) * 100);
  document.getElementById('readiness-label').innerText = pct + '% Ready (' + count + '/' + chks.length + ')';
  document.getElementById('readiness-bar').style.width = pct + '%';
  const box = document.getElementById('advice-box');
  if (pct === 100) {
    box.style.background = '#edf7ed';
    box.style.borderColor = '#c8e6c9';
    box.innerHTML = '<strong>Documentation Complete:</strong> You have all required documents ready. You can confidently proceed to the official KSB/DESW portal.';
  } else {
    box.style.background = '#fdfaf3';
    box.style.borderColor = '#ebd9b8';
    box.innerHTML = '<strong>In Progress:</strong> You have ' + (chks.length - count) + ' pending item(s). Collect all documents prior to filing to prevent delays.';
  }
}
</script>
{% endblock %}
"""

    # Grievance Guidance
    templates['grievance.html'] = """{% extends "base.html" %}
{% block title %}Grievance Support — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header">
  <h1 class="section-title">Official Grievance Redressal Guidance</h1>
  <p class="section-subtitle">Understanding authorized grievance channels for defense pensions, OROP, ECHS, and service anomalies.</p>
</div>

<div style="background: #fff9e6; border: 1px solid #ebd9a2; padding: 16px 20px; border-radius: var(--radius-sm); margin-bottom: 32px; font-size: 0.925rem; color: #574106;">
  <strong>Important Notice:</strong> Sainik Sahayak does not arbitrate or resolve government grievances. For authentic government filings, refer to the three authorized central mechanisms below.
</div>

<div class="service-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 44px;">
  <div class="card">
    <div>
      <span class="badge">Central Portal</span>
      <h3>CPGRAMS (pgportal.gov.in)</h3>
      <p>The Government of India central monitoring system for complaints concerning defense pension revisions, OROP arrears, and general administrative hold-ups.</p>
    </div>
    <a href="https://pgportal.gov.in" target="_blank" rel="noopener" class="btn btn-primary btn-sm">Visit CPGRAMS Portal &rarr;</a>
  </div>

  <div class="card">
    <div>
      <span class="badge badge-olive">Departmental Cell</span>
      <h3>DESW Redressal Cell</h3>
      <p>The dedicated grievance mechanism under the Department of Ex-Servicemen Welfare for RSB/ZSB coordination and RMDF disbursal delays.</p>
    </div>
    <a href="https://www.desw.gov.in/grievances-redressal-desw" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">Open DESW Page &rarr;</a>
  </div>

  <div class="card">
    <div>
      <span class="badge">Medical Redressal</span>
      <h3>ECHS Grievance Cell</h3>
      <p>Specialized helpline and portal for 64-KB ECHS Smart Card processing, polyclinic approvals, and hospital reimbursement hold-ups.</p>
    </div>
    <a href="https://echs.gov.in" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">Open ECHS Portal &rarr;</a>
  </div>
</div>

<div class="form-panel" style="max-width: 820px; margin: 0 auto;">
  <span class="badge" style="margin-bottom: 8px;">Academic Demonstration</span>
  <h2 style="font-size: 1.35rem; color: var(--primary-navy); margin-bottom: 6px;">Submit Prototype Grievance Record</h2>
  <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 22px;">Use this form to test reference ID tracking within this prototype. Submissions here are demonstration records only.</p>

  <form method="POST" action="{{ url_for('lodge_grievance') }}">
    {% if not session.get('user_id') %}
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div class="form-group">
          <label class="form-label">Full Name</label>
          <input type="text" name="guest_name" class="form-control" placeholder="e.g. Havildar S. Jadhav" required>
        </div>
        <div class="form-group">
          <label class="form-label">Email Address</label>
          <input type="email" name="guest_email" class="form-control" placeholder="name@example.com" required>
        </div>
      </div>
    {% endif %}

    <div class="form-group">
      <label class="form-label">Grievance Classification</label>
      <select name="category" class="form-select" required>
        <option value="Pension / OROP">Pension / OROP Arrears</option>
        <option value="ECHS / Medical Claim">ECHS Healthcare / Polyclinic Issue</option>
        <option value="Service Records / Discharge">Service Records / Discharge Correction</option>
        <option value="Welfare Grant Disbursal">Welfare Grant Disbursal (RMDF / PMSS)</option>
        <option value="Other Redressal">Other Administrative Redressal</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Issue Summary</label>
      <input type="text" name="issue_summary" class="form-control" placeholder="e.g. Clarification needed on RMDF Education Grant application status" required>
    </div>

    <div class="form-group">
      <label class="form-label">Detailed Description</label>
      <textarea name="detailed_description" rows="4" class="form-control" placeholder="Enter factual details regarding your concern for academic review..." required></textarea>
    </div>

    <button type="submit" class="btn btn-primary" style="width: 100%; height: 44px;">Submit Demo Grievance &amp; Get Reference ID</button>
  </form>

  <div style="text-align: center; margin-top: 18px;">
    <a href="{{ url_for('track_grievance') }}" style="color: var(--primary-navy); font-size: 0.9rem; font-weight: 600;">Already have a Reference ID? Track it here &rarr;</a>
  </div>
</div>
{% endblock %}
"""

    # Grievance Track
    templates['track.html'] = """{% extends "base.html" %}
{% block title %}Track Prototype Grievance — Sainik Sahayak{% endblock %}
{% block content %}
<div class="form-panel" style="max-width: 680px; margin: 0 auto 30px;">
  <h1 style="font-size: 1.45rem; color: var(--primary-navy); margin-bottom: 6px;">Track Demonstration Grievance</h1>
  <p style="color: var(--text-muted); font-size: 0.875rem; margin-bottom: 18px;">Enter your generated reference code (e.g., SS-2026-XXXXX) to check prototype status.</p>

  <form method="GET" action="{{ url_for('track_grievance') }}" style="display: flex; gap: 10px;">
    <input type="text" name="ref" value="{{ ref_query }}" class="form-control" placeholder="SS-2026-XXXX" required>
    <button type="submit" class="btn btn-primary" style="height: 42px;">Track</button>
  </form>
</div>

{% if grievance %}
  <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 30px; max-width: 680px; margin: 0 auto; box-shadow: var(--shadow-card);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <div>
        <span class="badge">{{ grievance['category'] }}</span>
        <h2 style="font-size: 1.35rem; color: var(--primary-navy); margin-top: 6px;">{{ grievance['reference_number'] }}</h2>
      </div>
      <span class="badge badge-olive" style="font-size: 0.85rem; padding: 6px 12px;">{{ grievance['status'] }}</span>
    </div>

    <p style="font-size: 1rem; color: var(--text-main); margin-bottom: 8px;"><strong>Summary:</strong> {{ grievance['issue_summary'] }}</p>
    <p style="font-size: 0.85rem; color: var(--text-muted);">Logged On: {{ grievance['created_at'] }}</p>

    {% if grievance['official_recommendation'] %}
      <div style="background: #f7f9f6; border-left: 4px solid var(--secondary-olive); padding: 14px 18px; margin-top: 18px; font-size: 0.925rem;">
        <strong>Prototype Advisory Note:</strong><br>
        {{ grievance['official_recommendation'] }}
      </div>
    {% endif %}
  </div>
{% endif %}
{% endblock %}
"""

    # Login
    templates['login.html'] = """{% extends "base.html" %}
{% block title %}Sign In — Sainik Sahayak{% endblock %}
{% block content %}
<div class="form-panel" style="max-width: 520px; margin: 40px auto;">
  <div style="text-align: center; margin-bottom: 24px;">
    <h1 style="font-size: 1.6rem; color: var(--primary-navy); margin-bottom: 6px;">Sign In</h1>
    <p style="color: var(--text-muted); font-size: 0.9rem;">Access your bookmarked schemes and grievance history.</p>
  </div>

  <form method="POST" action="{{ url_for('login') }}">
    <div class="form-group">
      <label class="form-label">Email Address</label>
      <input type="email" name="email" class="form-control" placeholder="name@example.com" required autocomplete="username">
    </div>
    <div class="form-group">
      <label class="form-label">Password</label>
      <input type="password" name="password" class="form-control" required autocomplete="current-password">
    </div>
    <button type="submit" class="btn btn-primary" style="width: 100%; height: 44px; margin-top: 8px;">Sign In</button>
  </form>

  <div style="text-align: center; margin-top: 22px; font-size: 0.9rem; color: var(--text-muted);">
    Don't have an account? <a href="{{ url_for('register') }}" style="color: var(--primary-navy); font-weight: 600;">Register here</a>
  </div>
</div>
{% endblock %}
"""

    # Register
    templates['register.html'] = """{% extends "base.html" %}
{% block title %}Create Prototype Account — Sainik Sahayak{% endblock %}
{% block content %}
<div class="form-panel" style="max-width: 600px; margin: 30px auto;">
  <div style="text-align: center; margin-bottom: 22px;">
    <h1 style="font-size: 1.6rem; color: var(--primary-navy); margin-bottom: 6px;">Register Account</h1>
    <p style="color: var(--text-muted); font-size: 0.9rem;">Personalize scheme discovery and save your document checklists.</p>
  </div>

  <div style="background: #fdfaf3; border: 1px solid #ebd9b8; padding: 12px 16px; border-radius: var(--radius-sm); font-size: 0.85rem; color: #6d5420; margin-bottom: 22px;">
    <strong>Notice:</strong> This registration establishes an unverified prototype session only. It does not certify military status. Do not submit sensitive identity card numbers.
  </div>

  <form method="POST" action="{{ url_for('register') }}">
    <div class="form-group">
      <label class="form-label">Full Name</label>
      <input type="text" name="full_name" class="form-control" placeholder="e.g. Ramesh Kumar" required>
    </div>

    <div class="form-group">
      <label class="form-label">Email Address</label>
      <input type="email" name="email" class="form-control" placeholder="name@example.com" required>
    </div>

    <div class="form-group">
      <label class="form-label">Beneficiary Category</label>
      <select name="beneficiary_category" class="form-select" required>
        <option value="Serving Soldier">Serving Soldier</option>
        <option value="Family Member of Serving Soldier">Family Member of Serving Soldier</option>
        <option value="Ex-serviceman / Veteran">Ex-serviceman / Veteran</option>
        <option value="Dependent of Ex-serviceman">Dependent of Ex-serviceman</option>
      </select>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
      <div class="form-group">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control" minlength="8" required>
      </div>
      <div class="form-group">
        <label class="form-label">Confirm Password</label>
        <input type="password" name="confirm_password" class="form-control" minlength="8" required>
      </div>
    </div>

    <button type="submit" class="btn btn-primary" style="width: 100%; height: 44px; margin-top: 8px;">Create Prototype Account</button>
  </form>

  <div style="text-align: center; margin-top: 20px; font-size: 0.9rem; color: var(--text-muted);">
    Already registered? <a href="{{ url_for('login') }}" style="color: var(--primary-navy); font-weight: 600;">Sign in here</a>
  </div>
</div>
{% endblock %}
"""

    # Dashboard
    templates['dashboard.html'] = """{% extends "base.html" %}
{% block title %}User Dashboard — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header" style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 14px;">
  <div>
    <h1 class="section-title">Beneficiary Dashboard</h1>
    <p class="section-subtitle">Welcome, <strong>{{ user['full_name'] }}</strong> &bull; <span class="badge badge-olive">{{ user['beneficiary_category'] }}</span></p>
  </div>
  <a href="{{ url_for('scheme_finder') }}" class="btn btn-olive btn-sm">Find Relevant Schemes</a>
</div>

<h2 style="font-size: 1.25rem; color: var(--primary-navy); margin: 28px 0 14px;">My Bookmarked Schemes</h2>
{% if saved_schemes %}
  <div class="service-grid">
    {% for s in saved_schemes %}
      <div class="card">
        <div>
          <span class="badge">{{ s['purpose'] }}</span>
          <h3 style="color: var(--primary-navy); margin: 8px 0;">{{ s['scheme_name'] }}</h3>
          <p style="font-size: 0.875rem; color: var(--text-muted);">{{ s['short_description'] }}</p>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 14px;">
          <a href="{{ url_for('scheme_detail', scheme_id=s['id']) }}" class="btn btn-primary btn-sm">Details</a>
          <a href="{{ url_for('checklist', scheme_id=s['id']) }}" class="btn btn-secondary btn-sm">Checklist</a>
        </div>
      </div>
    {% endfor %}
  </div>
{% else %}
  <div style="background: #ffffff; padding: 24px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); margin-bottom: 30px; font-size: 0.925rem; color: var(--text-muted); box-shadow: var(--shadow-card);">
    You have not bookmarked any schemes. <a href="{{ url_for('schemes_list') }}" style="color: var(--primary-navy); font-weight: 600;">Explore the schemes directory</a> to save grants here.
  </div>
{% endif %}

<h2 style="font-size: 1.25rem; color: var(--primary-navy); margin: 28px 0 14px;">My Demo Grievance Submissions</h2>
{% if grievances %}
  <div class="table-responsive">
    <table class="data-table">
      <thead>
        <tr>
          <th>Reference ID</th>
          <th>Category</th>
          <th>Issue Summary</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {% for g in grievances %}
          <tr>
            <td style="font-weight: 600;">{{ g['reference_number'] }}</td>
            <td>{{ g['category'] }}</td>
            <td>{{ g['issue_summary'] }}</td>
            <td><span class="badge">{{ g['status'] }}</span></td>
            <td><a href="{{ url_for('track_grievance', ref=g['reference_number']) }}" class="btn btn-secondary btn-sm">View</a></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
{% else %}
  <div style="background: #ffffff; padding: 24px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 0.925rem; color: var(--text-muted); box-shadow: var(--shadow-card);">
    No prototype grievances filed under your account.
  </div>
{% endif %}
{% endblock %}
"""

    # Admin Desk
    templates['admin.html'] = """{% extends "base.html" %}
{% block title %}Admin Review Desk — Sainik Sahayak{% endblock %}
{% block content %}
<div class="section-header">
  <h1 class="section-title">Administrator Review Desk</h1>
  <p class="section-subtitle">Academic supervision and mock grievance triage management.</p>
</div>

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px;">
  <div style="background: #ffffff; border: 1px solid var(--border-subtle); padding: 22px; border-radius: var(--radius-sm); box-shadow: var(--shadow-card);">
    <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Registered Users</div>
    <div style="font-size: 2rem; font-weight: 700; color: var(--primary-navy); margin-top: 4px;">{{ total_users }}</div>
  </div>
  <div style="background: #ffffff; border: 1px solid var(--border-subtle); padding: 22px; border-radius: var(--radius-sm); box-shadow: var(--shadow-card);">
    <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Active Schemes</div>
    <div style="font-size: 2rem; font-weight: 700; color: var(--secondary-olive); margin-top: 4px;">{{ total_schemes }}</div>
  </div>
  <div style="background: #ffffff; border: 1px solid var(--border-subtle); padding: 22px; border-radius: var(--radius-sm); box-shadow: var(--shadow-card);">
    <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Demo Grievances</div>
    <div style="font-size: 2rem; font-weight: 700; color: var(--accent-gold); margin-top: 4px;">{{ total_grievances }}</div>
  </div>
</div>

<div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 26px; box-shadow: var(--shadow-card);">
  <h2 style="font-size: 1.25rem; color: var(--primary-navy); margin-bottom: 16px;">Triage Demo Grievances</h2>
  {% if grievances %}
    <div class="table-responsive">
      <table class="data-table">
        <thead>
          <tr>
            <th>Ref ID</th>
            <th>Category</th>
            <th>Applicant</th>
            <th>Summary</th>
            <th>Status</th>
            <th>Update Status</th>
          </tr>
        </thead>
        <tbody>
          {% for g in grievances %}
            <tr>
              <td style="font-weight: 600;">{{ g['reference_number'] }}</td>
              <td>{{ g['category'] }}</td>
              <td>{{ g['guest_name'] or 'Registered User' }}</td>
              <td>{{ g['issue_summary'] }}</td>
              <td><span class="badge">{{ g['status'] }}</span></td>
              <td>
                <form method="POST" action="{{ url_for('admin_update_status') }}" style="display: flex; gap: 8px;">
                  <input type="hidden" name="grievance_id" value="{{ g['id'] }}">
                  <select name="status" class="form-select" style="padding: 4px 8px; font-size: 0.85rem; width: auto;">
                    <option value="Submitted" {% if g['status'] == 'Submitted' %}selected{% endif %}>Submitted</option>
                    <option value="Under Review" {% if g['status'] == 'Under Review' %}selected{% endif %}>Under Review</option>
                    <option value="Guidance Provided" {% if g['status'] == 'Guidance Provided' %}selected{% endif %}>Guidance Provided</option>
                    <option value="Resolved" {% if g['status'] == 'Resolved' %}selected{% endif %}>Resolved</option>
                  </select>
                  <input type="text" name="notes" placeholder="Advisory note" value="{{ g['official_recommendation'] or '' }}" class="form-control" style="padding: 4px 8px; font-size: 0.85rem; max-width: 200px;">
                  <button type="submit" class="btn btn-secondary btn-sm">Save</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <div style="text-align: center; color: var(--text-muted); padding: 36px 20px;">
      No demonstration grievances logged in the prototype database.
    </div>
  {% endif %}
</div>
{% endblock %}
"""

    # About
    templates['about.html'] = """{% extends "base.html" %}
{% block title %}About — Sainik Sahayak{% endblock %}
{% block content %}
<article style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 40px; max-width: 920px; margin: 0 auto; line-height: 1.7; box-shadow: var(--shadow-card);">
  <h1 style="color: var(--primary-navy); font-size: 1.85rem; margin-bottom: 14px;">About Sainik Sahayak</h1>
  <p style="font-size: 1rem; color: var(--text-main);"><strong>Sainik Sahayak</strong> is an independent academic digital public-service engineering project designed to simplify welfare scheme discovery, document preparation, and grievance redressal pathways for Indian armed forces personnel, veterans, and military dependents.</p>

  <h2 style="color: var(--primary-navy); font-size: 1.3rem; margin-top: 26px; margin-bottom: 10px;">Academic Scope and Limitations</h2>
  <ul style="margin-left: 20px; color: var(--text-main);">
    <li>This platform is non-governmental and is not affiliated with the Indian Army, Navy, Air Force, or the Ministry of Defence.</li>
    <li>No authentic government grievances can be registered through this portal.</li>
    <li>No official military identity cards, Aadhaar numbers, or banking credentials are requested or stored.</li>
  </ul>

  <h2 style="color: var(--primary-navy); font-size: 1.3rem; margin-top: 26px; margin-bottom: 10px;">Official Welfare Sources</h2>
  <p style="color: var(--text-main);">Information inside this platform is aligned with published charters from:</p>
  <ul style="margin-left: 20px; color: var(--text-main);">
    <li><a href="https://ksb.gov.in" target="_blank" rel="noopener" style="color: var(--primary-navy); font-weight: 600;">Kendriya Sainik Board (RMDF Schemes)</a></li>
    <li><a href="https://desw.gov.in" target="_blank" rel="noopener" style="color: var(--primary-navy); font-weight: 600;">Department of Ex-Servicemen Welfare (PMSS &amp; Redressal)</a></li>
    <li><a href="https://echs.gov.in" target="_blank" rel="noopener" style="color: var(--primary-navy); font-weight: 600;">Ex-Servicemen Contributory Health Scheme</a></li>
  </ul>
</article>
{% endblock %}
"""

    for name, content in templates.items():
        with open(os.path.join(tpl_dir, name), 'w', encoding='utf-8') as f:
            f.write(content)

# ============================================================================
# APPLICATION ROUTES (Identical, preserved logic)
# ============================================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/schemes')
def schemes_list():
    cat = request.args.get('category', 'All')
    pur = request.args.get('purpose', 'All')
    q = request.args.get('q', '').strip()

    sql = "SELECT * FROM schemes WHERE is_active = 1"
    params = []
    if cat != 'All':
        sql += " AND (category = ? OR category = 'All Categories')"
        params.append(cat)
    if pur != 'All':
        sql += " AND purpose = ?"
        params.append(pur)
    if q:
        sql += " AND (scheme_name LIKE ? OR short_description LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    sql += " ORDER BY id DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    schemes = cursor.fetchall()
    conn.close()

    return render_template('schemes.html', schemes=schemes, selected_category=cat, selected_purpose=pur, query=q)

@app.route('/schemes/<int:scheme_id>')
def scheme_detail(scheme_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,))
    scheme = cursor.fetchone()
    if not scheme:
        conn.close()
        abort(404)

    cursor.execute("SELECT * FROM scheme_documents WHERE scheme_id = ?", (scheme_id,))
    documents = cursor.fetchall()

    is_saved = False
    if 'user_id' in session:
        cursor.execute("SELECT id FROM saved_schemes WHERE user_id = ? AND scheme_id = ?", (session['user_id'], scheme_id))
        is_saved = cursor.fetchone() is not None

    conn.close()
    return render_template('scheme_detail.html', scheme=scheme, documents=documents, is_saved=is_saved)

@app.route('/schemes/save/<int:scheme_id>', methods=['POST'])
def toggle_save(scheme_id):
    if 'user_id' not in session:
        flash('Please login to bookmark schemes.', 'info')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM saved_schemes WHERE user_id = ? AND scheme_id = ?", (session['user_id'], scheme_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM saved_schemes WHERE user_id = ? AND scheme_id = ?", (session['user_id'], scheme_id))
        flash('Scheme removed from your saved list.', 'info')
    else:
        cursor.execute("INSERT INTO saved_schemes (user_id, scheme_id) VALUES (?, ?)", (session['user_id'], scheme_id))
        flash('Scheme bookmarked in your dashboard.', 'success')

    conn.commit()
    conn.close()
    return redirect(url_for('scheme_detail', scheme_id=scheme_id))

@app.route('/finder', methods=['GET', 'POST'])
def scheme_finder():
    results = None
    answers = {}

    if request.method == 'POST':
        category = request.form.get('category')
        purpose = request.form.get('purpose')
        pension_status = request.form.get('pension_status')
        answers = {'category': category, 'purpose': purpose, 'pension_status': pension_status}

        sql = "SELECT * FROM schemes WHERE is_active = 1"
        params = []

        if category:
            sql += " AND (category = ? OR category = 'All Categories')"
            params.append(category)

        if purpose and purpose != 'Any':
            sql += " AND purpose = ?"
            params.append(purpose)

        if pension_status == 'Non-Pensioner':
            sql += " AND (scheme_code = 'KSB-PENURY-03' OR purpose = ?)"
            params.append(purpose)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()

    return render_template('finder.html', results=results, answers=answers)

@app.route('/checklist')
def checklist():
    scheme_id = request.args.get('scheme_id', type=int)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, scheme_name, scheme_code FROM schemes WHERE is_active = 1")
    all_schemes = cursor.fetchall()

    selected_scheme = None
    documents = []
    if scheme_id:
        cursor.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,))
        selected_scheme = cursor.fetchone()
        if selected_scheme:
            cursor.execute("SELECT * FROM scheme_documents WHERE scheme_id = ?", (scheme_id,))
            documents = cursor.fetchall()

    conn.close()
    return render_template('checklist.html', all_schemes=all_schemes, selected_scheme=selected_scheme, documents=documents)

@app.route('/grievance')
def grievance():
    return render_template('grievance.html')

@app.route('/grievance/lodge', methods=['POST'])
def lodge_grievance():
    category = request.form.get('category')
    issue_summary = request.form.get('issue_summary', '').strip()
    detailed_desc = request.form.get('detailed_description', '').strip()
    guest_name = request.form.get('guest_name') if 'user_id' not in session else session.get('user_name')
    guest_email = request.form.get('guest_email') if 'user_id' not in session else session.get('user_email')
    user_id = session.get('user_id')

    ref_code = f"SS-2026-{uuid.uuid4().hex[:5].upper()}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO prototype_grievances
    (reference_number, user_id, guest_name, guest_email, category, issue_summary, detailed_description, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'Submitted')
    """, (ref_code, user_id, guest_name, guest_email, category, issue_summary, detailed_desc))
    conn.commit()
    conn.close()

    flash(f"Academic demo grievance logged. Reference ID: {ref_code}", "success")
    return redirect(url_for('track_grievance', ref=ref_code))

@app.route('/grievance/track')
def track_grievance():
    ref = request.args.get('ref', '').strip()
    grievance_rec = None
    if ref:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prototype_grievances WHERE reference_number = ?", (ref,))
        grievance_rec = cursor.fetchone()
        conn.close()
        if not grievance_rec:
            flash(f"No grievance found matching reference '{ref}'.", "error")

    return render_template('track.html', grievance=grievance_rec, ref_query=ref)

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        category = request.form.get('beneficiary_category')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        cursor.execute("""
        INSERT INTO users (full_name, email, password_hash, beneficiary_category, role)
        VALUES (?, ?, ?, ?, 'user')
        """, (full_name, email, hashed, category))
        conn.commit()
        conn.close()

        flash('Prototype account created. You may now sign in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            session['role'] = user['role']
            session['category'] = user['beneficiary_category']

            flash(f"Welcome back, {user['full_name']}.", 'info')
            if user['role'] == 'admin':
                return redirect(url_for('admin_desk'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password credentials.', 'error')

    return render_template('login.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    flash('You have logged out safely.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("""
    SELECT s.* FROM schemes s
    INNER JOIN saved_schemes ss ON s.id = ss.scheme_id
    WHERE ss.user_id = ?
    """, (session['user_id'],))
    saved_schemes = cursor.fetchall()

    cursor.execute("SELECT * FROM prototype_grievances WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
    grievances = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', user=user, saved_schemes=saved_schemes, grievances=grievances)

@app.route('/admin')
def admin_desk():
    if session.get('role') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM schemes")
    total_schemes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM prototype_grievances")
    total_grievances = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM prototype_grievances ORDER BY created_at DESC LIMIT 15")
    grievances = cursor.fetchall()
    conn.close()

    return render_template('admin.html', total_users=total_users, total_schemes=total_schemes, total_grievances=total_grievances, grievances=grievances)

@app.route('/admin/update_status', methods=['POST'])
def admin_update_status():
    if session.get('role') != 'admin':
        abort(403)

    gid = request.form.get('grievance_id')
    status = request.form.get('status')
    notes = request.form.get('notes', '').strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE prototype_grievances
    SET status = ?, official_recommendation = ?
    WHERE id = ?
    """, (status, notes, gid))
    conn.commit()
    conn.close()

    flash('Grievance status updated.', 'success')
    return redirect(url_for('admin_desk'))

if __name__ == '__main__':
    print("[*] Updating Sainik Sahayak frontend assets with refined UI/UX...")
    setup_frontend_assets()
    print("[*] Checking database structure...")
    init_db()
    print("\n=======================================================")
    print("  SAINIK SAHAYAK — REFINED PUBLIC SERVICE PROTOTYPE")
    print("  URL: http://127.0.0.1:5000")
    print("  Admin Credentials:")
    print("    Email:    admin@sainiksahayak.internal")
    print("    Password: Admin@Sainik2026")
    print("=======================================================\n")
    app.run(debug=True, port=5000)
