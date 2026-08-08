import os

def get_client_ip(request):
    """
    Extract the client IP address safely from the request.
    Only trust HTTP_X_FORWARDED_FOR if explicitly configured (e.g. on Render/reverse proxy).
    """
    if os.getenv('RENDER_EXTERNAL_HOSTNAME') or os.getenv('TRUST_PROXY_HEADERS'):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')

