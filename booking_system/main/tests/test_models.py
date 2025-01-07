# your_app/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Service, ServiceOption, Reservation, Review, Message
from django.utils import timezone

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            balance=1000
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, 'testuser@example.com')
        self.assertTrue(self.user.check_password('testpassword123'))
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.balance, 1000)
        self.assertFalse(self.user.is_active)  # Jeśli konto jest domyślnie nieaktywne

class ServiceModelTest(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            name='Hotel Test',
            type='Hotel',
            location='Test Location'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Standard Room',
            capacity=2,
            price=200.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=30)
        )

    def test_service_creation(self):
        self.assertEqual(self.service.name, 'Hotel Test')
        self.assertEqual(self.service.type, 'Hotel')
        self.assertEqual(self.service.location, 'Test Location')
        self.assertIn(self.service_option, self.service.service_options.all())

    def test_service_option_creation(self):
        self.assertEqual(self.service_option.name, 'Standard Room')
        self.assertEqual(self.service_option.capacity, 2)
        self.assertEqual(self.service_option.price, 200.00)

class ReservationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reserver@example.com',
            password='reservepassword',
            first_name='Reserver',
            last_name='User',
            balance=500
        )
        self.service = Service.objects.create(
            name='SPA Test',
            type='SPA&WELLNESS',
            location='Wellness Center'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Massage Package',
            capacity=1,
            price=150.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=60)
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.service_option,
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            end_datetime=timezone.now() + timezone.timedelta(days=2),
            status='confirmed',
            price=150.00
        )

    def test_reservation_creation(self):
        self.assertEqual(self.reservation.user, self.user)
        self.assertEqual(self.reservation.option, self.service_option)
        self.assertEqual(self.reservation.status, 'confirmed')
        self.assertEqual(self.reservation.price, 150.00)

class ReviewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reviewer@example.com',
            password='reviewerpass123',
            first_name='Reviewer',
            last_name='User'
        )
        self.service = Service.objects.create(
            name='Restaurant Test',
            type='Restauracja',
            location='Food Court'
        )
        self.review = Review.objects.create(
            user=self.user,
            service=self.service,
            rating=5,
            comment='Excellent service!'
        )

    def test_review_creation(self):
        self.assertEqual(self.review.user, self.user)
        self.assertEqual(self.review.service, self.service)
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Excellent service!')

class MessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='messenger@example.com',
            password='messagepassword',
            first_name='Messenger',
            last_name='User'
        )
        self.message = Message.objects.create(
            user=self.user,
            subject='Test Subject',
            content='This is a test message.',
            sender='user'
        )

    def test_message_creation(self):
        self.assertEqual(self.message.user, self.user)
        self.assertEqual(self.message.subject, 'Test Subject')
        self.assertEqual(self.message.content, 'This is a test message.')
        self.assertEqual(self.message.sender, 'user')
        self.assertFalse(self.message.is_read)
        self.assertIsNone(self.message.response_date)
