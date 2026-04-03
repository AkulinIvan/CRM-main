from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from core.logging_utils import NotificationLog
from .models import PushNotification, PushSubscription
from accounts.models import User

@require_POST
@csrf_exempt
def subscribe(request):
    try:
        data = json.loads(request.body)
        user = request.user if request.user.is_authenticated else None
        
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Не авторизован'}, status=401)
            
        # Проверяем, есть ли уже такая подписка
        subscription, created = PushSubscription.objects.get_or_create(
            user=user,
            endpoint=data['endpoint'],
            defaults={'keys': data['keys']}
        )
        
        if not created:
            subscription.keys = data['keys']
            subscription.save()
        
        NotificationLog.log(
            notification_type='SUBSCRIPTION',
            sender=f'user:{user.username}',
            recipient=f'endpoint:{data["endpoint"]}',
            status='created' if created else 'updated',
            details='Push notification subscription'
        )
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        NotificationLog.log(
            notification_type='SUBSCRIPTION',
            sender=f'user:{user.username if user else "anonymous"}',
            recipient=f'endpoint:{data.get("endpoint", "unknown")}',
            status='failed',
            details=str(e)
        )
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
@csrf_exempt
def unsubscribe(request):
    try:
        data = json.loads(request.body)
        subscriptions = PushSubscription.objects.filter(
            endpoint=data['endpoint']
        )
        
        if subscriptions.exists():
            user_info = ", ".join([f"user:{sub.user.username}" for sub in subscriptions])
            subscriptions.delete()
            
            NotificationLog.log(
                notification_type='UNSUBSCRIPTION',
                sender=user_info,
                recipient=f'endpoint:{data["endpoint"]}',
                status='success',
                details='Push notification unsubscription'
            )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        NotificationLog.log(
            notification_type='UNSUBSCRIPTION',
            sender='system',
            recipient=f'endpoint:{data.get("endpoint", "unknown")}',
            status='failed',
            details=str(e)
        )
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    
@csrf_exempt
@require_POST
def mark_notification_as_read(request, notification_id):
    try:
        notification = PushNotification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
    except PushNotification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

@csrf_exempt
def get_unread_notifications(request):
    notifications = PushNotification.objects.filter(
        recipient=request.user,
        status='delivered'
    ).order_by('-created_at')[:10]
    
    data = [{
        'id': n.id,
        'type': n.notification_type,
        'title': n.title,
        'body': n.body,
        'ticket_id': n.ticket_id,
        'created_at': n.created_at
    } for n in notifications]
    
    return JsonResponse({'notifications': data})