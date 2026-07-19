from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Record, Document, Barangay, Category
from .serializers import RecordSerializer, DocumentSerializer, BarangaySerializer, CategorySerializer
from django.core.exceptions import PermissionDenied


class IsAuthenticatedJWT(permissions.BasePermission):
    """
    Allow access to authenticated users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticatedJWT]

    def get_queryset(self):
        user = self.request.user
        queryset = Record.objects.filter(status='active').select_related('barangay', 'category', 'created_by')
        
        # Admin and Engineer can see all active records.
        if user.role in ['admin', 'engineer']:
            return queryset
        
        # Staff can only see their own created records.
        return queryset.filter(created_by=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ['admin', 'staff']:
            raise PermissionDenied("You do not have permission to encode records.")
        serializer.save(created_by=user)

    def perform_update(self, serializer):
        user = self.request.user
        record = self.get_object()
        
        # Only admin or the staff member who created the record can update it.
        if user.role != 'admin' and (user.role != 'staff' or record.created_by != user):
            raise PermissionDenied("You do not have permission to edit this record.")
            
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        # Soft delete: archive the record rather than delete it.
        if user.role != 'admin':
            raise PermissionDenied("Only Administrators can archive records.")
            
        instance.status = 'archived'
        instance.save()


class BarangayViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Barangay.objects.all()
    serializer_class = BarangaySerializer
    permission_classes = [IsAuthenticatedJWT]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedJWT]
