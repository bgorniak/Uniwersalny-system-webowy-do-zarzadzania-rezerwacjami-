import unittest
from datetime import date, timedelta, datetime
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import make_aware, now
from ..models import UserManager, User, Service, ServiceOption, Reservation, Review, Message, ServiceStatus


class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.user_manager = UserManager()


    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            self.user_manager.create_user(email='', first_name='Test', last_name='User', password='password123')


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.service = Service(
            name='Hotel Service',
            location='Test Location',
            type='Hotel',
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )

    def test_service_creation(self):
        self.assertEqual(str(self.service), 'Hotel Service')


class ServiceOptionTestCase(unittest.TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel',
        )
        self.service_option = ServiceOption(
            service=self.service,
            name='Room Option',
            capacity=2,
            price=100.0,
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )

    def test_clean_valid_dates(self):
        try:
            self.service_option.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    def test_clean_invalid_dates(self):
        self.service_option.available_from = date.today() + timedelta(days=5)
        self.service_option.available_to = date.today()
        with self.assertRaises(ValidationError):
            self.service_option.clean()


class ReservationTestCase(unittest.TestCase):
    def setUp(self):
        self.email = f'user{timezone.now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=self.email,
            first_name='Test',
            last_name='User',
            password='password123'
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
            name='Room Option',
            capacity=2,
            price=100.0,
        )
        self.reservation = Reservation(
            user=self.user,
            service=self.service,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5)),
        )

    def test_clean_valid_dates(self):
        try:
            self.reservation.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    def test_clean_start_date_in_past(self):
        self.reservation.start_datetime = make_aware(datetime.now() - timedelta(days=1))
        with self.assertRaises(ValidationError):
            self.reservation.clean()

    def test_clean_end_date_before_start_date(self):
        self.reservation.end_datetime = self.reservation.start_datetime - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.reservation.clean()


class ReviewTestCase(unittest.TestCase):
    def setUp(self):
        self.email = f'user{timezone.now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=self.email,
            first_name='Reviewer',
            last_name='User',
            password='password123'
        )
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel',
            available_from=date.today(),
            available_to=date.today() + timedelta(days=10),
        )
        self.review = Review(
            user=self.user,
            service=self.service,
            comment='Great service!',
            rating=5
        )

    def test_review_creation(self):
        self.assertEqual(str(self.review), f"Opinia 5/5 od {self.email} dla Hotel Service")


class MessageTestCase(unittest.TestCase):
    def setUp(self):
        self.email = f'user{timezone.now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=self.email,
            first_name='Messager',
            last_name='User',
            password='password123'
        )
        self.message = Message(
            user=self.user,
            subject='Test Message',
            sender='admin',
            content='This is a test message.'
        )

    def test_message_creation(self):
        self.assertEqual(self.message.subject, 'Test Message')
        self.assertEqual(self.message.content, 'This is a test message.')

class UserStrTestCase(unittest.TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='password123'
        )

    def test_user_str(self):
        self.assertEqual(str(self.user), 'Test User')


class ServiceMinPriceTestCase(unittest.TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel'
        )

    def test_get_min_price_no_options(self):
        self.assertEqual(self.service.get_min_price(), 0)


class ServiceOptionStrTestCase(unittest.TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Luxury Room',
            capacity=10,
            price=1000.0
        )

    def test_service_option_str(self):
        self.assertEqual(str(self.service_option), 'Luxury Room - 10 osób - 1000.0 zł')


class MessageAutoLinkTestCase(unittest.TestCase):
    def setUp(self):
        unique_email = f'testuser{now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=unique_email,
            first_name='Test',
            last_name='User',
            password='password123'
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            service_name='Hotel Service',
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5))
        )
        self.message = Message.objects.create(
            user=self.user,
            subject='Test Message',
            sender='admin',
            content='This is a test message.'
        )

    def test_auto_link_reservation(self):
        self.message.save()
        self.assertIn(self.reservation, self.message.reservations.all())


class ReservationStatusTestCase(unittest.TestCase):
    def setUp(self):
        unique_email = f'testuser{now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=unique_email,
            first_name='Test',
            last_name='User',
            password='password123'
        )
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel'
        )
        self.option = ServiceOption.objects.create(
            service=self.service,
            name='Standard Room',
            capacity=2,
            price=100.0
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            service=self.service,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=5)),
            status='pending'
        )

    def test_reservation_status_change(self):
        self.reservation.status = 'confirmed'
        self.reservation.save()
        self.assertEqual(self.reservation.status, 'confirmed')


class ReviewRatingValidationTestCase(unittest.TestCase):
    def setUp(self):
        unique_email = f'testuser{now().timestamp()}@example.com'
        self.user = User.objects.create_user(
            email=unique_email,
            first_name='Reviewer',
            last_name='User',
            password='password123'
        )
        self.service = Service.objects.create(
            name='Hotel Service',
            location='Test Location',
            type='Hotel'
        )

    def test_review_invalid_rating(self):
        review = Review(
            user=self.user,
            service=self.service,
            comment='Excellent service!',
            rating=6
        )
        with self.assertRaises(ValidationError):
            review.full_clean()


class ServiceStatusTestCase(unittest.TestCase):
    def setUp(self):
        self.status = ServiceStatus.objects.create(
            status='maintenance',
            message='Service under maintenance',
            next_available=make_aware(datetime.now() + timedelta(days=1))
        )

    def test_service_status_str(self):
        self.assertEqual(str(self.status), f"Status: {self.status.get_status_display()} - {self.status.next_available}")

