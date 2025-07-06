import csv
from os import path
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponseRedirect
from reportlab.lib.pagesizes import letter
from . import models
from .forms import ReservationAdminForm
from .models import User, Review, ServiceOption, ServiceStatus, DataSummaryLink
from django.utils.timezone import now
from django import forms
from django.contrib import admin
from django.db import models
from .models import Service
from django.http import HttpResponse
from django.db.models import Count, Min
from django.db.models import Sum
from .models import Reservation, Review
from django.template.response import TemplateResponse
from django.urls import path
from .models import Reservation, Message
from django.db import transaction
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import ttfonts
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch

class CustomUserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'balance', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_filter = ('is_active', 'is_staff')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'balance')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'balance', 'is_active', 'is_staff')}),
    )

admin.site.register(User, CustomUserAdmin)


class RoomTypeInline(admin.TabularInline):
    model = ServiceOption
    extra = 1  # Liczba pustych wierszy do dodania


class ServiceOptionInline(admin.TabularInline):
    model = ServiceOption
    extra = 1  # Liczba pustych wierszy do dodania w adminie

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'location', 'get_min_price', 'get_capacity')
    inlines = [ServiceOptionInline]

    def get_min_price(self, obj):
        options = obj.service_options.all()
        min_price = options.aggregate(Min('price'))['price__min']
        if min_price is not None:
            return f"{min_price:.2f} punktów"
        return "Brak cen"

    get_min_price.short_description = "Najniższa cena"

    def get_capacity(self, obj):
        # Pobierz maksymalną pojemność z powiązanych opcji
        options = obj.service_options.all()

        # Obsługa queryset i listy
        if hasattr(options, 'exists') and not options.exists():
            return "Brak danych"

        if not options:  # Dla listy, sprawdzamy, czy jest pusta
            return "Brak danych"

        return max(option.capacity for option in options)

    get_capacity.short_description = "Maks. pojemność"

admin.site.register(Service, ServiceAdmin)

class ReservationAdmin(admin.ModelAdmin):
    form = ReservationAdminForm
    list_display = (
        'user', 'service_name', 'option', 'start_datetime', 'end_datetime', 'status', 'price'
    )
    list_filter = ('status', 'option', 'user')
    search_fields = ('user__email', 'option__name', 'service_name')

    readonly_fields = ('new_start_datetime', 'new_end_datetime')

    actions = ['cancel_reservation', 'approve_cancellation', 'approve_modification', 'reject_modification','confirm_reservations']



    def save_model(self, request, obj, form, change):
        """Tworzy wiadomość od administratora i automatycznie powiązuje ją z rezerwacją."""
        super().save_model(request, obj, form, change)

        content = form.cleaned_data.get('message_content', None)
        if content:
            # Tworzenie wiadomości od administratora
            message = Message.objects.create(
                user=obj.user,
                subject="Wiadomość od administratora",
                content=content,
                sender='admin'
            )
            # Automatyczne powiązanie z bieżącą rezerwacją
            message.reservations.add(obj)
            self.message_user(request, f"Wiadomość została wysłana do {obj.user.email}.")

    def service_name(self, obj):
        return obj.option.service.name if obj.option and obj.option.service else "Brak danych"

    service_name.short_description = "Nazwa usługi"

    def confirm_reservations(self, request, queryset):
        updated = 0
        for reservation in queryset:
            if reservation.status == 'pending':
                reservation.status = 'confirmed'
                reservation.save()
                updated += 1
        self.message_user(
            request,
            f"{updated} rezerwacja(-e) zostały potwierdzone.",
            level='success'
        )

    confirm_reservations.short_description = "Potwierdź wybrane rezerwacje"

    def approve_cancellation(self, request, queryset):
        for reservation in queryset:
            if reservation.status == 'pending cancellation':
                try:
                    with transaction.atomic():
                        reservation.status = 'cancelled'
                        reservation.save()

                        refund_points = reservation.price
                        reservation.user.balance += refund_points
                        reservation.user.save()

                        self.message_user(
                            request,
                            f"Rezerwacja {reservation.id} została anulowana. Zwrocono {refund_points:.2f} punktów (50%)."
                        )
                except Exception as e:
                    self.message_user(
                        request,
                        f"Błąd podczas anulowania rezerwacji {reservation.id}: {str(e)}",
                        level='error'
                    )
            else:
                self.message_user(
                    request,
                    f"Rezerwacja {reservation.id} nie jest w stanie oczekującym na anulowanie.",
                    level='warning'
                )
    approve_cancellation.short_description = "Zatwierdź anulowanie rezerwacji i zwróć pieniądze"


admin.site.register(Reservation, ReservationAdmin)

# Konfiguracja dla modelu opinii
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'rating', 'comment')
    list_filter = ('rating',)
    search_fields = ('user__email', 'service__name', 'comment')
    ordering = ('service',)

admin.site.register(Review, ReviewAdmin)

# Konfiguracja dla modelu wiadomości
class MessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'created_at', 'is_read', 'response_date')
    list_filter = ('is_read', 'created_at', 'response_date')
    search_fields = ('user__email', 'subject', 'content', 'response')
    fields = ('user', 'subject', 'content', 'created_at', 'is_read', 'response', 'response_date')
    readonly_fields = ('user', 'subject', 'content', 'created_at', 'response_date')

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} wiadomości oznaczono jako przeczytane.")
    mark_as_read.short_description = "Oznacz jako przeczytane"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(sender='user')  # 👈 tylko od użytkowników

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} wiadomości oznaczono jako nieprzeczytane.")
    mark_as_unread.short_description = "Oznacz jako nieprzeczytane"

    def save_model(self, request, obj, form, change):
        if 'response' in form.changed_data and obj.response:
            obj.response_date = now()
        super().save_model(request, obj, form, change)

admin.site.register(Message, MessageAdmin)

@admin.register(ServiceStatus)
class ServiceStatusAdmin(admin.ModelAdmin):
    list_display = ('status', 'message', 'next_available')
    search_fields = ('status',)

class DataSummaryAdminView:

    def get_urls(self):
        custom_urls = [
            path('data-summary/', self.admin_site.admin_view(self.finance_summary_view), name='data-summary'),
            path('data-summary/export-csv/', self.admin_site.admin_view(self.export_csv), name='export-csv'),
            path('data-summary/export-pdf/', self.admin_site.admin_view(self.export_pdf), name='export-pdf'),
        ]
        return custom_urls

    def data_summary_view(self, request, *args, **kwargs):
        """Widok dla podsumowania finansowego."""

        # Obliczenia danych
        total_reservations = Reservation.objects.count()
        total_reviews = Review.objects.count()
        total_revenue = Reservation.objects.aggregate(total=Sum('price'))['total'] or 0
        total_users = User.objects.count()
        most_popular_service = (
            Service.objects.annotate(
                reservation_count=Count('service_options__reservation')
            )
            .order_by('-reservation_count')
            .first()
        )

        # Przygotowanie danych do szablonu
        context = {
            'total_reservations': total_reservations,
            'total_reviews': total_reviews,
            'total_revenue': total_revenue,
            'total_users': total_users,
            'most_popular_service': most_popular_service.name if most_popular_service else "Brak danych",
            'most_popular_service_count': most_popular_service.reservation_count if most_popular_service else 0,
        }

        # Renderowanie szablonu
        return TemplateResponse(request, "admin/data_summary.html", context)

    def export_csv(self, request, *args, **kwargs):
        """Eksport danych do pliku CSV."""

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="data_summary.csv"'

        # Dodaj kodowanie UTF-8 dla polskich znaków
        response.write('\ufeff'.encode('utf-8'))  # BOM dla poprawnej obsługi UTF-8 w Excelu

        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Nagłówek pliku CSV
        writer.writerow(['Podsumowanie danych'])
        writer.writerow([])  # Pusta linia
        writer.writerow(['Statystyka', 'Wartość'])

        # Pobieranie danych
        total_reservations = Reservation.objects.count()
        total_reviews = Review.objects.count()
        total_revenue = Reservation.objects.aggregate(total=Sum('price'))['total'] or 0
        total_users = User.objects.count()
        most_popular_service = (
            Service.objects.annotate(reservation_count=Count('service_options__reservation'))
            .order_by('-reservation_count')
            .first()
        )

        most_popular_service_name = most_popular_service.name if most_popular_service else "Brak danych"
        most_popular_service_count = most_popular_service.reservation_count if most_popular_service else 0

        # Dane wierszy
        writer.writerow(['Liczba rezerwacji', total_reservations])
        writer.writerow(['Liczba opinii', total_reviews])
        writer.writerow(['Przychód (punkty)', f"{total_revenue:.2f}"])
        writer.writerow(['Liczba użytkowników', total_users])
        writer.writerow(['Najpopularniejsza usługa', most_popular_service_name])
        writer.writerow(['Liczba rezerwacji usługi', most_popular_service_count])

        return response

    def export_pdf(self, request, *args, **kwargs):
        """Eksport danych do pliku PDF z polskimi znakami"""

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="data_summary.pdf"'

        # Rejestracja czcionki (ścieżka względem głównego folderu projektu)
        font_path = os.path.join(settings.BASE_DIR, 'fonts', 'DejaVuSans.ttf')
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []

        # Tytuł
        title = [['Podsumowanie danych']]
        title_table = Table(title)
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Pobieranie danych
        total_reservations = Reservation.objects.count()
        total_reviews = Review.objects.count()
        total_revenue = Reservation.objects.aggregate(total=Sum('price'))['total'] or 0
        total_users = User.objects.count()
        most_popular_service = (
            Service.objects.annotate(reservation_count=Count('service_options__reservation'))
            .order_by('-reservation_count')
            .first()
        )
        most_popular_service_name = most_popular_service.name if most_popular_service else "Brak danych"
        most_popular_service_count = most_popular_service.reservation_count if most_popular_service else 0

        # Tabela danych
        data = [
            ['Statystyka', 'Wartość'],
            ['Liczba rezerwacji', str(total_reservations)],
            ['Liczba opinii', str(total_reviews)],
            ['Przychód (punkty)', f"{total_revenue:.2f}"],
            ['Liczba użytkowników', str(total_users)],
            ['Najpopularniejsza usługa', most_popular_service_name],
            ['Liczba rezerwacji usługi', str(most_popular_service_count)],
        ]

        table = Table(data, colWidths=[2.5 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        doc.build(elements)
        return response


@admin.register(DataSummaryLink)
class DataSummaryLinkAdmin(admin.ModelAdmin):
    # Ukryj przyciski "Dodaj", "Edytuj" itd.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Przekierowanie do widoku podsumowania
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('data-summary'))  # Nazwa URL Twojego widoku