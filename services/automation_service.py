import os
import time
from datetime import datetime

from dotenv import load_dotenv

from .alert_service import rebuild_alerts
from .career_service import rebuild_career_tracker
from .database_service import get_alert_counts, init_db
from .gmail_service import fetch_emails
from .whatsapp_service import (
    send_unsent_alerts_to_whatsapp,
    whatsapp_config_status,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, '.env')


def load_automation_config():
    load_dotenv(ENV_PATH)

    return {
        'interval_seconds': int(os.getenv('PMA_FETCH_INTERVAL_SECONDS', '300')),
        'max_results': int(os.getenv('PMA_FETCH_MAX_RESULTS', '10')),
        'auto_send_whatsapp': os.getenv(
            'PMA_AUTO_SEND_WHATSAPP',
            'false',
        ).strip().lower() == 'true',
    }


def run_once(verbose=True):
    init_db()
    config = load_automation_config()
    started_at = datetime.now().isoformat(timespec='seconds')

    fetch_result = fetch_emails(
        max_results=config['max_results'],
        verbose=verbose,
    )
    career_count = rebuild_career_tracker()
    alert_count = rebuild_alerts()
    alert_counts = get_alert_counts()
    whatsapp_result = None
    whatsapp_status = whatsapp_config_status()

    if config['auto_send_whatsapp'] and whatsapp_status['configured']:
        whatsapp_result = send_unsent_alerts_to_whatsapp()

    result = {
        'started_at': started_at,
        'fetch': fetch_result,
        'career_count': career_count,
        'alert_count': alert_count,
        'alert_counts': alert_counts,
        'whatsapp_configured': whatsapp_status['configured'],
        'auto_send_whatsapp': config['auto_send_whatsapp'],
        'whatsapp': whatsapp_result,
    }

    if verbose:
        print_automation_result(result)

    return result


def run_forever():
    config = load_automation_config()
    print(
        "PriorityMail worker started. "
        f"Interval: {config['interval_seconds']} seconds."
    )

    while True:
        try:
            run_once(verbose=True)
        except Exception as exc:
            print(f"Worker error: {exc}")

        time.sleep(config['interval_seconds'])


def print_automation_result(result):
    print("-" * 50)
    print(f"Run started: {result['started_at']}")
    print(f"Emails fetched: {result['fetch']['fetched']}")
    print(f"Emails saved: {result['fetch']['saved']}")
    print(f"Career records synced: {result['career_count']}")
    print(f"Alerts synced: {result['alert_count']}")
    print(f"Unread alerts: {result['alert_counts']['unread']}")
    print(f"WhatsApp configured: {result['whatsapp_configured']}")
    print(f"Auto-send WhatsApp: {result['auto_send_whatsapp']}")

    if result['whatsapp']:
        print(f"WhatsApp sent: {result['whatsapp']['sent_count']}")
        print(f"WhatsApp skipped: {result['whatsapp']['skipped_count']}")
        print(f"WhatsApp failures: {len(result['whatsapp']['failed'])}")
