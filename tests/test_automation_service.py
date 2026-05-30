import unittest
from unittest.mock import patch

from services import automation_service


class AutomationServiceTests(unittest.TestCase):
    @patch('services.automation_service.whatsapp_config_status')
    @patch('services.automation_service.get_alert_counts')
    @patch('services.automation_service.rebuild_alerts')
    @patch('services.automation_service.rebuild_career_tracker')
    @patch('services.automation_service.fetch_emails')
    @patch('services.automation_service.init_db')
    @patch('services.automation_service.load_automation_config')
    def test_run_once_syncs_email_records_and_leaves_whatsapp_off(
        self,
        load_config,
        init_db,
        fetch_emails,
        rebuild_career_tracker,
        rebuild_alerts,
        get_alert_counts,
        whatsapp_config_status,
    ):
        load_config.return_value = {
            'interval_seconds': 300,
            'max_results': 7,
            'auto_send_whatsapp': False,
        }
        fetch_emails.return_value = {
            'fetched': 3,
            'saved': 2,
            'category_counts': {'job': 2},
        }
        rebuild_career_tracker.return_value = 2
        rebuild_alerts.return_value = 2
        get_alert_counts.return_value = {
            'total': 2,
            'unread': 2,
            'high': 2,
            'career': 2,
        }
        whatsapp_config_status.return_value = {
            'configured': False,
            'missing': ['TWILIO_ACCOUNT_SID'],
        }

        result = automation_service.run_once(verbose=False)

        init_db.assert_called_once_with()
        fetch_emails.assert_called_once_with(max_results=7, verbose=False)
        rebuild_career_tracker.assert_called_once_with()
        rebuild_alerts.assert_called_once_with()
        get_alert_counts.assert_called_once_with()
        self.assertEqual(result['career_count'], 2)
        self.assertEqual(result['alert_count'], 2)
        self.assertFalse(result['auto_send_whatsapp'])
        self.assertFalse(result['whatsapp_configured'])
        self.assertIsNone(result['whatsapp'])

    @patch('services.automation_service.send_unsent_alerts_to_whatsapp')
    @patch('services.automation_service.whatsapp_config_status')
    @patch('services.automation_service.get_alert_counts')
    @patch('services.automation_service.rebuild_alerts')
    @patch('services.automation_service.rebuild_career_tracker')
    @patch('services.automation_service.fetch_emails')
    @patch('services.automation_service.init_db')
    @patch('services.automation_service.load_automation_config')
    def test_run_once_sends_whatsapp_only_when_enabled_and_configured(
        self,
        load_config,
        init_db,
        fetch_emails,
        rebuild_career_tracker,
        rebuild_alerts,
        get_alert_counts,
        whatsapp_config_status,
        send_unsent_alerts_to_whatsapp,
    ):
        load_config.return_value = {
            'interval_seconds': 300,
            'max_results': 10,
            'auto_send_whatsapp': True,
        }
        fetch_emails.return_value = {
            'fetched': 1,
            'saved': 1,
            'category_counts': {'important': 1},
        }
        rebuild_career_tracker.return_value = 0
        rebuild_alerts.return_value = 1
        get_alert_counts.return_value = {
            'total': 1,
            'unread': 1,
            'high': 1,
            'career': 0,
        }
        whatsapp_config_status.return_value = {
            'configured': True,
            'missing': [],
        }
        send_unsent_alerts_to_whatsapp.return_value = {
            'sent_count': 1,
            'skipped_count': 0,
            'failed': [],
        }

        result = automation_service.run_once(verbose=False)

        send_unsent_alerts_to_whatsapp.assert_called_once_with()
        self.assertEqual(result['whatsapp']['sent_count'], 1)
        self.assertTrue(result['auto_send_whatsapp'])
        self.assertTrue(result['whatsapp_configured'])


if __name__ == '__main__':
    unittest.main()
