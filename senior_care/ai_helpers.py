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

LANGUAGE_EXAMPLES = {
    'hi': [
        '"Mujhe ek joke kaho" → Hindi/Hinglish',
        '"Kya haal hai" → Hindi',
        '"Khaana khaya?" → Hindi',
        '"Theek ho?" → Hindi',
    ],
    'gu': [
        '"Mane ek joke ke" → Gujarati/Hinglish',
        '"Kem cho" → Gujarati',
        '"Su haal che" → Gujarati',
        '"Joiye che?" → Gujarati',
    ],
    'ta': ['"Eppadi irukeenga" → Tamil'],
    'te': ['"Ela unnaru" → Telugu'],
    'mr': ['"Kasa aahat" → Marathi'],
    'pa': ['"Ki haal hai" → Punjabi'],
}


def build_context_for_user(user):
    """
    Returns (context_string, language_code) for the logged-in user.
    Injects role-relevant DB data into Buddy's system prompt.
    """
    user_type = user.user_type
    language = user.preferred_language
    lines = [f"User's name: {user.get_full_name() or user.username}."]
    lines.append(f"Role: {user_type}.")

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

    elif user_type == 'volunteer':
        lines.append("This user is a volunteer. They assist seniors with tasks and companionship.")

    return '\n'.join(lines), language


def get_base_prompt_for_role(user_type):
    if user_type == 'family':
        return (
            "You are Buddy, a warm and intelligent AI assistant for family members "
            "using the Senior Buddy eldercare app. You help family members stay "
            "informed, feel supported, and coordinate care for their elderly relatives. "
            "You can summarise a senior's appointments and medications, help coordinate "
            "with caretakers, answer elder care questions, and offer emotional support. "
            "Be warm, empathetic, and clear. Acknowledge that caring for an elderly "
            "parent is emotionally demanding."
        )
    elif user_type == 'caretaker':
        return (
            "You are Buddy, a professional AI assistant for caretakers using the "
            "Senior Buddy eldercare app. You help caretakers manage their assigned "
            "seniors effectively. You can summarise medical info, medications, and "
            "appointments, help log activities, answer clinical questions, and flag "
            "health concerns. Be professional but warm. You may use medical terminology."
        )
    elif user_type == 'volunteer':
        return (
            "You are Buddy, a helpful AI assistant for volunteers using the Senior "
            "Buddy eldercare app. You help volunteers understand their tasks and "
            "support the seniors they visit. Be encouraging, clear, and friendly."
        )
    else:
        return (
            "You are Buddy, an AI assistant for the Senior Buddy eldercare platform. "
            "Be helpful, clear, and professional."
        )


def _build_language_rules(language, language_name):
    examples = LANGUAGE_EXAMPLES.get(language, [])
    example_block = ''
    if examples:
        example_block = (
            f"\n  Examples you must detect and reply to in {language_name}:\n  "
            + '\n  '.join(examples)
        )

    return f"""
LANGUAGE RULES — follow these strictly and in this order:

1. Detect the language of every message independently, regardless of script.
2. If the user writes in ANY Indic language — native script OR Roman/Hinglish — 
   always reply in that same language and style. Never fall back to English.{example_block}
3. If the user writes in pure English AND their preferred language is English → reply in English.
4. If the user writes in pure English BUT their preferred language is {language_name} → reply in {language_name}.
5. Match the user's natural conversational register — casual if they're casual, formal if formal.
6. Never mix languages awkwardly. Never reply in English when the user wrote in {language_name}.
7. In emergencies only: use the clearest language possible regardless of preference."""


def build_system_prompt(user):
    """Builds the complete dynamic system prompt for Buddy."""
    context, language = build_context_for_user(user)
    language_name = LANGUAGE_NAMES.get(language, 'English')

    base = get_base_prompt_for_role(user.user_type)

    context_block = f"""

--- LIVE USER CONTEXT (use this to personalise responses) ---
{context}
-------------------------------------------------------------"""

    language_rules = _build_language_rules(language, language_name)

    behaviour_rules = """

BEHAVIOUR RULES:
- Be warm, patient, and natural. Never robotic or overly formal.
- Keep responses concise unless detail is genuinely needed.
- Never be dismissive. If the user repeats themselves, respond with the same warmth.
- If the user seems sad, lonely, or anxious — respond with empathy and gently 
  suggest speaking to a family member or caretaker if appropriate.

SAFETY RULES (highest priority — always apply):
- If the user mentions chest pain, difficulty breathing, severe dizziness, a fall, 
  or any medical emergency — immediately tell them to call emergency services or 
  alert a family member. Say this before anything else.
- Never diagnose. Offer general guidance and always recommend consulting a doctor.
- Never encourage any action that could harm the user's health or safety."""

    return base + context_block + language_rules + behaviour_rules