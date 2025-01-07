from xml.etree.ElementInclude import include

from django.urls import path

from . import views, admin
from .admin import FinanceSummaryAdminView
from .views import delete_account, user_messages, password_reset_request, CustomPasswordResetConfirmView, \
    email_change_confirm
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', views.home, name='home'),  # Główna strona
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('service/<int:service_id>/reserve/', views.make_reservation, name='make_reservation'),
    path('service/<int:service_id>/review/', views.add_review, name='add_review'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    path('profile/', views.profile, name='profile'),
    path('profile/data/', views.user_data, name='user_data'),
    path('profile/reservations/', views.my_reservations, name='my_reservations'),
    path('profile/reviews/', views.my_reviews, name='my_reviews'),
    path('profile/contact/', views.contact_admin, name='contact_admin'),
    path('profile/delete_account/', delete_account, name='delete_account'),
    path('profile/messages/', user_messages, name='user_messages'),
    path('reservation/<int:reservation_id>/cancel/', views.cancel_reservation_request, name='cancel_reservation'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('reservations/<int:reservation_id>/change/', views.request_change_date, name='request_change_date'),
    path('reservations/', views.my_reservations, name='reservations'),
    path('service/<int:service_id>/reserve/', views.make_reservation, name='make_reservation'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('password_reset.css/', password_reset_request, name='password_reset'),
    path('reservation/cancel/<int:reservation_id>/', views.cancel_reservation_request, name='cancel_reservation_request'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
         name='password_reset_done'),
    path(
        'reset/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
         name='password_reset_complete'),
    path('email-change-confirm/<uidb64>/<token>/', email_change_confirm, name='email_change_confirm'),
    # Widok dla administratora
    path('api/get_service_options/', views.get_service_options, name='get_service_options'),
    path('service-status/', views.service_status, name='service_status'),
    path('admin/finance-summary/', FinanceSummaryAdminView().finance_summary_view, name='finance-summary'),
    path('admin/finance-summary/export-csv/', FinanceSummaryAdminView().export_csv, name='export-csv'),
    path('admin/finance-summary/export-pdf/', FinanceSummaryAdminView().export_pdf, name='export-pdf'),
    path('admin/reservation/<int:reservation_id>/confirm_cancel/', views.confirm_reservation_cancellation,
         name='confirm_cancel_reservation'),

]