import csv
from os import path
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponseRedirect
from reportlab.lib.pagesizes import letter
from . import models
from .forms import ReservationAdminForm
from .models import User, Review, ServiceOption, ServiceStatus, FinanceSummaryLink
from django.utils.timezone import now
from django import forms
from django.contrib import admin
from django.db import models
from .models import Service
from django.http import HttpResponse
from django.db.models import Count
from django.db.models import Sum
from .models import Reservation, Review
from django.template.response import TemplateResponse
from django.urls import path
from .models import Reservation, Message
from django.db import transaction

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
        # Pobranie powiązanych opcji usługi
        options = obj.service_options.all()
        min_price = options.aggregate(models.Min('price'))['price__min']
        if min_price is not None:
            return f"{min_price:.2f} zł"  # Dodanie dwóch miejsc po przecinku dla stałego formatu
        return "Brak cen"
    def get_capacity(self, obj):
        # Pobierz maksymalną pojemność z powiązanych opcji
        options = obj.service_options.all()
        if options.exists():
            return max(option.capacity for option in options)
        return "Brak danych"

    get_capacity.short_description = "Maks. pojemność"

admin.site.register(Service, ServiceAdmin)

class ReservationAdmin(admin.ModelAdmin):
    form = ReservationAdminForm
    list_display = (
        'user', 'service_name', 'option', 'start_datetime', 'end_datetime', 'status', 'price'
    )
    list_filter = ('status', 'option', 'user')
    search_fields = ('user__email', 'option__name', 'service_name')
    actions = ['cancel_reservation', 'approve_cancellation', 'approve_modification', 'reject_modification']

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

    def approve_modification(self, request, queryset):
        for reservation in queryset.filter(status='pending modification'):
            if reservation.new_start_datetime and reservation.new_end_datetime:
                reservation.start_datetime = reservation.new_start_datetime
                reservation.end_datetime = reservation.new_end_datetime
                reservation.new_start_datetime = None
                reservation.new_end_datetime = None
                reservation.status = 'confirmed'
                reservation.save()
                self.message_user(request, f"Zmiana terminu rezerwacji {reservation.id} została zatwierdzona.")
            else:
                self.message_user(
                    request,
                    f"Rezerwacja {reservation.id} nie ma nowych terminów do zatwierdzenia.",
                    level='error'
                )

    approve_modification.short_description = "Zatwierdź zmiany terminów"
    def reject_modification(self, request, queryset):
        queryset.filter(status='pending modification').update(
            new_start_datetime=None,
            new_end_datetime=None,
            status='confirmed'
        )
        self.message_user(request, f"Zmiana terminów została odrzucona.")

    reject_modification.short_description = "Odrzuć zmiany terminów"

    def cancel_reservation(self, request, queryset):
        """Anulowanie rezerwacji i zwrot pieniędzy"""
        for reservation in queryset:
            if reservation.status == 'pending cancellation':
                try:
                    with transaction.atomic():
                        reservation.status = 'cancelled'
                        reservation.save()
                        reservation.user.balance += reservation.price
                        reservation.user.save()
                        self.message_user(request, f"Rezerwacja {reservation.id} została anulowana, a środki zwrócone.")
                except Exception as e:
                    self.message_user(request, f"Błąd podczas anulowania rezerwacji {reservation.id}: {str(e)}",
                                      level='error')
            else:
                self.message_user(request, f"Rezerwacja {reservation.id} nie jest w stanie oczekiwania na anulowanie.",
                                  level='error')

    cancel_reservation.short_description = 'Anuluj wybrane rezerwacje i zwróć pieniądze'

    def approve_cancellation(self, request, queryset):
        """Zatwierdzenie anulowania rezerwacji"""
        for reservation in queryset:
            if reservation.status == 'pending cancellation':
                try:
                    with transaction.atomic():
                        reservation.status = 'cancelled'
                        reservation.save()
                        reservation.user.balance += reservation.price
                        reservation.user.save()
                        self.message_user(request, f"Rezerwacja {reservation.id} została anulowana, a środki zwrócone.")
                except Exception as e:
                    self.message_user(request,
                                      f"Błąd podczas zatwierdzania anulowania rezerwacji {reservation.id}: {str(e)}",
                                      level='error')
            else:
                self.message_user(request, f"Rezerwacja {reservation.id} nie jest w stanie oczekiwania na anulowanie.",
                                  level='error')

    approve_cancellation.short_description = 'Zatwierdź anulowanie rezerwacji'


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

class FinanceSummaryAdminView:
    """Niestandardowy widok administracyjny dla podsumowania finansowego."""

    def get_urls(self):
        """Dodaje niestandardowe ścieżki URL."""
        custom_urls = [
            path('finance-summary/', self.admin_site.admin_view(self.finance_summary_view), name='finance-summary'),
            path('finance-summary/export-csv/', self.admin_site.admin_view(self.export_csv), name='export-csv'),
            path('finance-summary/export-pdf/', self.admin_site.admin_view(self.export_pdf), name='export-pdf'),
        ]
        return custom_urls

    def finance_summary_view(self, request, *args, **kwargs):
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
        return TemplateResponse(request, "admin/finance_summary.html", context)

    def export_csv(self, request, *args, **kwargs):
        """Eksport danych do pliku CSV."""

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="finance_summary.csv"'

        # Dodaj kodowanie UTF-8 dla polskich znaków
        response.write('\ufeff'.encode('utf-8'))  # BOM dla poprawnej obsługi UTF-8 w Excelu

        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Nagłówek pliku CSV
        writer.writerow(['Podsumowanie finansowe'])
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
        writer.writerow(['Przychód (PLN)', f"{total_revenue:.2f}"])
        writer.writerow(['Liczba użytkowników', total_users])
        writer.writerow(['Najpopularniejsza usługa', most_popular_service_name])
        writer.writerow(['Liczba rezerwacji usługi', most_popular_service_count])

        return response

    def export_pdf(self, request, *args, **kwargs):
        """Eksport danych do pliku PDF."""


        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="finance_summary.pdf"'

        # Dokument PDF
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []

        # Tytuł
        title = [['Podsumowanie finansowe']]
        title_table = Table(title)
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Tabela danych
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

        data = [
            ['Statystyka', 'Wartość'],
            ['Liczba rezerwacji', total_reservations],
            ['Liczba opinii', total_reviews],
            ['Przychód (PLN)', f"{total_revenue:.2f}"],
            ['Liczba użytkowników', total_users],
            ['Najpopularniejsza usługa', most_popular_service_name],
            ['Liczba rezerwacji usługi', most_popular_service_count],
        ]

        table = Table(data, colWidths=[2.5 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Generowanie PDF
        doc.build(elements)

        return response


@admin.register(FinanceSummaryLink)
class FinanceSummaryLinkAdmin(admin.ModelAdmin):
    # Ukryj przyciski "Dodaj", "Edytuj" itd.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Przekierowanie do widoku podsumowania
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('finance-summary'))  # Nazwa URL Twojego widoku