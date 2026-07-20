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
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('register/', views.register_view, name='register'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Barangays
    path('barangays/', views.barangays_view, name='barangays'),
    path('barangays/<int:barangay_id>/', views.barangay_workspace_view, name='barangay_workspace'),

    # Engineering Records — Create Wizard (3 steps)
    path('records/new/', views.record_create_step1_view, name='create_step1'),
    path('records/new/type/', views.record_create_step2_view, name='create_step2'),
    path('records/new/form/', views.record_create_step3_view, name='create_step3'),

    # Engineering Records — Module Lists
    path('municipal/', views.municipal_projects_view, name='municipal_projects'),
    path('barangay/', views.barangay_projects_view, name='barangay_projects'),
    path('permits/', views.permit_records_view, name='permit_records'),

    # Engineering Records — CRUD
    path('records/', views.records_browse_view, name='records_browse'),
    path('records/create/', views.record_create_view, name='create_record'),
    path('records/<int:record_id>/', views.record_detail_view, name='record_detail'),
    path('records/<int:record_id>/edit/', views.record_edit_view, name='edit_record'),
    path('records/<int:record_id>/illegal-status/', views.update_illegal_status_view, name='update_illegal_status'),
    path('records/<int:record_id>/archive/', views.record_archive_view, name='archive_record'),
    path('records/<int:record_id>/restore/', views.record_restore_view, name='restore_record'),

    # Documents
    path('documents/serve/<str:token>/', views.serve_document_view, name='serve_document'),
    path('records/<int:record_id>/document/upload/', views.document_upload_view, name='upload_document'),
    path('records/<int:record_id>/document/<int:document_id>/delete/', views.document_delete_view, name='delete_document'),
    path('requirements/<int:req_id>/toggle-waive/', views.toggle_requirement_waived_view, name='toggle_requirement_waived'),
    path('alerts/list/', views.alerts_list_json_view, name='alerts_list_json'),

    # Search, Archive, Reports
    path('search/', views.search_view, name='search'),
    path('archive/', views.archive_view, name='archive'),
    path('reports/', views.reports_view, name='reports'),
    path('activity-logs/export/', views.export_activity_logs_view, name='export_activity_logs'),
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),

    # Profile & Settings
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.users_view, name='users'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/user/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),

    # Legacy redirect
    path('projects/', views.projects_view, name='projects'),

    # REST API & JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]
