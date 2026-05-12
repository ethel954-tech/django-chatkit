from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Status, StatusView, StatusHidden
from chatkit.models import Friendship, FriendRequest

User = get_user_model()


class StatusModelTests(TestCase):
    """Test Status model functionality"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.user3 = User.objects.create_user(username='user3', password='pass123')
    
    def test_status_auto_expiration_24_hours(self):
        """Test that status automatically expires after 24 hours"""
        status = Status.objects.create(user=self.user1, content='Test status')
        expected_expiry = timezone.now() + timedelta(hours=24)
        
        # Check expiry is within 1 minute of expected
        self.assertLess(abs((status.expires_at - expected_expiry).total_seconds()), 60)
    
    def test_status_is_expired(self):
        """Test expiration checking"""
        # Create expired status
        expired_status = Status.objects.create(
            user=self.user1,
            content='Expired',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(expired_status.is_expired())
        
        # Create active status
        active_status = Status.objects.create(
            user=self.user1,
            content='Active',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertFalse(active_status.is_expired())
    
    def test_get_active_statuses_for_user(self):
        """Test getting active statuses only from friends"""
        # Create friendship
        FriendRequest.objects.create(from_user=self.user1, to_user=self.user2, status='pending')
        FriendRequest.objects.create(from_user=self.user2, to_user=self.user1, status='pending')
        friendship = Friendship.create_friendship(self.user1, self.user2)
        
        # Create statuses
        friend_status = Status.objects.create(
            user=self.user2,
            content='Friend status',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        non_friend_status = Status.objects.create(
            user=self.user3,
            content='Non-friend status',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Get active statuses for user1
        active = Status.get_active_statuses_for_user(self.user1)
        
        # Should only see friend's status
        self.assertIn(friend_status, active)
        self.assertNotIn(non_friend_status, active)
    
    def test_status_hidden_excludes_status(self):
        """Test that hidden statuses are excluded"""
        FriendRequest.objects.create(from_user=self.user1, to_user=self.user2, status='pending')
        FriendRequest.objects.create(from_user=self.user2, to_user=self.user1, status='pending')
        Friendship.create_friendship(self.user1, self.user2)
        
        status = Status.objects.create(
            user=self.user2,
            content='Test',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Hide the status
        StatusHidden.objects.create(status=status, user=self.user1)
        
        # Should not appear in active statuses
        active = Status.get_active_statuses_for_user(self.user1)
        self.assertNotIn(status, active)
    
    def test_status_view_tracking(self):
        """Test status view tracking"""
        status = Status.objects.create(user=self.user1, content='Test')
        
        # Create views
        StatusView.objects.create(status=status, viewer=self.user2)
        StatusView.objects.create(status=status, viewer=self.user3)
        
        # Test view count
        self.assertEqual(status.get_view_count(), 2)
        
        # Test has_been_viewed_by
        self.assertTrue(status.has_been_viewed_by(self.user2))
        self.assertTrue(status.has_been_viewed_by(self.user3))
        self.assertFalse(status.has_been_viewed_by(self.user1))
