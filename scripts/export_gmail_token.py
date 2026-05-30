import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(PROJECT_ROOT, 'token.json')


def main():
    if not os.path.exists(TOKEN_PATH):
        print('token.json was not found. Run python worker.py --once locally first.')
        return 1

    with open(TOKEN_PATH, 'r', encoding='utf-8') as token_file:
        token_data = json.load(token_file)

    print('Copy this into Streamlit Cloud Secrets:')
    print()
    print('[gmail]')
    print("token_json = '''")
    print(json.dumps(token_data, indent=2))
    print("'''")
    return 0


if __name__ == '__main__':
    sys.exit(main())
