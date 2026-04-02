"""
API Views for Senior Care App
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import random


# ── Role constants matching Flutter's role_helper.dart ──────────────────────
ROLE_FAMILY = 'family'
ROLE_CARETAKER = 'caretaker'
ROLE_SENIOR = 'senior'
ROLE_ADMIN = 'admin'

# Django stores 'family' in user_type (set by registration role),
# but the actual value stored depends on how RegisterSerializer maps it.
# We check both 'family' and 'family_member' to be safe.
FAMILY_TYPES = {'family', 'family_member'}
CARETAKER_TYPES = {'caretaker'}
SENIOR_TYPES = {'senior'}
ADMIN_TYPES = {'admin', 'senior_admin', 'ngo_admin'}


def _permission_denied(action_label, allowed_role):
    """Return a standard 403 response."""
    return Response(
        {'error': f'Only {allowed_role}s can {action_label}.'},
        status=status.HTTP_403_FORBIDDEN,
    )


from .models import (
    User, SeniorProfile, CaretakerProfile, NGO, VolunteerProfile,
    CareAssignment, Appointment, Medicine, MedicineLog,
    VolunteerTask, EmergencyAlert, HealthRecord, EmergencyContact, Doctor, DailyActivity,
    HelpRequest, VolunteerEmergency, ChatMessage, VolunteerRating
)
from .serializers import (
    UserSerializer, RegisterSerializer, SeniorProfileSerializer,
    CaretakerProfileSerializer, NGOSerializer, VolunteerProfileSerializer,
    CareAssignmentSerializer, AppointmentSerializer, MedicineSerializer,
    MedicineLogSerializer, VolunteerTaskSerializer, EmergencyAlertSerializer,
    HealthRecordSerializer, EmergencyContactSerializer, DoctorSerializer, DailyActivitySerializer,
    HelpRequestSerializer, VolunteerEmergencySerializer, ChatMessageSerializer, VolunteerRatingSerializer
)


# Authentication Views
class RegisterView(generics.CreateAPIView):
    """
    Register a new user
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        try:
            # Only allow registration of certain roles
            role = request.data.get('user_type')
            if role == 'senior':
                return Response({'error': 'Seniors cannot register directly. Family members must create profiles for them.'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Create corresponding profile based on user_type
            if user.user_type == 'caretaker':
                CaretakerProfile.objects.create(user=user, phone=user.phone_number)
            elif user.user_type == 'volunteer':
                # Create a default NGO if none exist, so volunteers can register freely
                default_ngo, _ = NGO.objects.get_or_create(
                    name='General Volunteers',
                    defaults={
                        'registration_number': 'GEN-001',
                        'address': 'Platform Default',
                        'phone': '0000000000',
                        'email': 'volunteers@seniorbuddy.app',
                        'description': 'Default NGO for independent volunteers',
                        'is_verified': True,
                    }
                )
                import random, string
                vid = 'VOL-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                VolunteerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'ngo': default_ngo,
                        'volunteer_id': vid,
                        'is_available': True,
                    }
                )
            
            # Create token for user
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print("🔴 REGISTRATION CRASH:")
            print(traceback.format_exc())
            return Response({
                'error': f'Internal Server Error during registration: {str(e)}',
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(generics.GenericAPIView):
    """
    Logout user and delete token
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Delete user's token
        request.user.auth_token.delete()
        logout(request)
        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)


# User ViewSet
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User operations
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['user_type', 'is_active_user']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile"""
        # Fetch fresh user instance from DB to avoid any proxy/lazy object issues
        user = User.objects.get(pk=request.user.pk)
        
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
            
        print(f"DEBUG: Updating profile for user {user.username}")
        print(f"DEBUG: request.data: {request.data}")
        
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            user.refresh_from_db() # Force reload from database
            print(f"DEBUG: After save & refresh - Name: {user.first_name}, City: {user.city}")
            
            # Sync caretaker profile phone if applicable
            if hasattr(user, 'caretaker_profile') and 'phone_number' in request.data:
                user.caretaker_profile.phone = user.phone_number
                user.caretaker_profile.save()
                
            return Response(UserSerializer(user).data)
            
        print(f"DEBUG: Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user"""
        user = self.get_object()
        user.is_active_user = True
        user.is_active = True
        user.save()
        return Response({'message': 'User activated successfully.'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user"""
        user = self.get_object()
        user.is_active_user = False
        user.is_active = False
        user.save()
        return Response({'message': 'User deactivated successfully.'})


# Profile ViewSets
class SeniorProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for Senior Profiles"""
    queryset = SeniorProfile.objects.all()
    serializer_class = SeniorProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['mobility_status', 'care_level']
    search_fields = ['name', 'primary_doctor']

    def get_permissions(self):
        if self.action == 'connect_senior':
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(family_member=user)
        elif user.user_type == 'caretaker':
            # Caretaker can only see assigned seniors
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(id__in=assigned_senior_ids)
        elif user.is_superuser or user.is_staff or user.user_type in ['admin', 'senior_admin']:
            return self.queryset
        return self.queryset.none()

    def perform_create(self, serializer):
        # Generate a unique random 6-digit pair code
        while True:
            pair_code = str(random.randint(100000, 999999))
            if not SeniorProfile.objects.filter(pair_code=pair_code).exists():
                break
        
        print(f"DEBUG: Generated unique pair_code {pair_code} for user {self.request.user}")
        instance = serializer.save(family_member=self.request.user, pair_code=pair_code)
        print(f"DEBUG: Saved senior ID {instance.id} with pair_code {instance.pair_code}")

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def connect_senior(self, request):
        """Connect a senior device using a 6-digit pair code"""
        pair_code = request.data.get('pair_code')
        if not pair_code:
            return Response({'error': 'Pair code is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            senior = SeniorProfile.objects.get(pair_code=pair_code)
            senior.is_connected = True
            senior.save()
            
            # For simplicity, we return the family member's token.
            # In a production app, we might create a dedicated 'senior' user or a scoped token.
            token, created = Token.objects.get_or_create(user=senior.family_member)
            
            return Response({
                'status': 'connected',
                'token': token.key,
                'senior_id': senior.id,
                'senior_name': senior.name,
                'family_member': senior.family_member.username
            }, status=status.HTTP_200_OK)
        except SeniorProfile.DoesNotExist:
            return Response({'error': 'Invalid pair code.'}, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['post'])
    def regenerate_pair_code(self, request, pk=None):
        """Regenerate a unique 6-digit pair code for a senior"""
        senior = self.get_object()
        
        # Only the family member who manages this senior can regenerate the code
        if senior.family_member != request.user:
            return _permission_denied('regenerate connection code', 'managing family member')
        
        # Verify password
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password is required to regenerate the code.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(password):
            return Response({'error': 'Invalid password.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Generate a unique random 6-digit pair code
        while True:
            new_pair_code = str(random.randint(100000, 999999))
            if not SeniorProfile.objects.filter(pair_code=new_pair_code).exists():
                break
        
        senior.pair_code = new_pair_code
        senior.is_connected = False # Reset connection status if code is regenerated? 
        # Actually, user said "if they forgot code or want to new", 
        # it's better to keep existing connection if any, but since the code changed, 
        # maybe we should allow existing devices to stay connected or force re-connection.
        # User requirement: "generate new one", usually implies old one is compromised or lost.
        senior.save()
        
        print(f"DEBUG: Regenerated pair_code {senior.pair_code} for senior {senior.name}")
        
        return Response({
            'pair_code': senior.pair_code,
            'message': 'New connection code generated successfully.'
        }, status=status.HTTP_200_OK)


class CaretakerProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for Caretaker Profiles"""
    queryset = CaretakerProfile.objects.all()
    serializer_class = CaretakerProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_available', 'background_check_completed']
    search_fields = ['user__first_name', 'user__last_name', 'skills']
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available caretakers"""
        caretakers = self.queryset.filter(is_available=True)
        serializer = self.get_serializer(caretakers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update current caretaker's profile"""
        try:
            profile = CaretakerProfile.objects.get(user=request.user)
            if request.method == 'PATCH':
                serializer = self.get_serializer(profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except CaretakerProfile.DoesNotExist:
            return Response({'error': 'Caretaker profile not found.'}, status=404)


class VolunteerProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for Volunteer Profiles"""
    queryset = VolunteerProfile.objects.all()
    serializer_class = VolunteerProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['ngo', 'is_available', 'background_check_completed']
    search_fields = ['user__first_name', 'user__last_name', 'volunteer_id']

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update current volunteer's profile"""
        try:
            profile = VolunteerProfile.objects.get(user=request.user)
            if request.method == 'PATCH':
                serializer = self.get_serializer(profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except VolunteerProfile.DoesNotExist:
            return Response({'error': 'Volunteer profile not found.'}, status=404)


# NGO ViewSet
class NGOViewSet(viewsets.ModelViewSet):
    """ViewSet for NGOs"""
    queryset = NGO.objects.all()
    serializer_class = NGOSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_verified']
    search_fields = ['name', 'registration_number', 'email']
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify an NGO"""
        ngo = self.get_object()
        ngo.is_verified = True
        ngo.save()
        return Response({'message': 'NGO verified successfully.'})


# Care Assignment ViewSet
class CareAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Care Assignments"""
    queryset = CareAssignment.objects.all()
    serializer_class = CareAssignmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['senior', 'caretaker', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type == 'caretaker':
            return self.queryset.filter(caretaker=user)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Family Members can assign caretakers
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('assign caretakers', 'family member')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=False, methods=['get'])
    def my_caretaker(self, request):
        senior_id = request.query_params.get('senior')
        user = request.user
        
        queryset = self.get_queryset().filter(is_active=True)
        if senior_id:
            queryset = queryset.filter(senior_id=senior_id)
            
        assignment = queryset.first()
        if not assignment or not assignment.caretaker:
            return Response({'error': 'No active caretaker assigned.'}, status=404)
            
        caretaker = assignment.caretaker
        
        # Determine photo URL
        photo_url = None
        if caretaker.profile_picture:
            photo_url = request.build_absolute_uri(caretaker.profile_picture.url)

        return Response({
            'id': caretaker.id,
            'name': caretaker.get_full_name() or caretaker.username,
            'phone': caretaker.phone_number,
            'photo': photo_url,
            'specialization': 'General Care',  # default or add to user model
            'rating': 4.8,  # mock or real
            'experience': '5+ years',
            'schedule': 'Flexible',
            'start_date': assignment.start_date,
        })


# Emergency Contact ViewSet
class EmergencyContactViewSet(viewsets.ModelViewSet):
    """ViewSet for Emergency Contacts"""
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['senior', 'is_primary']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        elif user.user_type in SENIOR_TYPES:
            return self.queryset.filter(senior__id=user.id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Family Members can add emergency contacts
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('add emergency contacts', 'family member')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('edit emergency contacts', 'family member')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('delete emergency contacts', 'family member')
        return super().destroy(request, *args, **kwargs)


# Appointment ViewSet
class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Appointments"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'appointment_type', 'senior', 'caretaker']
    search_fields = ['title', 'doctor_name', 'location']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        elif user.user_type in SENIOR_TYPES:
            return self.queryset.filter(senior__id=user.id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Family Members can create appointments
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('create appointments', 'family member')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('edit appointments', 'family member')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('delete appointments', 'family member')
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        today = timezone.now().date()
        appointments = self.filter_queryset(self.get_queryset()).filter(
            appointment_date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date', 'appointment_time')
        
        page = self.paginate_queryset(appointments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'confirmed'
        appointment.save()
        return Response({'message': 'Appointment confirmed.'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'completed'
        appointment.save()
        return Response({'message': 'Appointment marked as completed.'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        return Response({'message': 'Appointment cancelled.'})


# Medicine ViewSets
class MedicineViewSet(viewsets.ModelViewSet):
    """ViewSet for Medicines"""
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'senior', 'frequency']
    search_fields = ['medicine_name']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        elif user.user_type in SENIOR_TYPES:
            return self.queryset.filter(senior__id=user.id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Family Members can add medicines
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('add medicines', 'family member')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('edit medicines', 'family member')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('delete medicines', 'family member')
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        medicines = self.filter_queryset(self.get_queryset()).filter(is_active=True)
        serializer = self.get_serializer(medicines, many=True)
        return Response(serializer.data)


class MedicineLogViewSet(viewsets.ModelViewSet):
    """ViewSet for Medicine Logs"""
    queryset = MedicineLog.objects.all()
    serializer_class = MedicineLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['was_taken', 'medicine__senior']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(medicine__senior__family_member=user)
        elif user.user_type == 'caretaker':
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(medicine__senior_id__in=assigned_senior_ids)
        return self.queryset
    
    @action(detail=True, methods=['post'])
    def mark_taken(self, request, pk=None):
        log = self.get_object()
        log.was_taken = True
        log.actual_time = timezone.now()
        log.confirmed_by = request.user
        log.save()
        return Response({'message': 'Medicine marked as taken.'})


# Volunteer Task ViewSet
class VolunteerTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Volunteer Tasks"""
    queryset = VolunteerTask.objects.all()
    serializer_class = VolunteerTaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'volunteer', 'ngo']
    search_fields = ['title']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'volunteer':
            return self.queryset.filter(volunteer=user)
        elif user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        return self.queryset
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        tasks = self.get_queryset().filter(
            status__in=['assigned', 'accepted', 'in_progress', 'assigned']
        ).order_by('scheduled_date')
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        task = self.get_object()
        task.status = 'accepted'
        task.save()
        return Response({'message': 'Task accepted.'})
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a task"""
        task = self.get_object()
        task.status = 'in_progress'
        task.actual_start_time = timezone.now()
        task.save()
        return Response({'message': 'Task started.'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.actual_end_time = timezone.now()
        task.save()
        return Response({'message': 'Task completed successfully.'})


# Emergency Alert ViewSet
class EmergencyAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for Emergency Alerts"""
    queryset = EmergencyAlert.objects.all()
    serializer_class = EmergencyAlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_resolved', 'alert_type', 'senior']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type == 'caretaker':
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        return self.queryset

    @action(detail=False, methods=['get'])
    def active(self, request):
        alerts = self.get_queryset().filter(is_resolved=False).order_by('-alert_time')
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.save()
        return Response({'message': 'Alert resolved successfully.'})


# Health Record ViewSet
class HealthRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for Health Records"""
    queryset = HealthRecord.objects.all()
    serializer_class = HealthRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['senior', 'record_date']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        elif user.user_type in SENIOR_TYPES:
            return self.queryset.filter(senior__id=user.id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Caretakers can record vitals/health records
        if request.user.user_type not in CARETAKER_TYPES:
            return _permission_denied('record health vitals', 'caretaker')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in CARETAKER_TYPES:
            return _permission_denied('edit health records', 'caretaker')
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


# Doctor ViewSet
class DoctorViewSet(viewsets.ModelViewSet):
    """ViewSet for Doctors"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['senior']
    search_fields = ['name', 'specialty']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            assigned_senior_ids = CareAssignment.objects.filter(caretaker=user, is_active=True).values_list('senior_id', flat=True)
            return self.queryset.filter(senior_id__in=assigned_senior_ids)
        elif user.user_type in SENIOR_TYPES:
            return self.queryset.filter(senior__id=user.id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Only Family Members can add doctors
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('add doctors', 'family member')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('edit doctors', 'family member')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('delete doctors', 'family member')
        return super().destroy(request, *args, **kwargs)





# Dashboard Stats View
class DashboardStatsView(generics.GenericAPIView):
    """
    Get dashboard statistics based on user type
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        stats = {}
        
        if user.user_type in FAMILY_TYPES:
            stats = self._get_family_stats(user)
        elif user.user_type == 'caretaker':
            stats = self._get_caretaker_stats(user)
        elif user.user_type == 'volunteer':
            stats = self._get_volunteer_stats(user)
        elif user.user_type in ADMIN_TYPES or user.is_superuser or user.is_staff:
            stats = self._get_admin_stats(user)
        
        return Response(stats)
    
    def _get_family_stats(self, user):
        """Statistics for family managing seniors"""
        today = timezone.now().date()
        seniors = SeniorProfile.objects.filter(family_member=user)
        senior_ids = seniors.values_list('id', flat=True)

        return {
            'managed_seniors': seniors.count(),
            'upcoming_appointments': Appointment.objects.filter(
                senior_id__in=senior_ids, 
                appointment_date__gte=today,
                status__in=['scheduled', 'confirmed']
            ).count(),
            'active_medicines': Medicine.objects.filter(
                senior_id__in=senior_ids, 
                is_active=True
            ).count(),
            'active_alerts': EmergencyAlert.objects.filter(
                senior_id__in=senior_ids,
                is_resolved=False
            ).count(),
            'active_alerts': EmergencyAlert.objects.filter(
                senior_id__in=senior_ids,
                is_resolved=False
            ).count(),
        }
    
    def _get_caretaker_stats(self, user):
        """Statistics for caretakers"""
        return {
            'assigned_seniors': CareAssignment.objects.filter(
                caretaker=user, 
                is_active=True
            ).count(),
            'today_appointments': Appointment.objects.filter(
                caretaker=user,
                appointment_date=timezone.now().date()
            ).count(),
        }
    
    def _get_volunteer_stats(self, user):
        """Statistics for volunteers"""
        try:
            profile = VolunteerProfile.objects.get(user=user)
            return {
                'total_hours': profile.total_hours,
                'pending_tasks': VolunteerTask.objects.filter(
                    volunteer=user,
                    status__in=['assigned', 'accepted']
                ).count(),
            }
        except VolunteerProfile.DoesNotExist:
            return {}
    
    def _get_admin_stats(self, user):
        """Statistics for all admin types"""
        today = timezone.now().date()
        return {
            'total_users': User.objects.count(),
            'total_families': User.objects.filter(user_type='family').count(),
            'total_seniors': SeniorProfile.objects.count(),
            'total_caretakers': User.objects.filter(user_type='caretaker').count(),
            'total_volunteers': User.objects.filter(user_type='volunteer').count(),
            'active_assignments': CareAssignment.objects.filter(is_active=True).count(),
            'active_alerts': EmergencyAlert.objects.filter(is_resolved=False).count(),
            'total_appointments': Appointment.objects.count(),
            'upcoming_appointments': Appointment.objects.filter(
                appointment_date__gte=today, status='scheduled'
            ).count(),
            'total_medicines': Medicine.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active_user=False).count(),
        }

class DailyActivityViewSet(viewsets.ModelViewSet):
    serializer_class = DailyActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        senior_id = self.request.query_params.get('senior_id')
        
        # Superusers and staff see everything
        if user.is_superuser or user.is_staff or user.user_type in ADMIN_TYPES:
            queryset = DailyActivity.objects.all()
        elif user.user_type in FAMILY_TYPES:
            # Family members can VIEW activities for their seniors
            queryset = DailyActivity.objects.filter(senior__family_member=user)
        elif user.user_type in CARETAKER_TYPES:
            # Caretakers see activities they logged OR activities for assigned seniors
            assigned_seniors = CareAssignment.objects.filter(caretaker=user).values_list('senior_id', flat=True)
            queryset = DailyActivity.objects.filter(Q(caretaker=user) | Q(senior_id__in=assigned_seniors))
        elif user.user_type in SENIOR_TYPES:
            # Seniors can view their own activities
            queryset = DailyActivity.objects.filter(senior__id=user.id)
        else:
            queryset = DailyActivity.objects.none()

        if senior_id:
            queryset = queryset.filter(senior_id=senior_id)
            
        return queryset

    def create(self, request, *args, **kwargs):
        # Only Caretakers can log daily activities
        if request.user.user_type not in CARETAKER_TYPES:
            return _permission_denied('log daily activities', 'caretaker')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in CARETAKER_TYPES:
            return _permission_denied('edit daily activities', 'caretaker')
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(caretaker=self.request.user)




# ── Senior Profile Specific Views ──────────────────────────────────────────

class UpdateSeniorView(generics.UpdateAPIView):
    """View for Family Member to update Senior Profile"""
    serializer_class = SeniorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES or user.is_superuser:
            return SeniorProfile.objects.filter(family_member=user)
        return SeniorProfile.objects.none()

class MySeniorProfileView(generics.RetrieveAPIView):
    """View for Senior to view their own profile"""
    serializer_class = SeniorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return SeniorProfile.objects.get(user=self.request.user)
        except SeniorProfile.DoesNotExist:
            # Fallback: if family member is logged in and looking for their managed senior
            # this might not be what's intended, but let's stick to the user's requirement.
            from django.http import Http404
            raise Http404("Senior profile not found for this user.")

# ==============================
# VOLUNTEER SYSTEM VIEWS
# ==============================

class HelpRequestViewSet(viewsets.ModelViewSet):
    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in FAMILY_TYPES:
            return self.queryset.filter(created_by=user)
        elif user.user_type == 'volunteer':
            status_filter = self.request.query_params.get('status')
            if status_filter == 'pending':
                return self.queryset.filter(status='pending')
            elif status_filter == 'accepted':
                return self.queryset.filter(assigned_volunteer=user, status='accepted')
            elif status_filter == 'completed':
                # Show both completed and verified as "Completed" for the volunteer
                return self.queryset.filter(assigned_volunteer=user, status__in=['completed', 'verified'])
            elif status_filter == 'all':
                return self.queryset.filter(Q(status='pending') | Q(assigned_volunteer=user))
            
            # Default: return everything relevant to the volunteer
            return self.queryset.filter(Q(status='pending') | Q(assigned_volunteer=user))
        return self.queryset

    def perform_create(self, serializer):
        if self.request.user.user_type not in FAMILY_TYPES:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only family members can create help requests.")
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('view my requests', 'family member')
        requests = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        if request.user.user_type != 'volunteer':
            return _permission_denied('accept help requests', 'volunteer')
        request_obj = self.get_object()
        if request_obj.status != 'pending':
            return Response({'error': 'Request is no longer pending.'}, status=status.HTTP_400_BAD_REQUEST)
        request_obj.status = 'accepted'
        request_obj.assigned_volunteer = request.user
        request_obj.save()
        return Response({'message': 'Request accepted.'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        if request.user.user_type != 'volunteer':
            return _permission_denied('mark requests as completed', 'volunteer')
        request_obj = self.get_object()
        if request_obj.assigned_volunteer != request.user:
            return Response({'error': 'You are not assigned to this request.'}, status=status.HTTP_403_FORBIDDEN)
        request_obj.status = 'completed'
        request_obj.save()
        return Response({'message': 'Request marked as completed.'})

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('verify requests', 'family member')
        request_obj = self.get_object()
        if request_obj.created_by != request.user:
            return Response({'error': 'You did not create this request.'}, status=status.HTTP_403_FORBIDDEN)
        request_obj.status = 'verified'
        request_obj.save()
        return Response({'message': 'Request verified.'})


class VolunteerEmergencyViewSet(viewsets.ModelViewSet):
    queryset = VolunteerEmergency.objects.all()
    serializer_class = VolunteerEmergencySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'volunteer':
            status_filter = self.request.query_params.get('status')
            if status_filter == 'active':
                return self.queryset.filter(status='active')
            return self.queryset.filter(Q(status='active') | Q(assigned_volunteer=user))
        return self.queryset

    def perform_create(self, serializer):
        # Senior triggers emergency. We need to find the SeniorProfile.
        try:
            senior_profile = SeniorProfile.objects.get(user=self.request.user)
        except SeniorProfile.DoesNotExist:
            # Fallback for family member triggering for senior (though user said senior triggers)
            senior_id = self.request.data.get('senior')
            if senior_id:
                senior_profile = SeniorProfile.objects.get(id=senior_id)
            else:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Only seniors can trigger emergency alerts.")
        
        serializer.save(senior=senior_profile)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        if request.user.user_type != 'volunteer':
            return _permission_denied('accept emergency alerts', 'volunteer')
        alert = self.get_object()
        if alert.status != 'active':
            return Response({'error': 'Alert is no longer active.'}, status=status.HTTP_400_BAD_REQUEST)
        alert.status = 'handled'
        alert.assigned_volunteer = request.user
        alert.save()
        return Response({'message': 'Alert accepted.'})


class ChatMessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='send')
    def send_message(self, request):
        receiver_id = request.data.get('receiver')
        message_text = request.data.get('message')
        if not receiver_id or not message_text:
            return Response({'error': 'Receiver and message are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response({'error': 'Receiver not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        chat_msg = ChatMessage.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message_text
        )
        return Response(ChatMessageSerializer(chat_msg).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """Override retrieve to fetch conversation"""
        return self.conversation(request, pk)

    @action(detail=True, methods=['get'], url_path='')
    def conversation(self, request, pk=None):
        """Fetch conversation with user pk"""
        try:
            peer_id = int(pk)
        except (ValueError, TypeError):
            print(f"DEBUG ERROR: Invalid peer ID {pk}")
            return Response([], status=200)

        print(f"DEBUG: Fetching chat for User {request.user.id} with Peer {peer_id}")
        
        messages = ChatMessage.objects.filter(
            (Q(sender_id=request.user.id) & Q(receiver_id=peer_id)) |
            (Q(sender_id=peer_id) & Q(receiver_id=request.user.id))
        ).order_by('timestamp')
        
        count = messages.count()
        print(f"DEBUG: Found {count} messages")
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)


class VolunteerRatingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='')
    def give_rating(self, request):
        if request.user.user_type not in FAMILY_TYPES:
            return _permission_denied('give ratings', 'family member')
            
        volunteer_id = request.data.get('volunteer')
        rating_value = request.data.get('rating')
        feedback = request.data.get('feedback', '')
        help_request_id = request.data.get('help_request')
        senior_id = request.data.get('senior')
        
        if not volunteer_id or not rating_value:
            return Response({'error': 'Volunteer and rating are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            volunteer = User.objects.get(id=volunteer_id, user_type='volunteer')
        except User.DoesNotExist:
            return Response({'error': 'Volunteer not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        # If we have a help_request, use it for uniqueness (one rating per request)
        if help_request_id:
            rating, created = VolunteerRating.objects.update_or_create(
                volunteer=volunteer,
                family=request.user,
                help_request_id=help_request_id,
                defaults={'rating': rating_value, 'feedback': feedback, 'senior_id': senior_id}
            )
        else:
            # Fallback to general rating if no help_request provided
            rating = VolunteerRating.objects.create(
                volunteer=volunteer,
                family=request.user,
                rating=rating_value,
                feedback=feedback,
                senior_id=senior_id
            )
        
        # Update volunteer profile average rating
        avg_rating = VolunteerRating.objects.filter(volunteer=volunteer).aggregate(Avg('rating'))['rating__avg']
        
        # Ensure profile exists and update rating
        profile, _ = VolunteerProfile.objects.get_or_create(user=volunteer)
        profile.rating = avg_rating if avg_rating is not None else 0.00
        profile.save()

        return Response(VolunteerRatingSerializer(rating).data)

    @action(detail=True, methods=['get'], url_path='rating')
    def volunteer_rating(self, request, pk=None):
        avg_rating = VolunteerRating.objects.filter(volunteer_id=pk).aggregate(Avg('rating'))['rating__avg'] or 0.0
        return Response({'volunteer_id': pk, 'average_rating': avg_rating})


class VolunteerDashboardView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'volunteer':
            return _permission_denied('view volunteer dashboard', 'volunteer')
            
        user = request.user
        print(f"DEBUG: VolunteerDashboard for {user.username} (ID: {user.id})")
        
        # Accepted: assigned to me and status is 'accepted'
        accepted_tasks = HelpRequest.objects.filter(assigned_volunteer=user, status='accepted').count()
        # Completed: assigned to me and status is either 'completed' or 'verified'
        completed_tasks = HelpRequest.objects.filter(assigned_volunteer=user, status__in=['completed', 'verified']).count()
        # Emergencies: handled or currently active assigned to me? 
        # User screenshot showed '3 Emergencies'. Let's count all assigned to me.
        emergencies_handled = VolunteerEmergency.objects.filter(assigned_volunteer=user).count()
        # Pending: All requests that are still pending (visible to all volunteers)
        pending_tasks = HelpRequest.objects.filter(status='pending').count()
        
        print(f"DEBUG: accepted={accepted_tasks}, completed={completed_tasks}, emergencies={emergencies_handled}, pending={pending_tasks}")
        
        # Get rating directly from profile or calculate
        avg_rating = 0.0
        try:
            profile = getattr(user, 'volunteer_profile', None)
            if profile:
                avg_rating = float(profile.rating)
                print(f"DEBUG: Rating from profile: {avg_rating}")
            else:
                avg_rating = VolunteerRating.objects.filter(volunteer=user).aggregate(Avg('rating'))['rating__avg'] or 0.0
                print(f"DEBUG: Rating calculated: {avg_rating}")
        except Exception as e:
            print(f"DEBUG: Rating calculation error: {e}")
            avg_rating = 0.0

        return Response({
            'accepted_tasks': accepted_tasks,
            'completed_tasks': completed_tasks,
            'emergencies_handled': emergencies_handled,
            'pending_tasks': pending_tasks,
            'average_rating': avg_rating
        })
