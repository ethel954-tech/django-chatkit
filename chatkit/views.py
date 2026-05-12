from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatRoom, Message, Attachment, UserSettings, Friendship, FriendRequest, InvitationLink
from .forms import MessageForm, FriendRequestForm, InvitationLinkForm

User = get_user_model()


# =========================
# INDEX
# =========================
@login_required
def index(request: HttpRequest):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    # What the template expects: friends_with_rooms + pending_requests
    friendships = Friendship.objects.filter(Q(user1=request.user) | Q(user2=request.user))

    friends_with_rooms = []
    for f in friendships:
        friend = f.get_other_user(request.user)

        # DM room is stored on the friendship (chat_room may be null until accepted)
        room = f.chat_room if getattr(f, "chat_room", None) else None

        friends_with_rooms.append(
            {
                "friend": friend,
                "room": room,
            }
        )

    pending_requests = FriendRequest.objects.filter(to_user=request.user, status="pending").select_related(
        "from_user"
    )

    return render(request, "chatkit/index.html", {
        "friends_with_rooms": friends_with_rooms,
        "pending_requests": pending_requests,
        "settings": settings_obj,
    })


# =========================
# ROOM
# =========================
@login_required
def room(request: HttpRequest, slug: str):
    room = get_object_or_404(ChatRoom, slug=slug)

    if room.participants.exists() and request.user not in room.participants.all():
        return HttpResponse("Not allowed", status=403)

    msgs = room.messages.select_related("sender").order_by("-created_at")[:100]
    msgs = list(reversed(msgs))

    # WhatsApp-style header needs the "other user" for 1:1 chats.
    # If this is not a 1:1 room, we’ll fall back gracefully.
    other_user = (
        room.participants.exclude(id=request.user.id).first()
        if room.participants.exists()
        else None
    )

    form = MessageForm()
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    return render(request, "chatkit/room.html", {
        "room": room,
        "messages": msgs,
        "form": form,
        "settings": settings_obj,
        "other_user": other_user,
    })


# =========================
# PRIVATE CHAT
# =========================
@login_required
def open_private_chat(request: HttpRequest, username: str):
    friend = get_object_or_404(User, username=username)

    friendship = Friendship.get_friendship(request.user, friend)

    if not friendship or not friendship.chat_room:
        return HttpResponse("No chat available", status=403)

    return redirect("chatkit:room", slug=friendship.chat_room.slug)


# =========================
# SEND MESSAGE
# =========================
@login_required
@require_POST
def api_send_message(request: HttpRequest):
    form = MessageForm(request.POST, request.FILES)
    slug = request.POST.get("room_slug")

    if not slug:
        return HttpResponseBadRequest("Missing room_slug")

    room = get_object_or_404(ChatRoom, slug=slug)

    if room.participants.exists() and request.user not in room.participants.all():
        return JsonResponse({"error": "not allowed"}, status=403)

    if form.is_valid():
        with transaction.atomic():
            msg = Message.objects.create(
                chat=room,
                sender=request.user,
                content=form.cleaned_data.get("content", "")
            )

            for f in request.FILES.getlist("files"):
                Attachment.objects.create(message=msg, file=f)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.slug}",
            {"type": "chat.message", "message": msg.to_dict()},
        )

        return JsonResponse({"ok": True, "message": msg.to_dict()})

    return JsonResponse({"errors": form.errors}, status=400)


# =========================
# SETTINGS
# =========================
@login_required
def user_settings(request: HttpRequest):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        settings_obj.theme = request.POST.get("theme", "system")
        settings_obj.save()

    return render(request, "chatkit/settings.html", {
        "settings": settings_obj
    })


# =========================
# FRIENDS LIST
# =========================
@login_required
def friends_list(request: HttpRequest):
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    )

    friends = [
        {
            "friend": f.get_other_user(request.user),
            "friendship": f
        }
        for f in friendships
    ]

    # Forms required by chatkit/templates/chatkit/friends.html
    friend_request_form = FriendRequestForm(current_user=request.user)
    invitation_form = InvitationLinkForm()

    # Friend request querysets required by the template
    received_requests = FriendRequest.objects.filter(to_user=request.user, status="pending").select_related("from_user")
    sent_requests = FriendRequest.objects.filter(from_user=request.user, status="pending").select_related("to_user")

    invitation_links = InvitationLink.objects.filter(created_by=request.user, is_active=True).order_by("-created_at")

    return render(request, "chatkit/friends.html", {
        "friends": friends,
        "friend_request_form": friend_request_form,
        "invitation_form": invitation_form,
        "received_requests": received_requests,
        "sent_requests": sent_requests,
        "invitation_links": invitation_links,
        # Template checks `if messages`, which is safe to include.
        "messages": messages.get_messages(request),
    })


# =========================
# FRIEND REQUESTS
# =========================
@login_required
@require_POST
def send_friend_request(request: HttpRequest):
    form = FriendRequestForm(request.POST, current_user=request.user)

    if form.is_valid():
        to_user = get_object_or_404(User, username=form.cleaned_data["username"])

        if not Friendship.are_friends(request.user, to_user):
            FriendRequest.objects.get_or_create(
                from_user=request.user,
                to_user=to_user
            )

    return redirect("chatkit:friends")


@login_required
@require_POST
def accept_friend_request(request: HttpRequest, request_id: int):
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    fr.accept()
    return redirect("chatkit:friends")


@login_required
@require_POST
def reject_friend_request(request: HttpRequest, request_id: int):
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    fr.reject()
    return redirect("chatkit:friends")


@login_required
@require_POST
def cancel_friend_request(request: HttpRequest, request_id: int):
    fr = get_object_or_404(FriendRequest, id=request_id, from_user=request.user)
    fr.delete()
    return redirect("chatkit:friends")


@login_required
@require_POST
def remove_friend(request: HttpRequest, friendship_id: int):
    friendship = get_object_or_404(Friendship, id=friendship_id)

    if friendship.user1 != request.user and friendship.user2 != request.user:
        return HttpResponse("Unauthorized", status=403)

    friendship.delete()
    return redirect("chatkit:friends")


# =========================
# INVITATIONS
# =========================
@login_required
def create_invitation_link(request: HttpRequest):
    form = InvitationLinkForm(request.POST)

    if form.is_valid():
        InvitationLink.objects.create(
            created_by=request.user,
            max_uses=form.cleaned_data["max_uses"]
        )

    return redirect("chatkit:friends")


@login_required
def accept_invitation(request: HttpRequest, token: str):
    inv = get_object_or_404(InvitationLink, token=token)
    inv.use(request.user)
    return redirect("chatkit:index")


@login_required
@require_POST
def deactivate_invitation(request: HttpRequest, invitation_id: int):
    inv = get_object_or_404(InvitationLink, id=invitation_id, created_by=request.user)
    inv.is_active = False
    inv.save()
    return redirect("chatkit:friends")
