import unittest
from unittest.mock import patch

from services import gmail_service


class GmailCloudConfigTests(unittest.TestCase):
    def test_parse_json_value_accepts_dict(self):
        value = {'token': 'abc'}

        self.assertEqual(
            gmail_service.parse_json_value(value, 'secret'),
            {'token': 'abc'},
        )

    def test_parse_json_value_accepts_json_string(self):
        value = '{"token": "abc"}'

        self.assertEqual(
            gmail_service.parse_json_value(value, 'secret'),
            {'token': 'abc'},
        )

    def test_token_info_has_required_scopes(self):
        token_data = {
            'scope': 'https://www.googleapis.com/auth/gmail.modify',
        }

        self.assertTrue(gmail_service.token_info_has_required_scopes(token_data))

    @patch('services.gmail_service.load_secret_token_info')
    def test_token_has_required_scopes_prefers_streamlit_secret(self, load_secret_token_info):
        load_secret_token_info.return_value = {
            'scope': 'https://www.googleapis.com/auth/gmail.modify',
        }

        self.assertTrue(gmail_service.token_has_required_scopes())


if __name__ == '__main__':
    unittest.main()
