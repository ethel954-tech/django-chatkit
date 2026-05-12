from django.core.management.base import BaseCommand
from django.utils import timezone
from status.models import Status


class Command(BaseCommand):
    help = 'Delete expired statuses from the database'

    def handle(self, *args, **options):
        now = timezone.now()
        deleted_count, _ = Status.objects.filter(expires_at__lt=now).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} expired statuses')
        )
