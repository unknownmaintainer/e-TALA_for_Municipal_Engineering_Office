from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('staff', 'Engineering Staff'),
        ('engineer', 'Municipal Engineer'),
        ('admin', 'Administrator'),
    )
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True, null=True
    )
    session_key = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)


class PasswordHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='password_histories')
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


# ─── BARANGAY ────────────────────────────────────────────────────────────────

class Barangay(models.Model):
    barangay_id = models.AutoField(primary_key=True)
    barangay_name = models.CharField(max_length=100, unique=True)
    district = models.CharField(max_length=50, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True, help_text='Geocoded center latitude for Carigara barangay map pin')
    longitude = models.FloatField(null=True, blank=True, help_text='Geocoded center longitude for Carigara barangay map pin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['barangay_name']

    def __str__(self):
        return self.barangay_name


# ─── LEGACY: Keep Category for backward compat during migration ─────────────

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['category_name']

    def __str__(self):
        return self.category_name


# ─── ENGINEERING RECORD (CENTRAL TABLE) ──────────────────────────────────────

class EngineeringRecord(models.Model):
    RECORD_TYPE_CHOICES = (
        ('Permit', 'Permit'),
        ('Project', 'Project'),
    )
    PROJECT_SCOPE_CHOICES = (
        ('Municipal', 'Municipal'),
        ('Barangay', 'Barangay'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    )

    record_id = models.AutoField(primary_key=True)
    record_type = models.CharField(max_length=10, choices=RECORD_TYPE_CHOICES)
    project_scope = models.CharField(
        max_length=20, choices=PROJECT_SCOPE_CHOICES, blank=True, default='',
        help_text='Municipal or Barangay — only applies to Project records.'
    )
    barangay = models.ForeignKey(Barangay, on_delete=models.PROTECT, related_name='engineering_records')
    title = models.CharField(max_length=255)
    year = models.PositiveIntegerField(null=True, blank=True, help_text='Year of the record / permit.')
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    date_started = models.DateField(null=True, blank=True)
    date_completed = models.DateField(null=True, blank=True)
    ILLEGAL_COMPLIANCE_CHOICES = (
        ('unresolved', 'Open / Unresolved'),
        ('pending_permit', 'Permit Application Filed'),
        ('resolved', 'Regularized / Complied'),
    )

    is_illegal_construction = models.BooleanField(
        default=False,
        help_text='Flagged as illegal construction (constructed without building permit).'
    )
    illegal_compliance_status = models.CharField(
        max_length=20,
        choices=ILLEGAL_COMPLIANCE_CHOICES,
        default='unresolved',
        blank=True,
        help_text='Compliance / regularization tracking for illegal construction.'
    )
    latitude = models.FloatField(null=True, blank=True, help_text='Geocoded latitude coordinate for map & Street View')
    longitude = models.FloatField(null=True, blank=True, help_text='Geocoded longitude coordinate for map & Street View')
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='engineering_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['record_type']),
            models.Index(fields=['project_scope']),
            models.Index(fields=['barangay']),
            models.Index(fields=['status']),
            models.Index(fields=['year']),
            models.Index(fields=['title']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.record_type}] {self.title}"

    @property
    def specific_type_label(self):
        """Returns a human-readable specific type, e.g., 'Fencing Permit' or 'Road & Bridge Project'."""
        if self.record_type == 'Permit':
            if hasattr(self, 'permit_detail') and self.permit_detail.permit_type:
                return f"{self.permit_detail.get_permit_type_display()} Permit"
            return "Permit"
        else: # Project
            if hasattr(self, 'project_detail') and self.project_detail.project_type:
                return f"{self.project_detail.get_project_type_display()} Project"
            return f"{self.get_project_scope_display()} Project"

    @property
    def illegal_status_info(self):
        """Returns dict with status label, color, and badge class for UI rendering."""
        if not self.is_illegal_construction:
            return None
        st = self.illegal_compliance_status or 'unresolved'
        if st == 'unresolved':
            return {
                'status': 'unresolved',
                'label': 'Illegal Construction — Unresolved',
                'short_label': 'Illegal Construction',
                'badge_class': 'bg-danger text-white',
                'bg_style': 'background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5;',
                'color': '#b91c1c'
            }
        elif st == 'pending_permit':
            return {
                'status': 'pending_permit',
                'label': 'Illegal Construction — Permit Filed',
                'short_label': 'Permit Filed',
                'badge_class': 'bg-warning text-dark',
                'bg_style': 'background:#fef3c7; color:#b45309; border:1px solid #fcd34d;',
                'color': '#b45309'
            }
        elif st == 'resolved':
            return {
                'status': 'resolved',
                'label': 'Regularized',
                'short_label': 'Regularized',
                'badge_class': 'bg-success text-white',
                'bg_style': 'background:#dcfce7; color:#15803d; border:1px solid #86efac;',
                'color': '#15803d'
            }
        return {
            'status': st,
            'label': 'Illegal Construction',
            'short_label': 'Illegal Construction',
            'badge_class': 'bg-secondary text-white',
            'bg_style': 'background:#f1f5f9; color:#475569; border:1px solid #cbd5e1;',
            'color': '#475569'
        }

    @property
    def active_lat(self):
        if self.latitude:
            return self.latitude
        if self.barangay and self.barangay.latitude:
            return self.barangay.latitude
        return 11.3021  # Carigara LGU Center Latitude

    @property
    def active_lng(self):
        if self.longitude:
            return self.longitude
        if self.barangay and self.barangay.longitude:
            return self.barangay.longitude
        return 124.6897  # Carigara LGU Center Longitude

    @property
    def discovery_photo(self):
        """Returns the discovery photo document if available."""
        doc = self.documents.filter(document_type='Picture').order_by('uploaded_at').first()
        if not doc:
            doc = self.documents.order_by('uploaded_at').first()
        return doc

    @property
    def completion_stats(self):
        """Returns dict with total, fulfilled, pct, and missing item names."""
        reqs = self.requirements.select_related('requirement_item', 'document')
        total = reqs.count()
        
        from django.utils import timezone
        today = timezone.now().date()
        
        fulfilled = 0
        missing = []
        for r in reqs:
            is_ok = (r.is_fulfilled and r.document is not None) or r.is_waived
            if is_ok and r.document and r.document.expiry_date:
                if r.document.expiry_date < today:
                    is_ok = False
            
            if is_ok:
                fulfilled += 1
            else:
                missing.append(r.requirement_item.name)
                
        pct = int((fulfilled / total) * 100) if total > 0 else 0
        return {
            'total': total,
            'fulfilled': fulfilled,
            'pct': pct,
            'missing': missing,
            'is_complete': total > 0 and fulfilled == total,
        }


# ─── PERMIT DETAILS ──────────────────────────────────────────────────────────

class PermitDetail(models.Model):
    PERMIT_TYPE_CHOICES = (
        ('Building', 'Building'),
        ('Electrical', 'Electrical'),
        ('Occupancy', 'Occupancy'),
        ('Fencing', 'Fencing'),
        ('Demolition', 'Demolition'),
        ('Renovation', 'Renovation'),
    )
    BUILDING_TYPE_CHOICES = (
        ('Residential', 'Residential'),
        ('Commercial', 'Commercial'),
        ('Industrial', 'Industrial'),
        ('Institutional', 'Institutional'),
        ('Agricultural', 'Agricultural'),
    )

    engineering_record = models.OneToOneField(
        EngineeringRecord, on_delete=models.CASCADE, related_name='permit_detail'
    )
    permit_type = models.CharField(max_length=30, choices=PERMIT_TYPE_CHOICES)
    building_type = models.CharField(max_length=30, choices=BUILDING_TYPE_CHOICES, blank=True, default='')
    permit_number = models.CharField(max_length=100, blank=True, default='')
    date_issued = models.DateField(null=True, blank=True, help_text='Date Building/Ancillary Permit was issued.')
    applicant_name = models.CharField(max_length=255, blank=True, default='')
    resolution_required = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.permit_type} Permit — {self.applicant_name or 'N/A'}"


# ─── PROJECT DETAILS ─────────────────────────────────────────────────────────

class ProjectDetail(models.Model):
    PROJECT_TYPE_CHOICES = (
        ('Road & Bridge', 'Road & Bridge'),
        ('Vertical Structure', 'Vertical Structure'),
        ('Flood Control', 'Flood Control'),
        ('Potable Water', 'Potable Water'),
    )
    PROJECT_STATUS_CHOICES = (
        ('Planning', 'Planning'),
        ('Procurement', 'Procurement'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Suspended', 'Suspended'),
    )

    engineering_record = models.OneToOneField(
        EngineeringRecord, on_delete=models.CASCADE, related_name='project_detail'
    )
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPE_CHOICES)
    funding_source = models.CharField(max_length=255, blank=True, default='')
    contractor = models.CharField(max_length=255, blank=True, default='')
    project_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    project_status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='Planning')

    def __str__(self):
        return f"{self.project_type} — {self.engineering_record.title}"


# ─── DOCUMENTS (UNIFIED) ─────────────────────────────────────────────────────

class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ('Permit Form', 'Permit Form'),
        ('Resolution', 'Resolution'),
        ('Inspection Report', 'Inspection Report'),
        ('Blueprint', 'Blueprint'),
        ('Picture', 'Picture'),
        ('Completion Report', 'Completion Report'),
        ('Acceptance Report', 'Acceptance Report'),
        ('Certificate', 'Certificate'),
        ('Program of Works', 'Program of Works'),
        ('Other', 'Other'),
    )

    document_id = models.AutoField(primary_key=True)
    engineering_record = models.ForeignKey(
        EngineeringRecord, on_delete=models.CASCADE, related_name='documents'
    )
    # Links this file to the specific checklist slot it fulfills (nullable for legacy docs)
    requirement_item = models.ForeignKey(
        'RequirementItem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documents'
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES, default='Other')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_size = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document_type} — {self.file_name}"


# ─── REQUIREMENT TEMPLATES ───────────────────────────────────────────────────

class RequirementTemplate(models.Model):
    """Defines the document checklist for a given record type/subtype/scope."""
    RECORD_TYPE_CHOICES = (
        ('Permit', 'Permit'),
        ('Project', 'Project'),
    )
    SCOPE_CHOICES = (
        ('', 'N/A (Permit)'),
        ('Municipal', 'Municipal'),
        ('Barangay', 'Barangay'),
    )

    template_id = models.AutoField(primary_key=True)
    record_type = models.CharField(max_length=10, choices=RECORD_TYPE_CHOICES)
    subtype = models.CharField(
        max_length=50,
        help_text='E.g. "Building", "Road & Bridge", "Flood Control"'
    )
    scope = models.CharField(
        max_length=20, choices=SCOPE_CHOICES, blank=True, default='',
        help_text='Municipal or Barangay for projects; blank for permits.'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('record_type', 'subtype', 'scope')
        ordering = ['record_type', 'subtype']

    def __str__(self):
        scope_label = f" ({self.scope})" if self.scope else ''
        return f"{self.record_type} — {self.subtype}{scope_label}"

    @property
    def active_items(self):
        return self.items.filter(is_active=True).order_by('order', 'name')


class RequirementItem(models.Model):
    """A single document required by a RequirementTemplate."""
    item_id = models.AutoField(primary_key=True)
    template = models.ForeignKey(
        RequirementTemplate, on_delete=models.CASCADE, related_name='items'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.template} › {self.name}"


class RecordRequirement(models.Model):
    """Tracks which checklist items have been fulfilled for a specific record."""
    req_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(
        EngineeringRecord, on_delete=models.CASCADE, related_name='requirements'
    )
    requirement_item = models.ForeignKey(
        RequirementItem, on_delete=models.PROTECT, related_name='record_requirements'
    )
    document = models.OneToOneField(
        Document, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='record_requirement'
    )
    is_fulfilled = models.BooleanField(default=False)
    is_waived = models.BooleanField(default=False)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fulfilled_requirements'
    )

    class Meta:
        unique_together = ('record', 'requirement_item')
        ordering = ['requirement_item__order', 'requirement_item__name']

    def __str__(self):
        status = '✓' if self.is_fulfilled else '☐'
        return f"{status} {self.record.title} › {self.requirement_item.name}"


# ─── LEGACY Record model (kept for migration) ────────────────────────────────

class Record(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('archived', 'Archived'),
    )
    LOCATION_CHOICES = (
        ('barangay', 'Barangay'),
        ('municipal', 'Municipal'),
    )
    record_id = models.AutoField(primary_key=True)
    record_title = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='records')
    location_type = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='barangay')
    barangay = models.ForeignKey(Barangay, on_delete=models.PROTECT, related_name='records', null=True, blank=True)
    year = models.PositiveIntegerField()
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2)
    archive_number = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='created_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project_name} ({self.year})"


# ─── AUDIT LOG ────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.TextField()
    target_record_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"[{self.performed_at:%Y-%m-%d %H:%M}] {self.user.username if self.user else 'System'}: {self.action}"


class LoginAttempt(models.Model):
    email_attempted = models.EmailField(max_length=254)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.email_attempted} - {status} at {self.timestamp}"


class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='blocked_ips')
    blocked_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-blocked_at']

    def __str__(self):
        return f"{self.ip_address} (Blocked)"
