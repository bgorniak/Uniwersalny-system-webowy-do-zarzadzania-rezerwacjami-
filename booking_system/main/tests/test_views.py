# your_app/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Service, ServiceOption, Reservation
from django.utils import timezone

User = get_user_model()

class RegistrationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')

    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')  # Upewnij się, że szablon istnieje w odpowiedniej lokalizacji

    def test_register_view_post_valid(self):
        form_data = {
            'first_name': 'Alice',
            'last_name': 'Wonderland',
            'email': 'alice@example.com',
            'password': 'SecurePass123',
            'confirm_password': 'SecurePass123'
        }
        response = self.client.post(self.register_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect po udanej rejestracji
        user = User.objects.get(email='alice@example.com')
        self.assertFalse(user.is_active)  # Konto domyślnie nieaktywne

    def test_register_view_post_invalid(self):
        form_data = {
            'first_name': '',
            'last_name': '',
            'email': 'invalid-email',
            'password': 'pass',
            'confirm_password': 'different'
        }
        response = self.client.post(self.register_url, data=form_data)
        self.assertEqual(response.status_code, 200)  # Formularz z błędami
        self.assertFormError(response, 'form', 'first_name', 'To pole jest wymagane.')
        self.assertFormError(response, 'form', 'last_name', 'To pole jest wymagane.')
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')
        self.assertFormError(response, 'form', 'password', 'This password is too short. It must contain at least 8 characters.')
        self.assertFormError(response, 'form', 'confirm_password', 'Hasła muszą być takie same.')

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.user = User.objects.create_user(
            email='loginuser@example.com',
            password='loginpass123',
            first_name='Login',
            last_name='User',
            is_active=True
        )

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_view_post_valid(self):
        form_data = {
            'username': 'loginuser@example.com',
            'password': 'loginpass123'
        }
        response = self.client.post(self.login_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect po udanym logowaniu

    def test_login_view_post_invalid(self):
        form_data = {
            'username': 'loginuser@example.com',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', None, 'Błędny adres email lub hasło.')

class ReservationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='reserver@example.com',
            password='reservepass123',
            first_name='Reserver',
            last_name='User',
            is_active=True,
            balance=500
        )
        self.service = Service.objects.create(
            name='Hotel Deluxe',
            type='Hotel',
            location='Luxury District'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Deluxe Room',
            capacity=2,
            price=300.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=365)
        )
        self.reservation_url = reverse('make_reservation')

    def test_make_reservation_view_get(self):
        self.client.login(email='reserver@example.com', password='reservepass123')
        response = self.client.get(self.reservation_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reservations/make_reservation.html')

    def test_make_reservation_view_post_valid(self):
        self.client.login(email='reserver@example.com', password='reservepass123')
        form_data = {
            'option': self.service_option.id,
            'start_datetime': timezone.now() + timezone.timedelta(days=10),
            'end_datetime': timezone.now() + timezone.timedelta(days=12),
        }
        response = self.client.post(self.reservation_url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect po udanej rezerwacji
        reservation = Reservation.objects.get(user=self.user, option=self.service_option)
        self.assertEqual(reservation.status, 'confirmed')
        self.assertEqual(reservation.price, 300.00)
        # Zakładając, że saldo jest aktualizowane po rezerwacji
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, 200)

    def test_make_reservation_view_post_insufficient_balance(self):
        self.user.balance = 100
        self.user.save()
        self.client.login(email='reserver@example.com', password='reservepass123')
        form_data = {
            'option': self.service_option.id,
            'start_datetime': timezone.now() + timezone.timedelta(days=10),
            'end_datetime': timezone.now() + timezone.timedelta(days=12),
        }
        response = self.client.post(self.reservation_url, data=form_data)
        self.assertEqual(response.status_code, 200)  # Formularz z błędami
        self.assertFormError(response, 'form', None, 'Insufficient balance to make this reservation.')
