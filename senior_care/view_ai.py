import re
from openai import OpenAI
from decouple import config
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from .ai_helpers import build_system_prompt
from .models import BuddyMessage


def get_sarvam_client():
    return OpenAI(
        api_key=config('SARVAM_API_KEY'),
        base_url="https://api.sarvam.ai/v1"
    )


def is_rate_limited(user_id):
    """Simple cache-based rate limit: max 30 requests per minute per user."""
    key = f'buddy_rate_{user_id}'
    count = cache.get(key, 0)
    if count >= 30:
        return True
    cache.set(key, count + 1, timeout=60)
    return False


def validate_history(history):
    """Sanitise history from client — reject bad entries."""
    if not isinstance(history, list):
        return []
    clean = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get('role', '')
        content = item.get('content', '')
        if role not in ('user', 'assistant'):
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        clean.append({'role': role, 'content': content[:2000]})
    return clean[-10:]  # keep last 10 turns max


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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if is_rate_limited(user.id):
            return Response(
                {'error': 'Too many messages. Please wait a moment before sending another.'},
                status=429
            )

        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'Message is required.'}, status=400)

        history = validate_history(request.data.get('history', []))
        system_prompt = build_system_prompt(user)

        messages = [
            {'role': 'system', 'content': system_prompt}
        ] + history + [
            {'role': 'user', 'content': user_message}
        ]

        try:
            client = get_sarvam_client()
            response = client.chat.completions.create(
                model='sarvam-m',
                messages=messages,
            )

            reply = response.choices[0].message.content
            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()

            # Fallback if stripping leaves empty reply
            if not reply:
                reply = response.choices[0].message.content.strip()

            # Log to DB for mood tracking / daily summaries later
            BuddyMessage.objects.create(user=user, role='user', content=user_message)
            BuddyMessage.objects.create(user=user, role='assistant', content=reply)

            updated_history = history + [
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': reply},
            ]

            return Response({
                'reply': reply,
                'history': updated_history,
            })

        except Exception as e:
            return Response(
                {'error': f'Buddy is unavailable right now. Please try again. ({str(e)})'},
                status=503
            )