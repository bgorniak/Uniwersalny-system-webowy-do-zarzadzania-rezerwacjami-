import unittest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import ValidationError, HiddenInput
from django.test import RequestFactory, TestCase
from django.utils import timezone

from ..forms import (
    CustomAuthenticationForm,
    RegistrationForm,
    UserUpdateForm,
    ServiceOptionForm,
    ServiceDetailForm,
    ReviewForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    EmailChangeForm,
    MessageForm,
    ServiceAdminForm,
    ReservationAdminForm
)
from ..models import Message, ServiceOption, Review, Reservation, Service


User = get_user_model()

class TestCustomAuthenticationForm(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            first_name='Test',
            last_name='User',
            password='password'  # Hasło ustawione poprawnie
        )

    def test_valid_authentication(self):
        form_data = {'username': 'user@example.com', 'password': 'password'}
        form = CustomAuthenticationForm(request=self.factory.post('/login/'), data=form_data)
        self.assertTrue(form.is_valid())  # Formularz powinien być poprawny

    def test_invalid_authentication(self):
        form_data = {'username': 'user@example.com', 'password': 'wrong_password'}
        form = CustomAuthenticationForm(request=self.factory.post('/login/'), data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'][0], "Błędny adres email lub hasło.")


class TestRegistrationForm(TestCase):
    def test_valid_registration(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'ComplexPass!23',
            'confirm_password': 'ComplexPass!23'
        }
        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'ComplexPass!23',
            'confirm_password': 'ComplexPass!22'
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Hasła muszą być takie same.', form.errors['confirm_password'])


    def test_invalid_password(self):
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'simple',
            'confirm_password': 'simple'
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(len(form.errors['password']) > 0)


class TestUserUpdateForm(TestCase):
    def test_valid_data(self):
        form_data = {'first_name': 'Jane', 'last_name': 'Doe'}
        form = UserUpdateForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_first_name(self):
        form_data = {'last_name': 'Doe'}
        form = UserUpdateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class TestServiceOptionForm(TestCase):
    def test_valid_data(self):
        service = Service.objects.create(name="Test Service")
        form_data = {
            'service': service.id,
            'name': 'Option 1',
            'capacity': 10,
            'price': 50.0,
            'available_from': date.today(),
            'available_to': date.today() + timedelta(days=5)
        }
        form = ServiceOptionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_date(self):
        service = Service.objects.create(name="Test Service")
        form_data = {
            'service': service.id,
            'name': 'Option 1',
            'capacity': 10,
            'price': 50.0,
            'available_from': date.today() + timedelta(days=5),
            'available_to': date.today()
        }
        form = ServiceOptionForm(data=form_data)
        self.assertFalse(form.is_valid())


class TestServiceDetailForm(TestCase):
    def test_valid_date(self):
        form_data = {'date': date.today() + timedelta(days=1)}
        form = ServiceDetailForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_past_date(self):
        form_data = {'date': date.today() - timedelta(days=1)}
        form = ServiceDetailForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Nie można wybrać daty z przeszłości.', form.errors['date'])


class TestReviewForm(TestCase):
    def test_valid_data(self):
        form_data = {'rating': 5, 'comment': 'Great service!'}
        form = ReviewForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_rating(self):
        form_data = {'rating': 6, 'comment': 'Great service!'}
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_missing_comment(self):
        form_data = {'rating': 4}
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('comment', form.errors)


class TestCustomPasswordResetForm(TestCase):
    def test_nonexistent_email(self):
        form_data = {'email': 'nonexistent@example.com'}
        form = CustomPasswordResetForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Podany adres e-mail nie istnieje w naszej bazie danych.', form.errors['email'])


class TestCustomSetPasswordForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
                email=f'user{timezone.now().timestamp()}@example.com',
                first_name='Test',
                last_name='User',
                password='password'
            )

    def test_valid_password_change(self):
        form_data = {'new_password1': 'newpassword123!', 'new_password2': 'newpassword123!'}
        form = CustomSetPasswordForm(user=self.user, data=form_data)
        self.assertTrue(form.is_valid())

    def test_new_password_same_as_old(self):
        form_data = {'new_password1': 'password', 'new_password2': 'password'}
        form = CustomSetPasswordForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Nowe hasło nie może być takie samo jak poprzednie.', form.errors['new_password1'])


class TestEmailChangeForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='password'
        )

    def test_email_already_registered(self):
        # Tworzymy użytkownika z adresem e-mail
        existing_email = 'user@example.com'
        User.objects.create_user(
            email=existing_email,
            first_name='Existing',
            last_name='User',
            password='password'
        )

        # Dane formularza z tym samym e-mailem
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': existing_email,
            'password': 'ComplexPass!23',
            'confirm_password': 'ComplexPass!23'
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())  # Formularz powinien być niepoprawny
        self.assertIn('Podany adres e-mail jest już zarejestrowany.', form.errors['email'])

    def test_existing_email(self):
        # Create a user with a known email
        self.user = User.objects.create_user(
            email='user@example.com',  # Ensure this matches the test form data
            first_name='Test',
            last_name='User',
            password='password123'
        )

        # Use the same email in the form data
        form_data = {'email': 'user@example.com'}
        form = CustomPasswordResetForm(data=form_data)

        # Debug form errors if validation fails
        if not form.is_valid():
            print("Form Errors:", form.errors)

        self.assertTrue(form.is_valid())  # Assert form validity
    def test_email_already_exists(self):
        User.objects.create_user(email='taken@example.com', first_name='Taken', last_name='User', password='password')
        form_data = {'new_email': 'taken@example.com'}
        form = EmailChangeForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Podany adres e-mail jest już zajęty.', form.errors['new_email'])

    def test_valid_email_change(self):
        form_data = {'new_email': 'newemail@example.com'}
        form = EmailChangeForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())


class TestMessageForm(TestCase):
    def test_valid_data(self):
        form_data = {'subject': 'Subject Test', 'content': 'Content Test'}
        form = MessageForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_content(self):
        form_data = {'subject': 'Subject Test'}
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)


class TestServiceAdminForm(TestCase):
    def test_hotel_service(self):
        service = Service.objects.create(type='Hotel', name='Hotel Test')  # Added required 'name' field
        form = ServiceAdminForm(instance=service)
        self.assertFalse(form.fields['available_dates'].widget.is_hidden)
        self.assertTrue(form.fields['room_types'].required)

    def test_other_service(self):
        service = Service.objects.create(type='Restauracja', name='Restauracja Test')  # Dodano wymagane 'name'
        form = ServiceAdminForm(instance=service)
        self.assertFalse(form.fields['available_dates'].widget.is_hidden)  # Sprawdzanie, czy pole nie jest ukryte
        self.assertIsInstance(form.fields['room_types'].widget, HiddenInput)  # Sprawdzanie, czy widget to HiddenInput


class TestReservationAdminForm(TestCase):
    def test_missing_message_content(self):
        # Create necessary instances
        service = Service.objects.create(
            name='Test Hotel',
            location='Test Location',
            type='Hotel',
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )

        option = ServiceOption.objects.create(
            service=service,
            name='Option 1',
            price=100,
            capacity=2,
            available_from=timezone.now(),
            available_to=timezone.now() + timedelta(days=10),
        )

        user = User.objects.create_user(
            email='user@example.com',
            first_name='Test',
            last_name='User',
            password='password123',
        )

        form_data = {
            'user': user.id,  # Required field
            'option': option.id,  # Link to the created option
            'start_datetime': timezone.now(),  # Required field
            'status': 'pending',  # Required field
            'price': 100,  # Required field
        }
        form = ReservationAdminForm(data=form_data)

        # Debug form errors if the test fails
        if not form.is_valid():
            print("Form Errors:", form.errors)

        self.assertTrue(form.is_valid())  # Assert form validity

    def test_valid_message_content(self):
        user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='password123'
        )
        service = Service.objects.create(name='Test Service')
        option = ServiceOption.objects.create(
            service=service,
            name='Option 1',
            price=100,
            capacity=2,
            available_from=timezone.now(),
            available_to=timezone.now() + timedelta(days=10)
        )

        form_data = {
            'message_content': 'This is a test message.',
            'user': user.id,
            'option': option.id,
            'start_datetime': timezone.now(),
            'end_datetime': timezone.now() + timedelta(days=1),
            'status': 'pending',  # Add status field
            'price': 100.0,  # Add price field
        }
        form = ReservationAdminForm(data=form_data)

        # Print errors to debug if form is invalid
        if not form.is_valid():
            print("Form Errors:", form.errors)

        self.assertTrue(form.is_valid())

if __name__ == '__main__':
    unittest.main()
