
import unittest
from django.contrib.auth.models import User
from django.utils.http import int_to_base36
from django.utils.timezone import now
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import TestCase

from ..tokens import AccountActivationTokenGenerator


class MockUser:
    def __init__(self, pk, is_active):
        self.pk = pk
        self.is_active = is_active

class TestAccountActivationTokenGenerator(TestCase):
    def setUp(self):
        self.token_generator = AccountActivationTokenGenerator()

    def test_make_hash_value_active_user(self):
        user = MockUser(pk=1, is_active=True)
        timestamp = int(now().timestamp())
        expected_hash = f"{user.pk}{timestamp}{user.is_active}"
        result = self.token_generator._make_hash_value(user, timestamp)
        self.assertEqual(expected_hash, result)

    def test_make_hash_value_inactive_user(self):
        user = MockUser(pk=2, is_active=False)
        timestamp = int(now().timestamp())
        expected_hash = f"{user.pk}{timestamp}{user.is_active}"
        result = self.token_generator._make_hash_value(user, timestamp)
        self.assertEqual(expected_hash, result)

    def test_check_token_valid(self):
        user = MockUser(pk=3, is_active=True)
        timestamp = int(now().timestamp())
        token = self.token_generator.make_token(user)
        self.assertTrue(self.token_generator.check_token(user, token))

    def test_check_token_invalid_due_to_user(self):
        user1 = MockUser(pk=4, is_active=True)
        user2 = MockUser(pk=5, is_active=True)
        token = self.token_generator.make_token(user1)
        self.assertFalse(self.token_generator.check_token(user2, token))

    def test_check_token_invalid_due_to_time(self):
        user = MockUser(pk=6, is_active=True)
        timestamp = int(now().timestamp()) - (60 * 60)
        token = f"{int_to_base36(timestamp)}-xyz"
        self.assertFalse(self.token_generator.check_token(user, token))

unittest.main(argv=[''], exit=False)
