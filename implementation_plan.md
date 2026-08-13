# Implementation Plan - eTala System Deep Scan & Enhancements

Deep code audit and system optimization for **eTala (Electronic Technical Administration & Licensing Application)** of the Municipal Engineering Office of Carigara, Leyte.

## User Review Required

> [!IMPORTANT]
> The system settings (`etala_project/settings.py`) have already been unified for environment security, dynamic host handling, and fallback file storage. Please review the proposed refinements below.

> [!NOTE]
> Core Dev-Stack skills (`python-pro`, `backend-architect`, `security-auditor`, `ux-ui-designer`, `sql-pro`, `database-optimizer`, `debugger`) are active in `.agents/skills/`.

## Open Questions

- Do you have specific production credentials for Supabase Storage (`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`) that you would like set in your `.env` file, or should it continue using the local FileSystem storage fallback during development?

## Proposed Changes

### Configuration & Settings (`etala_project/settings.py`)

#### [MODIFY] [settings.py](file:///c:/Users/Dion/Desktop/eTala/etala_project/settings.py)
- Consolidate environment loading and ensure secret key safety guards (`ImproperlyConfigured`).
- Ensure fallback email handling (Gmail SMTP -> Resend -> Console).
- Verify database connection parameters and timezone (`Asia/Manila`).

---

### Security & Input Validation (`permits/`)

#### [MODIFY] [models.py](file:///c:/Users/Dion/Desktop/eTala/permits/models.py)
- Add file extension and file size validator helper functions for document uploads.

#### [MODIFY] [views.py](file:///c:/Users/Dion/Desktop/eTala/permits/views.py)
- Ensure all POST handlers validate permissions and sanitize user input.

---

### Responsive UI Alignment (`permits/templates/permits/`)

#### [MODIFY] [etala.css](file:///c:/Users/Dion/Desktop/eTala/assets/css/etala.css)
- Confirm `.etala-page-header` aligns with the `.agents/AGENTS.md` responsive 3-breakpoint matrix (`≥768px` row vs `<768px` column).

## Verification Plan

### Automated Tests
- Run Django test suite: `python manage.py test`
- Run Django system check: `python manage.py check`

### Manual Verification
- Verify running server at `http://127.0.0.1:8000/` opens cleanly without errors.
- Test responsive page header behavior on desktop and mobile viewports.
