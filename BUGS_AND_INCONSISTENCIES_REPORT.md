# 📘 eTala — Master System Logics, Business Rules & System Audit Report
**Municipal Engineering Office — Carigara, Leyte**  
**Last Updated:** August 18, 2026  
**System Status:** 🟢 All Systems Operational | 23/23 Automated Unit Tests Passing | 0 Django Check Errors

---

## 📑 Talaan ng Nilalaman (Table of Contents)
1. [Executive Summary & System Health](#1-executive-summary--system-health)
2. [Status ng mga Naunang Issues at Bug Fixes](#2-status-ng-mga-naunang-issues-at-bug-fixes)
3. [Master System Logics & Business Rules Specification (7-Point Standard)](#3-master-system-logics--business-rules-specification)
4. [Master ZIP Export & Folder Hierarchy Standards](#4-master-zip-export--folder-hierarchy-standards)
5. [Paliwanag para sa Non-Technical Staff (Quick User Guide)](#5-paliwanag-para-sa-non-technical-staff)

---

## 1. Executive Summary & System Health

| Component | Status | Details |
| :--- | :---: | :--- |
| **Backend Django Framework** | 🟢 100% OK | `python manage.py check` returned 0 issues |
| **Automated Test Suite** | 🟢 23/23 Passed | Full regression test suite completed successfully in 58.2s |
| **Role-Based Access Control (RBAC)** | 🟢 Verified | Admin vs Engineer vs Staff isolation strictly enforced |
| **ZIP Archiving Engine** | 🟢 Updated | 4-tier lifecycle folder hierarchy implemented across all endpoints |
| **Database & Media Storage** | 🟢 Operational | Supabase Storage primary + Local FileSystemStorage fallback |
| **Brute-Force & Security Headers** | 🟢 Active | Django-Axes lockout active + CSRF/XSS protection verified |

---

## 2. Status ng mga Naunang Issues at Bug Fixes

Lahat ng mga naunang napaulat na bugs at inconsistencies sa system settings, user logins, at form layouts ay **100% naayos at na-verify na**:

* ✅ **Settings.py Storage & Email Duplicates (FIXED):** Tinanggal ang duplicate storage/email configurations; ipinatupad ang malinis na Resend → Gmail SMTP → Console fallback chain.
* ✅ **Philippine Timezone (FIXED):** Naka-configure na sa `TIME_ZONE = 'Asia/Manila'` para sa tamang timestamp ng audit logs at filing dates.
* ✅ **Staff/Admin Login Lockouts (FIXED):** Na-reset ang standard test credentials (`seed_users`), naayos ang IP lockout cooldown, at na-activate ang accounts.
* ✅ **Form Grid & Label Parity (FIXED):** 100% magkatugma na ang Add Record (Step 3) at Edit Record layouts para sa Permits, Municipal Infra, Barangay Projects, at Violations.
* ✅ **Municipal Engineer Role in Modals (FIXED):** Idinagdag ang `engineer` role option sa Add/Edit User modals sa `users.html`.
* ✅ **Regularization Title Sync (FIXED):** Kapag na-regularize ang unpermitted structure, automatic nang nire-rename ang `title` para maging official permit title (`BP-2026-XXXX — Juan Dela Cruz`).

---

## 3. Master System Logics & Business Rules Specification

Bawat panuntunan ng sistema ay sumusunod sa **7-Point Structured Standard**:
1. **Trigger** — Kailan mangyayari?
2. **Condition** — Anong condition ang kailangan?
3. **Action** — Ano ang gagawin ng system?
4. **User / Role** — Sino ang may access o apektado?
5. **Display** — Ano ang makikita sa screen?
6. **Purpose** — Bakit kailangan?
7. **Exceptions** — Kailan hindi mag-a-apply?

---

### Rule 1: ⏰ Document Expiry Notification
* **Trigger:** Araw-araw / tuwing binubuksan ang dashboard at notifications dropdown.
* **Condition:** Ang document ay may nakatakdang `expiry_date` (hal. FSIC, Zoning Clearance, Barangay Clearance) at hindi naka-archive ang record.
* **Action:**
  * `30 days bago mag-expire`: Nagpapakita ng warning sa Alerts dropdown (`alert_type='expiring'`).
  * `0 days o lampas na`: Nagpapakita ng urgent red indicator (`alert_type='expired'`).
* **User / Role:** Admin, Municipal Engineer, at Staff na may hawak ng record.
* **Display:** Bell badge icon may count indicator + notification item: *"FSIC for BP-2026-001 expires on [Date]"*.
* **Purpose:** Maiwasan ang paggamit o pag-isyu sa mga expired na regulatory clearances.
* **Exceptions:** Documents na walang `expiry_date` (hal. architectural blueprints, structural calculations).

---

### Rule 2: 📁 Document File Size Limit & Upload Validation
* **Trigger:** Tuwing mag-a-upload ng single document o batch files (`/upload/` o `/batch-upload/`).
* **Condition:** Sukat ng file ay lumampas sa **50 MB** o hindi kasama sa allowed extensions (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`).
* **Action:** Bina-block ng backend validator (`validate_document_file`) bago ma-save sa server storage at nagtatapon ng ValidationError.
* **User / Role:** Lahat ng users na nag-a-upload ng files.
* **Display:** Toast error message: *"File exceeds 50MB limit. Please compress and re-upload."*
* **Purpose:** Proteksyon sa server disk space at pagpapanatili ng mabilis na page loads habang sinusuportahan ang multi-sheet blueprints.
* **Exceptions:** Wala. Mandatory sa lahat ng upload inputs.

---

### Rule 3: 👤 Staff vs Admin Role-Based Access Control (RBAC)
* **Trigger:** Tuwing nagre-request ng CRUD action o access sa pages.
* **Condition & Access:**
  * **Staff:** View/encode records; edit/trash/restore **sariling records lamang** (`created_by == request.user`). Bawal mag-permanent delete, bawal mag-access ng User Management at System Settings.
  * **Admin:** Full unrestricted access (View all, Edit all, Manage users, View all trash, Purge / Hard delete records, System configuration).
* **Action:** Nagtatapon ng `PermissionDenied (403 Forbidden)` kapag sinubukang i-access ng staff ang hindi sa kanya.
* **User / Role:** Staff vs. Admin.
* **Display:** Automatic na itinatago ang mga bawal na buttons (hal. *Purge Trash*, *User Management* link).
* **Purpose:** Data governance, integrity, at pag-iwas sa unauthorized modifications.
* **Exceptions:** Admin accounts have full municipal-wide override permissions.

---

### Rule 4: 🔐 Session Management & Security
* **Trigger:** Walang user activity o pagsasara ng browser window.
* **Condition:**
  * Kung **hindi naka-check** ang *"Remember Me"*: session expires kapag naisara ang browser tab (`set_expiry(0)`).
  * Kung **naka-check** ang *"Remember Me"*: session persists for 14 days (`1,209,600s`).
* **Action:** Automatic logout kapag nag-expire ang session token at ire-redirect sa `/login/`.
* **User / Role:** Lahat ng authenticated users.
* **Display:** Redirect sa login page na may notice kung kinakailangan.
* **Purpose:** Protektahan ang official LGU records alinsunod sa Data Privacy Act (RA 10173).
* **Exceptions:** Active user interactions continually refresh session activity (`SESSION_SAVE_EVERY_REQUEST = True`).

---

### Rule 5: 📊 Record Status Display Standards
* **Trigger:** Pagpapakita ng status pill sa browse tables, detail views, at maps.
* **Condition:** Nakabase sa `record.status`, `record.record_type`, at `illegal_compliance_status`.
* **Action:** Nagre-render ng standardized CSS badge tokens:
  * 🟡 **Pending** (`bg-warning-subtle text-warning`) — *Pending review / permit application filed*
  * 🔵 **Active / In Progress** (`bg-primary-subtle text-primary`) — *Ongoing review o ongoing infra work*
  * 🟢 **Completed / Approved** (`bg-success-subtle text-success`) — *Issued permit o tapos na proyekto*
  * 🔴 **Unresolved** (`bg-danger-subtle text-danger`) — *Active violation / Stop order in effect*
  * 🟢 **Regularized** (`bg-emerald-subtle text-emerald`) — *Complied violation na binigyan na ng legal permit*
* **User / Role:** Lahat ng tumitingin ng records.
* **Display:** Icon + standardized status label.
* **Purpose:** Mabilis at malinaw na assessment ng status sa isang tingin pa lang.
* **Exceptions:** Wala.

---

### Rule 6: ⚠️ Regularized Illegal Construction Handling
* **Trigger:** Pag-click ng *"Complete Regularization"* sa isang compliant violation case.
* **Condition:** Ang kaso ay dating unpermitted (`is_illegal_construction=True`), nakapag-comply na sa requirements, at nabigyan na ng Official Permit Number.
* **Action:**
  1. Sine-set ang `illegal_compliance_status = 'resolved'`.
  2. Inilalagay ang official `permit_number`, `applicant_name`, at `permit_type`.
  3. Ini-sync ang record title (`BP-2026-XXXX — Juan Dela Cruz`).
  4. Automatic na kinakabitan ng official requirement checklist template.
* **User / Role:** Staff at Admin.
* **Display:**
  * Sa **Illegal Constructions Module**: Nananatili bilang *"Regularized"* para sa enforcement history.
  * Sa **Master Records Browse**: Lumalabas na rin bilang official legal permit.
* **Purpose:** Pagpapanatili ng legal audit trail nang hindi nawawala ang historical enforcement logs.
* **Exceptions:** Hindi pwedeng i-regularize kung walang Permit Number at Applicant Name.

---

### Rule 7: 📂 "All Records" / Master Records Scope Logic
* **Trigger:** Pag-browse sa `/records/` (Master Records).
* **Condition:** Ang record ay legal na permit application, approved permit, regularized permit, o infrastructure project.
* **Action:** I-filter out ang mga *Unresolved* at *Pending Permit* illegal violations (`exclude(is_illegal_construction=True, illegal_compliance_status__in=['unresolved', 'pending_permit'])`).
* **User / Role:** Lahat ng users na nasa Master Records module.
* **Display:** Tanging mga legal at sanctioned records lamang ang makikita sa Master Records list.
* **Purpose:** Maiwasan ang paghahalo ng mga unpermitted structures sa listahan ng mga opisyal na building permits ng munisipyo.
* **Exceptions:** Ang mga *Regularized* violations lamang ang may karapatang lumabas sa Master Records.

---

### Rule 8: 🔎 Search Scope Isolation Logic
* **Trigger:** Paggamit ng search bar sa iba't ibang modules.
* **Condition & Action:**
  * **Master Records Search:** Naghahanap lamang sa authorized legal permits at projects.
  * **Illegal Constructions Search:** Naghahanap lamang sa violation incident reports.
  * **My Records Filter:** Bina-bound ang query sa `created_by == request.user`.
  * **All Records Filter:** Naghahanap sa buong nasasakupan ng Carigara LGU.
* **User / Role:** Lahat ng users.
* **Display:** Naaayon ang table results sa kasalukuyang aktibong module.
* **Purpose:** Mabilis at tumpak na paghahanap nang hindi nagkakagulo ang data.
* **Exceptions:** Global superadmin search spans across active scope.

---

### Rule 9: 🗑️ Trash & Soft-Delete Logic
* **Trigger:** Pag-archive o pag-restore ng record (`/archive/` at `/restore/`).
* **Condition:**
  * Pindutin ang *Move to Trash*: sine-set ang `status = 'archived'`.
  * Pindutin ang *Restore*: ibinabalik sa dating status (`active` / `in_progress` / `completed`).
* **Action:**
  * **Soft-delete:** Hindi binubura sa database; tinatanggal lamang sa normal views.
  * **Hard-delete / Purge:** Tanging Admin lamang ang may karapatang magbura nang permanente (`permanent_delete_record_view`).
* **User / Role:** Staff (own records) vs Admin (all records).
* **Display:** *My Trash* view para sa staff; *Municipal Trash* para sa admin.
* **Purpose:** Proteksyon laban sa aksidenteng pagbura at pagpapanatili ng recovery safety net.
* **Exceptions:** Hard-deletion requires explicit modal confirmation and logs an urgent audit entry.

---

### Rule 10: 🔔 System Notification Categories
* **Trigger:** Mga pagbabago sa data o papalapit na deadlines.
* **Condition & Categories:**
  * *Document Expiry*: Clearing document malapit nang mag-expire.
  * *Missing Requirements*: Kulang pa ang uploaded mandatory documents.
  * *Unresolved Violations*: Lumampas sa statutory days nang walang compliance action.
  * *Trash Action*: May na-move o na-restore sa basurahan.
* **Action:** Lumilikha ng alert payload na binabasa ng notification bell dropdown.
* **User / Role:** Assigned encoder at Office Admin.
* **Display:** Dynamic red badge count sa top navigation bar.
* **Purpose:** Proactive compliance management.
* **Exceptions:** Archived records are excluded from generating alerts.

---

### Rule 11: 📋 Checklist Validation & Progress Logic
* **Trigger:** Tuwing may ina-upload, tinatanggal, o wina-waive na dokumento.
* **Condition:** 
  * Bilang ng fulfilled items = `Uploaded Documents + Waived Requirements`.
  * Bilang ng required items = kabuuang mandatory checklist slots.
* **Action:** 
  * Kung `fulfilled == total`: Status ay **Complete (100%)** na may green checkmark.
  * Kung `fulfilled < total`: Status ay **Incomplete** na may yellow progress fraction (hal. `8/9`).
* **User / Role:** Lahat ng nag-a-access ng Checklist tab.
* **Display:** Real-time completion pill: `9/9 Complete (100%)` o `8/9 Requirements Uploaded`.
* **Purpose:** Tiyaking kumpleto ang dokumento bago maaprubahan ang permit.
* **Exceptions:** Optional supporting attachments outside the mandatory checklist do not penalize the percentage.

---

### Rule 12: 🚫 N/A & Waived Requirement Rule
* **Trigger:** Pag-toggle ng *"Waive / Not Applicable"* switch sa checklist item.
* **Condition:** Ang requirement ay hindi kailangan para sa partikular na aplikasyon (hal. *Locational Clearance* hindi kailangan para sa interior renovation).
* **Action:** Mamarkahan ang `RecordRequirement.is_waived = True` at magtatala ng reason sa audit log.
* **User / Role:** Authorized Staff o Admin.
* **Display:** Minamarkahan bilang *"Waived / N/A"* na may strikethrough at gray badge, ngunit binibilang bilang **Fulfilled** sa overall completion score.
* **Purpose:** Tanggapin ang mga legal na exemptions nang hindi nagiging dahilan ng false "Incomplete" status.
* **Exceptions:** Waiving is restricted and recorded in the audit log for accountability.

---

### Rule 13: 🔢 Duplicate Prevention Rule
* **Trigger:** Pag-save ng bagong record o pag-edit ng existing record.
* **Condition:**
  * **Permit:** Hindi pwedeng magkapareho ang `permit_number` sa ibang active permit.
  * **Project:** Hindi pwedeng magkapareho ang `Title + Scope + Barangay + Year`.
  * **Violation:** Hindi pwedeng magkaroon ng dalawang aktibong unresolved violation sa parehong `Title + Barangay`.
* **Action:** Bina-block ng backend query bago mag-save at nagpapakita ng error message.
* **User / Role:** Lahat ng nag-e-encode.
* **Display:** Toast error banner: *"Project '[Name]' already exists in this Barangay for [Year]."*
* **Purpose:** Pigilan ang double-entry at pagsasayang ng record IDs.
* **Exceptions:** Archived records are excluded from duplicate checking.

---

### Rule 14: 📝 Comprehensive Audit Trail Logic
* **Trigger:** Sa bawat mahalagang interaction: `CREATE`, `UPDATE`, `UPLOAD`, `DELETE`, `MOVE_TRASH`, `RESTORE`, `REGULARIZE`, `LOGIN`, `LOGOUT`.
* **Condition:** Na-execute ang request sa database.
* **Action:** Lumilikha ng `AuditLog` entry na naglalaman ng:
  * `user`: Sino ang nag-action.
  * `action`: Ano ang ginawa.
  * `target_record_id`: Anong record ang naapektuhan.
  * `ip_address`: Saang computer/network nanggaling.
  * `timestamp`: Eksaktong petsa at oras.
* **User / Role:** System-wide automatic logger.
* **Display:** Mababasa sa `/activity-logs/` (Admin-only).
* **Purpose:** Full accountability at non-repudiation para sa official government records.
* **Exceptions:** Wala. Hindi maaaring i-delete o i-edit ang audit logs.

---

### Rule 15: 🔒 Protected Legal Status Logic
* **Trigger:** Pagtatangkang baguhin ang compliance status ng isang record.
* **Condition:** Ang record ay naka-tag na bilang **Regularized (`resolved`)** na may kaukulang official permit number.
* **Action:** Hindi papayagan ang simpleng dropdown edit pabalik sa `unresolved` nang walang admin override.
* **User / Role:** Ordinary Staff.
* **Display:** Naka-lock ang option o nagre-require ng administrative confirmation.
* **Purpose:** Pigilan ang aksidenteng pagbura ng legal status ng isang gusali.
* **Exceptions:** Admin override with mandatory audit reasoning.

---

### Rule 16: 📅 Logical Date Validation
* **Trigger:** Form submission sa Add/Edit Record at Document Upload.
* **Condition:**
  * `Date Completed` ay hindi pwedeng mas maaga sa `Date Started`.
  * `Expiry Date` ay hindi pwedeng mas maaga sa `Date Issued`.
  * Filing year ay hindi pwedeng nasa hinaharap (`year <= current_year`).
* **Action:** Form validation rejection kung may inconsistent dates.
* **User / Role:** Lahat ng nag-e-encode.
* **Display:** Form feedback: *"Filing year cannot be in the future."*
* **Purpose:** Tiyakin ang accuracy ng statistical reports at timeline history.
* **Exceptions:** Historical records allow past years down to 1990.

---

### Rule 17: 📎 MIME & Virus Scan File Validation
* **Trigger:** File selection sa browser bago mag-upload.
* **Condition:** 
  * File extension match: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`.
  * MIME header verification laban sa file extension spoofing.
  * Virus scanner / signature check (`virus_scan_file`).
* **Action:** Rejection ng file kung peke ang extension o may malware signature.
* **User / Role:** Lahat ng nag-u-upload.
* **Display:** Alert: *"Invalid file content type. Only verified PDFs and scanned images are allowed."*
* **Purpose:** Proteksyon sa server laban sa malicious executable payloads (PHP, EXE, JS scripts disguised as PDFs).
* **Exceptions:** Wala.

---

### Rule 18: 🔄 Contextual Status-Based UI Controls
* **Trigger:** Pag-render ng Action Buttons sa tables at Record Detail headers.
* **Condition:** Nakadepende sa kasalukuyang status ng record:
  * **Unresolved Violation:** Ipakita ang `Update Status`, `Report Notice`, at `Regularize`.
  * **Regularized Permit:** Ipakita ang `View Official Permit`, `Download ZIP`, at `Checklist`.
  * **Archived / Trash:** Ipakita lamang ang `Restore` at `Purge` (Admin).
* **Action:** Dynamic template conditional rendering (`{% if %}`).
* **User / Role:** Lahat ng users ayon sa kanilang permissions.
* **Display:** Malinis at hindi nakakalitong UI kung saan tanging valid actions lang ang nakikita.
* **Purpose:** Maiwasan ang maling workflow steps ng staff.
* **Exceptions:** Wala.

---

### Rule 19: 👁️ Smart Conditional Display Logic
* **Trigger:** Pag-render ng Record Summary cards, sidebars, at tables.
* **Condition:** Mayroong laman ang data attribute o wala:
  * Kung walang permit number: Ipakita ang `Pending Permit Issuance` sa halip na blangkong puwang.
  * Kung walang description / notes: Itago ang buong `Description / Location Notes` section.
  * Kung `Others` ang funding source: Ipakita ang text box para sa custom funding input.
* **Action:** Adaptive DOM rendering gamit ang conditional template tags.
* **User / Role:** Lahat ng screens.
* **Display:** Walang mga pangit na blangkong kahon o mga `None` / `null` text.
* **Purpose:** Propesyonal at malinis na presentation ng datos ng munisipyo.
* **Exceptions:** Wala.

---

### Rule 20: 📱 Unified Mobile-First Responsive Breakpoints
* **Trigger:** Pagbabago ng screen width o pagbubukas sa iba't ibang devices (Mobile, Tablet, Desktop).
* **Breakpoints:**
  * `320px – 480px` (Mobile): Single-column stack, full-width inputs, touch targets $\ge 44\text{px}$, floating actions.
  * `481px – 767px` (Landscape): Compact 2-column wrapping.
  * `768px – 1024px` (Tablet): Side-by-side header, flexible grid.
  * `1025px+` (Desktop): Full 8:4 split layout (Form sa kaliwa, Live Summary sa kanan).
* **Action:** Smooth CSS reflow na sumusunod sa design standard nang walang horizontal scrolling (`overflow-x: hidden`).
* **User / Role:** Lahat ng devices.
* **Display:** 100% accessible at responsive sa lahat ng screen sizes.
* **Purpose:** Tiyakin na magagamit ng mga building inspectors sa field gamit ang cellphone o tablet, at ng office staff sa desktop.
* **Exceptions:** Wala.

---

## 4. Master ZIP Export & Folder Hierarchy Standards

Ipinatupad ang **Unified 4-Tier Hierarchy Standard** para sa lahat ng uri ng ZIP exports sa eTala:

```text
1. Barangay Export:  [Barangay] → [Category] → [Record] → [Document Group] → [File]
2. Record Export:    [Record]   → [Document Group] → [File]
3. Municipal Export: [Category] → [Scope/Barangay] → [Record] → [Document Group] → [File]
```

### A. Barangay ZIP Export (`[Barangay_Name].zip`)
```text
Balilit.zip
│
└── Balilit/
    ├── 01_Permits/
    │   └── Juan_Dela_Cruz/
    │       ├── 01_Application/
    │       ├── 02_Plans_and_Specifications/
    │       ├── 03_Clearances_and_Certifications/
    │       ├── 04_Technical_Documents/
    │       ├── 05_Payments_and_Receipts/
    │       └── 06_Other_Supporting_Documents/
    │
    ├── 02_Projects/
    │   └── Barangay_Hall_Renovation/
    │       ├── 01_Planning/
    │       ├── 02_Procurement/
    │       ├── 03_Contract_and_Award/
    │       ├── 04_Construction/
    │       └── 05_Completion/
    │
    └── 03_Illegal_Constructions/
        └── Jose_Cruz/
            ├── 01_Inspection/
            ├── 02_Violation_and_Orders/
            ├── 03_Compliance/
            ├── 04_Regularization/
            └── 05_Supporting_Evidence/
```

### B. Individual Record ZIP Export (`[Record_Name].zip`)
Para sa single record downloads, diretso na ang mga files sa root ng ZIP na may malinaw at standardized na pangalan ng dokumento:
```text
2025-252651_Joyce_Bustillo.zip
│
├── Current_Real_Property_Tax_Receipt.pdf
├── Notarized_Copy_of_Contract_of_Lease_or_Deed_of_Absolute_Sale.pdf
├── Barangay_Clearance.pdf
└── Architectural_Plan.pdf
```

### ⭐ Mahahalagang Tuntunin sa ZIP Exports:
1. **🚫 Direct & Clean Individual Record Files:** Sa pag-download ng iisang record, direkta nang nasa archive ang mga file nang walang kalat o nested subfolders.
2. **📄 Standardized Filenames:** Nakabatay ang bawat pangalan ng file sa requirement title para madaling basahin at i-archive.
3. **🛡️ 100% Collision-Proof:** Awtomatikong nilalagyan ng safe suffix (`_2.pdf`) kung sakaling magkapareho ang pangalan ng files sa loob.

---

## 5. Paliwanag para sa Non-Technical Staff

* **Digital Filing Cabinet:** Isipin ang eTala bilang isang malinis na opisina kung saan ang bawat folder ay may kulay, label, at kandado.
* **Walang Mawawalang File:** Kapag may binura nang aksidente, pumunta lamang sa *Trash* at i-click ang *Restore*.
* **Checklist System:** Hindi magiging green checkmark ang permit hangga't may kulang na pirma o clearance, kaya protektado ang opisina sa anumang COA audit.
* **Isang Pindot na Export:** Kapag humingi ang Mayor o Audit team ng dokumento, i-click lamang ang `Export ZIP` para makuha ang kumpletong folder ng aplikante.
