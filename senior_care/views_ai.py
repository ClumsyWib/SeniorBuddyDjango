import re
import json
from openai import OpenAI
from decouple import config
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .ai_helpers import build_system_prompt


def get_sarvam_client():
    return OpenAI(api_key=config('SARVAM_API_KEY'), base_url="https://api.sarvam.ai/v1")


def _execute_action(user, action_data, active_senior_id=None):
    from .models import SeniorProfile, Appointment, Medicine, EmergencyAlert, CareAssignment

    action_type = action_data.get('type')
    # Flutter-pinned senior_id takes priority over AI-guessed one
    senior_id = active_senior_id or action_data.get('senior_id')
    if not senior_id:
        return False, 'No senior specified.'

    try:
        if user.user_type in ('family',):
            senior = SeniorProfile.objects.get(id=senior_id, family_member=user)
        elif user.user_type == 'caretaker':
            assignment = CareAssignment.objects.get(senior_id=senior_id, caretaker=user, is_active=True)
            senior = assignment.senior
        else:
            return False, 'Action not permitted for volunteers.'

        if action_type == 'create_appointment':
            if user.user_type not in ('family',):
                return False, 'Only family members can create appointments.'
            Appointment.objects.create(
                senior=senior,
                title=action_data.get('title', 'Appointment'),
                appointment_date=action_data['date'],
                appointment_time=action_data['time'],
                status='scheduled',
            )
            return True, f"Appointment '{action_data.get('title')}' scheduled for {action_data['date']} at {action_data['time']}."

        elif action_type == 'create_medicine':
            Medicine.objects.create(
                senior=senior,
                medicine_name=action_data.get('medicine_name', ''),
                dosage=action_data.get('dosage', ''),
                frequency=action_data.get('frequency', 'daily'),
                start_date=action_data.get('start_date', timezone.now().date()),
                is_active=True,
            )
            return True, f"Medicine '{action_data.get('medicine_name')}' added successfully."

        elif action_type == 'sos':
            EmergencyAlert.objects.create(
                senior=senior,
                alert_type='sos',
                is_resolved=False,
            )
            return True, f"SOS alert triggered for {senior.name}."

        return False, f"Unknown action: {action_type}"

    except SeniorProfile.DoesNotExist:
        return False, 'Senior not found or access denied.'
    except CareAssignment.DoesNotExist:
        return False, 'Senior not assigned to you.'
    except Exception as e:
        return False, str(e)


class BuddyAIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message', '').strip()
        history = request.data.get('history', [])
        active_senior_id = request.data.get('active_senior_id') 

        if not user_message:
            return Response({'error': 'Message is required.'}, status=400)
        if not isinstance(history, list):
            history = []
        if len(history) > 20:
            history = history[-20:]

        messages = [
            {"role": "system", "content": build_system_prompt(request.user)}
        ] + history + [
            {"role": "user", "content": user_message}
        ]

        try:
            client = get_sarvam_client()
            response = client.chat.completions.create(model="sarvam-m", messages=messages)
            reply = response.choices[0].message.content
            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()

            # Parse and execute action if present
            action_result = None
            action_match = re.search(r'<action>(.*?)</action>', reply, re.DOTALL)
            if action_match:
                reply = reply.replace(action_match.group(0), '').strip()
                try:
                    action_data = json.loads(action_match.group(1))
                    success, msg = _execute_action(request.user, action_data, active_senior_id)
                    action_result = {'success': success, 'message': msg, 'type': action_data.get('type')}
                except Exception:
                    action_result = {'success': False, 'message': 'Action could not be processed.', 'type': None}

            updated_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]

            resp = {"reply": reply, "history": updated_history}
            if action_result:
                resp['action_result'] = action_result
            return Response(resp)

        except Exception as e:
            return Response({'error': f'Buddy is unavailable right now. ({str(e)})'}, status=503)