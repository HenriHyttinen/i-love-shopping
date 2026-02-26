from django.shortcuts import render
from django.core.mail import send_mail
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class ContactSupportView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        name = str(request.data.get("name", "")).strip()
        email = str(request.data.get("email", "")).strip()
        subject = str(request.data.get("subject", "")).strip()
        message = str(request.data.get("message", "")).strip()

        if not name or not email or not subject or not message:
            return Response({"detail": "name, email, subject, and message are required."}, status=400)

        body = (
            f"Support message from {name} <{email}>\n\n"
            f"Subject: {subject}\n\n"
            f"{message}"
        )
        send_mail(
            subject=f"[Support] {subject}",
            message=body,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        return Response({"detail": "Support request sent."}, status=201)


def custom_404(request, exception):
    return render(request, "404.html", status=404)
