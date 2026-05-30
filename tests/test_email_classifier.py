import unittest

from services.email_classifier import classify_email


class EmailClassifierTests(unittest.TestCase):
    def test_nxtwave_opportunity_digest_classifies_as_job(self):
        result = classify_email(
            sender='NxtWave <updates@nxtwave.co.in>',
            subject='Fresh job opportunities for your profile',
            snippet='Apply to hiring opportunities before the deadline.',
        )

        self.assertEqual(result.category, 'job')
        self.assertEqual(result.priority, 'high')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_internshala_invitation_classifies_as_job(self):
        result = classify_email(
            sender='Internshala <student@mail.internshala.com>',
            subject='Update: Your Invitation from HCL Tech | Confirm your spot.',
            snippet='Confirm your spot for the hiring opportunity.',
        )

        self.assertEqual(result.category, 'job')
        self.assertEqual(result.priority, 'high')
        self.assertGreaterEqual(result.confidence, 0.9)


if __name__ == '__main__':
    unittest.main()
