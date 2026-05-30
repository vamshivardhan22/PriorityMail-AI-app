import argparse
import sys

from services.automation_service import run_forever, run_once


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description='PriorityMail AI worker')
    parser.add_argument(
        '--once',
        action='store_true',
        help='run one Gmail check and exit',
    )
    args = parser.parse_args()

    if args.once:
        run_once(verbose=True)
        return

    run_forever()


if __name__ == '__main__':
    main()
