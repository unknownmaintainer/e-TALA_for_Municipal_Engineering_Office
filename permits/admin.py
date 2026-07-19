from django.contrib import admin
from .models import (
    CustomUser, PasswordHistory, Barangay, Category,
    EngineeringRecord, PermitDetail, ProjectDetail,
    Document, Record, AuditLog, LoginAttempt
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'full_name', 'email')


@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = ('barangay_id', 'barangay_name', 'district', 'created_at')
    search_fields = ('barangay_name', 'district')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name')


class PermitDetailInline(admin.StackedInline):
    model = PermitDetail
    extra = 0


class ProjectDetailInline(admin.StackedInline):
    model = ProjectDetail
    extra = 0


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ('uploaded_at',)


@admin.register(EngineeringRecord)
class EngineeringRecordAdmin(admin.ModelAdmin):
    list_display = ('record_id', 'record_type', 'title', 'barangay', 'status', 'created_by', 'created_at')
    list_filter = ('record_type', 'status', 'barangay')
    search_fields = ('title', 'description')
    inlines = [PermitDetailInline, ProjectDetailInline, DocumentInline]


@admin.register(PermitDetail)
class PermitDetailAdmin(admin.ModelAdmin):
    list_display = ('engineering_record', 'permit_type', 'building_type', 'permit_number', 'applicant_name')
    list_filter = ('permit_type', 'building_type')
    search_fields = ('permit_number', 'applicant_name')


@admin.register(ProjectDetail)
class ProjectDetailAdmin(admin.ModelAdmin):
    list_display = ('engineering_record', 'project_type', 'funding_source', 'contractor', 'project_cost', 'project_status')
    list_filter = ('project_type', 'project_status')
    search_fields = ('contractor', 'funding_source')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('document_id', 'engineering_record', 'document_type', 'file_name', 'version', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('file_name',)


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('record_id', 'project_name', 'category', 'barangay', 'year', 'status')
    list_filter = ('status', 'category')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'user', 'action', 'target_record_id', 'ip_address', 'performed_at')
    list_filter = ('user',)
    search_fields = ('action',)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('email_attempted', 'success', 'ip_address', 'timestamp')
    list_filter = ('success',)
