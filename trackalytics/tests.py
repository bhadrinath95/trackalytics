from django.test import TestCase
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
import os
from django.core.exceptions import ValidationError


class TrackAlyticsTest(TestCase):

    def test_secret_key_strength(self):
        _secret_key = os.environ.get('DJANGO_SECRET_KEY')
        try:
            validate_password(_secret_key)
        except ValidationError as e:
            self.fail(f"SECRET_KEY is not strong enough: {e}")
