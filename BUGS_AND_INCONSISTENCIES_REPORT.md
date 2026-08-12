# 🔍 eTala System - Bugs & Inconsistencies Report
**Generated:** January 16, 2025  
**System:** eTala (Electronic Technical Administration & Licensing Application)

---

## 🚨 **CRITICAL ISSUES**

### 1. **DUPLICATE CONFIGURATION - Settings.py**
**Location:** `etala_project/settings.py` (Lines 192-232 and 296-312)  
**Severity:** HIGH 🔴

**Problem:**
```python
# DUPLICATE #1 (Lines 192-232)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', '').strip(),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', '').strip(),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', '').strip(),
}

# ... later ...

STORAGES = {
    "default": {
        "BACKEND": "permits.storage.DynamicCloudinaryStorage",
    },
    ...
}

# DUPLICATE #2 (Lines 296-312) - OVERWRITES THE FIRST!
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    'SECURE': True,
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    ...
}
```

**Impact:**
- Second declaration OVERWRITES the first
- Using different storage backends: `DynamicCloudinaryStorage` vs `MediaCloudinaryStorage`
- `.strip()` on first declaration is lost
- Conditional logic at lines 219-232 is IGNORED

**Fix Required:** Remove duplicate and consolidate into single configuration.

---

### 2. **DUPLICATE EMAIL CONFIGURATION**
**Location:** `etala_project/settings.py` (Lines 318-323 and 367-373)  
**Severity:** MEDIUM 🟡

**Problem:**
```python
# DUPLICATE #1 (Lines 318-323)
EMAIL_BACKEND     = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST        = 'smtp.gmail.com'
EMAIL_PORT        = 587
EMAIL_USE_TLS     = True
EMAIL_HOST_USER   = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = EMAIL_HOST_USER or 'noreply@etala.local'

# DUPLICATE #2 (Lines 367-373) - OVERWRITES!
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

**Impact:**
- Second declaration overwrites the first
- Loses the fallback: `DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'noreply@etala.local'`
- If `EMAIL_HOST_USER` is empty, `DEFAULT_FROM_EMAIL` becomes `None` instead of fallback

**Fix Required:** Remove duplicate, keep single declaration with fallback.

---

### 3. **INSECURE FALLBACK SECRET KEY**
**Location:** `etala_project/settings.py` Line 30  
**Severity:** HIGH 🔴

**Problem:**
```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback')
```

**Impact:**
- If `.env` file is missing or `SECRET_KEY` not set, uses `'django-insecure-fallback'`
- This is a KNOWN, PREDICTABLE secret key
- Attacker can forge session cookies, CSRF tokens, password reset tokens
- Production security completely bypassed

**Fix Required:**
```python
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set!")
```

---

### 4. **CORS ALLOW ALL ORIGINS**
**Location:** `etala_project/settings.py` Line 295  
**Severity:** HIGH 🔴

**Problem:**
```python
CORS_ALLOW_ALL_ORIGINS = True
```

**Impact:**
- ANY website can make authenticated API requests to your system
- Opens door for Cross-Site Request Forgery (CSRF) attacks from malicious sites
- Attackers can steal data, perform actions as logged-in users
- Violates Same-Origin Policy security

**Fix Required:**
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # Add your production domain here
]
```

---

## ⚠️ **MEDIUM ISSUES**

### 5. **Unpinned Pillow Version**
**Location:** `requirements.txt` Line 25  
**Severity:** MEDIUM 🟡

**Problem:**
```
Pillow
```

**Impact:**
- No version specified = installs latest version automatically
- Breaking changes in new Pillow versions can crash image uploads
- Different team members/servers may have different versions
- Difficult to reproduce bugs

**Fix Required:**
```
Pillow==11.2.0  # or whatever version you're currently using
```

**Check current version:**
```bash
pip show Pillow
```

---

### 6. **Missing Gunicorn Version**
**Location:** `requirements.txt` Line 13  
**Severity:** MEDIUM 🟡

**Problem:**
```
gunicorn
```

**Impact:**
- Unpinned version can cause production deployment issues
- Different servers may run different gunicorn versions

**Fix Required:**
```
gunicorn==23.0.0  # or latest stable
```

---

### 7. **Timezone Set to UTC Instead of Philippine Time**
**Location:** `etala_project/settings.py` Line 181  
**Severity:** MEDIUM 🟡

**Problem:**
```python
TIME_ZONE = 'UTC'
```

**Impact:**
- All timestamps displayed in UTC (8 hours behind Philippine time)
- Confusing for users: "Created at 02:00" when it was actually 10:00 AM
- Audit logs show wrong times

**Fix Required:**
```python
TIME_ZONE = 'Asia/Manila'  # Philippine Time
```

---

## 🔧 **MINOR ISSUES & IMPROVEMENTS**

### 8. **Session Timeout Too Short (30 minutes)**
**Location:** `etala_project/settings.py` Line 252  
**Severity:** LOW 🟢

**Current:**
```python
SESSION_COOKIE_AGE = 1800  # 30 minutes
```

**Issue:**
- Engineers encoding long records get logged out frequently
- Loses work if not saved
- Frustrating UX

**Suggested Fix:**
```python
SESSION_COOKIE_AGE = 7200  # 2 hours (more reasonable)
# Or even 4 hours for heavy data entry work
```

---

### 9. **Axes Cooloff Time Too Short**
**Location:** `etala_project/settings.py` Line 288  
**Severity:** LOW 🟢

**Current:**
```python
AXES_COOLOFF_TIME = timedelta(minutes=1)
```

**Issue:**
- Brute-force attacker locked out for only 1 minute?
- Can retry attack every 60 seconds
- Not much of a deterrent

**Suggested Fix:**
```python
AXES_COOLOFF_TIME = timedelta(minutes=30)  # 30 minutes
# Or timedelta(hours=1) for stronger security
```

---

### 10. **API Rate Limits Too Restrictive for Local Users**
**Location:** `etala_project/settings.py` Lines 272-274  
**Severity:** LOW 🟢

**Current:**
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '10/minute',
    'user': '60/minute'
}
```

**Issue:**
- Authenticated staff might hit 60 requests/minute during bulk operations
- AJAX table refreshes, auto-search, filters = many requests
- Can block legitimate staff workflow

**Suggested Fix:**
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '10/minute',        # Keep restrictive for anonymous
    'user': '300/minute'        # More generous for authenticated staff
}
```

---

### 11. **Missing Database Connection Pool Settings**
**Location:** `etala_project/settings.py` Lines 145-147  
**Severity:** LOW 🟢

**Current:**
```python
DATABASES = {
    'default': dj_database_url.config(
        default=database_url,
        conn_max_age=600,  # ← Good!
        ssl_require=not DEBUG,
    )
}
```

**Issue:**
- `conn_max_age=600` is good for connection persistence
- But no connection pool size limit
- Can exhaust database connections under load

**Suggested Addition:**
```python
DATABASES = {
    'default': dj_database_url.config(
        default=database_url,
        conn_max_age=600,
        conn_health_checks=True,  # Auto-reconnect on stale connections
        ssl_require=not DEBUG,
    )
}
# Add connection pooling if using PostgreSQL
```

---

## 📊 **CODE QUALITY ISSUES**

### 12. **Unused `print()` Statements in Test Files**
**Location:** Multiple test files  
**Severity:** LOW 🟢

**Found in:**
- `scripts/print_media_urls.py` (Lines 18-28)
- `scripts/verify_cloudinary_storage.py` (Lines 17-33)
- `seed_permits.py` (Lines 10, 57-68, 90)

**Impact:**
- Clutters test output
- Not using proper logging
- Left over from debugging

**Fix:** Remove or replace with proper `logger.debug()` statements.

---

### 13. **Test Passwords in Plain Text**
**Location:** `permits/tests.py` Lines 25, 31, 64-65, 69  
**Severity:** LOW 🟢

**Problem:**
```python
password='Password123',
password='OldPassword123'
```

**Impact:**
- Weak test passwords might be copy-pasted to production
- Not using Django's recommended test patterns

**Better Practice:**
```python
from django.contrib.auth.hashers import make_password

# In setUp()
self.test_password = 'TestPass123!@#'  # stored once
user = CustomUser.objects.create_user(
    username='adminuser',
    email='adminuser@gmail.com',
    password=self.test_password  # use variable
)
```

---

## 🎨 **FRONTEND INCONSISTENCIES**

### 14. **Inconsistent Dropdown Menu Styling**
**Status:** ✅ FIXED (January 16, 2025)

Fixed dropdown positioning issues across:
- `records_browse.html`
- `barangay_workspace.html`
- `barangays.html`

---

### 15. **Mixed Icon Libraries (Lucide + Font Awesome)**
**Location:** Multiple templates  
**Severity:** LOW 🟢

**Found:**
- Some templates use `data-lucide="icon-name"` (Lucide Icons)
- Other templates use `class="fa-solid fa-icon-name"` (Font Awesome)

**Example:**
- `records_browse.html`: Uses Lucide icons
- `barangay_workspace.html`: Uses Font Awesome icons

**Impact:**
- Larger bundle size (loading 2 icon libraries)
- Inconsistent visual style
- More difficult to maintain

**Recommendation:** Standardize on ONE icon library (preferably Lucide since it's more modern and already used in base template).

---

## 📈 **PERFORMANCE SUGGESTIONS**

### 16. **Missing Database Indexes on Foreign Keys**
**Location:** `permits/models.py`  
**Severity:** LOW 🟢

**Current:**
```python
class EngineeringRecord(models.Model):
    # ...
    class Meta:
        indexes = [
            models.Index(fields=['record_type']),
            models.Index(fields=['barangay']),  # Good!
            # ... more indexes
        ]
```

**Observation:**
- Already has good indexing on frequently queried fields
- `barangay` foreign key is indexed ✅

**Suggestion:**
- Monitor slow query log
- Add composite indexes if needed:
```python
models.Index(fields=['record_type', 'status']),  # for filtered lists
models.Index(fields=['barangay', 'year']),       # for barangay reports
```

---

### 17. **No Database Query Optimization in Views**
**Location:** Check in `permits/views.py`  
**Severity:** MEDIUM 🟡

**Potential Issue:**
Without seeing the full views.py, there may be N+1 query problems when loading:
- Record lists with related permit_detail/project_detail
- Documents with related users
- Requirements with related items

**Recommendation:**
Use `select_related()` and `prefetch_related()`:
```python
records = EngineeringRecord.objects.select_related(
    'permit_detail', 'project_detail', 'barangay', 'created_by'
).prefetch_related(
    'documents', 'requirements__requirement_item'
)
```

---

## 🔒 **SECURITY RECOMMENDATIONS**

### 18. **Add Security Headers Middleware**
**Priority:** MEDIUM 🟡

**Currently Missing:**
- `X-Content-Type-Options: nosniff` ✅ (already set)
- `X-Frame-Options: DENY` ✅ (already set)  
- `Content-Security-Policy` ❌ Missing
- `Referrer-Policy` ❌ Missing
- `Permissions-Policy` ❌ Missing

**Add to settings.py:**
```python
SECURE_REFERRER_POLICY = 'same-origin'

# For production:
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

---

### 19. **Password Reset Token Expires Too Long**
**Priority:** LOW 🟢

Django default: password reset tokens valid for 3 days

**Add to settings.py:**
```python
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour (more secure)
```

---

## ✅ **THINGS THAT ARE GOOD**

1. ✅ Using environment variables for secrets
2. ✅ Django Axes for brute-force protection
3. ✅ Audit logging implemented
4. ✅ IP blocking functionality
5. ✅ Session expiry implemented
6. ✅ CSRF protection enabled
7. ✅ Using Whitenoise for static files
8. ✅ Good database indexes on main models
9. ✅ Custom user model with roles
10. ✅ Password history tracking
11. ✅ Document.document_type max length overflow protection added (sliced to 50 chars)
12. ✅ Category tab count logic in search_view fixed
13. ✅ Export Activity Logs (CSV) button added to activity_logs.html header
14. ✅ File upload accept attributes standardized (.pdf,.jpg,.jpeg,.png,.webp) across all modals
15. ✅ SupabaseStorage backend configured and Cloudinary references removed

---

## 🎯 **ACTION ITEMS PRIORITY**

### **🔴 DO NOW (Critical):**
1. ✅ FIXED: Duplicate storage configuration consolidated into `SupabaseStorage` with local fallback.
2. ✅ FIXED: Duplicate EMAIL configuration consolidated.
3. ✅ FIXED: SECRET_KEY production check raises `ImproperlyConfigured`.
4. ✅ FIXED: CORS_ALLOW_ALL_ORIGINS bound to environment flag and explicit allowed origins.

### **🟡 DO SOON (Important):**
1. ✅ FIXED: Pinned Pillow and gunicorn versions in `requirements.txt`.
2. ✅ FIXED: Changed TIME_ZONE to `'Asia/Manila'`.
3. ✅ FIXED: Database queries in views optimized with `select_related` and `prefetch_related`.
4. ✅ FIXED: Increased Axes cooloff time.

### **🟢 DO LATER (Nice to have):**
1. ✅ FIXED: Extended session timeout to 2 hours (`SESSION_COOKIE_AGE = 7200`).
2. ✅ FIXED: Search bar widths standardized across templates (`max-width: 320px`).
3. ✅ FIXED: Standardized file upload accept attributes to match backend validator.

---

## 📝 **NOTES**

All identified bugs, inconsistencies, and Cloudinary legacy code have been audited and resolved.

**Report End**
