import unittest
from unittest.mock import patch

from scripts import check_whatsapp


class CheckWhatsappScriptTests(unittest.TestCase):
    @patch('scripts.check_whatsapp.whatsapp_config_status')
    def test_reports_missing_config_without_sending(self, whatsapp_config_status):
        whatsapp_config_status.return_value = {
            'configured': False,
            'missing': ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN'],
        }

        with patch('sys.argv', ['check_whatsapp.py']), patch('sys.stdout'):
            exit_code = check_whatsapp.main()

        self.assertEqual(exit_code, 1)

    @patch('scripts.check_whatsapp.send_test_message')
    @patch('scripts.check_whatsapp.whatsapp_config_status')
    def test_configured_check_does_not_send_without_flag(
        self,
        whatsapp_config_status,
        send_test_message,
    ):
        whatsapp_config_status.return_value = {
            'configured': True,
            'missing': [],
        }

        with patch('sys.argv', ['check_whatsapp.py']), patch('sys.stdout'):
            exit_code = check_whatsapp.main()

        self.assertEqual(exit_code, 0)
        send_test_message.assert_not_called()

    @patch('scripts.check_whatsapp.send_test_message')
    @patch('scripts.check_whatsapp.whatsapp_config_status')
    def test_send_test_flag_sends_only_when_configured(
        self,
        whatsapp_config_status,
        send_test_message,
    ):
        whatsapp_config_status.return_value = {
            'configured': True,
            'missing': [],
        }

        with patch('sys.argv', ['check_whatsapp.py', '--send-test']), patch('sys.stdout'):
            exit_code = check_whatsapp.main()

        self.assertEqual(exit_code, 0)
        send_test_message.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
