# your_app/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..forms import RegistrationForm, ReviewForm, EmailChangeForm
from ..models import Service, ServiceOption
from django.utils import timezone

User = get_user_model()

class RegistrationFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='existing@example.com',
            password='password',
            first_name='Existing',
            last_name='User'
        )

    def test_valid_form(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123'
        }
        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertFalse(user.is_active)  # Konto domyślnie nieaktywne

    def test_password_mismatch(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'WrongPass123'
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)

    def test_existing_email(self):
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'existing@example.com',
            'password': 'AnotherPass123',
            'confirm_password': 'AnotherPass123'
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class ReviewFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reviewer@example.com',
            password='reviewerpass',
            first_name='Reviewer',
            last_name='User'
        )
        self.service = Service.objects.create(
            name='Gym Test',
            type='Fitness',
            location='Gym Location'
        )

    def test_valid_review_form(self):
        form_data = {
            'rating': '4',
            'comment': 'Good facilities.'
        }
        form = ReviewForm(data=form_data)
        self.assertTrue(form.is_valid())
        review = form.save(commit=False)
        review.user = self.user
        review.service = self.service
        review.save()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'Good facilities.')

    def test_invalid_rating(self):
        form_data = {
            'rating': '6',  # Invalid rating, should be between 1-5
            'comment': 'Too good!'
        }
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)

class EmailChangeFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='original@example.com',
            password='originalpass',
            first_name='Original',
            last_name='User'
        )
        User.objects.create_user(
            email='existing@example.com',
            password='password',
            first_name='Existing',
            last_name='User'
        )

    def test_valid_email_change(self):
        form_data = {
            'new_email': 'new@example.com'
        }
        form = EmailChangeForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        new_email = form.cleaned_data['new_email']
        self.assertEqual(new_email, 'new@example.com')

    def test_existing_email(self):
        form_data = {
            'new_email': 'existing@example.com'
        }
        form = EmailChangeForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('new_email', form.errors)
