from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import BlockedIP
from .utils import get_client_ip


class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_session_key = request.session.session_key
            # If the user has a session key stored and it differs from current, log out
            if request.user.session_key and request.user.session_key != current_session_key:
                logout(request)
                messages.warning(request, "You have been logged out because another session was started on a different device.")
                return redirect('login')
        response = self.get_response(request)
        return response


class IPBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        if BlockedIP.objects.filter(ip_address=ip).exists():
            return HttpResponseForbidden("Access Denied: Your IP address has been blocked by the administrator.")
        response = self.get_response(request)
        return response
