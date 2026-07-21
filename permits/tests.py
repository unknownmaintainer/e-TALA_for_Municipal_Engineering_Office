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
        self.assertEqual(clean_output, "alert('xss') Hello World!")

    def test_file_validation(self):
        # Invalid file type
        invalid_file = SimpleUploadedFile("test.txt", b"plain text content")
        with self.assertRaises(ValidationError):
            validate_document_file(invalid_file)

        # Valid file type, invalid size (> 10MB)
        large_file = SimpleUploadedFile("test.pdf", b"x" * (11 * 1024 * 1024), content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_file(large_file)

        # Valid file (PDF under 10MB)
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
        self.assertIn("Account temporarily locked", msg)

    def test_permanent_lockout(self):
        # Simulate 10 failed logins total
        for i in range(10):
            LoginAttempt.objects.create(email_attempted='staffuser@gmail.com', success=False)

        locked, msg = check_lockout('staffuser@gmail.com', '127.0.0.1')
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)  # Account should be deactivated
        self.assertTrue(locked)
        self.assertIn("Account locked. Please contact the administrator", msg)

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

    def test_api_records_staff_masking(self):
        from django.urls import reverse
        from rest_framework_simplejwt.tokens import RefreshToken
        from permits.models import Record, Category
        
        # Create category
        cat = Category.objects.create(category_name="Building Permit")
        # Create record
        rec = Record.objects.create(
            project_name="Test Project",
            record_title="Test Title",
            category=cat,
            location_type="municipal",
            year=2026,
            budget_amount=100000.00,
            created_by=self.staff
        )
        
        # Authenticate as staff
        refresh = RefreshToken.for_user(self.staff)
        auth_header = f'Bearer {refresh.access_token}'
        
        url = reverse('api_record-detail', kwargs={'pk': rec.record_id})
        response = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(response.status_code, 200)
        # Should be masked
        self.assertEqual(response.data['budget_amount'], '₱*,***,***.**')

    def test_api_records_engineer_unmasking(self):
        from django.urls import reverse
        from rest_framework_simplejwt.tokens import RefreshToken
        from permits.models import Record, Category
        
        # Create engineer
        engineer = CustomUser.objects.create_user(
            username='engineeruser',
            email='engineeruser@gmail.com',
            password='Password123',
            role='engineer'
        )
        
        # Create category
        cat = Category.objects.create(category_name="Building Permit")
        # Create record
        rec = Record.objects.create(
            project_name="Test Project",
            record_title="Test Title",
            category=cat,
            location_type="municipal",
            year=2026,
            budget_amount=100000.00,
            created_by=self.staff
        )
        
        # Authenticate as engineer
        refresh = RefreshToken.for_user(engineer)
        auth_header = f'Bearer {refresh.access_token}'
        
        url = reverse('api_record-detail', kwargs={'pk': rec.record_id})
        response = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(response.status_code, 200)
        # Should be unmasked
        self.assertEqual(float(response.data['budget_amount']), 100000.00)


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

    def test_engineer_reports_access(self):
        from django.urls import reverse
        # Logged in as staff -> Blocked
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 403)

        # Logged in as engineer -> Allowed
        self.client.login(username='engineeruser', password='Password123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)

    def test_engineer_read_only_restriction(self):
        from django.urls import reverse
        self.client.login(username='engineeruser', password='Password123')
        
        # Creating a record should be blocked
        response = self.client.get(reverse('create_record'))
        self.assertEqual(response.status_code, 403)

        # Document upload should be blocked
        url = reverse('upload_document', kwargs={'record_id': self.record.record_id})
        doc_file = SimpleUploadedFile("test.pdf", b"pdf content", content_type="application/pdf")
        response = self.client.post(url, {'document_file': doc_file})
        self.assertEqual(response.status_code, 403)

    def test_archive_view_restricted_to_admin(self):
        from django.urls import reverse
        # Logged in as staff -> Blocked
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('archive'))
        self.assertEqual(response.status_code, 403)

        # Logged in as engineer -> Blocked
        self.client.login(username='engineeruser', password='Password123')
        response = self.client.get(reverse('archive'))
        self.assertEqual(response.status_code, 403)

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

        # 2. Upload replacement document
        doc2 = SimpleUploadedFile("test2.pdf", b"pdf content 2", content_type="application/pdf")
        response = self.client.post(url, {
            'document_file': doc2,
            'requirement_item_id': self.item.item_id
        })
        self.assertEqual(response.status_code, 302)

        # Verify old document is deleted from database
        self.assertFalse(Document.objects.filter(document_id=first_doc_id).exists())

        # Verify new document is linked and database record count remains 1 for documents
        self.req.refresh_from_db()
        self.assertTrue(self.req.is_fulfilled)
        self.assertNotEqual(self.req.document.document_id, first_doc_id)
        self.assertEqual(Document.objects.filter(engineering_record=self.record).count(), 1)

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

        # 2. Filter by illegal construction on records_browse
        response = self.client.get(reverse('records_browse') + '?illegal=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        page_objs = response.context['page_obj']
        self.assertTrue(any(r.record_id == illegal_rec.record_id for r in page_objs))

        # 3. Update regularization status to pending_permit
        update_url = reverse('update_illegal_status', kwargs={'record_id': illegal_rec.record_id})
        res = self.client.post(update_url, {'illegal_compliance_status': 'pending_permit'})
        self.assertEqual(res.status_code, 302)
        illegal_rec.refresh_from_db()
        self.assertEqual(illegal_rec.illegal_compliance_status, 'pending_permit')

    def test_flag_illegal_construction_endpoint(self):
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile
        from permits.models import EngineeringRecord, AuditLog

        self.client.login(username='staffuser', password='Password123')
        flag_url = reverse('flag_illegal_construction')

        dummy_img = SimpleUploadedFile("site_photo.png", b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82', content_type="image/png")

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
        self.assertIn("Flagged Illegal Construction", audit_entry.action)

    def test_gis_map_view_endpoint(self):
        self.client.login(username='adminuser', password='Password123')
        map_url = reverse('gis_map')
        res = self.client.get(map_url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'permits/gis_map.html')
        self.assertIn('map_features_json', res.context)







