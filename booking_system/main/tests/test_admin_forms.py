# your_app/tests/test_admin_forms.py
from django.test import TestCase
from ..forms import ReservationAdminForm
from ..models import Reservation, ServiceOption, User, Message
from django.utils import timezone

class ReservationAdminFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='adminform@example.com',
            password='adminformpass',
            is_active=True,
            balance=1000
        )
        self.service_option = ServiceOption.objects.create(
            name='Deluxe Room',
            capacity=2,
            price=200.00,
            available_from=timezone.now(),
            available_to=timezone.now() + timezone.timedelta(days=365)
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.service_option,
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            end_datetime=timezone.now() + timezone.timedelta(days=2),
            status='confirmed',
            price=200.00
        )

    def test_form_valid_data(self):
        form_data = {
            'message_content': 'Your reservation has been updated.'
        }
        form = ReservationAdminForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_no_message_content(self):
        form_data = {}
        form = ReservationAdminForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data.get('message_content'))

    def test_form_save_creates_message(self):
        form_data = {
            'message_content': 'Your reservation has been updated.'
        }
        form = ReservationAdminForm(data=form_data)
        reservation = form.save(commit=False)
        reservation.save()
        # Sprawdź, czy wiadomość została utworzona
        messages = Message.objects.filter(user=self.user, sender='admin')
        self.assertEqual(messages.count(), 1)
        self.assertIn(reservation, messages.first().reservations.all())
        self.assertEqual(messages.first().content, 'Your reservation has been updated.')
