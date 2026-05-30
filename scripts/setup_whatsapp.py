import getpass
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

REQUIRED_KEYS = (
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_WHATSAPP_FROM',
    'TWILIO_WHATSAPP_TO',
)


def read_existing_env():
    values = {}

    if not os.path.exists(ENV_PATH):
        return values

    with open(ENV_PATH, 'r', encoding='utf-8') as env_file:
        for line in env_file:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue

            key, value = stripped.split('=', 1)
            values[key] = value

    return values


def prompt_value(key, current_value=''):
    masked = ' already set' if current_value else ''
    prompt = f'{key}{masked}: '

    if key == 'TWILIO_AUTH_TOKEN':
        value = getpass.getpass(prompt)
    else:
        value = input(prompt).strip()

    return value or current_value


def write_env(values):
    lines = [
        f"TWILIO_ACCOUNT_SID={values.get('TWILIO_ACCOUNT_SID', '')}",
        f"TWILIO_AUTH_TOKEN={values.get('TWILIO_AUTH_TOKEN', '')}",
        f"TWILIO_WHATSAPP_FROM={values.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')}",
        f"TWILIO_WHATSAPP_TO={values.get('TWILIO_WHATSAPP_TO', '')}",
        f"PMA_FETCH_INTERVAL_SECONDS={values.get('PMA_FETCH_INTERVAL_SECONDS', '300')}",
        f"PMA_FETCH_MAX_RESULTS={values.get('PMA_FETCH_MAX_RESULTS', '10')}",
        f"PMA_AUTO_SEND_WHATSAPP={values.get('PMA_AUTO_SEND_WHATSAPP', 'false')}",
    ]

    with open(ENV_PATH, 'w', encoding='utf-8') as env_file:
        env_file.write('\n'.join(lines) + '\n')


def main():
    values = read_existing_env()
    values.setdefault('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
    values.setdefault('PMA_FETCH_INTERVAL_SECONDS', '300')
    values.setdefault('PMA_FETCH_MAX_RESULTS', '10')
    values['PMA_AUTO_SEND_WHATSAPP'] = 'false'

    print('Enter Twilio WhatsApp settings. Leave a value blank to keep the current value.')
    print('WhatsApp auto-send will stay off until you test successfully.')

    for key in REQUIRED_KEYS:
        values[key] = prompt_value(key, values.get(key, '')).strip()

    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    write_env(values)

    if missing:
        print('.env was saved, but WhatsApp is still incomplete.')
        print('Missing: ' + ', '.join(missing))
        return 1

    print('.env was saved with WhatsApp auto-send still disabled.')
    print('Next: python .\\scripts\\check_whatsapp.py --send-test')
    print('After the test succeeds, set PMA_AUTO_SEND_WHATSAPP=true in .env.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
