from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.utils import timezone
import base64
import json
import hashlib
import user_agents
from .models import Device


def generate_verification_token(user):
    """Generate a verification token for user"""
    signer = TimestampSigner()
    data = {
        'user_id': str(user.id),
        'email': user.email
    }
    encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
    return signer.sign(encoded_data)


def verify_token(token):
    """Verify a token and return user_id if valid"""
    try:
        signer = TimestampSigner()
        value = signer.unsign(token, max_age=settings.VERIFICATION_TOKEN_EXPIRY or 86400)
        decoded_data = json.loads(base64.b64decode(value.encode()).decode())
        return decoded_data.get('user_id')
    except (BadSignature, SignatureExpired, json.JSONDecodeError, KeyError):
        return None


def create_device(user, request):
    """Create or update device record for user"""
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    ip_address = get_client_ip(request)
    
    ua = user_agents.parse(user_agent_string)
    
    device_id = hashlib.sha256(
        f"{user.id}{user_agent_string}{ip_address}".encode()
    ).hexdigest()
    
    if ua.is_mobile:
        device_type = 'mobile'
    elif ua.is_tablet:
        device_type = 'tablet'
    elif ua.is_pc:
        device_type = 'desktop'
    else:
        device_type = 'web'
    
    device, created = Device.objects.get_or_create(
        user=user,
        device_id=device_id,
        defaults={
            'device_type': device_type,
            'device_name': ua.browser.family or 'Unknown Browser',
            'browser': ua.browser.family,
            'os': ua.os.family,
            'ip_address': ip_address,
            'user_agent': user_agent_string,
            'is_active': True
        }
    )
    
    if not created:
        device.ip_address = ip_address
        device.last_login = timezone.now()
        device.is_active = True
        device.save()
    
    return device


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip