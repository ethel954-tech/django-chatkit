from __future__ import annotations
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import CallSession, CallSignal
from .forms import InitiateCallForm
from chatkit.models import Friendship

User = get_user_model()


@login_required
def calls_list(request: HttpRequest) -> HttpResponse:
    """Display call history"""
    
    calls = CallSession.get_call_history_for_user(request.user, limit=100)
    
    # Separate calls by type
    incoming_calls = []
    outgoing_calls = []
    missed_calls = []
    
    for call in calls:
        if call.status == 'missed' and call.receiver == request.user:
            missed_calls.append(call)
        elif call.receiver == request.user:
            incoming_calls.append(call)
        else:
            outgoing_calls.append(call)
    
    context = {
        'calls': calls,
        'incoming_calls': incoming_calls,
        'outgoing_calls': outgoing_calls,
        'missed_calls': missed_calls,
    }
    
    return render(request, 'calls/calls_list.html', context)


@login_required
def initiate_call(request: HttpRequest, user_id: int) -> HttpResponse:
    """Initiate a call to another user"""
    
    recipient = get_object_or_404(User, id=user_id)
    
    # Check if calling self
    if recipient == request.user:
        messages.error(request, "You cannot call yourself.")
        return redirect('calls:calls_list')
    
    # Check if they are friends
    if not Friendship.are_friends(request.user, recipient):
        messages.error(request, f"You are not friends with {recipient.username}.")
        return redirect('calls:calls_list')
    
    # Check for ongoing call
    ongoing_call = CallSession.get_ongoing_call_between(request.user, recipient)
    if ongoing_call:
        messages.info(request, f"There is already an active call with {recipient.username}.")
        return redirect('calls:view_call', call_id=ongoing_call.id)
    
    if request.method == 'POST':
        form = InitiateCallForm(request.POST)
        if form.is_valid():
            call_type = form.cleaned_data['call_type']
            
            # Create call session
            call = CallSession.objects.create(
                caller=request.user,
                receiver=recipient,
                call_type=call_type,
                status='ringing'
            )
            
            messages.success(request, f"Calling {recipient.username}...")
            return redirect('calls:view_call', call_id=call.id)
    else:
        form = InitiateCallForm()
    
    context = {
        'recipient': recipient,
        'form': form,
    }
    
    return render(request, 'calls/initiate_call.html', context)


@login_required
def view_call(request: HttpRequest, call_id: int) -> HttpResponse:
    """View an active call"""
    
    call = get_object_or_404(CallSession, id=call_id)
    
    # Check if user is participant
    if request.user not in [call.caller, call.receiver]:
        return HttpResponse("You are not part of this call.", status=403)
    
    # Get the other participant
    other_user = call.receiver if call.caller == request.user else call.caller
    is_caller = call.caller == request.user
    
    context = {
        'call': call,
        'other_user': other_user,
        'is_caller': is_caller,
        'is_receiver': not is_caller,
    }
    
    return render(request, 'calls/view_call.html', context)


@login_required
@require_POST
def accept_call(request: HttpRequest, call_id: int) -> HttpResponse:
    """Accept an incoming call"""
    
    call = get_object_or_404(CallSession, id=call_id)
    
    # Verify user is receiver
    if call.receiver != request.user:
        return HttpResponse("You are not the receiver of this call.", status=403)
    
    # Check if call is still ringing
    if call.status != 'ringing':
        messages.info(request, "This call is no longer available.")
        return redirect('calls:calls_list')
    
    call.accept()
    messages.success(request, f"Call accepted with {call.caller.username}.")
    
    return redirect('calls:view_call', call_id=call.id)


@login_required
@require_POST
def reject_call(request: HttpRequest, call_id: int) -> HttpResponse:
    """Reject an incoming call"""
    
    call = get_object_or_404(CallSession, id=call_id)
    
    # Verify user is receiver
    if call.receiver != request.user:
        return HttpResponse("You are not the receiver of this call.", status=403)
    
    # Check if call is still ringing
    if call.status != 'ringing':
        messages.info(request, "This call is no longer available.")
        return redirect('calls:calls_list')
    
    call.reject()
    messages.info(request, f"Call from {call.caller.username} rejected.")
    
    return redirect('calls:calls_list')


@login_required
@require_POST
def end_call(request: HttpRequest, call_id: int) -> HttpResponse:
    """End an ongoing call"""
    
    call = get_object_or_404(CallSession, id=call_id)
    
    # Verify user is participant
    if request.user not in [call.caller, call.receiver]:
        return HttpResponse("You are not part of this call.", status=403)
    
    # Check if call is active
    if call.status not in ['ringing', 'ongoing']:
        messages.info(request, "This call has already ended.")
        return redirect('calls:calls_list')
    
    other_user = call.receiver if call.caller == request.user else call.caller
    call.end()
    messages.info(request, f"Call with {other_user.username} ended.")
    
    return redirect('calls:calls_list')


@login_required
def call_with_friend(request: HttpRequest, username: str) -> HttpResponse:
    """Quick call initiation from chat/contacts page (generic; kept for compatibility)"""
    
    friend = get_object_or_404(User, username=username)
    
    # Check if they are friends
    if not Friendship.are_friends(request.user, friend):
        return HttpResponse("You are not friends with this user.", status=403)
    
    if request.method == 'POST':
        form = InitiateCallForm(request.POST)
        if form.is_valid():
            call_type = form.cleaned_data['call_type']
            
            call = CallSession.objects.create(
                caller=request.user,
                receiver=friend,
                call_type=call_type,
                status='ringing'
            )
            
            return redirect('calls:view_call', call_id=call.id)
    else:
        form = InitiateCallForm()
    
    context = {
        'recipient': friend,
        'form': form,
    }
    
    return render(request, 'calls/initiate_call.html', context)


@login_required
def call_with_friend_audio(request: HttpRequest, username: str) -> HttpResponse:
    """Quick audio call initiation from chat header."""
    friend = get_object_or_404(User, username=username)

    if not Friendship.are_friends(request.user, friend):
        return HttpResponse("You are not friends with this user.", status=403)

    ongoing_call = CallSession.get_ongoing_call_between(request.user, friend)
    if ongoing_call:
        return redirect('calls:view_call', call_id=ongoing_call.id)

    call = CallSession.objects.create(
        caller=request.user,
        receiver=friend,
        call_type='audio',
        status='ringing',
    )
    return redirect('calls:view_call', call_id=call.id)


@login_required
def call_with_friend_video(request: HttpRequest, username: str) -> HttpResponse:
    """Quick video call initiation from chat header."""
    friend = get_object_or_404(User, username=username)

    if not Friendship.are_friends(request.user, friend):
        return HttpResponse("You are not friends with this user.", status=403)

    ongoing_call = CallSession.get_ongoing_call_between(request.user, friend)
    if ongoing_call:
        return redirect('calls:view_call', call_id=ongoing_call.id)

    call = CallSession.objects.create(
        caller=request.user,
        receiver=friend,
        call_type='video',
        status='ringing',
    )
    return redirect('calls:view_call', call_id=call.id)



@login_required
def get_incoming_calls(request: HttpRequest) -> JsonResponse:
    """Get incoming calls (AJAX for notifications)"""

    # Get pending incoming calls
    incoming = CallSession.objects.filter(
        receiver=request.user,
        status='ringing'
    ).select_related('caller').values('id', 'caller__username', 'call_type', 'created_at')

    return JsonResponse({
        'incoming_calls': list(incoming),
        'count': incoming.count()
    })


@login_required
def call_status(request: HttpRequest, call_id: int) -> JsonResponse:
    """Return current call status for polling clients."""
    call = get_object_or_404(CallSession, id=call_id)

    if request.user not in [call.caller, call.receiver]:
        return JsonResponse({"error": "Forbidden"}, status=403)

    return JsonResponse(
        {
            "id": call.id,
            "status": call.status,
            "call_type": call.call_type,
            "caller_id": call.caller_id,
            "receiver_id": call.receiver_id,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "started_at": call.started_at.isoformat() if call.started_at else None,
        }
    )


@login_required
def call_signal(request: HttpRequest, call_id: int) -> JsonResponse:
    """
    MVP signaling endpoint (REST + polling).

    - POST: submit { signal_type: "offer"|"answer"|"ice", payload: {...} }
    - GET: poll with ?after=<signal_id> and receive { signals: [...], next_after: <id|null> }
    """
    call = get_object_or_404(CallSession, id=call_id)

    # Only participants can signal
    if request.user not in [call.caller, call.receiver]:
        return JsonResponse({"error": "Forbidden"}, status=403)

    if request.method == "POST":
        if call.status not in ["ringing", "ongoing"]:
            return JsonResponse({"error": "Call not active"}, status=400)

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        signal_type = body.get("signal_type")
        payload = body.get("payload")

        if signal_type not in dict(CallSignal.CALL_SIGNAL_TYPE_CHOICES):
            return JsonResponse({"error": "Invalid signal_type"}, status=400)
        if payload is None:
            return JsonResponse({"error": "Missing payload"}, status=400)

        CallSignal.objects.create(
            call=call,
            sender=request.user,
            signal_type=signal_type,
            payload=payload,
        )
        return JsonResponse({"ok": True})

    # GET: polling
    after = request.GET.get("after")
    qs = CallSignal.objects.filter(call=call).order_by("id")

    if after:
        try:
            after_int = int(after)
            qs = qs.filter(id__gt=after_int)
        except ValueError:
            return JsonResponse({"error": "Invalid after"}, status=400)

    # Only return signals from the other participant
    qs = qs.exclude(sender=request.user)

    signals = [
        {
            "id": s.id,
            "signal_type": s.signal_type,
            "payload": s.payload,
            "created_at": s.created_at.isoformat(),
        }
        for s in qs[:200]
    ]
    next_after = signals[-1]["id"] if signals else None

    return JsonResponse({"signals": signals, "next_after": next_after})
