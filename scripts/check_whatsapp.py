import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.whatsapp_service import send_test_message, whatsapp_config_status


def main():
    parser = argparse.ArgumentParser(
        description='Check PriorityMail AI WhatsApp alert configuration.'
    )
    parser.add_argument(
        '--send-test',
        action='store_true',
        help='send one WhatsApp test message if Twilio is configured',
    )
    args = parser.parse_args()

    status = whatsapp_config_status()

    if not status['configured']:
        print('WhatsApp is not configured.')
        print('Missing: ' + ', '.join(status['missing']))
        print('No message was sent.')
        return 1

    print('WhatsApp configuration is complete.')

    if not args.send_test:
        print('No message was sent. Add --send-test to send one test alert.')
        return 0

    send_test_message()
    print('Test WhatsApp message sent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
