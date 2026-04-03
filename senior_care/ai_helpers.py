from django.utils import timezone
from .models import SeniorProfile, CareAssignment, Appointment, Medicine

LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'Hindi',
    'gu': 'Gujarati',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'bn': 'Bengali',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
}


def get_base_prompt_for_role(user_type):
    if user_type == 'family':
        return """
You are Buddy, a warm and caring AI assistant for family members using the Senior Buddy app.
You help family members stay informed and feel supported while managing the care of their elderly relatives.
You can:
- Summarise a senior's upcoming appointments, medications, and health notes
- Help them coordinate with caretakers or volunteers
- Answer general elder care questions in plain, clear language
- Offer reassurance and emotional support — family members are often anxious and juggling a lot
Be warm, empathetic, and clear. Acknowledge the emotional weight of caring for an elderly parent.
"""
    elif user_type == 'caretaker':
        return """
You are Buddy, a professional AI assistant for caretakers using the Senior Buddy app.
You help caretakers do their job effectively and stay on top of their responsibilities.
You can:
- Summarise a senior's medical info, medications, and upcoming appointments
- Help log activities or draft notes
- Answer clinical or caregiving questions clearly and directly
- Flag potential concerns about a senior's reported condition
Speak professionally but warmly. You can use medical terminology — caretakers are trained professionals.
"""
    elif user_type == 'volunteer':
        return """
You are Buddy, a helpful AI assistant for volunteers using the Senior Buddy app.
You help volunteers understand their tasks and support the seniors they visit.
You can:
- Summarise upcoming volunteer tasks
- Answer general questions about elder companionship and support
- Help volunteers communicate clearly with the family members they work with
Be encouraging, clear, and friendly.
"""
    else:
        return """
You are Buddy, an AI assistant for the Senior Buddy eldercare platform.
Be helpful, clear, and professional.
"""


def build_context_for_user(user):
    """
    Returns (context_string, language_code) for the logged-in user.
    Injects role-relevant DB data into Buddy's system prompt.
    """
    user_type = user.user_type
    language = user.preferred_language
    lines = [f"The user's name is {user.get_full_name() or user.username}."]
    lines.append(f"Their role is: {user_type}.")

    today = timezone.now().date()

    if user_type == 'family':
        seniors = SeniorProfile.objects.filter(
            family_member=user
        ).values('name', 'age', 'medical_conditions', 'allergies')[:3]

        if seniors:
            for s in seniors:
                line = f"Managed senior: {s['name']}, age {s['age']}."
                if s['medical_conditions']:
                    line += f" Conditions: {s['medical_conditions'][:200]}."
                if s['allergies']:
                    line += f" Allergies: {s['allergies'][:100]}."
                lines.append(line)

            senior_ids = SeniorProfile.objects.filter(
                family_member=user
            ).values_list('id', flat=True)

            upcoming = Appointment.objects.filter(
                senior_id__in=senior_ids,
                appointment_date=today,
                status='scheduled'
            ).values('title', 'appointment_time', 'senior__name')[:3]

            if upcoming:
                appt_list = ', '.join(
                    f"{a['title']} for {a['senior__name']} at {a['appointment_time'].strftime('%I:%M %p')}"
                    for a in upcoming
                )
                lines.append(f"Today's appointments: {appt_list}.")

    elif user_type == 'caretaker':
        assignments = CareAssignment.objects.filter(
            caretaker=user,
            is_active=True
        ).select_related('senior')[:3]

        if assignments:
            for a in assignments:
                s = a.senior
                line = f"Assigned senior: {s.name}, age {s.age}."
                if s.medical_conditions:
                    line += f" Conditions: {s.medical_conditions[:200]}."
                lines.append(line)

            senior_ids = [a.senior_id for a in assignments]

            upcoming = Appointment.objects.filter(
                senior_id__in=senior_ids,
                appointment_date=today,
                status='scheduled'
            ).values('title', 'appointment_time', 'senior__name')[:3]

            if upcoming:
                appt_list = ', '.join(
                    f"{a['title']} for {a['senior__name']} at {a['appointment_time'].strftime('%I:%M %p')}"
                    for a in upcoming
                )
                lines.append(f"Today's appointments: {appt_list}.")

    return '\n'.join(lines), language


def build_system_prompt(user):
    """Builds the full dynamic system prompt for Buddy."""
    context, language = build_context_for_user(user)
    language_name = LANGUAGE_NAMES.get(language, 'English')
    base = get_base_prompt_for_role(user.user_type)

    context_block = f"""
--- USER CONTEXT (use this to personalise your responses) ---
{context}
-------------------------------------------------------------
"""

    language_block = f"""
LANGUAGE INSTRUCTION:
The user's preferred language is {language_name}.
- If they write in their preferred language or a mix, respond in that same style.
- If they write casual Roman-script Hindi/Gujarati (Hinglish etc.), match their style.
- If they write in English, respond in English unless their preference is non-English,
  in which case gently mirror their preferred language.
- In an emergency, always respond in the clearest language possible.
"""

    return base + context_block + language_block