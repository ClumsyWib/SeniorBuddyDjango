"""
# ==============================================================================
# FILE: urls.py
# PURPOSE: This is the "Traffic Cop" or "Map" of the Django Backend.
#
# Whenever the Flutter app asks for data from a URL (e.g., /api/users/), 
# this file decides which View in `views.py` should handle that request.
#
# KEY EXAM CONCEPTS:
# 1. DefaultRouter: A Django REST framework tool that automatically generates 
#    all standard URLs for a ViewSet (like /users/, /users/1/ for updates, etc.) 
#    without us having to type them all out manually.
# 2. urlpatterns: The master list of all valid website addresses/endpoints 
#    for the Senior Buddy backend.
# ==============================================================================

API URLs for Senior Care App
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views
from .view_ai import BuddyAIChatView

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'seniors', views.SeniorProfileViewSet, basename='senior')
router.register(r'caretakers', views.CaretakerProfileViewSet, basename='caretaker')
router.register(r'ngos', views.NGOViewSet, basename='ngo')
router.register(r'volunteers', views.VolunteerProfileViewSet, basename='volunteer')
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')
router.register(r'medicines', views.MedicineViewSet, basename='medicine')
router.register(r'medicine-logs', views.MedicineLogViewSet, basename='medicine-log')
router.register(r'tasks', views.VolunteerTaskViewSet, basename='task')
router.register(r'emergency-alerts', views.EmergencyAlertViewSet, basename='emergency-alert')
router.register(r'health-records', views.HealthRecordViewSet, basename='health-record')
router.register(r'emergency-contacts', views.EmergencyContactViewSet, basename='emergency-contact')
router.register(r'care-assignments', views.CareAssignmentViewSet, basename='care-assignment')
router.register(r'doctors', views.DoctorViewSet, basename='doctor')
router.register(r'daily-activities', views.DailyActivityViewSet, basename='daily-activity')
router.register(r'help-requests', views.HelpRequestViewSet, basename='help-request')
router.register(r'emergency', views.VolunteerEmergencyViewSet, basename='volunteer-emergency')
router.register(r'messages', views.ChatMessageViewSet, basename='message')
router.register(r'rating', views.VolunteerRatingViewSet, basename='rating')

urlpatterns = [
    # Authentication
    path('auth/login/', obtain_auth_token, name='api-login'),
    path('auth/register/', views.RegisterView.as_view(), name='api-register'),
    path('auth/logout/', views.LogoutView.as_view(), name='api-logout'),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('connect-senior/', views.SeniorProfileViewSet.as_view({'post': 'connect_senior'}), name='connect-senior'),
    path('volunteer/dashboard/', views.VolunteerDashboardView.as_view(), name='volunteer-dashboard'),

    # Senior Profile specific
    path('seniors/<int:pk>/update/', views.UpdateSeniorView.as_view(), name='senior-update'),
    path('senior/me/', views.MySeniorProfileView.as_view(), name='senior-me'),

    # AI Chatbot endpoint
    path('ai-chat/', BuddyAIChatView.as_view(), name='buddy-ai-chat'),

    # Language update endpoint
    path('update-language/', views.update_language, name='update-language'),
]