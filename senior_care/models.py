"""
# ==============================================================================
# FILE: models.py
# PURPOSE: Defines the Database Structure (Tables).
#
# Every class in this file represents a table in the database. Django uses an 
# ORM (Object-Relational Mapper), meaning we write Python code instead of SQL 
# to create and interact with database tables.
#
# KEY EXAM CONCEPTS:
# 1. AbstractUser: We customized Django's default User model to add extra fields 
#    like 'user_type' (Admin, Family, Caretaker, Volunteer).
# 2. ForeignKey & OneToOneField: These define relationships between tables. 
#    E.g., A SeniorProfile has a ForeignKey pointing to a Family User. An Appointment
#    has a Foreign Key pointing to a SeniorProfile (1 Senior can have many Appointments).
# 3. __str__ method: Controls how the object is displayed in the Django Admin panel.
# ==============================================================================
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# ==============================
# Custom User Model
# ==============================
class User(AbstractUser):

    USER_ROLES = (
        ('family', 'Family Member'),
        ('caretaker', 'Caretaker'),
        ('volunteer', 'Volunteer'),
        ('ngo', 'NGO'),
    )

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('gu', 'Gujarati'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('mr', 'Marathi'),
        ('bn', 'Bengali'),
        ('kn', 'Kannada'),
        ('ml', 'Malayalam'),
        ('pa', 'Punjabi'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_ROLES, default='family')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)

    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)

    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    is_active_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='en'
    )

    def __str__(self):
        return self.username


# ==============================
# Senior Profile
# ==============================
class SeniorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='senior_profile')
    family_member = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'family'}, related_name='managed_seniors')
    
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(default=65)
    gender = models.CharField(max_length=50, blank=True)

    medical_info = models.TextField(blank=True)
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    daily_routine = models.TextField(blank=True)

    mobility_status = models.CharField(max_length=100, blank=True)
    care_level = models.CharField(max_length=100, blank=True)

    primary_doctor = models.CharField(max_length=100, blank=True)
    doctor_phone = models.CharField(max_length=15, blank=True)

    emergency_contact = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='senior_photos/', null=True, blank=True)

    # New fields for Pair Code connection
    pair_code = models.CharField(max_length=6, blank=True)
    is_connected = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Senior: {self.name} (Family: {self.family_member.username})"


# ==============================
# NGO
# ==============================
class NGO(models.Model):

    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)

    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()

    description = models.TextField(blank=True)

    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==============================
# Caretaker Profile
# ==============================
class CaretakerProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='caretaker_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)

    experience_years = models.PositiveIntegerField(default=0)
    skills = models.TextField(blank=True)
    
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=255, blank=True, default='Professional Caretaker')
    availability_status = models.CharField(max_length=50, default='Full-time')

    is_available = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)

    background_check_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Caretaker: {self.user.get_full_name()}"


# ==============================
# Volunteer Profile
# ==============================
class VolunteerProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='volunteers')

    volunteer_id = models.CharField(max_length=50, unique=True)
    join_date = models.DateField(default=timezone.now)

    is_available = models.BooleanField(default=True)
    skills = models.TextField(blank=True)
    
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=255, blank=True, default='Volunteer')
    availability_status = models.CharField(max_length=50, default='Part-time')

    total_hours = models.FloatField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Volunteer: {self.user.get_full_name()}"


# ==============================
# Care Assignment
# ==============================
class CareAssignment(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='care_assignments'
    )

    caretaker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'caretaker'},
        related_name='assigned_seniors'
    )
    
    assigned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'family'}, 
        related_name='assignments_made'
    )

    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('senior', 'caretaker')

    def __str__(self):
        return f"{self.caretaker.username} caring for {self.senior.name}"


# ==============================
# Medicine
# ==============================
class Medicine(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='medicines'
    )

    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    time_of_day = models.CharField(max_length=50, blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    def __str__(self):
        return self.medicine_name


# ==============================
# Medicine Log
# ==============================
class MedicineLog(models.Model):

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='logs'
    )

    scheduled_time = models.DateTimeField()
    was_taken = models.BooleanField(default=False)

    actual_time = models.DateTimeField(null=True, blank=True)

    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_medicines'
    )

    def __str__(self):
        return f"{self.medicine.medicine_name} Log"


# ==============================
# Appointment
# ==============================
class Appointment(models.Model):

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    caretaker = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caretaker_appointments'
    )

    title = models.CharField(max_length=200)
    appointment_type = models.CharField(max_length=50, blank=True, null=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    location = models.CharField(max_length=255, blank=True, null=True)
    doctor_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    def __str__(self):
        return self.title


# ==============================
# Volunteer Task
# ==============================
class VolunteerTask(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='volunteer_tasks_received',
        null=True,
        blank=True
    )

    volunteer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='volunteer_tasks_assigned'
    )

    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    scheduled_date = models.DateField()

    status = models.CharField(max_length=50, default='assigned')

    def __str__(self):
        return self.title


# ==============================
# Emergency Alert
# ==============================
class EmergencyAlert(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='emergency_alerts'
    )

    alert_type = models.CharField(max_length=100)
    alert_time = models.DateTimeField(default=timezone.now)

    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )

    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Alert - {self.senior.name}"


# ==============================
# Health Record
# ==============================
class HealthRecord(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='health_records'
    )

    record_date = models.DateField(default=timezone.now)
    record_time = models.TimeField(default=timezone.now)

    blood_pressure = models.CharField(max_length=20, blank=True) # e.g. 120/80
    heart_rate = models.IntegerField(null=True, blank=True) # bpm
    temperature = models.FloatField(null=True, blank=True) # Celsius/Fahrenheit
    blood_sugar = models.IntegerField(null=True, blank=True) # mg/dL
    weight = models.FloatField(null=True, blank=True) # kg
    oxygen_level = models.IntegerField(null=True, blank=True) # SpO2 percentage

    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_health_records'
    )

    def __str__(self):
        return f"Health Record - {self.senior.name}"




# ==============================
# Emergency Contact
# ==============================
class EmergencyContact(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )

    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.senior.name}"
# ==============================
# Doctor
# ==============================
class Doctor(models.Model):

    senior = models.ForeignKey(
        SeniorProfile,
        on_delete=models.CASCADE,
        related_name='doctors'
    )

    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    clinic_address = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.name} ({self.specialty})"

class DailyActivity(models.Model):
    ACTIVITY_TYPES = [
        ('meal', 'Meal'),
        ('medicine', 'Medicine'),
        ('exercise', 'Exercise'),
        ('hygiene', 'Hygiene'),
        ('mood', 'Mood/Social'),
        ('rest', 'Rest/Sleep'),
        ('other', 'Other'),
    ]

    senior = models.ForeignKey(SeniorProfile, on_delete=models.CASCADE, related_name='daily_activities')
    caretaker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logged_activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.activity_type} for {self.senior.name} by {self.caretaker.username} at {self.timestamp}"

# ==============================
# VOLUNTEER SYSTEM MODELS
# ==============================

class HelpRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    senior = models.ForeignKey(SeniorProfile, on_delete=models.CASCADE, related_name='help_requests')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_help_requests', limit_choices_to={'user_type': 'family'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_volunteer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_help_requests', limit_choices_to={'user_type': 'volunteer'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.status}"

class VolunteerEmergency(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('handled', 'Handled'),
    )

    senior = models.ForeignKey(SeniorProfile, on_delete=models.CASCADE, related_name='volunteer_emergencies')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    assigned_volunteer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_emergencies', limit_choices_to={'user_type': 'volunteer'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Emergency: {self.senior.name} - {self.status}"

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"

class VolunteerRating(models.Model):
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_ratings', limit_choices_to={'user_type': 'volunteer'})
    family = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings', limit_choices_to={'user_type': 'family'})
    senior = models.ForeignKey(SeniorProfile, on_delete=models.CASCADE, related_name='volunteer_ratings', null=True, blank=True)
    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='ratings', null=True, blank=True)
    rating = models.PositiveIntegerField(default=5) # 1-5
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for {self.volunteer.username}: {self.rating}"
    
# ==============================
# Buddy AI Conversation Log
# ==============================
class BuddyMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buddy_messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} [{self.role}] at {self.created_at:%Y-%m-%d %H:%M}"
