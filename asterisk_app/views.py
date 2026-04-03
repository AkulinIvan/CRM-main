from dateutil.parser import parse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import logging
from .forms import AttachCallToTicketForm
from tickets.models import Ticket
from .models import Call

logger = logging.getLogger(__name__)


@csrf_exempt
def asterisk_webhook(request):
    if request.method == 'POST':
        print("Полученные данные:", request.POST)
        try:
            # Получаем данные из POST-запроса
            call_data = {
                'phone': request.POST.get('phone', '').strip(),
                'unique_id': request.POST.get('unique_id', '').strip(),
                'call_date': request.POST.get('call_date', '').strip(),
                'duration': request.POST.get('duration', '0').strip(),
                'call_type': request.POST.get('call_type', '').strip(),
            }

            # Проверяем обязательные поля
            required_fields = ['phone', 'unique_id', 'call_date', 'call_type']
            if not all(call_data[field] for field in required_fields):
                return JsonResponse(
                    {'status': 'error', 'message': 'Missing required fields'}, 
                    status=400,
                    json_dumps_params={'ensure_ascii': False}
                )

            # Проверяем существование звонка с таким unique_id
            if Call.objects.filter(unique_id=call_data['unique_id']).exists():
                return JsonResponse(
                    {'status': 'error', 'message': 'Call with this unique_id already exists'},
                    status=400,
                    json_dumps_params={'ensure_ascii': False}
                )
                
            # Преобразуем дату и продолжительность
            try:
                call_date = parse(call_data['call_date'])
                duration = int(call_data['duration'])
            except (ValueError, TypeError) as e:
                return JsonResponse(
                    {'status': 'error', 'message': f'Invalid data format: {str(e)}'}, 
                    status=400,
                    json_dumps_params={'ensure_ascii': False}
                )

            # Создаем и сохраняем звонок
            call = Call.objects.create(
                phone=call_data['phone'],
                unique_id=call_data['unique_id'],
                call_date=call_date,
                duration=duration,
                call_type=call_data['call_type'],
                is_processed=False
            )

            logger.info(f"Created call: {call.id}")
            return JsonResponse(
                {'status': 'success', 'id': call.id}, 
                status=201,
                json_dumps_params={'ensure_ascii': False}
            )

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return JsonResponse(
                {'status': 'error', 'message': 'Internal server error'}, 
                status=500,
                json_dumps_params={'ensure_ascii': False}
            )
    
    return JsonResponse(
        {'status': 'error', 'message': 'Method not allowed'}, 
        status=405,
        json_dumps_params={'ensure_ascii': False}
    )


class CallStatusAPI(APIView):
    def get(self, request, unique_id):
        try:
            call = Call.objects.get(unique_id=unique_id)
            return Response({
                'status': 'success',
                'call': {
                    'phone': call.phone,
                    'call_date': call.call_date,
                    'duration': call.duration,
                    'call_type': call.get_call_type_display(),
                    'recording_url': call.recording_path if call.recording_path else None
                }
            })
        except Call.DoesNotExist:
            return Response({'status': 'error', 'message': 'Call not found'}, status=404)
        
        
@login_required
def call_list(request):
    # Фильтрация звонков для текущего пользователя
    calls = Call.objects.all().order_by('-call_date')
    
    # Фильтры
    phone = request.GET.get('phone')
    call_type = request.GET.get('call_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if phone:
        calls = calls.filter(phone__icontains=phone)
    if call_type:
        calls = calls.filter(call_type=call_type)
    if date_from:
        calls = calls.filter(call_date__gte=date_from)
    if date_to:
        calls = calls.filter(call_date__lte=date_to)
    
    # Пагинация
    paginator = Paginator(calls, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'asterisk_app/call_list.html', {
        'page_obj': page_obj,
        'call_types': Call.CALL_TYPES,
    })

@login_required
def call_detail(request, pk):
    call = get_object_or_404(Call, pk=pk)
    return render(request, 'asterisk_app/call_detail.html', {'call': call})

@login_required
def attach_call_to_ticket(request, call_id):
    call = get_object_or_404(Call, pk=call_id)
    
    if request.method == 'POST':
        form = AttachCallToTicketForm(request.POST)
        if form.is_valid():
            ticket = form.cleaned_data['ticket']
            call.ticket = ticket
            call.save()
            return redirect('calls:call_detail', pk=call.id)
    else:
        # Предлагаем только релевантные заявки (по номеру телефона или без привязанных звонков)
        tickets = Ticket.objects.filter(
            Q(contact_phone__icontains=call.phone) | 
            Q(calls__isnull=True)
        )
        form = AttachCallToTicketForm(initial={'ticket': None})
        form.fields['ticket'].queryset = tickets
    
    return render(request, 'asterisk_app/attach_to_ticket.html', {
        'call': call,
        'form': form,
    })

@login_required
def ticket_calls(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    calls = ticket.call_set.all().order_by('-call_date')
    return render(request, 'asterisk_app/ticket_calls.html', {
        'ticket': ticket,
        'calls': calls,
    })