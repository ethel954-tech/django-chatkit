from __future__ import annotations
from django.conf import settings
from django.db import models
from django.utils import timezone


class CallSession(models.Model):
    """Represents a call session between two users"""
    CALL_TYPE_CHOICES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]

    STATUS_CHOICES = [
        ('ringing', 'Ringing'),
        ('ongoing', 'Ongoing'),
        ('ended', 'Ended'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
    ]

    # Call participants
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incoming_calls')

    # Call details
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, default='audio')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ringing')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.caller} → {self.receiver} ({self.call_type}) - {self.status}"

    def get_duration(self):
        """Get call duration in seconds"""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds())
        elif self.started_at:
            delta = timezone.now() - self.started_at
            return int(delta.total_seconds())
        return 0

    def format_duration(self):
        """Format duration as HH:MM:SS"""
        duration = self.get_duration()
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def accept(self):
        """Accept the incoming call"""
        if self.status == 'ringing':
            self.status = 'ongoing'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])

    def reject(self):
        """Reject the incoming call"""
        if self.status == 'ringing':
            self.status = 'rejected'
            self.ended_at = timezone.now()
            self.save(update_fields=['status', 'ended_at'])

    def end(self):
        """End the ongoing call"""
        if self.status in ['ringing', 'ongoing']:
            # If call was never answered, mark as missed
            if self.status == 'ringing':
                self.status = 'missed'
            else:
                self.status = 'ended'
            self.ended_at = timezone.now()
            self.save(update_fields=['status', 'ended_at'])

    @classmethod
    def get_ongoing_call_between(cls, user_a, user_b):
        """Get ongoing call between two users"""
        return cls.objects.filter(
            models.Q(
                caller=user_a,
                receiver=user_b,
                status__in=['ringing', 'ongoing']
            ) | models.Q(
                caller=user_b,
                receiver=user_a,
                status__in=['ringing', 'ongoing']
            )
        ).first()

    @classmethod
    def get_call_history_for_user(cls, user, limit=50):
        """Get call history for a user"""
        calls = cls.objects.filter(
            models.Q(caller=user) | models.Q(receiver=user)
        ).select_related('caller', 'receiver').order_by('-created_at')[:limit]
        return calls


class CallSignal(models.Model):
    """
    Store WebRTC signaling messages (MVP).
    We’ll use REST endpoints + polling so each side can fetch new signals.
    """
    CALL_SIGNAL_TYPE_CHOICES = [
        ('offer', 'Offer'),
        ('answer', 'Answer'),
        ('ice', 'ICE Candidate'),
    ]

    call = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name='signals')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_call_signals')

    signal_type = models.CharField(max_length=10, choices=CALL_SIGNAL_TYPE_CHOICES)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['call', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"Signal({self.signal_type}) for call {self.call_id} from {self.sender_id}"
