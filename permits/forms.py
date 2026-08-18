from django import forms
from django.contrib.auth import get_user_model
from .models import CustomUser, EngineeringRecord, Barangay, PermitDetail, ProjectDetail
from .validators import sanitize_input, validate_password_strength

User = get_user_model()


class UserCreationForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=255)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, initial='staff')
    designation = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = sanitize_input(self.cleaned_data.get('email', '')).strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_full_name(self):
        return sanitize_input(self.cleaned_data.get('full_name', '')).strip()

    def clean_designation(self):
        return sanitize_input(self.cleaned_data.get('designation', '')).strip()

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        ok, err_msg = validate_password_strength(password)
        if not ok:
            raise forms.ValidationError(err_msg)
        return password


class UserEditForm(forms.Form):
    user_id = forms.IntegerField()
    email = forms.EmailField()
    full_name = forms.CharField(max_length=255)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, initial='staff')
    designation = forms.CharField(max_length=150, required=False)

    def clean_email(self):
        email = sanitize_input(self.cleaned_data.get('email', '')).strip().lower()
        user_id = self.cleaned_data.get('user_id')
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_full_name(self):
        return sanitize_input(self.cleaned_data.get('full_name', '')).strip()

    def clean_designation(self):
        return sanitize_input(self.cleaned_data.get('designation', '')).strip()


class FlagIllegalConstructionForm(forms.Form):
    title = forms.CharField(max_length=255, required=False)
    barangay = forms.IntegerField()
    location_address = forms.CharField(max_length=255, required=False)
    violation_type = forms.CharField(max_length=100, required=False, initial='Unpermitted Construction')
    description = forms.CharField(widget=forms.Textarea, required=False)
    date_discovered = forms.DateField(required=False)
    remarks = forms.CharField(widget=forms.Textarea, required=False)

    def clean_title(self):
        t = sanitize_input(self.cleaned_data.get('title', '')).strip()
        return t or "Unpermitted Structure Discovered"

    def clean_location_address(self):
        return sanitize_input(self.cleaned_data.get('location_address', '')).strip()

    def clean_violation_type(self):
        return sanitize_input(self.cleaned_data.get('violation_type', 'Unpermitted Construction')).strip()

    def clean_description(self):
        return sanitize_input(self.cleaned_data.get('description', '')).strip()

    def clean_remarks(self):
        return sanitize_input(self.cleaned_data.get('remarks', '')).strip()


class OfficeSettingsForm(forms.Form):
    office_name = forms.CharField(max_length=255)
    municipality = forms.CharField(max_length=255)
    province = forms.CharField(max_length=255)

    def clean_office_name(self):
        return sanitize_input(self.cleaned_data.get('office_name', '')).strip()

    def clean_municipality(self):
        return sanitize_input(self.cleaned_data.get('municipality', '')).strip()

    def clean_province(self):
        return sanitize_input(self.cleaned_data.get('province', '')).strip()
