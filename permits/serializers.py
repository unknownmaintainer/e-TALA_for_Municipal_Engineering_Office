from rest_framework import serializers
from .models import Barangay, Category, Record, Document, CustomUser, EngineeringRecord, PermitDetail, ProjectDetail

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'full_name', 'role']


class BarangaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Barangay
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.full_name')

    class Meta:
        model = Document
        fields = ['document_id', 'document_type', 'file', 'file_name', 'file_size', 'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'expiry_date']


class PermitDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermitDetail
        fields = ['permit_type', 'building_type', 'permit_number', 'date_issued', 'applicant_name', 'remarks']


class ProjectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDetail
        fields = ['project_type', 'funding_source', 'contractor', 'project_cost', 'project_status']


class EngineeringRecordSerializer(serializers.ModelSerializer):
    barangay_name = serializers.ReadOnlyField(source='barangay.barangay_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.full_name')
    specific_type = serializers.ReadOnlyField(source='specific_type_label')
    permit_detail = PermitDetailSerializer(read_only=True)
    project_detail = ProjectDetailSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = EngineeringRecord
        fields = [
            'record_id', 'record_type', 'project_scope', 'title', 'year', 'description',
            'status', 'is_illegal_construction', 'illegal_compliance_status',
            'barangay', 'barangay_name', 'created_by', 'created_by_name',
            'specific_type', 'permit_detail', 'project_detail',
            'date_started', 'date_completed', 'created_at', 'updated_at', 'documents'
        ]


# Backward compatibility serializer for legacy Record model
class RecordSerializer(EngineeringRecordSerializer):
    pass

