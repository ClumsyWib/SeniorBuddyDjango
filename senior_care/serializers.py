"""
Serializers for Senior Care API
Convert Django models to JSON and vice versa
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, SeniorProfile, CaretakerProfile, NGO, VolunteerProfile,
    CareAssignment, Appointment, Medicine, MedicineLog,
    VolunteerTask, EmergencyAlert, HealthRecord, EmergencyContact, Doctor, DailyActivity,
    HelpRequest, VolunteerEmergency, ChatMessage, VolunteerRating
)


# ==============================
# User Serializers
# ==============================
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source='get_full_name')
    caretaker_profile = serializers.SerializerMethodField()
    volunteer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'phone_number', 'address', 'city', 'state',
            'date_of_birth', 'emergency_contact_name', 'emergency_contact_phone',
            'profile_picture', 'zip_code', 'is_active_user', 'created_at',
            'last_active', 'is_superuser', 'is_staff',
            'caretaker_profile', 'volunteer_profile'
        ]
        read_only_fields = ['id', 'created_at']

    def get_caretaker_profile(self, obj):
        if hasattr(obj, 'caretaker_profile'):
            from .models import CaretakerProfile
            try:
                profile = obj.caretaker_profile
                return {
                    'experience_years': profile.experience_years,
                    'skills': profile.skills,
                    'bio': profile.bio,
                    'specialization': profile.specialization,
                    'availability_status': profile.availability_status,
                    'is_available': profile.is_available,
                    'hourly_rate': str(profile.hourly_rate),
                    'rating': str(profile.rating),
                }
            except:
                return None
        return None

    def get_volunteer_profile(self, obj):
        if hasattr(obj, 'volunteer_profile'):
            try:
                profile = obj.volunteer_profile
                return {
                    'skills': profile.skills,
                    'bio': profile.bio,
                    'specialization': profile.specialization,
                    'availability_status': profile.availability_status,
                    'is_available': profile.is_available,
                    'total_hours': profile.total_hours,
                    'rating': str(profile.rating),
                }
            except:
                return None
        return None


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'user_type', 'phone_number'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Passwords don't match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


# ==============================
# Profile Serializers
# ==============================
class SeniorProfileSerializer(serializers.ModelSerializer):
    family_member_name = serializers.CharField(
        source='family_member.get_full_name',
        read_only=True
    )

    class Meta:
        model = SeniorProfile
        fields = [
            'id', 'family_member', 'family_member_name', 'name', 'age', 'gender',
            'medical_info', 'medical_conditions', 'allergies', 'daily_routine',
            'mobility_status', 'care_level', 'primary_doctor',
            'doctor_phone', 'emergency_contact', 'address', 'city', 'photo',
            'pair_code', 'is_connected', 'created_at'
        ]
        read_only_fields = ['family_member', 'pair_code', 'is_connected']



class CaretakerProfileSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)
    caretaker_name = serializers.CharField(
        source='user.get_full_name',
        read_only=True
    )

    class Meta:
        model = CaretakerProfile
        fields = '__all__'


class VolunteerProfileSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)
    volunteer_name = serializers.CharField(
        source='user.get_full_name',
        read_only=True
    )
    ngo_name = serializers.CharField(
        source='ngo.name',
        read_only=True
    )

    class Meta:
        model = VolunteerProfile
        fields = '__all__'


# ==============================
# NGO Serializer
# ==============================
class NGOSerializer(serializers.ModelSerializer):

    admin_name = serializers.CharField(
        source='admin.get_full_name',
        read_only=True
    )
    volunteer_count = serializers.IntegerField(
        source='volunteers.count',
        read_only=True
    )

    class Meta:
        model = NGO
        fields = '__all__'


# ==============================
# Care Assignment
# ==============================
class CareAssignmentSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )
    caretaker_name = serializers.CharField(
        source='caretaker.get_full_name',
        read_only=True
    )
    caretaker_photo = serializers.ImageField(
        source='caretaker.profile_picture',
        read_only=True
    )
    caretaker_phone = serializers.CharField(
        source='caretaker.phone_number',
        read_only=True
    )

    class Meta:
        model = CareAssignment
        fields = '__all__'


# ==============================
# Emergency Contact
# ==============================
class EmergencyContactSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )

    class Meta:
        model = EmergencyContact
        fields = '__all__'


# ==============================
# Appointment
# ==============================
class AppointmentSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )
    caretaker_name = serializers.CharField(
        source='caretaker.get_full_name',
        read_only=True
    )

    class Meta:
        model = Appointment
        fields = '__all__'


# ==============================
# Medicine Serializer
# ==============================
class MedicineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Medicine
        fields = [
            'id',
            'senior',
            'medicine_name',
            'dosage',
            'frequency',
            'time_of_day',
            'instructions',
            'start_date',
            'end_date',
            'is_active',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        # Validate end_date is after start_date
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        return data


# ==============================
# Medicine Log
# ==============================
class MedicineLogSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source='medicine.medicine_name',
        read_only=True
    )
    senior_name = serializers.CharField(
        source='medicine.senior.name',
        read_only=True
    )
    confirmed_by_name = serializers.CharField(
        source='confirmed_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = MedicineLog
        fields = '__all__'


# ==============================
# Volunteer Task
# ==============================
class VolunteerTaskSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )
    volunteer_name = serializers.CharField(
        source='volunteer.get_full_name',
        read_only=True
    )
    ngo_name = serializers.CharField(
        source='ngo.name',
        read_only=True
    )

    class Meta:
        model = VolunteerTask
        fields = '__all__'


# ==============================
# Emergency Alert
# ==============================
class EmergencyAlertSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )
    resolved_by_name = serializers.CharField(
        source='resolved_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = EmergencyAlert
        fields = '__all__'


# ==============================
# Health Record
# ==============================
class HealthRecordSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )
    recorded_by_name = serializers.CharField(
        source='recorded_by.get_full_name',
        read_only=True
    )

    class Meta:
        model = HealthRecord
        fields = '__all__'



# ==============================
# Doctor
# ==============================
class DoctorSerializer(serializers.ModelSerializer):

    senior_name = serializers.CharField(
        source='senior.name',
        read_only=True
    )

    class Meta:
        model = Doctor
        fields = '__all__'

class DailyActivitySerializer(serializers.ModelSerializer):
    senior_name = serializers.ReadOnlyField(source='senior.name')
    caretaker_name = serializers.ReadOnlyField(source='caretaker.username')

    class Meta:
        model = DailyActivity
        fields = ['id', 'senior', 'senior_name', 'caretaker', 'caretaker_name', 'activity_type', 'notes', 'timestamp']
        read_only_fields = ['caretaker', 'timestamp']

# ==============================
# VOLUNTEER SYSTEM SERIALIZERS
# ==============================

class HelpRequestSerializer(serializers.ModelSerializer):
    senior_name = serializers.ReadOnlyField(source='senior.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    volunteer_name = serializers.ReadOnlyField(source='assigned_volunteer.username')

    class Meta:
        model = HelpRequest
        fields = '__all__'
        read_only_fields = ['created_by', 'status', 'assigned_volunteer', 'created_at']

class VolunteerEmergencySerializer(serializers.ModelSerializer):
    senior_name = serializers.ReadOnlyField(source='senior.name')
    volunteer_name = serializers.ReadOnlyField(source='assigned_volunteer.username')

    class Meta:
        model = VolunteerEmergency
        fields = '__all__'
        read_only_fields = ['status', 'assigned_volunteer', 'created_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.username')
    receiver_name = serializers.ReadOnlyField(source='receiver.username')

    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ['sender', 'timestamp']

class VolunteerRatingSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.ReadOnlyField(source='volunteer.username')
    family_name = serializers.ReadOnlyField(source='family.username')

    class Meta:
        model = VolunteerRating
        fields = '__all__'
        read_only_fields = ['family', 'created_at']
