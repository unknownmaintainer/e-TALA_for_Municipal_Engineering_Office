from rest_framework import serializers
from .models import Barangay, Category, Record, Document, CustomUser

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
        fields = ['document_id', 'document_type', 'file', 'file_name', 'file_size', 'uploaded_by', 'uploaded_by_name', 'uploaded_at']


class RecordSerializer(serializers.ModelSerializer):
    barangay_name = serializers.ReadOnlyField(source='barangay.barangay_name')
    category_name = serializers.ReadOnlyField(source='category.category_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.full_name')
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Record
        fields = [
            'record_id', 'record_title', 'project_name', 'category', 'category_name',
            'location_type', 'barangay', 'barangay_name', 'year', 'budget_amount',
            'archive_number', 'description', 'status', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'documents'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        
        # Role-based field masking: Only Admins and Engineers can see raw budget amount.
        # Engineering Staff and external API users see masked string.
        if request and request.user:
            if request.user.role not in ['admin', 'engineer']:
                rep['budget_amount'] = '₱*,***,***.**'
        else:
            rep['budget_amount'] = '₱*,***,***.**'
            
        return rep
