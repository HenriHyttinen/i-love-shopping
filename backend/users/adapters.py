from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from django.contrib.auth import get_user_model


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        user = sociallogin.user
        email = getattr(user, "email", None)
        if not email:
            return
        existing = get_user_model().objects.filter(email__iexact=email).first()
        if existing:
            sociallogin.connect(request, existing)
            EmailAddress.objects.get_or_create(
                user=existing,
                email=existing.email,
                defaults={"verified": True, "primary": True},
            )
