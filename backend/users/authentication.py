from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import AccessTokenBlocklist


class BlocklistJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        jti = token.get("jti")
        if jti and AccessTokenBlocklist.objects.filter(jti=jti).exists():
            raise AuthenticationFailed("Token revoked", code="token_revoked")
        return token
