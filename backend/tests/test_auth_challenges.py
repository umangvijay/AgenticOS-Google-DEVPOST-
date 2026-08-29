"""Unit tests for HITL challenge classification (never solves CAPTCHA/OTP/MFA)."""

import unittest

from backend.services.auth_challenges import classify_auth_challenge, challenge_user_message


class ChallengeClassificationTests(unittest.TestCase):
    def test_captcha_from_text(self):
        kind = classify_auth_challenge({"text": "Please verify you are human", "title": "Just a moment", "url": "https://example.com"})
        self.assertEqual(kind, "captcha")

    def test_recaptcha_iframe(self):
        kind = classify_auth_challenge({"text": "", "iframes": ["https://www.google.com/recaptcha/api2/anchor"]})
        self.assertEqual(kind, "captcha")

    def test_otp(self):
        kind = classify_auth_challenge({"text": "Enter the 6-digit verification code we sent", "url": "https://app.example/verify"})
        self.assertEqual(kind, "otp")

    def test_mfa(self):
        kind = classify_auth_challenge({"text": "Open your authenticator app and enter the code", "title": "Two-factor authentication"})
        self.assertEqual(kind, "mfa")

    def test_plain_page_is_not_a_challenge(self):
        kind = classify_auth_challenge({"text": "Example Domain. This domain is for use in illustrative examples.", "title": "Example Domain", "url": "https://example.com/"})
        self.assertIsNone(kind)

    def test_message_tells_user_to_resume(self):
        msg = challenge_user_message("captcha", "https://example.com/login")
        self.assertIn("Resume", msg)
        self.assertIn("will not fill", msg.lower())


if __name__ == "__main__":
    unittest.main()
