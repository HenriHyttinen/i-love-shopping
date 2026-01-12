from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import AccessTokenBlocklist


class Command(BaseCommand):
    help = "Delete expired access token blocks"

    def handle(self, *args, **options):
        now = timezone.now()
        deleted, _ = AccessTokenBlocklist.objects.filter(expires_at__lt=now).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired entries"))
