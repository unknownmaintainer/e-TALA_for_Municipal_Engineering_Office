# e-TALA_for_Municipal_Engineering_Office

# Engineering Records Archiving & Retrieval Management System (ERARMS)

ERARMS is a comprehensive, Django-based records management system designed for the Municipal Engineering Office. It serves as a central repository for digitizing, tracking, and managing building permits, municipal and barangay projects, and all associated documentation.

The system is built with a clean, accessible, and government-standard design philosophy, ensuring ease of use for all staff members while maintaining robust functionality.

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Data Models](#data-models)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Running the Development Server](#running-the-development-server)
  - [Useful Management Commands](#useful-management-commands)
- [Deployment](#deployment)
- [License](#license)

## Key Features

### Core Functionality
- **Role-Based Access Control (RBAC)**: Pre-defined roles for `Administrator`, `Municipal Engineer`, and `Engineering Staff` with distinct permissions.
- **Dynamic Checklist Management**: Requirement checklists are dynamically generated based on the record type (Permit, Municipal Project, Barangay Project) and subtype (e.g., Building Permit, Road & Bridge Project).
- **Document Management**: Secure document uploads with validation, Cloudinary for cloud storage, and version history. Includes batch uploading capabilities.
- **Record Lifecycle Tracking**: Status tracking for records, from creation and submission to review, revision, and completion.
- **Audit & Activity Logs**: Comprehensive logging of user actions for transparency and accountability. Logs can be exported to CSV.
- **Search & Filtering**: Advanced search and filtering capabilities across all records, projects, and permits.

### UI/UX Enhancements
- **Dashboard Analytics**: A central dashboard featuring KPI widgets, including a donut chart for digitization compliance statistics.
- **Document Expiry Tracking**: The system tracks document expiry dates and displays prominent warning badges for expiring or expired documents.
- **Interactive Maps**: A heatmap toggle on the barangay map provides a visual density overlay of projects.
- **Responsive Design**: The UI is fully responsive, adapting from desktop to tablet and mobile layouts, ensuring accessibility on any device.
- **Modern Interface**: A clean and intuitive interface built with a professional color palette and clear typography, conforming to the provided UI/UX design specifications.

### Technical Features
- **REST API**: Provides RESTful endpoints for `Records`, `Barangays`, and `Categories` with JWT-based authentication for extensibility.
- **Secure Authentication**: Features include login attempt tracking and password history to enhance security.
- **Cloud Integration**: Leverages Cloudinary for scalable and reliable media file storage.
- **Static Asset Handling**: Uses WhiteNoise to efficiently serve static files in production.

## System Architecture

The application is built on a modern Python and Django stack.

- **Backend**: Django 6, Django REST Framework
- **Frontend**: Django Templates, Chart.js, and custom CSS (moving towards Tailwind CSS).
- **Database**: SQLite for local development, with seamless support for PostgreSQL in production via `dj-database-url`.
- **Media Storage**: Cloudinary is used for all user-uploaded files (documents, profile pictures).
- **Static Files**: Served by WhiteNoise in production environments.
- **Deployment**: Configured for Render via `render.yaml`, but adaptable to other platforms.

## Data Models

The core of the system is its relational data structure. The main models are:

- **`CustomUser`**: Extends the default Django User model to include roles (`staff`, `engineer`, `admin`), a full name, and profile picture.
- **`Record`**: The central model representing a project or permit. It links to a `Category`, `Barangay`, and the user who created it. It tracks key metadata like project name, year, budget, and status.
- **`Document`**: Represents an uploaded file. It is linked to a `Record` and stores file metadata, including the uploader, file size, and an optional `expiry_date`.
- **`RequirementTemplate`**: Defines a checklist for a specific `record_type` (e.g., 'Permit'), `subtype` (e.g., 'Building'), and `scope` ('Municipal' or 'Barangay').
- **`RequirementItem`**: An individual item within a `RequirementTemplate`, such as "Architectural Plans". This model is used to dynamically generate checklists for each record.
- **`Barangay` & `Category`**: Simple models for organizing records by location and type (e.g., 'Road & Bridge', 'Vertical Structure').
- **`AuditLog`**: Logs significant actions performed by users, such as creating, updating, or deleting records.
- **`LoginAttempt` & `PasswordHistory`**: Security-focused models to track login activity and prevent password reuse.

## Getting Started

Follow these instructions to get the project running on your local machine for development and testing.

### Prerequisites

- Python 3.12+
- A virtual environment tool (`venv` is recommended)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the project root and add the following for local development. For production, these should be set in your hosting environment.
    ```env
    SECRET_KEY='your-strong-secret-key'
    DEBUG=True
    DATABASE_URL='sqlite:///db.sqlite3'
    ALLOWED_HOSTS='127.0.0.1,localhost'
    
    # Optional for local dev if you want to use Cloudinary
    CLOUDINARY_CLOUD_NAME=''
    CLOUDINARY_API_KEY=''
    CLOUDINARY_API_SECRET=''
    ```

5.  **Run database migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Seed the database with initial data:**
    This command populates the database with the necessary requirement checklists for all record types. It is safe to run multiple times.
    ```bash
    python manage.py seed_requirement_templates
    ```

7.  **Create a superuser account:**
    This account will have administrator privileges.
    ```bash
    python manage.py createsuperuser
    ```

## Usage

### Running the Development Server

Once the setup is complete, you can run the local development server:

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Useful Commands

```bash
python manage.py check
python manage.py test
python manage.py collectstatic --no-input
```

## Deployment Notes

Render deployment is configured in `render.yaml`. Production requires these environment variables:

- `SECRET_KEY`
- `DEBUG=False`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Keep `.env`, `db.sqlite3`, `media/`, `staticfiles/`, and `logs/` out of source control.
