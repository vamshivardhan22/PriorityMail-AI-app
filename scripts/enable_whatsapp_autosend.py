import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

from services.whatsapp_service import whatsapp_config_status


def main():
    status = whatsapp_config_status()
    if not status['configured']:
        print('WhatsApp cannot be enabled yet.')
        print('Missing: ' + ', '.join(status['missing']))
        return 1

    if not os.path.exists(ENV_PATH):
        print('.env not found. Run python .\\scripts\\setup_whatsapp.py first.')
        return 1

    with open(ENV_PATH, 'r', encoding='utf-8') as env_file:
        lines = env_file.readlines()

    updated = False
    output = []
    for line in lines:
        if line.startswith('PMA_AUTO_SEND_WHATSAPP='):
            output.append('PMA_AUTO_SEND_WHATSAPP=true\n')
            updated = True
        else:
            output.append(line)

    if not updated:
        output.append('PMA_AUTO_SEND_WHATSAPP=true\n')

    with open(ENV_PATH, 'w', encoding='utf-8') as env_file:
        env_file.writelines(output)

    print('WhatsApp auto-send is enabled.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
