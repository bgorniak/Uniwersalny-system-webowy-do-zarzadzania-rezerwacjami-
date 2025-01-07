# your_app/tests/test_admin.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from ..admin import CustomUserAdmin, ServiceAdmin, ReservationAdmin
from ..models import Service, ServiceOption, Reservation, Message

User = get_user_model()

class MockRequest:
    pass

class CustomUserAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)
        self.user = User.objects.create_user(
            email='adminuser@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            balance=1000,
            is_active=True
        )

    def test_list_display(self):
        self.assertEqual(
            self.admin.list_display,
            ('email', 'first_name', 'last_name', 'balance', 'is_active', 'is_staff', 'date_joined')
        )

    def test_search_fields(self):
        self.assertEqual(
            self.admin.search_fields,
            ('email', 'first_name', 'last_name')
        )

class ServiceAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ServiceAdmin(Service, self.site)
        self.service = Service.objects.create(
            name='Test Service',
            type='Hotel',
            location='Test Location'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Single Room',
            capacity=1,
            price=100.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=365)
        )

    def test_get_min_price(self):
        min_price = self.admin.get_min_price(self.service)
        self.assertEqual(min_price, '100.00 zł')

    def test_get_capacity(self):
        max_capacity = self.admin.get_capacity(self.service)
        self.assertEqual(max_capacity, 1)

class ReservationAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ReservationAdmin(Reservation, self.site)
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='custpass123',
            first_name='Customer',
            last_name='User',
            is_active=True,
            balance=500
        )
        self.service = Service.objects.create(
            name='Spa Retreat',
            type='SPA&WELLNESS',
            location='Wellness Park'
        )
        self.service_option = ServiceOption.objects.create(
            service=self.service,
            name='Full Spa Package',
            capacity=3,
            price=400.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=180)
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.service_option,
            start_datetime=timezone.now() + timezone.timedelta(days=5),
            end_datetime=timezone.now() + timezone.timedelta(days=7),
            status='confirmed',
            price=400.00
        )
        self.mock_request = MockRequest()

    def test_service_name(self):
        service_name = self.admin.service_name(self.reservation)
        self.assertEqual(service_name, 'Spa Retreat')

    def test_save_model_creates_message(self):
        form_data = {'message_content': 'Test message'}
        form = ReservationAdmin.form(data=form_data)
        form.is_valid()  # Upewnij się, że formularz jest ważny
        self.admin.save_model(self.mock_request, self.reservation, form, change=True)
        messages = Message.objects.filter(user=self.user, sender='admin')
        self.assertEqual(messages.count(), 1)
        self.assertIn(self.reservation, messages.first().reservations.all())
        self.assertEqual(messages.first().content, 'Test message')
