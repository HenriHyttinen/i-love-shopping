import os

from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "Create a demo admin user from env variables"

    def handle(self, *args, **options):
        email = os.getenv("DEMO_ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("DEMO_ADMIN_PASSWORD", "AdminPass123!")
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING("Admin already exists"))
            return
        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Admin created: {email}"))
