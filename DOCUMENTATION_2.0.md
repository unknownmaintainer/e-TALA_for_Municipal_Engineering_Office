# 🌟 eTala: Engineering Records Archiving & Retrieval Management System
### 🏛️ Municipal Engineering Office — Local Government Unit (LGU) of Carigara, Leyte
**📘 Master System Documentation, Technical Mechanics Encyclopedia & Academic Manuscript Guide (Version 2.0)**

---

## 📑 Table of Contents
* [1. 🎯 Project Context, Problem Statement & Plain-Language Purpose](#1--project-context-problem-statement--plain-language-purpose)
* [2. 🏛️ Academic / Thesis Manuscript Chapter Mapping (Chapters 1–5)](#2-️-academic--thesis-manuscript-chapter-mapping-chapters-15)
* [3. 💻 System Architecture, Tech Stack & 100% On-Premise Topology](#3--system-architecture-tech-stack--100-on-premise-topology)
* [4. 🗄️ Database Schema & Entity-Relationship Architecture (ERD)](#4-️-database-schema--entity-relationship-architecture-erd)
* [5. 👥 2-Tier Role-Based Access Control (RBAC) & Permission Matrix](#5--2-tier-role-based-access-control-rbac--permission-matrix)
* [6. ⚙️ IN-DEPTH SYSTEM MECHANICS & BUSINESS RULES (THE ENCYCLOPEDIA)](#6-️-in-depth-system-mechanics--business-rules-the-encyclopedia)
  * [6.1 🔐 Login, Multi-Tier Lockout & IP Blacklist Mechanics](#61--login-multi-tier-lockout--ip-blacklist-mechanics)
  * [6.2 📧 Email Relay, 2FA OTP & Device Approval Mechanics](#62--email-relay-2fa-otp--device-approval-mechanics)
  * [6.3 🗑️ 30-Day Trash, Soft-Delete & Automated Midnight Purge Mechanics](#63-️-30-day-trash-soft-delete--automated-midnight-purge-mechanics)
  * [6.4 📁 Document Archiving, 50MB Limits, Versioning (v1 $\rightarrow$ v2) & Signed URLs](#64--document-archiving-50mb-limits-versioning-v1-rightarrow-v2--signed-urls)
  * [6.5 🔔 Expiration Alerts, 30-Day Threshold & Cross-Device Sync Mechanics](#65--expiration-alerts-30-day-threshold--cross-device-sync-mechanics)
  * [6.6 💾 Disaster Recovery, Automated Midnight Backups & 14-Snapshot Rolling Retention](#66--disaster-recovery-automated-midnight-backups--14-snapshot-rolling-retention)
  * [6.7 📊 Accomplishment Computation & COA Compliance Formulas](#67--accomplishment-computation--coa-compliance-formulas)
  * [6.8 📜 Tamper-Proof Audit Trail & Reference Linking Mechanics](#68--tamper-proof-audit-trail--reference-linking-mechanics)
  * [6.9 🗺️ 49-Barangay GIS Coordinates Persistence Mechanics](#69-️-49-barangay-gis-coordinates-persistence-mechanics)
* [7. 👤 User Management, Safe Deactivation & Profile Workflows](#7--user-management-safe-deactivation--profile-workflows)
* [8. 📊 Executive Dashboard, Visualizations & Topbar Search](#8--executive-dashboard-visualizations--topbar-search)
* [9. 📝 Records Encoding, 3-Step Wizard & Bulk Ingestion](#9--records-encoding-3-step-wizard--bulk-ingestion)
* [10. 🏗️ Official Engineering Permits Management (PD 1096)](#10-️-official-engineering-permits-management-pd-1096)
* [11. 🌉 Municipal & Barangay Infrastructure Projects](#11--municipal--barangay-infrastructure-projects)
* [12. 🚨 Illegal Construction Monitoring & Regularization Process](#12--illegal-construction-monitoring--regularization-process)
* [13. 📄 Official Accomplishment Reports & Legal Signatures (PDF / Excel)](#13--official-accomplishment-reports--legal-signatures-pdf--excel)
* [14. 📦 Data Export & Multi-Level ZIP Archival Structures](#14--data-export--multi-level-zip-archival-structures)
* [15. 📱 Mobile, Tablet & Print Ergonomics Guidelines](#15--mobile-tablet--print-ergonomics-guidelines)
* [16. ⚖️ Legal & Regulatory Compliance (RA 10173, PD 1096, COA)](#16-️-legal--regulatory-compliance-ra-10173-pd-1096-coa)
* [17. 🧪 System Testing, Verification & Quality Assurance](#17--system-testing-verification--quality-assurance)
* [18. 🗺️ Complete System Master Flowchart Architecture](#18-️-complete-system-master-flowchart-architecture)

---

## 1. 🎯 Project Context, Problem Statement & Plain-Language Purpose

### 💡 What is eTala?
**eTala** (combining the digital prefix *"e"* for electronic governance and the Filipino word *"Tala"* meaning record, star, or guiding light) is the specialized web-based **Engineering Records Archiving and Retrieval Management System (ERARMS)** engineered specifically for the **Municipal Engineering Office (MEO) of Carigara, Leyte, Philippines**.

```mermaid
flowchart LR
    A[📂 Physical Paper Archive<br>Water/Insect Damage Risk] -->|Digital Transformation| B(⚡ eTala Enterprise Master)
    B --> C[🏗️ 4 Permit Types]
    B --> D[🌉 Public Infra Projects]
    B --> E[🗺️ 49 Barangays GIS]
    B --> F[📄 1-Click COA Reports]
    B --> G[💾 100% On-Premise Local Storage]
```

### 🔴 Problem Statement (The Legacy Setup)
Prior to eTala, the Carigara Municipal Engineering Office managed thousands of physical building permits, CAD blueprints, and infrastructure folders manually:
1. **Slow Retrieval Times**: Finding historical permits or blueprint plans from past years took hours to days of manually searching physical filing cabinets.
2. **Physical Degradation & Disaster Vulnerability**: Physical paper documents in coastal Leyte are vulnerable to typhoons, floodings, humidity, termites, and accidental misplacement.
3. **Tracking Compliance Gaps**: LGU inspectors had no automated alert system to track expiring Fire Safety (FSIC) certificates, contractor insurance bonds, or pending checklist items.
4. **Disjointed Reporting for Audits**: Preparing Annual Accomplishment Reports for the **Commission on Audit (COA)** or the **Sangguniang Bayan (SB)** required days of manual spreadsheet compilation.

### 🟢 The eTala Solution (Core Objectives)
1. 🗂️ **Zero Misplaced Folders**: 100% centralized digital indexing for all 4 permit types (*Building, Electrical, Occupancy, Fencing*) and public civil works (*Municipal and Barangay*).
2. 🗺️ **Full 49-Barangay Coverage**: Dedicated interactive geospatial mapping and digital workspace for all 49 barangays of Carigara.
3. 📋 **Automated Checklists**: Dynamic requirement slots (*Tax Declarations, Structural Plans, Fire Safety Certificates*) auto-generated per record.
4. 🔍 **Crystal-Clear In-Browser CAD Blueprint Viewer**: Pan, zoom, and inspect high-resolution CAD drawings directly in the web browser without downloading.
5. 📊 **1-Click Print-Ready Reports**: Generates formal PDF and Excel accomplishment reports with official municipal letterheads and tripartite signature blocks.
6. 🔒 **100% Data Sovereignty & Zero Recurring Cost**: Operates entirely on-premise on the LGU's local dedicated server with zero dependency on costly cloud subscriptions.

---

## 2. 🏛️ Academic / Thesis Manuscript Chapter Mapping (Chapters 1–5)

```
┌────────────────────────────────────────────────────────────────────────┐
│               THESIS / CAPSTONE MANUSCRIPT MAPPING                      │
├─────────────────┬──────────────────────────────────────────────────────┤
│ 📖 Chapter 1    │ • Introduction, Project Context & Objectives         │
│ (Introduction)  │ • Problem Statement & Scope/Delimitations            │
│                 │ • Significance to LGU Carigara & DICT Standards      │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 📚 Chapter 2    │ • Review of Related Literature & Studies (RRL/RRS)   │
│ (RRL & Systems) │ • National Building Code (PD 1096) & PSGC Standards  │
│                 │ • Data Privacy Act (RA 10173) & Electronic Gov Laws  │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 🛠️ Chapter 3    │ • Agile Software Development Lifecycle (SDLC)        │
│ (Methodology)   │ • System Architecture & On-Premise Network Topology  │
│                 │ • Database ERD, Data Dictionary & Security Model     │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 💻 Chapter 4    │ • Results, Discussion & Feature Implementation       │
│ (Results & UI)  │ • Module Walkthroughs, GIS Engine & Report Exports   │
│                 │ • In-Depth System Mechanics & Business Logic Rules   │
│                 │ • User Acceptance Testing (UAT) & Performance Stats │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 🎯 Chapter 5    │ • Summary of Findings, Conclusions & Recommendations │
│ (Conclusion)    │ • Future Expansion (Inter-Office LGU Integration)   │
└─────────────────┴──────────────────────────────────────────────────────┘
```

---

## 3. 💻 System Architecture, Tech Stack & 100% On-Premise Topology

### 3.1 Technology Stack Matrix

| Layer | Technology | Version | Key Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **Python / Django** | 5.1+ | Robust MTV architecture, ORM, CSRF/Auth security |
| **Database Engine** | **PostgreSQL / SQLite** | 16+ / 3+ | High-concurrency relational data & zero-latency queries |
| **Frontend Core** | **HTML5, Vanilla CSS3, JavaScript (ES6+)** | Modern | Zero dependency bloat, maximum rendering speed |
| **Mapping Engine** | **Leaflet.js + OpenStreetMap** | 1.9+ | Fast client-side GIS rendering for all 49 barangays |
| **Visualizations** | **Chart.js** | 4.4+ | Interactive annual bar charts & permit distribution doughnuts |
| **Document Engine** | **WeasyPrint / ReportLab & openpyxl** | Latest | Vector PDF rendering with letterheads & multi-sheet Excel |
| **Email Relay** | **Brevo SMTP / Google Workspace** | TLS 587 | 2FA verification codes, password resets & error alerts |

### 3.2 Municipal On-Premise Network Topology

eTala is architected for **100% On-Premise / Local Intranet Hosting** inside the Municipal Hall of Carigara, Leyte:

```mermaid
graph TD
    subgraph ServerRoom [🏢 LGU CARIGARA SERVER ROOM / IT OFFICE]
        Host[🖥️ Dedicated LGU Server Machine]
        DB[(🗄️ Local PostgreSQL Database)]
        Storage[💾 Local Disk / NAS Media Storage]
        Host --- DB
        Host --- Storage
    end

    subgraph MunicipalIntranet [🌐 LGU Local Area Network / Intranet / WiFi]
        Switch[🔀 Central Municipal Switch / Router]
        Host <--> Switch
    end

    subgraph OfficeClients [👥 Municipal Offices & Client Terminals]
        MEO[👷 Municipal Engineering Office<br>• Encoders & Inspectors]
        Mayor[🏛️ Mayor's Office<br>• Approval & Review]
        MPDC[📐 MPDC Office<br>• Planning & Zoning]
        Assessor[📋 Municipal Assessor<br>• Property Verification]
        Field[📱 Tablet Field Inspectors<br>• Site Ocular Inspections]

        Switch <--> MEO
        Switch <--> Mayor
        Switch <--> MPDC
        Switch <--> Assessor
        Switch <--> Field
    end
```

---

## 4. 🗄️ Database Schema & Entity-Relationship Architecture (ERD)

```mermaid
erDiagram
    CustomUser ||--o{ EngineeringRecord : "creates/manages"
    CustomUser ||--o{ AuditLog : "triggers"
    CustomUser ||--o{ UserDevice : "authorizes"
    CustomUser ||--o{ LoginAttempt : "logs"

    Barangay ||--o{ EngineeringRecord : "contains"
    
    EngineeringRecord ||--o{ RecordDocument : "holds"
    EngineeringRecord ||--o{ RequirementItem : "tracks"
    
    RequirementTemplate ||--o{ RequirementItem : "defines"

    Barangay {
        int barangay_id PK
        string barangay_name
        string psgc_code
        string district
        float latitude
        float longitude
    }

    EngineeringRecord {
        int id PK
        string record_type
        string sub_type
        string permit_number
        string project_title
        string applicant_name
        decimal project_cost
        string funding_source
        date date_issued
        date target_completion_date
        string status
        boolean is_illegal_construction
        boolean is_regularized
        datetime deleted_at
    }

    RecordDocument {
        int id PK
        string file
        string original_filename
        int version
        date expiration_date
        datetime uploaded_at
    }

    AuditLog {
        int id PK
        string action
        int target_record_id
        string ip_address
        datetime timestamp
    }
```

---

## 5. 👥 2-Tier Role-Based Access Control (RBAC) & Permission Matrix

```mermaid
graph TD
    subgraph AdminLevel [👑 SYSTEM ADMINISTRATOR]
        A1[User Accounts Management]
        A2[Database Backups & Recovery]
        A3[Permanent Trash Purge]
        A4[Security Logs & Blocked IPs]
    end
    subgraph StaffLevel [👷 ENGINEERING STAFF]
        S1[Encode Permits & Projects]
        S2[Upload Blueprints & Checklists]
        S3[49 Barangays GIS & Search]
        S4[Restore Own Deleted Items]
    end
    AdminLevel -.->|Inherits All Capabilities of| StaffLevel
```

### 📊 Master Permission Matrix

| 🛠️ System Action / Feature | 👷 Engineering Staff | 👑 System Administrator |
| :--- | :---: | :---: |
| **Encode New Permits, Projects & Violations** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Edit & Update Active Records** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Upload PDF Blueprints & Inspection Photos** | 🟢 **Allowed** | 🟢 **Allowed** |
| **In-Browser Document Preview (Pan/Zoom)** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Search Records & Use 49 Barangays GIS Map** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Export Accomplishment Reports (PDF & Excel)** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Export Single Record / Barangay ZIP Packages** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Move Records to Trash (Soft-Delete)** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Restore Own Deleted Records ("My Trash")** | 🟢 **Allowed** | 🟢 **Allowed** |
| **Restore Other Staff's Records ("All Trash")** | 🔴 *Denied* | 🟢 **Allowed** |
| **Permanent Record Deletion (Early Purge)** | 🔴 *Denied* | 🟢 **Allowed** |
| **Export Municipal Master ZIP (All 49 Barangays)**| 🔴 *Denied* | 🟢 **Allowed** |
| **Create, Edit & Deactivate User Accounts** | 🔴 *Denied* | 🟢 **Allowed** |
| **Database Backups & 1-Click Restoration** | 🔴 *Denied* | 🟢 **Allowed** |
| **Configure LGU Seal & Signatory Settings** | 🔴 *Denied* | 🟢 **Allowed** |
| **Security Audit Logs & Blocked IP Management** | 🔴 *Denied* | 🟢 **Allowed** |

---

## 6. ⚙️ IN-DEPTH SYSTEM MECHANICS & BUSINESS RULES (THE ENCYCLOPEDIA)

This section provides the rigorous technical mechanics, algorithms, triggers, formulas, and exact numbers governing eTala.

---

### 6.1 🔐 Login, Multi-Tier Lockout & IP Blacklist Mechanics

eTala defends municipal records against brute-force attacks and credential stuffing using a **2-Tier Security Lockout Algorithm**:

```mermaid
flowchart TD
    A[User Submits Credentials] --> B{Password Valid?}
    B -->|YES| C[Reset Failed Attempts = 0<br>Proceed to 2FA Check]
    B -->|NO| D[Log Failed Attempt in DB<br>Increment Failure Count]
    D --> E{Failed Attempts Count?}
    E -->|1 to 4 Tries| F[Display 'Invalid Credentials'<br>Remaining Tries Indicator]
    E -->|5 Tries in 15 Mins| G[⛔ TIER 1 LOCKOUT<br>15-Minute Temporary Cool-Off]
    E -->|10 Tries in 24 Hrs| H[🚫 TIER 2 LOCKOUT<br>Permanent Account Deactivation + IP Blacklisted]
```

#### 🔢 Exact Lockout Parameters & Auto-Unlock Rules:
1. **Tier 1 (Temporary 15-Minute Lockout)**:
   * **Trigger**: **5 consecutive failed password attempts** within a **15-minute rolling window**.
   * **System Behavior**: The login form locks out the user and displays a countdown timer.
   * **Unlock Methods**:
     * **Auto-Unlock**: Automatically unlocks after **15 minutes** elapse.
     * **Self-Service**: The user clicks *"Forgot Password"* and resets credentials via email.
     * **Admin Intervention**: An Administrator resets the password in `/users/`.
2. **Tier 2 (Permanent Deactivation & IP Blacklist)**:
   * **Trigger**: **10 failed login attempts** within **24 hours**.
   * **System Behavior**:
     * Sets `is_active = False` on the targeted user account.
     * Adds the client IP address to the `BlockedIP` table.
     * Dispatches an urgent security alert to `DEVELOPER_FEEDBACK_EMAILS`.
   * **Unlock Method**: Requires a System Administrator to unblock the IP and manually reactivate the account in the Admin Panel.

---

### 6.2 📧 Email Relay, 2FA OTP & Device Approval Mechanics

All automated emails (2FA OTPs, password resets, security notifications) are dispatched via an encrypted **SMTP Relay (Brevo / Gmail Workspace)** on port `587 (TLS)`:

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Staff User
    participant System as 🏛️ eTala Security Engine
    participant SMTP as 📨 Brevo / Gmail SMTP
    participant Inbox as 📬 User Email Inbox

    User->>System: Sign in from Unrecognized Browser
    System->>System: Generate 6-Digit Cryptographic OTP
    System->>SMTP: Dispatch OTP Email Template
    SMTP-->>Inbox: Deliver "Your eTala Verification Code"
    User->>System: Enter 6-Digit Code on Screen
    Note over System: Verifies Code (< 10 Mins, ≤ 5 Tries)
    System->>System: Set HTTP-Only 365-Day Trusted Cookie
    System-->>User: Grant Dashboard Access (Trusted for 1 Year)
```

#### 🔢 Email & Verification Constants:
* **2FA OTP Length**: **6 numeric digits** (e.g., `482910`).
* **2FA OTP Lifetime**: **10 minutes** from dispatch.
* **Maximum OTP Retries**: **5 failed attempts** before the OTP code is invalidated.
* **Resend Cooldown Timer**: **60 seconds** to prevent email flooding/spam.
* **Trusted Device Token Lifetime**: **365 Calendar Days (1 Year)** stored in an encrypted, HTTP-only, SameSite cookie.
* **Password Reset Token Lifetime**: **15 minutes** (single-use cryptographic HMAC token).
* **New Device Security Alert**: Instantly sends an email alert containing:
  * Device Name & Browser User-Agent
  * IP Address & Timestamp
  * 1-Click *"Lock My Account"* emergency security link.

---

### 6.3 🗑️ 30-Day Trash, Soft-Delete & Automated Midnight Purge Mechanics

To eliminate the catastrophe of accidental file deletion, eTala implements an **Indestructible 30-Day Soft-Delete Architecture**:

```mermaid
flowchart TD
    A[Staff Clicks Delete Record] --> B[Record Stamped with deleted_at = Now<br>Moved to /archive/ Trash]
    B --> C{30-Day Recovery Timer}
    C -->|Day 1 to 30| D[🟢 1-Click Instant Restore<br>Staff: 'My Trash' | Admin: 'All Trash']
    C -->|Day 23 to 30| E[🔔 High-Visibility Bell Alert<br>'7 Days Left Before Deletion']
    C -->|Day 0 Reached| F[⚙️ Automated Midnight Server Purge<br>Permanently Erased from Disk & DB]
```

#### 📐 The 30-Day Recovery Formula:
$$\text{Days Remaining} = \max\left(0, 30 - \left\lfloor\frac{\text{Current Timestamp} - \text{deleted\_at}}{86400}\right\rfloor\right)$$

#### 🔢 Trash Lifecycle Rules:
1. **Soft-Delete**: When deleted, the record is NOT erased. The field `deleted_at` is stamped with the current UTC timestamp, immediately hiding it from active modules, GIS maps, and accomplishment reports.
2. **Access Separation**:
   * **Staff ("My Trash")**: Encoders can view and restore only the records they personally soft-deleted.
   * **Admin ("All Trash")**: Administrators can view and restore any deleted record in the entire municipality.
3. **Automated Midnight Purge Command (`purge_expired_trash`)**:
   * Executes every night at **12:00 AM (Midnight)**.
   * Queries records where `deleted_at <= Now - 30 Days`.
   * Permanently erases the database rows and removes attached PDF files from disk, maintaining server storage hygiene.

---

### 6.4 📁 Document Archiving, 50MB Limits, Versioning (v1 $\rightarrow$ v2) & Signed URLs

```mermaid
flowchart LR
    Upload[PDF / Photo Upload] --> SizeCheck{File Size ≤ 50.0 MB?}
    SizeCheck -->|NO| ErrSize[🔴 Reject: Exceeds 50MB]
    SizeCheck -->|YES| TypeCheck{Valid MIME Type?<br>PDF for Permits / Photos for Illegal}
    TypeCheck -->|NO| ErrType[🔴 Reject: Invalid Format]
    TypeCheck -->|YES| SaveFile[💾 Save to Server /media/ Folder<br>Generate Dynamic Checklist Link]
    SaveFile --> ReplaceCheck{Is this a replacement?}
    ReplaceCheck -->|YES| IncVersion[Increment Version: v1 ➔ v2<br>Archive Old File in History]
    ReplaceCheck -->|NO| Done[Mark Checklist Slot Satisfied]
```

#### 🔢 Document Specifications:
* **Per-File Size Limit**: **50.0 MB** (accommodates high-resolution multi-page vector CAD drawings).
* **Format Restrictions**:
  * **Permits & Public Projects**: Strictly **PDF (`.pdf`)** to prevent document tampering.
  * **Illegal Construction Violations**: **PDF + Images (`.jpg`, `.jpeg`, `.png`, `.webp`)** for field inspection evidence.
* **Document Versioning (v1 $\rightarrow$ v2)**:
  * Replacing a blueprint automatically increments the version counter (**v1 $\rightarrow$ v2 $\rightarrow$ v3**).
  * The previous version is permanently archived in historical records for legal evidentiary audits.
* **10-Minute Temporary Signed URLs**:
  * In-browser document viewing generates a time-limited HMAC signed token (`/documents/serve/<token>/`).
  * Links expire in **10 minutes**, preventing unauthorized link copying or public leakage.

---

### 6.5 🔔 Expiration Alerts, 30-Day Threshold & Cross-Device Sync Mechanics

```mermaid
graph LR
    subgraph DocScanning [📄 STATUTORY DOCUMENT MONITORING]
        D1[Document with Expiration Date<br>e.g., FSIC, Contractor Bond] -->|≤ 30 Days Remaining| D2[🟡 Amber Bell Notification]
        D1 -->|Date Surpassed| D3[🔴 Red Expired Notification]
    end
    subgraph TrashScanning [🗑️ TRASH EXPIRATION MONITORING]
        T1[Soft-Deleted Record] -->|≤ 7 Days Remaining| T2[🚨 High-Visibility Purge Warning]
    end
```

#### 🔢 Notification Rules:
1. **Document Expiration (30-Day Window)**:
   * System continuously monitors documents with statutory expiration dates (e.g., Fire Safety Inspection Certificates, Contractor Licenses, Insurance Bonds).
   * Generates notifications when **remaining days $\le$ 30 days**.
   * Uploading an updated replacement document automatically satisfies the requirement and dismisses the alert.
2. **Trash Purge Warning (7-Day Window)**:
   * Generates an urgent warning when an archived record has **$\le$ 7 days** before permanent midnight deletion.
3. **Database-Backed Cross-Device Sync**:
   * Dismissing an alert on your desktop workstation updates your user notification state in the database.
   * When you log in on a field tablet or laptop, dismissed alerts **remain dismissed**.

---

### 6.6 💾 Disaster Recovery, Automated Midnight Backups & 14-Snapshot Rolling Retention

```mermaid
flowchart TD
    Midnight[🕛 Daily at 12:00 AM Midnight] --> CheckSameDay{Did Admin execute manual backup today?}
    CheckSameDay -->|YES| Skip[Smart Same-Day Skip<br>Conserves Server Disk Space]
    CheckSameDay -->|NO| RunBackup[Execute Automated JSON Snapshot Routine]
    RunBackup --> Snapshot[Generate Encrypted .json Snapshot<br>Users, Permits, Checklists, Logs]
    Snapshot --> Retention[Enforce 14-Snapshot Retention Window<br>Auto-Purge Backups Older than 14 Days]
```

#### 🔢 Backup & Recovery Rules:
* **Automated Schedule**: **Daily at 12:00 AM (Midnight)**.
* **Rolling Retention Window**: Retains the **14 most recent daily snapshots** (2 full weeks of rollback history); older snapshot files are automatically pruned to prevent server storage bloat.
* **Smart Same-Day Skip**: If an Admin manually clicks *"Download Backup"* during the day, the automated midnight script detects the fresh backup and skips redundant execution.
* **1-Click Emergency Disaster Recovery**: Uploading a valid `.json` backup file in `/settings/` restores all database tables, user accounts, records, checklists, and audit trails in under **2 minutes**.

---

### 6.7 📊 Accomplishment Computation & COA Compliance Formulas

$$\text{Total Official Accomplishments} = \text{Total Infrastructure Projects} + \text{Total Official Permits Issued}$$

$$\text{Checklist Completion Rate (\%)} = \left(\frac{\text{Fulfilled Required Documents}}{\text{Total Required Documents}}\right) \times 100$$

> [!CAUTION]
> ### ⚖️ Commission on Audit (COA) Compliance Rule
> **Illegal Construction Violations are NEVER counted as positive municipal accomplishments** in official accomplishment reports. They are tracked strictly as administrative enforcement indicators.

---

### 6.8 📜 Tamper-Proof Audit Trail & Reference Linking Mechanics

* **Module**: `/activity-logs/` (Administrators only).
* **Immutable Storage**: Every critical action (login, record creation, modification, soft-deletion, restoration, requirement waiving, document replacement) creates a permanent `AuditLog` row.
* **Exact Log Structure**:
  * **Timestamp**: Exact date and time (`YYYY-MM-DD HH:MM:SS`).
  * **User Account**: Full name and username of the acting employee.
  * **Action**: Human-readable summary (e.g., `Created Building Permit: 2026-06-00001`).
  * **Reference Link**: Direct clickable link (`Ref: Record #42`) navigating instantly to the affected record.
  * **IP Address**: Client network IP address.
* **Anti-Bloat Filter**: Routine background events (page views, thumbnail rendering, ping checks) are automatically excluded to preserve database query speed.

---

### 6.9 🗺️ 49-Barangay GIS Coordinates Persistence Mechanics

* **Module**: `/barangays/`
* Contains all **49 official barangays of Carigara, Leyte** with official Philippine Statistics Authority (PSA) PSGC 10-digit codes.
* **Persistence Guarantee**:
  * In `seed_coordinates.py` and `views.py`, the system checks:
    ```python
    if b.latitude is None or b.longitude is None:
        b.latitude = lat
        b.longitude = lng
    ```
  * Any coordinates modified or adjusted by LGU staff in the Barangay Workspace or Admin Panel are **permanently preserved** in the database and will **never be overwritten** by git pushes, server updates, or redeployments.

---

## 7. 👤 User Management, Safe Deactivation & Profile Workflows

* **Module**: `/users/` (System Administrators only).
* **Safe Employee Offboarding (`on_delete=models.PROTECT`)**:
  When an employee resigns or transfers, clicking **Deactivate** immediately revokes login privileges while keeping all historical permits, projects, checklists, and audit trail entries created by that employee 100% intact.
* **Self-Service Profile Updates (`/profile/`)**:
  Staff can update their Name, Job Title, Avatar photo, and Password. Updating a work email requires 6-digit OTP verification sent to their current email inbox.

---

## 8. 📊 Executive Dashboard, Visualizations & Topbar Search

* **Module**: `/dashboard/`
* **6 High-Visibility KPI Metric Cards**: Real-time totals of Total Records, Municipal Projects, Barangay Projects, Issued Permits, Incomplete Checklists, and Trash Items.
* **Chart.js Dynamic Visualizations**:
  * **Annual Volume Bar Chart**: Visualizes yearly infrastructure growth and permit issuance across years (1995–Present).
  * **Permit Distribution Doughnut**: Visualizes the breakdown of Building, Electrical, Occupancy, and Fencing permits.
* **Universal 250px Live Search**: Asynchronous multi-token searching debounced at 300ms.
* **Zero-Flicker Theme Switcher**: Dark Navy and Clean White modes stored in `localStorage`.

---

## 9. 📝 Records Encoding, 3-Step Wizard & Bulk Ingestion

* **Method 1: 3-Step Guided Wizard (`/records/new/`)**:
  * **Step 1: Scope & Categorization**: Select category, sub-type, 1 of 49 barangays, and year (1995–Present).
  * **Step 2: Technical & Financial Details**: Permit number, applicant/contractor name, cost (₱), dates, and remarks.
  * **Step 3: Checklist Upload**: Dynamically generated slots for attaching required PDFs.
* **Method 2: Single-Screen Form (`/records/create/`)**: Rapid encoding when all data and attachments are pre-gathered.
* **Method 3: Bulk Data Ingestion (`/records/bulk-encoding/`)**: Multi-row rapid data entry for digitizing historical paper backlogs.

---

## 10. 🏗️ Official Engineering Permits Management (PD 1096)

* **Module**: `/permits/`
* Enforces standard requirements in full compliance with the **National Building Code of the Philippines (Presidential Decree No. 1096)**.
* **4 Permit Types Supported**:
  1. 🏗️ **Building Permit**: Residential, Commercial, Industrial, Institutional, Agricultural.
  2. ⚡ **Electrical Permit**: Wiring installations, temporary service connections, transformer setups.
  3. 🏠 **Occupancy Permit**: Final completion certificates, safety clearances.
  4. 🧱 **Fencing Permit**: Perimeter concrete walls, boundary fences.

---

## 11. 🌉 Municipal & Barangay Infrastructure Projects

* **Modules**: `/municipal/` (Municipal Projects) & `/barangay/` (Barangay Projects).
* **4 Primary Civil Works Types**:
  * 🛣️ **Roads and Bridges**: Concreting, asphalt overlays, box culverts, bridge repairs.
  * 🏢 **Vertical Structures**: Multi-purpose evacuation centers, barangay halls, health clinics, school buildings.
  * 🌊 **Flood Control and Drainage**: River revetments, concrete drainage canals, seawalls.
  * 🚰 **Potable Water Systems**: Level II/III water supply networks, pumping stations, filtration facilities.
* **14 Standard Funding Sources**: `20% Development Fund`, `LGU General Fund`, `Barangay Fund`, `LDRRM Fund`, `Trust Fund`, `National Government Fund`, `DPWH`, `DILG`, `DOH`, `DepEd`, `Private`, `NGO`, `Others`.

---

## 12. 🚨 Illegal Construction Monitoring & Regularization Process

* **Module**: `/illegal-constructions/`
* **Flagging Violations (`/records/flag-illegal/`)**: Pin unpermitted structures on the GIS map, record inspection dates (cannot be in the future), and attach Notice of Violation (NOV) PDFs and field photos (`.jpg`, `.png`, `.webp`).
* **Regularization (`/records/<id>/regularize/`)**: Converts settled violations into legitimate Building Permits upon compliance, while permanently archiving all historical inspection evidence for legal audit.

---

## 13. 📄 Official Accomplishment Reports & Legal Signatures (PDF / Excel)

* **Module**: `/reports/`
* **Print-Ready PDF Reports**: Formatted for Legal (8.5" x 13") and A4 sheets with Republic of the Philippines letterhead, LGU Seal, and tripartite signature blocks:
  * **Prepared by**: Engineering Encoder / Inspector
  * **Verified & Recommending Approval**: Municipal Engineer
  * **Approved by**: Municipal Mayor
* **Multi-Sheet Excel (`.xlsx`)**: Formatted data tables ready for Sangguniang Bayan and Commission on Audit submissions.

---

## 14. 📦 Data Export & Multi-Level ZIP Archival Structures

```
Sanitized_Record_Title_Documents.zip/
├── 00_RECORD_SUMMARY.txt             <-- Formatted metadata sheet (Title, Date, Cost, Owner)
├── 01_Building_Plans/                <-- Parent group folder with child blueprints
│   ├── Architectural_Plans.pdf
│   └── Structural_Calculations.pdf
├── 02_Program_of_Works.pdf           <-- Direct leaf document
├── 03_Detailed_Estimates.pdf
├── Supporting_Documents/             <-- Extra affidavits, letters, or site photos
└── Incident_Evidence/                <-- Preserved NOV & photos (for regularized cases)
```

---

## 15. 📱 Mobile, Tablet & Print Ergonomics Guidelines

* **Mobile Breakpoints**:
  * `320px – 480px`: Wide tables automatically reflow into stacked cards.
  * `768px – 1024px`: Tablet split GIS map & list layout.
  * `1281px – 1920px+`: Full desktop tabular dashboard.
* **Touch Target Standard**: All interactive buttons, icon triggers, and dropdowns maintain a minimum **44px – 48px hitbox**.
* **iOS Zoom Prevention**: Form inputs maintain a minimum `font-size: 16px` to prevent unwanted iOS Safari zooming.
* **Ink-Saving Clean Print (`@media print`)**: Strips dark backgrounds and sidebars, producing clean white paper prints.

---

## 16. ⚖️ Legal & Regulatory Compliance (RA 10173, PD 1096, COA)

| Legal Framework | How eTala Complies |
| :--- | :--- |
| **Data Privacy Act of 2012 (RA 10173)** | On-premise hosting, 10-minute temporary signed URLs, strict 2-tier RBAC, password hashing, 2FA device verification. |
| **National Building Code (PD 1096)** | Standardizes building, electrical, occupancy, and fencing permit checklists and structural approval records. |
| **COA Archival Guidelines** | Immutable audit trails, 30-day soft-delete grace periods, and audit-compliant reporting. |
| **Anti-Red Tape Act (ARTA / RA 11032)** | Accelerates permit retrieval from days to seconds; automated tracking of document completion rates. |

---

## 17. 🧪 System Testing, Verification & Quality Assurance

* **Unit & Integration Test Suite (`permits/tests.py`)**: Covers authentication, 2FA OTP flows, permit creation wizard, document uploads, and report generation.
* **Cross-Browser Testing**: Tested and verified on Google Chrome, Mozilla Firefox, Microsoft Edge, and Apple Safari.

---

## 18. 🗺️ Complete System Master Flowchart Architecture

```mermaid
flowchart TD
    subgraph S1 [1. AUTHENTICATION & SECURITY]
        L1[User Login] --> L2{Device Recognized?}
        L2 -->|New Device| L3[6-Digit OTP to Gmail]
        L3 --> L4[365-Day Trusted Cookie]
        L2 -->|Trusted| L5[Direct Dashboard Access]
        L1 -->|5 Failed Tries| L6[15-Min Cool-Off Lockout]
    end

    subgraph S2 [2. EXECUTIVE DASHBOARD]
        L5 --> D1[KPI Summaries & Incomplete Alerts]
        D1 --> D2[Chart.js Volume & Permit Distributions]
        D1 --> D3[30-Day Document & 7-Day Trash Bell Alerts]
    end

    subgraph S3 [3. ENCODING & MODULES]
        D1 --> E1[3-Step Wizard / Single Page]
        E1 --> E2[49 Barangays & Year 1995-Present]
        E1 --> E3[Permits: Building, Electrical, Occupancy, Fencing]
        E1 --> E4[Projects: Municipal vs Barangay & 14 Fund Sources]
        E1 --> E5[Violations: GPS Pin, Photos & Regularization]
    end

    subgraph S4 [4. COMPLIANCE & FILES]
        E3 & E4 & E5 --> C1[Dynamic Checklist Template]
        C1 --> C2[Up to 50 MB PDFs & Photos]
        C1 --> C3[Batch Upload & Versioning v1 to v2]
        C1 --> C4[10-Min In-Browser Secure Preview]
    end

    subgraph S5 [5. EXPORTS & GOVERNANCE]
        C1 --> G1[Dual PDF & Excel Accomplishment Reports]
        C1 --> G2[Single Record & Barangay ZIP Archives]
        C1 --> G3[Immutable AuditLog Trail]
        C1 --> G4[Daily Backups with 14-Day Retention]
    end

    subgraph S6 [6. TRASH & DATA LIFECYCLE]
        G1 & G2 --> T1[Soft-Delete to Trash /archive/]
        T1 --> T2[30-Day Recovery Countdown Window]
        T2 --> T3[Staff 'My Trash' vs Admin 'All Trash' Restore]
        T2 -->|Day 0 Reached| T4[Automated Midnight Server Purge]
    end
```

---
*End of Master System Documentation, Technical Mechanics Encyclopedia & Academic Manuscript Guide (Version 2.0)*  
*🏛️ eTala (ERARMS) — Municipal Engineering Office, Local Government Unit (LGU) of Carigara, Leyte*
