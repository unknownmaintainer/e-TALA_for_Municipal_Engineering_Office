import logging
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import BlockedIP
from .utils import get_client_ip

logger = logging.getLogger('permits')


class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.user.is_authenticated:
                current_session_key = request.session.session_key
                # If the user has a session key stored and it differs from current, log out
                if request.user.session_key and request.user.session_key != current_session_key:
                    logout(request)
                    messages.warning(request, "You have been logged out because another session was started on a different device.")
                    return redirect('login')
        except Exception as exc:
            logger.debug(f"SingleSessionMiddleware check skipped: {exc}")

        response = self.get_response(request)
        return response


class IPBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip database IP checks for static assets, media, and CSS/JS files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        try:
            ip = get_client_ip(request)
            if ip and BlockedIP.objects.filter(ip_address=ip).exists():
                return HttpResponseForbidden("Access Denied: Your IP address has been blocked by the administrator.")
        except Exception as exc:
            logger.debug(f"IPBlockMiddleware check skipped during startup: {exc}")

        response = self.get_response(request)
        return response


class NoCacheForAuthenticatedMiddleware:
    """Ensures dynamic authenticated management pages are never served from stale browser bfcache."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response

