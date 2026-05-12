from __future__ import annotations
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Status(models.Model):
    """User status/story that expires after 24 hours"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="statuses")
    content = models.TextField(max_length=500, blank=True)
    media = models.FileField(upload_to="statuses/%Y/%m/%d/", null=True, blank=True, help_text="Image or video")
    media_type = models.CharField(
        max_length=10,
        choices=[("image", "Image"), ("video", "Video")],
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at", "user"]),
        ]

    def __str__(self):
        return f"Status by {self.user} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """Auto-set expiration to 24 hours from now if not set"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_statuses_for_user(cls, user):
        """Get all active statuses (not expired) from user's friends"""
        from chatkit.models import Friendship
        
        # Get all friendships for this user
        friendships = Friendship.objects.filter(
            models.Q(user1=user) | models.Q(user2=user)
        ).select_related('user1', 'user2')
        
        # Extract friend user objects
        friend_ids = set()
        for friendship in friendships:
            if friendship.user1 == user:
                friend_ids.add(friendship.user2.id)
            else:
                friend_ids.add(friendship.user1.id)
        
        # Get active statuses from friends (not expired, not hidden)
        now = timezone.now()
        statuses = cls.objects.filter(
            user_id__in=friend_ids,
            expires_at__gt=now
        ).exclude(
            hidden_from_users__user=user
        ).select_related('user').distinct().order_by('-created_at')
        
        return statuses

    def is_expired(self):
        """Check if status has expired"""
        return timezone.now() > self.expires_at

    def get_view_count(self):
        """Get number of viewers"""
        return self.views.count()

    def has_been_viewed_by(self, user):
        """Check if user has viewed this status"""
        return self.views.filter(viewer=user).exists()


class StatusView(models.Model):
    """Track who viewed each status"""
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viewed_statuses")
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [["status", "viewer"]]
        ordering = ["viewed_at"]

    def __str__(self):
        return f"{self.viewer} viewed {self.status}"


class StatusHidden(models.Model):
    """Track users who have hidden a status from a specific user"""
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name="hidden_from_users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hidden_statuses")
    hidden_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [["status", "user"]]

    def __str__(self):
        return f"{self.status.user}'s status hidden from {self.user}"
