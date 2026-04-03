from django.http import JsonResponse
from accounts.models import Address
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Ticket


def get_buildings(request):
    street = request.GET.get('street', '')
    if street:
        buildings = Address.objects.filter(
            street=street
        ).values_list('building', flat=True).distinct()
        return JsonResponse({'buildings': list(buildings)})
    return JsonResponse({'buildings': []})


def get_executors_for_master(request):
    from accounts.models import User
    master_id = request.GET.get('master_id')
    if not master_id:
        return JsonResponse({'executors': []})
    
    try:
        master = User.objects.get(pk=master_id, role=User.Role.MASTER)
        executors = User.objects.filter(
            management_company=master.management_company,
            role=User.Role.EXECUTOR
        ).select_related('executor_profile').exclude(pk=master.pk)
        
        data = {
            'executors': [
                {
                    'id': e.pk,
                    'full_name': e.get_full_name(),
                    'specialization': e.executor_profile.get_specialization_name() if e.executor_profile else 'Не указана'
                }
                for e in executors
            ]
        }
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'executors': []})
    
    

@api_view(['GET'])
def ticket_notifications(request, ticket_id):
    try:
        ticket = Ticket.objects.get(pk=ticket_id)
        
        data = {
            'sms': [{
                'id': sms.id,
                'phone': sms.phone,
                'status': sms.get_status_display(),
                'date': sms.created_at
            } for sms in ticket.get_sms_statuses()],
            
            'push': [{
                'id': push.id,
                'recipient': push.recipient.get_full_name(),
                'status': push.get_status_display(),
                'date': push.created_at
            } for push in ticket.get_push_statuses()]
        }
        
        return Response(data)
    except Ticket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=404)