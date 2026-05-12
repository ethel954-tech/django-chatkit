from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import CallSession
from chatkit.models import Friendship, FriendRequest

User = get_user_model()


class CallSessionModelTests(TestCase):
    """Test CallSession model functionality"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.user3 = User.objects.create_user(username='user3', password='pass123')
        
        # Create friendship between user1 and user2
        FriendRequest.objects.create(from_user=self.user1, to_user=self.user2, status='pending')
        FriendRequest.objects.create(from_user=self.user2, to_user=self.user1, status='pending')
        Friendship.create_friendship(self.user1, self.user2)
    
    def test_create_call_session(self):
        """Test creating a call session"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            status='ringing'
        )
        
        self.assertEqual(call.caller, self.user1)
        self.assertEqual(call.receiver, self.user2)
        self.assertEqual(call.call_type, 'audio')
        self.assertEqual(call.status, 'ringing')
    
    def test_accept_call(self):
        """Test accepting a call"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            status='ringing'
        )
        
        call.accept()
        
        self.assertEqual(call.status, 'ongoing')
        self.assertIsNotNone(call.started_at)
    
    def test_reject_call(self):
        """Test rejecting a call"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            status='ringing'
        )
        
        call.reject()
        
        self.assertEqual(call.status, 'rejected')
        self.assertIsNotNone(call.ended_at)
    
    def test_end_ongoing_call(self):
        """Test ending an ongoing call"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='video',
            status='ongoing',
            started_at=timezone.now() - timedelta(seconds=30)
        )
        
        call.end()
        
        self.assertEqual(call.status, 'ended')
        self.assertIsNotNone(call.ended_at)
    
    def test_get_duration(self):
        """Test call duration calculation"""
        started = timezone.now() - timedelta(minutes=5, seconds=30)
        ended = timezone.now()
        
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            started_at=started,
            ended_at=ended,
            status='ended'
        )
        
        duration = call.get_duration()
        # Should be approximately 330 seconds (5 mins 30 secs)
        self.assertGreater(duration, 320)
        self.assertLess(duration, 340)
    
    def test_format_duration(self):
        """Test duration formatting"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            started_at=timezone.now() - timedelta(minutes=1, seconds=30),
            ended_at=timezone.now(),
            status='ended'
        )
        
        formatted = call.format_duration()
        self.assertIn(':', formatted)
    
    def test_get_ongoing_call_between(self):
        """Test finding ongoing call between users"""
        call = CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            status='ringing'
        )
        
        found_call = CallSession.get_ongoing_call_between(self.user1, self.user2)
        self.assertEqual(found_call.id, call.id)
        
        # Should also find it in reverse
        found_call_reverse = CallSession.get_ongoing_call_between(self.user2, self.user1)
        self.assertEqual(found_call_reverse.id, call.id)
    
    def test_get_call_history_for_user(self):
        """Test getting call history"""
        # Create multiple calls
        CallSession.objects.create(
            caller=self.user1,
            receiver=self.user2,
            call_type='audio',
            status='ended'
        )
        CallSession.objects.create(
            caller=self.user2,
            receiver=self.user1,
            call_type='video',
            status='ended'
        )
        
        history = CallSession.get_call_history_for_user(self.user1)
        self.assertEqual(history.count(), 2)
