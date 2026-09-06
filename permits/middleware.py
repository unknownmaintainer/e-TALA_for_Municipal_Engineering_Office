import logging
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib import messages
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


from django.core.cache import cache

class IPBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip database IP checks for static assets, media, and CSS/JS files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        try:
            ip = get_client_ip(request)
            if ip:
                blocked_ips = cache.get('system_blocked_ips_set')
                if blocked_ips is None:
                    blocked_ips = set(BlockedIP.objects.values_list('ip_address', flat=True))
                    cache.set('system_blocked_ips_set', blocked_ips, timeout=60)

                if ip in blocked_ips:
                    return render(request, 'permits/access_denied.html', {
                        'is_blocked_ip': True,
                        'blocked_ip': ip,
                    }, status=403)
        except Exception as exc:
            logger.debug(f"IPBlockMiddleware check skipped during startup: {exc}")

        response = self.get_response(request)
        return response


class NoCacheForAuthenticatedMiddleware:
    """Ensures dynamic authenticated pages remain private while allowing browser Paint Holding (zero white flash)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            response['Cache-Control'] = 'private, no-cache'
        return response

