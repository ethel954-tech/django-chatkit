from __future__ import annotations
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db.models import Q, F
from django.contrib import messages

from .models import Status, StatusView, StatusHidden
from .forms import StatusForm


@login_required
def status_list(request: HttpRequest) -> HttpResponse:
    """Display list of statuses from friends (WhatsApp Stories UI)"""
    
    # Get active statuses from friends
    statuses = Status.get_active_statuses_for_user(request.user)
    
    # Group statuses by user for Stories-like UI
    status_dict = {}
    for status in statuses:
        if status.user.id not in status_dict:
            status_dict[status.user.id] = {
                'user': status.user,
                'statuses': [],
                'has_viewed': False
            }
        
        is_viewed = status.has_been_viewed_by(request.user)
        status_dict[status.user.id]['statuses'].append({
            'status': status,
            'viewed': is_viewed,
            'view_count': status.get_view_count()
        })
        
        # Mark as has_viewed if any status from this user is viewed
        if is_viewed:
            status_dict[status.user.id]['has_viewed'] = True
    
    # Sort by most recent status from each user
    status_dict_sorted = sorted(
        status_dict.values(),
        key=lambda x: max([s['status'].created_at for s in x['statuses']]),
        reverse=True
    )
    
    # Check if user has any active statuses
    user_statuses = request.user.statuses.filter(
        expires_at__gt=timezone.now()
    ).exists()
    
    context = {
        'status_dict': status_dict_sorted,
        'status_list': status_dict_sorted,  # For backward compatibility
        'user_has_statuses': user_statuses,
    }
    
    return render(request, 'status/stories.html', context)


@login_required
def create_status(request: HttpRequest) -> HttpResponse:
    """Create a new status"""
    
    if request.method == 'POST':
        form = StatusForm(request.POST, request.FILES)
        if form.is_valid():
            status = form.save(commit=False)
            status.user = request.user
            status.save()
            messages.success(request, 'Status posted successfully!')
            return redirect('status:status_list')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = StatusForm()
    
    return render(request, 'status/create_status.html', {'form': form})


@login_required
def view_status(request: HttpRequest, status_id: int) -> HttpResponse:
    """View a specific status and mark as viewed"""
    
    status = get_object_or_404(Status, id=status_id)
    
    # Check if user is allowed to view (must be friends or own status)
    if status.user != request.user:
        from chatkit.models import Friendship
        if not Friendship.are_friends(request.user, status.user):
            return HttpResponse("You are not friends with this user.", status=403)
    
    # Check if expired
    if status.is_expired():
        return HttpResponse("This status has expired.", status=404)
    
    # Check if hidden from user
    if StatusHidden.objects.filter(status=status, user=request.user).exists():
        return HttpResponse("This status is not visible to you.", status=403)
    
    # Mark as viewed (only if not own status)
    if status.user != request.user:
        StatusView.objects.get_or_create(status=status, viewer=request.user)
    
    # Get viewer list (only show for status owner)
    viewers = None
    if status.user == request.user:
        viewers = status.views.select_related('viewer').order_by('-viewed_at')
    
    context = {
        'status': status,
        'viewers': viewers,
        'is_owner': status.user == request.user,
    }
    
    return render(request, 'status/view_status.html', context)


@login_required
@require_POST
def mark_as_viewed(request: HttpRequest, status_id: int) -> JsonResponse:
    """Mark a status as viewed (AJAX)"""
    
    status = get_object_or_404(Status, id=status_id)
    
    # Verify user is allowed to view
    if status.user != request.user:
        from chatkit.models import Friendship
        if not Friendship.are_friends(request.user, status.user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if status.is_expired():
        return JsonResponse({'error': 'Status expired'}, status=404)
    
    if StatusHidden.objects.filter(status=status, user=request.user).exists():
        return JsonResponse({'error': 'Status hidden'}, status=403)
    
    # Mark as viewed
    if status.user != request.user:
        StatusView.objects.get_or_create(status=status, viewer=request.user)
    
    return JsonResponse({'ok': True, 'view_count': status.get_view_count()})


@login_required
@require_POST
def hide_status(request: HttpRequest, status_id: int) -> HttpResponse:
    """Hide a status from the user"""
    
    status = get_object_or_404(Status, id=status_id)
    
    # Verify user is not the owner
    if status.user == request.user:
        return HttpResponse("You cannot hide your own status.", status=403)
    
    # Verify user is friends with status owner
    from chatkit.models import Friendship
    if not Friendship.are_friends(request.user, status.user):
        return HttpResponse("You are not friends with this user.", status=403)
    
    # Hide the status
    StatusHidden.objects.get_or_create(status=status, user=request.user)
    
    messages.info(request, f"Status from {status.user.username} hidden.")
    return redirect('status:status_list')


@login_required
def user_status_history(request: HttpRequest, username: str) -> HttpResponse:
    """View all active statuses from a specific user"""
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    status_user = get_object_or_404(User, username=username)
    
    # Check if friends (unless viewing own)
    if status_user != request.user:
        from chatkit.models import Friendship
        if not Friendship.are_friends(request.user, status_user):
            return HttpResponse("You are not friends with this user.", status=403)
    
    # Get active statuses
    now = timezone.now()
    statuses = Status.objects.filter(
        user=status_user,
        expires_at__gt=now
    ).order_by('-created_at')
    
    # Mark all as viewed
    for status in statuses:
        if status_user != request.user:
            StatusView.objects.get_or_create(status=status, viewer=request.user)
    
    context = {
        'status_user': status_user,
        'statuses': statuses,
        'is_own_history': status_user == request.user,
    }
    
    return render(request, 'status/user_history.html', context)
