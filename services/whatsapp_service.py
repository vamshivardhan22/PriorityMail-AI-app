import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

try:
    from .database_service import (
        get_alerts,
        mark_alert_whatsapp_failed,
        mark_alert_whatsapp_sent,
    )
except ImportError:
    from database_service import (
        get_alerts,
        mark_alert_whatsapp_failed,
        mark_alert_whatsapp_sent,
    )


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, '.env')


def load_whatsapp_config():
    load_dotenv(ENV_PATH)

    return {
        'account_sid': os.getenv('TWILIO_ACCOUNT_SID', '').strip(),
        'auth_token': os.getenv('TWILIO_AUTH_TOKEN', '').strip(),
        'from_number': os.getenv('TWILIO_WHATSAPP_FROM', '').strip(),
        'to_number': os.getenv('TWILIO_WHATSAPP_TO', '').strip(),
    }


def whatsapp_config_status():
    config = load_whatsapp_config()
    missing = []

    for env_name, key in (
        ('TWILIO_ACCOUNT_SID', 'account_sid'),
        ('TWILIO_AUTH_TOKEN', 'auth_token'),
        ('TWILIO_WHATSAPP_FROM', 'from_number'),
        ('TWILIO_WHATSAPP_TO', 'to_number'),
    ):
        if not config[key]:
            missing.append(env_name)

    return {
        'configured': not missing,
        'missing': missing,
    }


def format_alert_message(alert):
    lines = [
        'PriorityMail AI Alert',
        '',
        f"Title: {alert['title']}",
        f"Type: {alert['alert_type']}",
        f"Severity: {alert['severity']}",
        f"Message: {alert['message']}",
        f"From: {alert['sender']}",
        f"Subject: {alert['subject']}",
    ]

    if alert.get('received_at'):
        lines.append(f"Received: {alert['received_at']}")

    return '\n'.join(lines)


def send_whatsapp_message(text):
    config = load_whatsapp_config()
    status = whatsapp_config_status()

    if not status['configured']:
        raise ValueError(
            'WhatsApp is not configured. Missing: ' + ', '.join(status['missing'])
        )

    endpoint = (
        'https://api.twilio.com/2010-04-01/Accounts/'
        f"{config['account_sid']}/Messages.json"
    )
    payload = urlencode({
        'From': config['from_number'],
        'To': config['to_number'],
        'Body': text,
    }).encode('utf-8')
    credentials = f"{config['account_sid']}:{config['auth_token']}".encode('utf-8')
    auth_header = base64.b64encode(credentials).decode('ascii')

    request = Request(
        endpoint,
        data=payload,
        headers={
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )

    try:
        with urlopen(request, timeout=20) as response:
            response_body = response.read().decode('utf-8')
    except HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f"Twilio API error {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Twilio network error: {exc.reason}") from exc

    return json.loads(response_body)


def send_test_message():
    send_whatsapp_message('PriorityMail AI WhatsApp alerts are connected.')


def send_unsent_alerts_to_whatsapp():
    alerts = get_alerts(status='unread')
    sent_count = 0
    skipped_count = 0
    failed = []

    for alert in alerts:
        if alert.get('whatsapp_sent_at'):
            skipped_count += 1
            continue

        try:
            send_whatsapp_message(format_alert_message(alert))
        except Exception as exc:
            mark_alert_whatsapp_failed(alert['gmail_message_id'], str(exc))
            failed.append({
                'title': alert['title'],
                'error': str(exc),
            })
            continue

        mark_alert_whatsapp_sent(alert['gmail_message_id'])
        sent_count += 1

    return {
        'sent_count': sent_count,
        'skipped_count': skipped_count,
        'failed': failed,
    }
