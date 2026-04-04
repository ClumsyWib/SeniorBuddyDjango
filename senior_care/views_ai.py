import re
from openai import OpenAI
from decouple import config
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .ai_helpers import build_context_for_user, LANGUAGE_NAMES

BUDDY_SYSTEM_PROMPT = """
You are Buddy, a warm and caring AI companion designed specifically for elderly users.
You serve two equally important purposes:

1. COMPANIONSHIP — Be a genuine friend. Have relaxed, engaging conversations.
Share jokes, stories, fun facts, and nostalgia. Ask about their day, their family,
their interests, and their memories. Never make them feel like they are talking to
a machine. Celebrate small things with them.

2. HELPFUL ASSISTANT — When the user needs real help, switch naturally into a
helpful mode. This includes:
   - Health questions: symptoms, medications, side effects, when to see a doctor
   - Emergency guidance: what to do if they feel chest pain, dizziness, a fall, etc.
   - Daily tasks: reminders, simple how-tos, reading out information clearly
   - Family coordination: helping them compose a message to a family member
   - Mental wellness: if they seem sad, lonely, anxious, or confused — respond
     with patience and empathy, and gently suggest speaking to a family member
     or caregiver if needed

TONE & BEHAVIOR RULES:
- Always speak simply, warmly, and slowly. Avoid jargon.
- Never be dismissive. Elderly users may repeat themselves — respond with the
  same warmth every time.
- If a user mentions chest pain, difficulty breathing, severe dizziness, or
  any emergency — ALWAYS tell them to call emergency services or alert a
  family member immediately before anything else.
- Never diagnose. For health concerns, give general guidance and always
  recommend consulting their doctor.
- Seamlessly switch between companion mode and helper mode based on context.
  A user might go from chatting about their grandchildren to asking about a
  medication — handle both without making the transition feel abrupt.

You are not just an AI. You are Buddy — a patient, cheerful, reliable
presence in their day.
"""


def build_system_prompt(user):
    """Builds the full system prompt with injected user context and language."""
    context, language = build_context_for_user(user)
    language_name = LANGUAGE_NAMES.get(language, 'English')

    context_block = f"""
--- USER CONTEXT (use this to personalise your responses) ---
{context}
-------------------------------------------------------------
"""

    language_block = f"""
LANGUAGE INSTRUCTION:
Always respond in {language_name}. Use simple, warm language suitable for elderly users.
If the user writes in a different language, still respond in {language_name} unless
it is an emergency — in which case respond in whatever language is clearest.
"""

    return BUDDY_SYSTEM_PROMPT + context_block + language_block


def get_sarvam_client():
    return OpenAI(
        api_key=config('SARVAM_API_KEY'),
        base_url="https://api.sarvam.ai/v1"
    )


class BuddyAIChatView(APIView):
    """
    POST /api/ai-chat/

    Request body:
    {
        "message": "Hello Buddy!",
        "history": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! How are you today?"}
        ]
    }

    Response:
    {
        "reply": "Buddy's response here",
        "history": [...]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message', '').strip()
        history = request.data.get('history', [])

        if not user_message:
            return Response({'error': 'Message is required.'}, status=400)

        if not isinstance(history, list):
            history = []

        # Keep last 20 turns to avoid token limits
        if len(history) > 20:
            history = history[-20:]

        system_prompt = build_system_prompt(request.user)

        messages = [
            {"role": "system", "content": system_prompt}
        ] + history + [
            {"role": "user", "content": user_message}
        ]

        try:
            client = get_sarvam_client()
            response = client.chat.completions.create(
                model="sarvam-m",
                messages=messages,
            )

            reply = response.choices[0].message.content
            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()

            updated_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply}
            ]

            return Response({
                "reply": reply,
                "history": updated_history
            })

        except Exception as e:
            return Response(
                {'error': f'Buddy is unavailable right now. Please try again. ({str(e)})'},
                status=503
            )