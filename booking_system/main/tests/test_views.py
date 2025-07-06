from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch
from django.utils.timezone import now
from django.utils.timezone import make_aware

from ..models import Service, Review, Reservation, ServiceOption, Message
from ..tokens import account_activation_token
from datetime import datetime, timedelta, date

User = get_user_model()

class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.service = Service.objects.create(
            name='Test Service',
            location='Test Location',
            type='Hotel',
            available_from=datetime.today().date(),
            available_to=(datetime.today() + timedelta(days=10)).date(),
        )
        self.option = ServiceOption.objects.create(
            service=self.service,
            name='Standard Room',
            price=100.0,
            capacity=2,
            available_from=make_aware(datetime.now()),
            available_to=make_aware(datetime.now() + timedelta(days=30))
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=2)),
            price=200.0,
            status='pending'
        )
        self.client.login(email='testuser@example.com', password='testpass123')

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_register_view(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_make_reservation_view(self):
        response = self.client.post(reverse('make_reservation', args=[self.service.id]), {
            'option': self.option.id,
            'start_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        })
        self.assertRedirects(response, reverse('service_detail', args=[self.service.id]))

    def test_profile_view(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_logout_view(self):
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))

    def test_service_detail_view(self):
        response = self.client.get(reverse('service_detail', args=[self.service.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service_detail.html')

    def test_my_reservations_view(self):
        response = self.client.get(reverse('my_reservations'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'my_reservations.html')

    def test_my_reviews(self):
        Review.objects.create(user=self.user, service=self.service, rating=5, comment='Great service!')
        response = self.client.get(reverse('my_reviews'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'my_reviews.html')

    def test_contact_admin(self):
        response = self.client.post(reverse('contact_admin'), {
            'subject': 'Test Subject',
            'message': 'Test message content.'
        })
        self.assertRedirects(response, reverse('contact_admin'))
        self.assertEqual(Message.objects.count(), 1)

    def test_delete_account(self):
        response = self.client.post(reverse('delete_account'))
        self.assertRedirects(response, reverse('home'))
        self.assertFalse(User.objects.filter(email='testuser@example.com').exists())

    def test_user_messages(self):
        Message.objects.create(user=self.user, sender='admin', content='Test admin message.')
        response = self.client.get(reverse('user_messages'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_messages.html')

    def test_delete_review(self):
        review = Review.objects.create(user=self.user, service=self.service, rating=5, comment='Good review')
        response = self.client.post(reverse('delete_review', args=[review.id]), {'redirect_to': 'my_reviews'})
        self.assertFalse(Review.objects.filter(id=review.id).exists())
        self.assertRedirects(response, reverse('my_reviews'))


    def test_password_reset_request(self):
        response = self.client.post(reverse('password_reset'), {
            'email': 'testuser@example.com'
        })
        self.assertRedirects(response, reverse('password_reset_done'))


    def test_service_status(self):
        response = self.client.get(reverse('service_status'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service_status.html')


class AccountTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_activate_view_success(self):
        user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='12345',
            is_active=False
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        response = self.client.get(reverse('activate', kwargs={'uidb64': uid, 'token': token}))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertRedirects(response, reverse('login'))

    def test_activate_view_invalid(self):
        response = self.client.get(reverse('activate', kwargs={'uidb64': 'invalid', 'token': 'invalid'}))
        self.assertTemplateUsed(response, 'activation_invalid.html')


class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123',
            is_active=True
        )

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_post_success(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        response = self.client.post(reverse('login'), {
            'username': 'testuser@example.com',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_view_post_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser@example.com',
            'password': 'wrongpass'
        })
        self.assertTemplateUsed(response, 'login.html')


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_logout_view(self):
        user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))


class ServiceDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.service = Service.objects.create(name='Test Service', type='Hotel')

    def test_service_detail_view(self):
        response = self.client.get(reverse('service_detail', args=[self.service.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service_detail.html')


class AddReviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel',
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )
        self.client.force_login(self.user)

    def test_add_review_view_post_failure(self):
        response = self.client.post(reverse('add_review', args=[self.service.id]), {
            'title': '',
            'content': '',
            'rating': 5
        })
        self.assertTemplateUsed(response, 'service_detail.html')
        self.assertContains(response, "Wystąpił błąd podczas dodawania opinii")

    def test_add_review_view_post_success(self):
        response = self.client.post(reverse('add_review', args=[self.service.id]), {
            'rating': 5,
            'comment': 'Great service!'
        })
        self.assertRedirects(response, reverse('service_detail', args=[self.service.id]))


class MakeReservationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email=f'user{timezone.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123',
            balance=5000
        )
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel',
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )
        self.option = ServiceOption.objects.create(
            service=self.service,
            name='Option 1',
            price=100,
            capacity=2,  # Dodaj wartość dla 'capacity'
            available_from=timezone.now(),
            available_to=timezone.now() + timedelta(days=1),
        )
        self.client.force_login(self.user)

    def test_make_reservation_insufficient_balance(self):
        self.user.balance = 10
        self.user.save()
        start_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('make_reservation', args=[self.service.id]), {
            'option': self.option.id,
            'start_date': start_date,
            'end_date': end_date
        })
        # Sprawdzenie przekierowania
        self.assertRedirects(response, reverse('service_detail', args=[self.service.id]))

        # Sprawdzenie, czy wiadomość o błędzie została dodana
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Nie masz wystarczających środków na koncie." in str(m) for m in messages))

    def test_make_reservation_view_post_success(self):
        start_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('make_reservation', args=[self.service.id]), {
            'option': self.option.id,
            'start_date': start_date,
            'end_date': end_date
        })
        self.assertRedirects(response, reverse('service_detail', args=[self.service.id]))

class CancelReservationRequestTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.service = Service.objects.create(name='Test Service', location='Test Location', type='Hotel')
        self.option = ServiceOption.objects.create(service=self.service, name='Option 1', capacity=2, price=100)
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5)),
            status='pending'
        )
        self.client = Client()
        self.client.login(username='testuser@example.com', password='password123')

    def test_cancel_reservation_request(self):
        response = self.client.post(reverse('cancel_reservation_request', args=[self.reservation.id]))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'pending cancellation')
        self.assertRedirects(response, reverse('my_reservations'))


class ConfirmReservationCancellationTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com', first_name='Admin', last_name='User', password='adminpass'
        )
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.service = Service.objects.create(name='Test Service', location='Test Location', type='Hotel')
        self.option = ServiceOption.objects.create(service=self.service, name='Option 1', capacity=2, price=100)
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5)),
            status='pending cancellation'
        )
        self.client = Client()
        self.client.login(username='admin@example.com', password='adminpass')

class AdminReplyTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com', first_name='Admin', last_name='User', password='adminpass'
        )
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.message = Message.objects.create(user=self.user, subject='Test Message', content='Hello')
        self.client = Client()
        self.client.login(username='admin@example.com', password='adminpass')

class RequestChangeDateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.service = Service.objects.create(name='Test Service', location='Test Location', type='Hotel')
        self.option = ServiceOption.objects.create(service=self.service, name='Option 1', capacity=2, price=100)
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5)),
            status='pending'
        )
        self.client = Client()
        self.client.login(username='testuser@example.com', password='password123')

    def test_request_change_date(self):
        new_start = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M')
        new_end = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('request_change_date', args=[self.reservation.id]), {
            'new_start_datetime': new_start,
            'new_end_datetime': new_end
        })
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'pending modification')
        self.assertEqual(self.reservation.new_start_datetime.strftime('%Y-%m-%dT%H:%M'), new_start)
        self.assertEqual(self.reservation.new_end_datetime.strftime('%Y-%m-%dT%H:%M'), new_end)
        self.assertRedirects(response, reverse('my_reservations'))


class CustomPasswordResetConfirmViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.client = Client()


class EmailChangeConfirmTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='old_email@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.client = Client()
        self.client.login(username='old_email@example.com', password='password123')

class ContactAdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser@example.com', password='password123')

    def test_contact_admin(self):
        response = self.client.post(reverse('contact_admin'), {'subject': 'Test Subject', 'message': 'Test Message'})
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.subject, 'Test Subject')
        self.assertEqual(message.content, 'Test Message')
        self.assertRedirects(response, reverse('contact_admin'))


class UserDataTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', first_name='Test', last_name='User', password='password123'
        )
        self.client = Client()
        self.client.login(username='testuser@example.com', password='password123')

    def test_user_data_update(self):
        response = self.client.post(reverse('user_data'), {'update_profile': '', 'first_name': 'NewName', 'last_name': 'NewLastName'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NewName')
        self.assertEqual(self.user.last_name, 'NewLastName')
        self.assertEqual(response.status_code, 200)


class GetServiceOptionsTestCase(TestCase):
    def setUp(self):
        self.service = Service.objects.create(name='Test Service', location='Test Location', type='Hotel')
        self.option1 = ServiceOption.objects.create(service=self.service, name='Option 1', capacity=2, price=100)
        self.option2 = ServiceOption.objects.create(service=self.service, name='Option 2', capacity=4, price=200)
        self.client = Client()

    def test_get_service_options(self):
        response = self.client.get(reverse('get_service_options'), {'type': 'Hotel'})
        self.assertEqual(response.status_code, 200)
        options = response.json().get('options', [])
        self.assertEqual(len(options), 2)
        self.assertIn({'id': self.option1.id, 'name': 'Option 1'}, options)
        self.assertIn({'id': self.option2.id, 'name': 'Option 2'}, options)



