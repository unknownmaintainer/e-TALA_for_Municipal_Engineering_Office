from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from permits.models import CustomUser, Barangay, Category, Record, Document, PasswordHistory, LoginAttempt
from permits.validators import validate_document_file, sanitize_input
from permits.views import check_lockout


@override_settings(
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}
    }
)
class PermitsTestCase(TestCase):
    def setUp(self):
        # Create standard user accounts
        self.admin = CustomUser.objects.create_user(
            username='adminuser',
            email='adminuser@gmail.com',
            password='Password123',
            role='admin'
        )
        self.staff = CustomUser.objects.create_user(
            username='staffuser',
            email='staffuser@gmail.com',
            password='Password123',
            role='staff'
        )

    def test_user_roles(self):
        self.assertEqual(self.admin.role, 'admin')
        self.assertEqual(self.staff.role, 'staff')

    def test_sanitize_input(self):
        dirty_input = "<script>alert('xss')</script> Hello World!"
        clean_output = sanitize_input(dirty_input)
        self.assertEqual(clean_output, "alert(&#x27;xss&#x27;) Hello World!")

    def test_file_validation(self):
        # Invalid file type
        invalid_file = SimpleUploadedFile("test.txt", b"plain text content")
        with self.assertRaises(ValidationError):
            validate_document_file(invalid_file)

        # Valid file type, invalid size (> 50MB)
        large_file = SimpleUploadedFile("test.pdf", b"x" * (51 * 1024 * 1024), content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_file(large_file)

        # Valid file (PDF under 50MB)
        valid_file = SimpleUploadedFile("test.pdf", b"x" * (5 * 1024 * 1024), content_type="application/pdf")
        try:
            validate_document_file(valid_file)
        except ValidationError:
            self.fail("validate_document_file raised ValidationError unexpectedly!")

    def test_password_history_policy(self):
        # Create password history
        PasswordHistory.objects.create(user=self.staff, password_hash=make_password('OldPassword123'))
        PasswordHistory.objects.create(user=self.staff, password_hash=make_password('AnotherOld123'))

        # Check if matched in history (simulating views check)
        histories = PasswordHistory.objects.filter(user=self.staff).order_by('-created_at')[:3]
        matches_history = False
        new_password = 'OldPassword123'
        from django.contrib.auth.hashers import check_password
        for h in histories:
            if check_password(new_password, h.password_hash):
                matches_history = True
                break
        self.assertTrue(matches_history)

    def test_temporary_lockout(self):
        # Simulate 5 failed logins within 15 minutes
        for i in range(5):
            LoginAttempt.objects.create(email_attempted='staffuser@gmail.com', success=False)

        locked, msg = check_lockout('staffuser@gmail.com', '127.0.0.1')
        self.assertTrue(locked)
        self.assertIn("Security cooldown active", msg)

    def test_permanent_lockout(self):
        # Simulate 10 failed logins total
        for i in range(10):
            LoginAttempt.objects.create(email_attempted='staffuser@gmail.com', success=False)

        locked, msg = check_lockout('staffuser@gmail.com', '127.0.0.1')
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)  # Account should be deactivated
        self.assertTrue(locked)
        self.assertIn("Account access is restricted", msg)

    def test_virus_scan_hook(self):
        # Filename containing 'eicar' should fail virus scan
        eicar_file = SimpleUploadedFile("eicar_test.pdf", b"pdf content", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_file(eicar_file)

    def test_mime_type_validation(self):
        # Invalid mime type should fail validation
        txt_file = SimpleUploadedFile("test.pdf", b"pdf content", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_document_file(txt_file)

    def test_api_jwt_protection(self):
        from django.urls import reverse
        url = reverse('api_record-list')
        
        # Anonymous request should return 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_api_records_staff_access(self):
        from django.urls import reverse
        from rest_framework_simplejwt.tokens import RefreshToken
        from permits.models import EngineeringRecord, Barangay
        
        brgy = Barangay.objects.create(barangay_name="API Test Barangay")
        rec = EngineeringRecord.objects.create(
            title="Test Engineering Record",
            record_type="Permit",
            barangay=brgy,
            year=2026,
            created_by=self.staff
        )
        
        # Authenticate as staff
        refresh = RefreshToken.for_user(self.staff)
        auth_header = f'Bearer {refresh.access_token}'
        
        url = reverse('api_record-detail', kwargs={'pk': rec.record_id})
        response = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Test Engineering Record')

    def test_api_records_admin_access(self):
        from django.urls import reverse
        from rest_framework_simplejwt.tokens import RefreshToken
        from permits.models import EngineeringRecord, Barangay
        
        brgy = Barangay.objects.create(barangay_name="Admin API Barangay")
        rec = EngineeringRecord.objects.create(
            title="Admin Test Record",
            record_type="Project",
            barangay=brgy,
            year=2026,
            created_by=self.staff
        )
        
        # Authenticate as admin (Engineering Office Head)
        refresh = RefreshToken.for_user(self.admin)
        auth_header = f'Bearer {refresh.access_token}'
        
        url = reverse('api_record-detail', kwargs={'pk': rec.record_id})
        response = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Admin Test Record')


@override_settings(
    AXES_ENABLED=False,
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}
    }
)
class RolePermissionsAndCleanupTestCase(TestCase):
    def setUp(self):
        from permits.models import CustomUser, Barangay, EngineeringRecord, PermitDetail, RequirementTemplate, RequirementItem, RecordRequirement
        self.admin = CustomUser.objects.create_user(
            username='adminuser',
            email='adminuser@gmail.com',
            password='Password123',
            role='admin'
        )
        self.staff = CustomUser.objects.create_user(
            username='staffuser',
            email='staffuser@gmail.com',
            password='Password123',
            role='staff'
        )
        self.engineer = CustomUser.objects.create_user(
            username='engineeruser',
            email='engineeruser@gmail.com',
            password='Password123',
            role='engineer'
        )
        self.barangay = Barangay.objects.create(barangay_name="Ponong")
        
        # Create an engineering record
        self.record = EngineeringRecord.objects.create(
            record_type='Permit',
            barangay=self.barangay,
            title='Test Permit Record',
            year=2026,
            created_by=self.staff
        )
        # Create details
        self.permit_detail = PermitDetail.objects.create(
            engineering_record=self.record,
            permit_type='Building',
            applicant_name='John Doe',
            permit_number='BP-2026-0001'
        )
        # Create requirement template & items
        self.template = RequirementTemplate.objects.create(
            record_type='Permit',
            subtype='Building',
            scope=''
        )
        self.item = RequirementItem.objects.create(
            template=self.template,
            name='Duly Accomplished Building Permit Application Form',
            order=1
        )
        self.req = RecordRequirement.objects.create(
            record=self.record,
            requirement_item=self.item
        )

    def test_staff_reports_access(self):
        from django.urls import reverse
        # Logged in as staff -> Allowed
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)

        # Logged in as admin -> Allowed
        self.client.login(username='adminuser', password='Password123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)

    def test_archive_view_permissions(self):
        from django.urls import reverse
        # Logged in as staff -> Allowed to view own trash
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('archive'))
        self.assertEqual(response.status_code, 200)

        # Logged in as admin -> Allowed
        self.client.login(username='adminuser', password='Password123')
        response = self.client.get(reverse('archive'))
        self.assertEqual(response.status_code, 200)

    def test_document_replacement_cleanup(self):
        from django.urls import reverse
        from permits.models import Document, RecordRequirement
        self.client.login(username='staffuser', password='Password123')

        # 1. Upload first document
        url = reverse('upload_document', kwargs={'record_id': self.record.record_id})
        doc1 = SimpleUploadedFile("test1.pdf", b"pdf content 1", content_type="application/pdf")
        response = self.client.post(url, {
            'document_file': doc1,
            'requirement_item_id': self.item.item_id
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify first document exists and is linked
        self.req.refresh_from_db()
        self.assertTrue(self.req.is_fulfilled)
        first_doc_id = self.req.document.document_id
        self.assertTrue(Document.objects.filter(document_id=first_doc_id).exists())

        # Mock the file delete on the storage backend to prevent network calls during testing
        original_delete = self.req.document.file.delete
        self.req.document.file.delete = lambda *args, **kwargs: None

        # 2. Upload additional document to the same slot (multi-file container support)
        doc2 = SimpleUploadedFile("test2.pdf", b"pdf content 2", content_type="application/pdf")
        response = self.client.post(url, {
            'document_file': doc2,
            'requirement_item_id': self.item.item_id
        })
        self.assertEqual(response.status_code, 302)

        # Verify both documents exist in database under the requirement slot
        self.assertTrue(Document.objects.filter(document_id=first_doc_id).exists())
        self.assertEqual(Document.objects.filter(engineering_record=self.record).count(), 2)

        # 3. Test replace_document endpoint (swapping first document with replacement)
        replace_url = reverse('replace_document', kwargs={'record_id': self.record.record_id, 'document_id': first_doc_id})
        replacement_doc = SimpleUploadedFile("test_replacement.pdf", b"pdf replacement content", content_type="application/pdf")
        replace_response = self.client.post(replace_url, {
            'replacement_file': replacement_doc,
        })
        self.assertEqual(replace_response.status_code, 302)

        # Verify first document record has been updated with replacement metadata
        first_doc_obj = Document.objects.get(document_id=first_doc_id)
        self.assertEqual(first_doc_obj.file_name, "test_replacement.pdf")
        self.assertEqual(first_doc_obj.version, 2)

    def test_search_view_returns_results(self):
        from django.urls import reverse
        self.client.login(username='staffuser', password='Password123')
        
        # Test basic search query matching the created permit record
        response = self.client.get(reverse('search') + '?q=John')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_records_browse_year_filter(self):
        from django.urls import reverse
        from permits.models import EngineeringRecord
        self.client.login(username='staffuser', password='Password123')

        # Create record for 2015
        EngineeringRecord.objects.create(
            record_type='Project',
            barangay=self.barangay,
            title='2015 Project',
            year=2015,
            created_by=self.staff
        )

        # Query year 2026 -> should only return 2026 record
        response = self.client.get(reverse('records_browse') + '?year=2026')
        self.assertEqual(response.status_code, 200)
        page_objs = response.context['page_obj']
        for r in page_objs:
            self.assertEqual(r.year, 2026)

        # Query year 2015 -> should only return 2015 record
        response_2015 = self.client.get(reverse('records_browse') + '?year=2015')
        self.assertEqual(response_2015.status_code, 200)
        page_objs_2015 = response_2015.context['page_obj']
        self.assertEqual(len(page_objs_2015), 1)
        self.assertEqual(page_objs_2015[0].year, 2015)

    def test_illegal_construction_tracking(self):
        from django.urls import reverse
        from permits.models import EngineeringRecord
        self.client.login(username='staffuser', password='Password123')

        # 1. Create record flagged as illegal construction
        illegal_rec = EngineeringRecord.objects.create(
            record_type='Permit',
            barangay=self.barangay,
            title='Unpermitted Structure Discovered',
            year=2026,
            is_illegal_construction=True,
            illegal_compliance_status='unresolved',
            created_by=self.staff
        )

        # 2. Access dedicated illegal_constructions view
        response = self.client.get(reverse('illegal_constructions'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        page_objs = response.context['page_obj']
        self.assertTrue(any(r.record_id == illegal_rec.record_id for r in page_objs))

        # 2b. Legacy redirect from records_browse?illegal=1 to illegal_constructions
        legacy_res = self.client.get(reverse('records_browse') + '?illegal=1')
        self.assertEqual(legacy_res.status_code, 302)
        self.assertIn('/illegal-constructions/', legacy_res.url)

        # 3. Update regularization status to pending_permit
        update_url = reverse('update_illegal_status', kwargs={'record_id': illegal_rec.record_id})
        res = self.client.post(update_url, {'illegal_compliance_status': 'pending_permit'})
        self.assertEqual(res.status_code, 302)
        illegal_rec.refresh_from_db()
        self.assertEqual(illegal_rec.illegal_compliance_status, 'pending_permit')

        # 4. Convert/Regularize to official Permit Record
        regularize_url = reverse('regularize_record', kwargs={'record_id': illegal_rec.record_id})
        reg_res = self.client.post(regularize_url, {
            'permit_type': 'Building Permit',
            'permit_number': 'BP-2026-9999',
            'applicant_name': 'Juan Dela Cruz',
            'building_type': 'Commercial'
        })
        self.assertEqual(reg_res.status_code, 302)
        illegal_rec.refresh_from_db()
        self.assertEqual(illegal_rec.illegal_compliance_status, 'resolved')
        self.assertEqual(illegal_rec.permit_detail.permit_number, 'BP-2026-9999')
        self.assertEqual(illegal_rec.permit_detail.applicant_name, 'Juan Dela Cruz')

    def test_flag_illegal_construction_endpoint(self):
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        from permits.models import EngineeringRecord, AuditLog

        self.client.login(username='staffuser', password='Password123')
        flag_url = reverse('flag_illegal_construction')

        dummy_img = SimpleUploadedFile("site_evidence.pdf", b'%PDF-1.4 sample pdf document bytes', content_type="application/pdf")

        post_data = {
            'title': 'Unpermitted Commercial Post Discovered',
            'barangay': self.barangay.barangay_id,
            'location_address': 'Sitio Riverside, Guinte',
            'date_discovered': '2026-07-21',
            'illegal_compliance_status': 'unresolved',
            'photo': dummy_img
        }

        res = self.client.post(flag_url, post_data)
        self.assertEqual(res.status_code, 302)

        record = EngineeringRecord.objects.get(title='Unpermitted Commercial Post Discovered')
        self.assertTrue(record.is_illegal_construction)
        self.assertEqual(record.illegal_compliance_status, 'unresolved')
        self.assertEqual(record.barangay, self.barangay)
        self.assertIsNotNone(record.discovery_photo)

        # Check Audit Log
        audit_entry = AuditLog.objects.filter(target_record_id=record.record_id).first()
        self.assertIsNotNone(audit_entry)
        self.assertIn("Reported violation", audit_entry.action)

    def test_flag_illegal_construction_with_photo(self):
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        from permits.models import EngineeringRecord

        self.client.login(username='staffuser', password='Password123')
        flag_url = reverse('flag_illegal_construction')

        dummy_photo = SimpleUploadedFile("inspection_snap.jpg", b'\xff\xd8\xff\xe0\x00\x10JFIF sample jpg bytes', content_type="image/jpeg")

        post_data = {
            'title': 'Illegal Fence Extension Discovered',
            'barangay': self.barangay.barangay_id,
            'location_address': 'Purok 2, Carigara',
            'date_discovered': '2026-08-10',
            'illegal_compliance_status': 'unresolved',
            'photo': dummy_photo
        }

        res = self.client.post(flag_url, post_data)
        self.assertEqual(res.status_code, 302)

        record = EngineeringRecord.objects.get(title='Illegal Fence Extension Discovered')
        self.assertTrue(record.is_illegal_construction)
        self.assertIsNotNone(record.discovery_photo)
        self.assertEqual(record.discovery_photo.document_type, 'Picture')
        self.assertEqual(record.discovery_photo.file_name, 'inspection_snap.jpg')

    def test_supabase_storage_routing(self):
        from permits.storage import SupabaseStorage
        storage = SupabaseStorage()
        self.assertIsNotNone(storage.fallback_storage)
        self.assertEqual(storage._clean_path('media/documents/test.pdf'), 'documents/test.pdf')

    def test_permissions_helper(self):
        from permits.permissions import has_role
        self.assertTrue(has_role(self.admin, 'admin'))
        self.assertTrue(has_role(self.admin, ['admin', 'staff']))
        self.assertFalse(has_role(self.staff, 'admin'))
        self.assertFalse(has_role(None, 'admin'))

    def test_services_filter_engineering_records(self):
        from permits.services import filter_engineering_records
        from permits.models import EngineeringRecord
        qs = EngineeringRecord.objects.all()
        filtered = filter_engineering_records(qs, query="Test Permit")
        self.assertTrue(filtered.exists())
        self.assertTrue(any(r.title == 'Test Permit Record' for r in filtered))

    def test_forms_user_creation(self):
        from permits.forms import UserCreationForm
        form_data = {
            'email': 'newtestuser@gmail.com',
            'full_name': 'New Test User',
            'role': 'staff',
            'password': 'SecurePassword123!'
        }
        form = UserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_health_and_ping_endpoints(self):
        # Test /health/
        health_res = self.client.get(reverse('health_check'))
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(health_res.json().get('status'), 'healthy')

        # Test /ping/
        ping_res = self.client.get(reverse('ping_check'))
        ping_res_status = ping_res.status_code
        self.assertEqual(ping_res_status, 200)
        self.assertEqual(ping_res.json().get('status'), 'healthy')

    def test_backlog_year_1995_cutoff(self):
        from permits.validators import validate_backlog_year
        from django.core.exceptions import ValidationError

        # Years before 1995 must fail
        with self.assertRaises(ValidationError):
            validate_backlog_year(1994)
        with self.assertRaises(ValidationError):
            validate_backlog_year("1994-12-31")
        with self.assertRaises(ValidationError):
            validate_backlog_year(1990)

        # 1995 and later must pass
        try:
            validate_backlog_year(1995)
            validate_backlog_year("1995-01-01")
            validate_backlog_year(2026)
            validate_backlog_year("2026-08-25")
        except ValidationError:
            self.fail("validate_backlog_year raised ValidationError for valid year >= 1995!")

    def test_strict_pdf_attachment_policy(self):
        from permits.validators import validate_document_file
        from django.core.exceptions import ValidationError

        # Disallowed document types
        docx_file = SimpleUploadedFile("document.docx", b"PK fake docx content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        png_file = SimpleUploadedFile("photo.png", b"\x89PNG fake image", content_type="image/png")
        txt_file = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")

        for f in [docx_file, png_file, txt_file]:
            with self.assertRaises(ValidationError):
                validate_document_file(f)

        # Allowed PDF
        pdf_file = SimpleUploadedFile("plan.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        try:
            validate_document_file(pdf_file)
        except ValidationError:
            self.fail("validate_document_file raised ValidationError for valid PDF document!")

    def test_lgu_general_fund_and_project_status_defaults(self):
        from permits.models import EngineeringRecord, ProjectDetail
        
        proj_record = EngineeringRecord.objects.create(
            record_type='Project',
            barangay=self.barangay,
            title='Brgy Hall Roofing',
            year=2026,
            status='completed',
            created_by=self.staff
        )
        proj_detail = ProjectDetail.objects.create(
            engineering_record=proj_record,
            project_type='Barangay Infrastructure',
            project_cost=500000.00
        )
        self.assertEqual(proj_detail.funding_source, 'LGU General Fund')
        self.assertEqual(proj_detail.project_status, 'Completed')
        self.assertEqual(proj_record.status_label, 'Archived')

    def test_annual_record_summary_report(self):
        self.client.login(username='adminuser', password='Password123')
        response = self.client.get(reverse('reports'), {'annual_year': 2026})
        self.assertEqual(response.status_code, 200)
        self.assertIn('annual_summary_year', response.context)
        self.assertEqual(response.context['annual_summary_year'], 2026)
        self.assertIn('funding_sources_summary', response.context)
        self.assertIn('annual_permits_count', response.context)
        self.assertIn('annual_projects_count', response.context)
        self.assertIn('annual_total_budget', response.context)

    def test_all_zip_export_endpoints(self):
        import zipfile
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from permits.models import Document, RequirementTemplate, RequirementItem, RecordRequirement

        self.client.login(username='adminuser', password='Password123')

        # Create template, parent group and child item
        tmpl = RequirementTemplate.objects.create(name='Standard Building Permit', record_type='Permit')
        parent_item = RequirementItem.objects.create(template=tmpl, name='Architectural Plans', is_parent_group=True, order=1)
        child_item = RequirementItem.objects.create(template=tmpl, parent=parent_item, name='Floor Plan', is_parent_group=False, order=1)

        # Upload a dummy file attached to child_item
        dummy_file = SimpleUploadedFile("floor_plan.pdf", b"%PDF-1.4 sample blueprint data", content_type="application/pdf")
        doc = Document.objects.create(
            engineering_record=self.record,
            requirement_item=child_item,
            document_type='Blueprint',
            file=dummy_file,
            file_name='floor_plan.pdf',
            file_size=len(b"%PDF-1.4 sample blueprint data"),
            uploaded_by=self.admin
        )
        parent_req = RecordRequirement.objects.create(record=self.record, requirement_item=parent_item)
        RecordRequirement.objects.create(record=self.record, requirement_item=child_item, document=doc, is_fulfilled=True)

        # 1. Single Record ZIP Export
        rec_zip_url = reverse('download_record_zip', kwargs={'record_id': self.record.record_id})
        res = self.client.get(rec_zip_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(res.content), 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('00_RECORD_SUMMARY.txt', namelist)
            self.assertTrue(any('floor_plan' in name.lower() or 'floor' in name.lower() for name in namelist))

        # 2. Category ZIP Export
        cat_zip_url = reverse('download_category_zip', kwargs={'record_id': self.record.record_id, 'req_id': parent_req.req_id})
        res = self.client.get(cat_zip_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(res.content), 'r') as zf:
            self.assertTrue(len(zf.namelist()) > 0)

        # 3. Slot ZIP Export
        slot_zip_url = reverse('download_slot_zip', kwargs={'record_id': self.record.record_id, 'item_id': child_item.item_id})
        res = self.client.get(slot_zip_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(res.content), 'r') as zf:
            self.assertTrue(len(zf.namelist()) > 0)

        # 4. Barangay ZIP Export
        brgy_zip_url = reverse('download_barangay_zip', kwargs={'barangay_id': self.barangay.barangay_id})
        res = self.client.get(brgy_zip_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(res.content), 'r') as zf:
            namelist = zf.namelist()
            self.assertTrue(any('00_BARANGAY_SUMMARY.txt' in name for name in namelist))

        # 5. Municipal Full Archive ZIP Export
        muni_zip_url = reverse('download_municipal_zip')
        res = self.client.get(muni_zip_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(res.content), 'r') as zf:
            namelist = zf.namelist()
            self.assertTrue(any('00_MUNICIPAL_SUMMARY.txt' in name for name in namelist))












