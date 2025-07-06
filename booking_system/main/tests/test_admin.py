import unittest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import RequestFactory, TestCase
from django.contrib.admin.sites import AdminSite
from django.http import HttpResponse
from django.utils.timezone import make_aware
from ..models import User, Reservation, Message, ServiceStatus, Service, Review,ServiceOption, \
    ReportSummaryLink
from ..forms import ReservationAdminForm
from ..admin import (
    CustomUserAdmin, ServiceAdmin,
    ReservationAdmin, MessageAdmin,
    ReviewAdmin, ServiceStatusAdmin, FinanceSummaryAdminView,
    ReportSummaryLinkAdmin,
)

class AdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        User.objects.filter(email='admin@example.com').delete()
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass',
            first_name='Admin',
            last_name='User'
        )
        self.user = User.objects.create_user(
            email='user@example.com',
            password='userpass',
            first_name='Test',
            last_name='User'
        )
        self.service = Service.objects.create(
            name='Test Service',
            type='Hotel',
            location='Test Location'
        )
        self.option = ServiceOption.objects.create(
            service=self.service,
            name='Room Option',
            price=100.0,
            capacity=2
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            option=self.option,
            start_datetime=make_aware(datetime.now() + timedelta(days=1)),
            end_datetime=make_aware(datetime.now() + timedelta(days=2)),
            price=200.0,
            status='pending'
        )
        self.message = Message.objects.create(
            user=self.user,
            subject='Test Message',
            content='This is a test message.',
            sender='admin'
        )

    def test_custom_user_admin(self):
        user_admin = CustomUserAdmin(User, self.site)
        self.assertGreater(len(user_admin.list_display), 0)
        self.assertGreater(len(user_admin.fieldsets), 0)
        self.assertIn('email', user_admin.search_fields)

    def test_service_admin_get_min_price(self):
        service_admin = ServiceAdmin(Service, self.site)
        mock_service = MagicMock()
        mock_queryset = MagicMock()
        mock_service.service_options.all.return_value = mock_queryset
        mock_queryset.aggregate.return_value = {'price__min': 100.0}
        result = service_admin.get_min_price(mock_service)
        self.assertEqual(result, '100.00 punktów')

    def test_service_admin_get_capacity(self):
        service_admin = ServiceAdmin(Service, self.site)
        mock_service = MagicMock()
        mock_service.service_options.all.return_value = [
            MagicMock(capacity=10),
            MagicMock(capacity=20)
        ]
        result = service_admin.get_capacity(mock_service)
        self.assertEqual(result, 20)

    def test_message_admin_mark_as_read(self):
        message_admin = MessageAdmin(Message, self.site)
        queryset = Message.objects.filter(id=self.message.id)
        message_admin.mark_as_read(Mock(), queryset)
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)

    def test_message_admin_mark_as_unread(self):
        message_admin = MessageAdmin(Message, self.site)
        queryset = Message.objects.filter(id=self.message.id)
        message_admin.mark_as_unread(Mock(), queryset)
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_read)

    def test_message_admin_save_model(self):
        message_admin = MessageAdmin(Message, self.site)
        mock_message = MagicMock()
        form = MagicMock()
        form.changed_data = ['response']
        request = MagicMock()
        message_admin.save_model(request, mock_message, form, change=True)
        self.assertIn('response', form.changed_data)

    def test_finance_summary_view_returns_correct_template(self):
        factory = RequestFactory()
        request = factory.get('/admin/finance-summary/')
        finance_summary_admin_view = FinanceSummaryAdminView()
        response = finance_summary_admin_view.finance_summary_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)

    def test_finance_summary_admin_export_csv(self):
        factory = RequestFactory()
        request = factory.get('/admin/finance-summary/export-csv/')
        finance_summary_admin_view = FinanceSummaryAdminView()
        response = finance_summary_admin_view.export_csv(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Podsumowanie finansowe', response.content)

    def test_finance_summary_admin_export_pdf(self):
        factory = RequestFactory()
        request = factory.get('/admin/finance-summary/export-pdf/')
        finance_summary_admin_view = FinanceSummaryAdminView()
        response = finance_summary_admin_view.export_pdf(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_report_summary_link_admin_permissions(self):
        report_summary_link_admin = ReportSummaryLinkAdmin(ReportSummaryLink, self.site)
        request = MagicMock()
        self.assertFalse(report_summary_link_admin.has_add_permission(request))
        self.assertFalse(report_summary_link_admin.has_change_permission(request))
        self.assertFalse(report_summary_link_admin.has_delete_permission(request))

    def test_finance_summary_link_admin_changelist_view(self):
        finance_summary_link_admin = ReportSummaryLinkAdmin(ReportSummaryLink, self.site)
        request = MagicMock()
        response = finance_summary_link_admin.changelist_view(request)
        self.assertEqual(response.status_code, 302)

    def test_save_model(self):
        form_data = {'message_content': 'Admin message content.'}
        form = Mock(cleaned_data=form_data)
        reservation_admin = ReservationAdmin(Reservation, self.site)
        reservation_admin.save_model(Mock(), self.reservation, form, change=True)
        self.assertEqual(Message.objects.count(), 2)

    def test_service_name(self):
        reservation_admin = ReservationAdmin(Reservation, self.site)
        result = reservation_admin.service_name(self.reservation)
        self.assertEqual(result, 'Test Service')

    def test_approve_modification(self):
        self.reservation.status = 'pending modification'
        self.reservation.new_start_datetime = self.reservation.start_datetime + timedelta(days=1)
        self.reservation.new_end_datetime = self.reservation.end_datetime + timedelta(days=1)
        self.reservation.save()
        reservation_admin = ReservationAdmin(Reservation, self.site)
        queryset = Reservation.objects.filter(id=self.reservation.id)
        reservation_admin.approve_modification(Mock(), queryset)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'confirmed')
        self.assertIsNone(self.reservation.new_start_datetime)
        self.assertIsNone(self.reservation.new_end_datetime)

    def test_reject_modification(self):
        self.reservation.status = 'pending modification'
        self.reservation.new_start_datetime = self.reservation.start_datetime + timedelta(days=1)
        self.reservation.new_end_datetime = self.reservation.end_datetime + timedelta(days=1)
        self.reservation.save()
        reservation_admin = ReservationAdmin(Reservation, self.site)
        queryset = Reservation.objects.filter(id=self.reservation.id)
        reservation_admin.reject_modification(Mock(), queryset)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'confirmed')
        self.assertIsNone(self.reservation.new_start_datetime)
        self.assertIsNone(self.reservation.new_end_datetime)

    def test_cancel_reservation(self):
        self.reservation.status = 'pending cancellation'
        self.reservation.save()
        reservation_admin = ReservationAdmin(Reservation, self.site)
        queryset = Reservation.objects.filter(id=self.reservation.id)
        reservation_admin.cancel_reservation(Mock(), queryset)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'cancelled')
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, 200.0)

    def test_approve_cancellation(self):
        self.reservation.status = 'pending cancellation'
        self.reservation.save()
        reservation_admin = ReservationAdmin(Reservation, self.site)
        queryset = Reservation.objects.filter(id=self.reservation.id)
        reservation_admin.approve_cancellation(Mock(), queryset)
        self.reservation.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.reservation.status, 'cancelled')
        self.assertEqual(self.user.balance, 200.0)

if __name__ == '__main__':
    unittest.main()
