import os
import tempfile
import unittest
from unittest.mock import patch

from scripts import enable_whatsapp_autosend, setup_whatsapp


class SetupWhatsappScriptTests(unittest.TestCase):
    def test_write_env_keeps_autosend_value_explicit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = os.path.join(temp_dir, '.env')
            with patch.object(setup_whatsapp, 'ENV_PATH', env_path):
                setup_whatsapp.write_env({
                    'TWILIO_ACCOUNT_SID': 'sid',
                    'TWILIO_AUTH_TOKEN': 'token',
                    'TWILIO_WHATSAPP_FROM': 'whatsapp:+10000000000',
                    'TWILIO_WHATSAPP_TO': 'whatsapp:+919999999999',
                    'PMA_FETCH_INTERVAL_SECONDS': '300',
                    'PMA_FETCH_MAX_RESULTS': '10',
                    'PMA_AUTO_SEND_WHATSAPP': 'false',
                })

                with open(env_path, 'r', encoding='utf-8') as env_file:
                    contents = env_file.read()

        self.assertIn('TWILIO_ACCOUNT_SID=sid', contents)
        self.assertIn('PMA_AUTO_SEND_WHATSAPP=false', contents)

    @patch('scripts.enable_whatsapp_autosend.whatsapp_config_status')
    def test_enable_autosend_requires_complete_config(self, whatsapp_config_status):
        whatsapp_config_status.return_value = {
            'configured': False,
            'missing': ['TWILIO_ACCOUNT_SID'],
        }

        with patch('sys.stdout'):
            exit_code = enable_whatsapp_autosend.main()

        self.assertEqual(exit_code, 1)


if __name__ == '__main__':
    unittest.main()
