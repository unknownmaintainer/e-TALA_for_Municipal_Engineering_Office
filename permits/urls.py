from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views, api_views

router = DefaultRouter()
router.register(r'records', api_views.RecordViewSet, basename='api_record')
router.register(r'barangays', api_views.BarangayViewSet, basename='api_barangay')
router.register(r'categories', api_views.CategoryViewSet, basename='api_category')

urlpatterns = [
    # Public / Auth
    path('', views.landing_view, name='landing'),
    path('landing/', views.landing_view, name='landing_page'),
    path('health/', views.health_check_view, name='health_check'),
    path('ping/', views.health_check_view, name='ping_check'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('auth/verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('auth/resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('auth/access-restricted/', views.access_restricted_view, name='access_restricted'),
    path('auth/email-preview/new-device-alert/', views.email_preview_new_device_view, name='preview_email_new_device_alert'),
    path('auth/email-preview/password-reset/', views.email_preview_password_reset_view, name='preview_email_password_reset'),
    path('auth/email-preview/otp-verification/', views.email_preview_otp_verification_view, name='preview_email_otp_verification'),
    path('auth/email-preview/device-approval/', views.email_preview_device_approval_view, name='preview_email_device_approval'),
    path('auth/email-preview/developer-feedback/', views.email_preview_feedback_view, name='preview_email_developer_feedback'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('password-reset/', views.forgot_password_view, name='password_reset_alias'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('preview-toasts/', views.toast_preview_view, name='preview_toasts'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Barangays
    path('barangays/', views.barangays_view, name='barangays'),
    path('barangays/<int:barangay_id>/', views.barangay_workspace_view, name='barangay_workspace'),
    path('barangays/<int:barangay_id>/download-zip/', views.download_barangay_zip_view, name='download_barangay_zip'),


    # Engineering Records — Create Wizard (3 steps)
    path('records/new/', views.record_create_step1_view, name='create_step1'),
    path('records/new/type/', views.record_create_step2_view, name='create_step2'),
    path('records/new/form/', views.record_create_step3_view, name='create_step3'),

    # Engineering Records — Module Lists
    path('municipal/', views.municipal_projects_view, name='municipal_projects'),
    path('barangay/', views.barangay_projects_view, name='barangay_projects'),
    path('permits/', views.permit_records_view, name='permit_records'),
    path('illegal-constructions/', views.illegal_constructions_view, name='illegal_constructions'),

    # Engineering Records — CRUD
    path('records/', views.records_browse_view, name='records_browse'),
    path('records/create/', views.record_create_view, name='create_record'),
    path('records/flag-illegal/', views.flag_illegal_construction_view, name='flag_illegal_construction'),
    path('records/<int:record_id>/', views.record_detail_view, name='record_detail'),
    path('records/<int:record_id>/edit/', views.record_edit_view, name='edit_record'),
    path('records/<int:record_id>/illegal-status/', views.update_illegal_status_view, name='update_illegal_status'),
    path('records/<int:record_id>/regularize/', views.regularize_record_view, name='regularize_record'),
    path('records/<int:record_id>/archive/', views.record_archive_view, name='archive_record'),
    path('records/<int:record_id>/restore/', views.record_restore_view, name='restore_record'),
    path('records/<int:record_id>/download-zip/', views.download_record_zip_view, name='download_record_zip'),
    path('records/<int:record_id>/download-category/<int:req_id>/', views.download_category_zip_view, name='download_category_zip'),
    path('records/<int:record_id>/download-slot/<int:item_id>/', views.download_slot_zip_view, name='download_slot_zip'),
    path('records/export/municipal-zip/', views.download_municipal_zip_view, name='download_municipal_zip'),
    path('records/<int:record_id>/requirement/<int:req_id>/', views.record_requirement_detail_view, name='record_requirement_detail'),
    path('records/<int:record_id>/batch-upload/', views.batch_upload_documents_view, name='batch_upload_documents'),
    path('records/bulk-encoding/', views.bulk_encoding_view, name='bulk_encoding'),
    path('records/<int:record_id>/permanent-delete/', views.permanent_delete_record_view, name='permanent_delete_record'),

    # Documents
    path('documents/serve/<str:token>/', views.serve_document_view, name='serve_document'),
    path('documents/serve/<str:token>/<str:filename>', views.serve_document_view, name='serve_document_named'),
    path('records/<int:record_id>/document/upload/', views.document_upload_view, name='upload_document'),
    path('records/<int:record_id>/document/<int:document_id>/replace/', views.document_replace_view, name='replace_document'),
    path('records/<int:record_id>/document/<int:document_id>/delete/', views.document_delete_view, name='delete_document'),
    path('records/<int:record_id>/requirement/<int:item_id>/delete-all/', views.delete_requirement_documents_view, name='delete_requirement_documents'),
    path('requirements/<int:req_id>/toggle-waive/', views.toggle_requirement_waived_view, name='toggle_requirement_waived'),
    path('alerts/list/', views.alerts_list_json_view, name='alerts_list_json'),
    path('notifications/action/', views.notification_sync_action_view, name='notification_sync_action'),

    # Search, Archive, Reports
    path('api/quick-search/', views.quick_search_api_view, name='api_quick_search'),
    path('search/', views.search_view, name='search'),
    path('archive/', views.archive_view, name='archive'),
    path('reports/', views.reports_view, name='reports'),
    path('activity-logs/export/', views.export_activity_logs_view, name='export_activity_logs'),
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),
    path('notifications/action/', views.notification_sync_action_view, name='notification_sync_action'),

    # Profile & Settings
    path('profile/', views.profile_view, name='profile'),
    path('users/<int:user_id>/avatar/', views.serve_user_avatar_view, name='serve_user_avatar'),
    path('about/', views.about_system_view, name='about_system'),
    path('about/feedback/', views.submit_system_feedback, name='submit_system_feedback'),
    path('users/', views.users_view, name='users'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/user/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),

    # Legacy redirect
    path('projects/', views.projects_view, name='projects'),

    # Error Page Previews & Diagnostics
    path('errors/404/', views.page_not_found, name='preview_404'),
    path('errors/500/', views.server_error, name='preview_500'),
    path('errors/403/', views.forbidden, name='preview_403'),
    path('errors/400/', views.bad_request, name='preview_400'),

    # Live Email Templates Preview & Redesign Viewer
    path('preview-email/', views.email_template_preview_view, name='preview_email_default'),
    path('preview-email/<str:template_name>/', views.email_template_preview_view, name='preview_email_template'),

    # REST API & JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]
