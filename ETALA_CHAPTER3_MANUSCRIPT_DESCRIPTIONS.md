# Chapter 3: System Architecture and System Design
### eTala: Engineering Office Management and GIS Information System
**Municipal Engineering Office — Local Government Unit of Carigara, Leyte**

---

## Figure 3.1: Hardware and Cloud Architecture

Figure 3.1 illustrates the hardware and cloud architecture connecting office workstations to the eTala web server. The server connects to cloud services for database records, document storage, GIS map displays, and email login verification codes.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart TD
    Client["Engineering Office Workstations"]
    Server["eTala Web Server"]

    subgraph Services [" Cloud Services "]
        direction LR
        C[("Records Database")]
        D["Document Storage"]
        E["GIS Map Service"]
        F["Email OTP Service"]
    end

    Client <-->|Web Access| Server
    Server <-->|Permits &<br/>Projects Data| C
    Server <-->|Uploaded<br/>Files| D
    Server <-->|Map<br/>Coordinates| E
    Server -->|Email OTP<br/>Codes| F

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef client fill:#f0f9ff,stroke:#0284c7,stroke-width:1.5px,color:#0369a1,font-weight:bold;
    classDef server fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;
    classDef db fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#14532d,font-weight:bold;
    classDef storage fill:#fefce8,stroke:#ca8a04,stroke-width:1.5px,color:#854d0e,font-weight:bold;
    classDef gis fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0369a1,font-weight:bold;
    classDef otp fill:#faf5ff,stroke:#7c3aed,stroke-width:1.5px,color:#581c87,font-weight:bold;
    classDef box fill:#f8fafc,stroke:#94a3b8,stroke-width:1.2px,stroke-dasharray: 4 4,color:#1e293b,font-weight:bold;

    class Client client;
    class Server server;
    class C db;
    class D storage;
    class E gis;
    class F otp;
    class Services box;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.1. Hardware and Cloud Architecture**

---

## Figure 3.2: Use Case Diagram

Figure 3.2 outlines the operational functions assigned to Engineering Staff and the Municipal Engineer in the eTala system. Engineering Staff handle record encoding, document uploads, map viewing, violation logging, and report generation, while the Municipal Engineer has full access to all operational tasks plus exclusive controls for user accounts, audit logs, and record restorations.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Staff["Engineering Staff"]

    subgraph System [" eTala System "]
        direction LR
        subgraph Ops [" Operational Features "]
            direction TB
            UC1(["Log In"])
            UC2(["Encode Records"])
            UC3(["Upload Documents"])
            UC4(["View GIS Map"])
            UC5(["Log Violations"])
            UC6(["Generate Reports"])
            UC7(["Move to Trash"])
        end

        subgraph AdminOps [" Administration "]
            direction TB
            UC8(["Restore Records"])
            UC9(["Manage User Accounts"])
            UC10(["View Audit Logs"])
        end
    end

    Admin["Municipal Engineer"]

    Staff --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7
    UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 --- Admin
    UC8 & UC9 & UC10 --- Admin

    classDef staffStyle fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1,font-weight:bold;
    classDef adminStyle fill:#0f2b5c,stroke:#091e42,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef ucOps fill:#ffffff,stroke:#0284c7,stroke-width:1.3px,color:#0f172a,font-weight:600;
    classDef ucAdmin fill:#faf5ff,stroke:#7c3aed,stroke-width:1.3px,color:#4c1d95,font-weight:600;
    classDef systemBox fill:#f8fafc,stroke:#0f2b5c,stroke-width:1.5px,stroke-dasharray: 4 4,color:#0f2b5c,font-weight:bold;
    classDef subBox fill:#ffffff,stroke:#cbd5e1,stroke-width:1px,stroke-dasharray: 3 3,color:#475569,font-weight:600;

    class Staff staffStyle;
    class Admin adminStyle;
    class UC1,UC2,UC3,UC4,UC5,UC6,UC7 ucOps;
    class UC8,UC9,UC10 ucAdmin;
    class System systemBox;
    class Ops,AdminOps subBox;
    linkStyle default stroke:#475569,stroke-width:1.3px;
```

**Figure 3.2. Use Case Diagram**

---

## Figure 3.3: Project Development Timeline (Gantt Chart)

Figure 3.3 presents the five-month development timeline of the eTala system from June to October. It details the sequential execution of planning, database design, software development, system testing, cloud deployment, and final user evaluation.

| Tasks / SDLC Phases | June | July | August | September | October |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Planning** | June 1 – 30 | | | | |
| **Design** | June 15 – 30 | July 1 – 31 | | | |
| **Development** | | July 1 – 31 | Aug 1 – 31 | Sept 1 – 15 | |
| **Testing** | | | Aug 15 – 31 | Sept 1 – 30 | |
| **Deployment** | | | | Sept 15 – 30 | Oct 1 – 15 |
| **Evaluation** | | | | | Oct 1 – 31 |
| **Documentation** | Continuous | Continuous | Continuous | Continuous | Continuous |

**Figure 3.3. Project Development Timeline (Gantt Chart)**

---

## Figure 3.4: Database Entity-Relationship Diagram (ERD)

Figure 3.4 shows the database tables and relationships supporting the eTala system. The central engineering records table links to barangay locations, user accounts, permit and project details, uploaded documents, and system audit logs.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
erDiagram
    CUSTOM_USER ||--o{ ENGINEERING_RECORD : "creates"
    CUSTOM_USER ||--o{ AUDIT_LOG : "triggers"
    CUSTOM_USER ||--o{ DOCUMENT : "uploads"
    BARANGAY ||--o{ ENGINEERING_RECORD : "geolocates"
    ENGINEERING_RECORD ||--o| PERMIT_DETAIL : "contains"
    ENGINEERING_RECORD ||--o| PROJECT_DETAIL : "contains"
    ENGINEERING_RECORD ||--o{ DOCUMENT : "stores"

    CUSTOM_USER {
        int user_id PK
        string username
        string email
        string role
        string full_name
        string designation
    }

    BARANGAY {
        int barangay_id PK
        string psgc_code
        string barangay_name
        string district
        float latitude
        float longitude
    }

    ENGINEERING_RECORD {
        int record_id PK
        string record_type
        string title
        int year
        string status
        boolean is_illegal_construction
        float latitude
        float longitude
        int barangay_id FK
        int created_by FK
    }

    PERMIT_DETAIL {
        int permit_id PK
        int record_id FK
        string permit_type
        string building_type
        string permit_number
        string applicant_name
        date date_issued
    }

    PROJECT_DETAIL {
        int project_id PK
        int record_id FK
        string project_type
        string funding_source
        string contractor
        decimal project_cost
        string project_status
    }

    DOCUMENT {
        int document_id PK
        int record_id FK
        string document_type
        string file_name
        int file_size
        int uploaded_by FK
        datetime uploaded_at
    }

    AUDIT_LOG {
        int log_id PK
        int user_id FK
        string action
        int target_record_id
        string details
        datetime performed_at
    }
```

**Figure 3.4. Database Entity-Relationship Diagram (ERD)**

---

## Figure 3.5A: Login and Two-Factor Authentication Flow

Figure 3.5A illustrates the two-factor authentication security workflow for accessing the eTala system. Recognized office devices open the dashboard directly, while unrecognized devices require a one-time verification code sent via email before access is granted.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Start(["Start"]) --> A["Enter Username & Password"]
    A --> B{"Valid Account?"}
    B -- "No" --> C["Invalid Login Error"] --> A
    B -- "Yes" --> D{"Recognized Device?"}
    D -- "Yes" --> Dash(["Open Dashboard"])
    D -- "No" --> E["Send Email OTP"]
    E --> F["Enter OTP Code"]
    F --> G{"Valid Code?"}
    G -- "No" --> H["Invalid OTP Error"] --> F
    G -- "Yes" --> I["Save as Trusted Device"] --> Dash

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e,font-weight:bold;
    classDef otp fill:#faf5ff,stroke:#7c3aed,stroke-width:1.5px,color:#581c87,font-weight:600;
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20,font-weight:bold;
    classDef fail fill:#ffcdd2,stroke:#c62828,stroke-width:1.5px,color:#b71c1c,font-weight:bold;
    classDef startEnd fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;

    class Start startEnd;
    class Dash pass;
    class B,D,G decision;
    class E otp;
    class C,H fail;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.5A. Login and Two-Factor Authentication Flow**

---

## Figure 3.5B: Record Encoding Flow

Figure 3.5B illustrates the step-by-step process of encoding permit and infrastructure records in eTala. The user selects the record type, designates the barangay, and fills in required details to save the entry and automatically generate the document checklist.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Start(["Start"]) --> A["Choose Record Type"]
    A --> B1["Building Permit"]
    A --> B2["Municipal Project"]
    B1 & B2 --> C["Select Barangay"]
    C --> D["Fill Application Details"]
    D --> E{"All Fields Valid?"}
    E -- "No" --> F["Show Validation Warning"] --> D
    E -- "Yes" --> G["Save Record &<br/>Generate Checklist"] --> End(["Record Saved"])

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef permit fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0369a1,font-weight:bold;
    classDef project fill:#ccfbf1,stroke:#0d9488,stroke-width:1.5px,color:#115e59,font-weight:bold;
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e,font-weight:bold;
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20,font-weight:bold;
    classDef fail fill:#ffcdd2,stroke:#c62828,stroke-width:1.5px,color:#b71c1c,font-weight:bold;
    classDef startEnd fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;

    class Start startEnd;
    class B1 permit;
    class B2 project;
    class E decision;
    class End pass;
    class F fail;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.5B. Record Encoding Flow**

---

## Figure 3.5C: Document Upload Flow

Figure 3.5C illustrates the document attachment and cloud synchronization process in the eTala system. An authorized user selects a pending checklist item and uploads a validated PDF file to update the record's progress and cloud storage.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Start(["Start"]) --> A["Open Document Checklist"]
    A --> B["Select Pending Requirement"]
    B --> C["Choose PDF Document"]
    C --> D{"Valid PDF<br/>& Size?"}
    D -- "No" --> E["File Error (Not PDF / Too Large)"] --> C
    D -- "Yes" --> F["Upload to Cloud Storage"]
    F --> G["Mark Completed &<br/>Update Progress %"] --> End(["Document Attached"])

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e,font-weight:bold;
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20,font-weight:bold;
    classDef fail fill:#ffcdd2,stroke:#c62828,stroke-width:1.5px,color:#b71c1c,font-weight:bold;
    classDef startEnd fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;

    class Start startEnd;
    class D decision;
    class End pass;
    class E fail;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.5C. Document Upload Flow**

---

## Figure 3.5D: Trash and Recovery Flow

Figure 3.5D illustrates the soft-deletion, restoration, and automated archiving lifecycle in eTala. Deleted records are moved to a temporary trash repository where the Municipal Engineer can restore them to active status, delete them permanently, or let the system purge them after thirty days.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Start(["Start"]) --> A["Move Record to Trash"]
    A --> B{"Choose Action"}
    B -- "Restore" --> C["Restore to Active List"] --> EndActive(["Active Record Restored"])
    B -- "Manual Delete" --> D["Permanently Delete Now"]
    B -- "30 Days Inactive" --> E["Automated System Purge"]
    D & E --> EndDeleted(["Permanently Deleted"])

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e,font-weight:bold;
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20,font-weight:bold;
    classDef del fill:#ffcdd2,stroke:#c62828,stroke-width:1.5px,color:#b71c1c,font-weight:bold;
    classDef startEnd fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;

    class Start startEnd;
    class B decision;
    class EndActive pass;
    class EndDeleted,D,E del;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.5D. Trash and Recovery Flow**

---

## Figure 3.5E: Violation Tracking and Regularization Flow

Figure 3.5E illustrates the regulatory workflow for logging and resolving illegal construction incidents in the municipality. Personnel log violation reports with photos, which are converted into official building permits once the owner complies with documentary requirements.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Start(["Start"]) --> A["Log Illegal Construction"]
    A --> B{"Owner Complies?"}
    B -- "Yes" --> C["Submit Permit Application"]
    C --> D["Regularize into Official Permit"]
    D --> EndResolved(["Case Resolved"])
    B -- "No" --> EndOpen(["Case Unresolved"])

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef startEnd fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;
    classDef report fill:#fee2e2,stroke:#dc2626,stroke-width:1.5px,color:#991b1b,font-weight:bold;
    classDef process fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e,font-weight:bold;
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20,font-weight:bold;

    class Start startEnd;
    class A,EndOpen report;
    class B process;
    class C default;
    class D,EndResolved pass;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.5E. Violation Tracking and Regularization Flow**

---

## Figure 3.6A: Data Flow Diagram Level 0 (Context Diagram)

Figure 3.6A illustrates the Level 0 Data Flow Diagram showing the high-level data exchanges between office users and the eTala system. Engineering Staff submit application details and files to receive document checklists and map displays, while the Municipal Engineer interacts with all operational functions in addition to managing user accounts, summary reports, and audit logs.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Staff["Engineering Staff"]
    Core(["eTala System"])
    Admin["Municipal Engineer"]

    Staff -->|Application Details & Files| Core
    Core -->|Checklists & Map Displays| Staff

    Admin -->|User Accounts & Settings| Core
    Core -->|Summary Reports & Audit Logs| Admin

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef staffEntity fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1,font-weight:bold;
    classDef adminEntity fill:#0f2b5c,stroke:#091e42,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef process fill:#0f2b5c,stroke:#091e42,stroke-width:2px,color:#ffffff,font-weight:bold;

    class Staff staffEntity;
    class Admin adminEntity;
    class Core process;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.6A. Data Flow Diagram Level 0 (Context Diagram)**

---

## Figure 3.6B: Data Flow Diagram Level 1

Figure 3.6B illustrates the Level 1 Data Flow Diagram showing how information moves across the core processes of the eTala system. Engineering Staff encode application details into Record Management to store and retrieve records in the database, while GIS Mapping displays interactive map locations and Report Generation compiles accomplishment reports for the Municipal Engineer.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Arial, sans-serif', 'fontSize': '12px'}}}%%
flowchart LR
    Staff["Engineering Staff"]
    
    P1["Record Management"]
    P2["GIS Mapping"]
    P3["Report Generation"]
    
    DB[("Records Database")]
    Admin["Municipal Engineer"]

    Staff -->|Application Details| P1
    P1 <-->|Permit & Project Records| DB

    DB -->|Map Coordinates| P2
    P2 -->|Interactive Map View| Staff

    DB -->|Compiled Record Summaries| P3
    P3 -->|Accomplishment Reports| Admin

    classDef default fill:#f8fafc,stroke:#1e3a8a,stroke-width:1.5px,color:#0f172a,font-weight:600;
    classDef staff fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1,font-weight:bold;
    classDef admin fill:#0f2b5c,stroke:#091e42,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef proc fill:#0f2b5c,stroke:#091e42,stroke-width:1.5px,color:#ffffff,font-weight:bold;
    classDef db fill:#f0fdf4,stroke:#16a34a,stroke-width:1.8px,color:#14532d,font-weight:bold;

    class Staff staff;
    class Admin admin;
    class P1,P2,P3 proc;
    class DB db;
    linkStyle default stroke:#475569,stroke-width:1.5px;
```

**Figure 3.6B. Data Flow Diagram Level 1**
