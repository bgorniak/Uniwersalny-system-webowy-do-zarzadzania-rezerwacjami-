from datetime import date
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.timezone import now, make_aware, is_naive
from django.db.models import Min

# Manager użytkowników
class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Adres email jest wymagany.")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, first_name, last_name, password, **extra_fields)

# Model użytkownika
class User(AbstractBaseUser, PermissionsMixin):
    DoesNotExist = None
    first_name = models.CharField(max_length=50, verbose_name="Imię")
    last_name = models.CharField(max_length=50, verbose_name="Nazwisko")
    email = models.EmailField(unique=True, verbose_name="Adres email")
    balance = models.IntegerField(default=0, verbose_name="Saldo")
    is_active = models.BooleanField(default=False, verbose_name="Aktywny")
    is_staff = models.BooleanField(default=False, verbose_name="Administrator")
    date_joined = models.DateTimeField(default=now, verbose_name="Data dołączenia")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "Użytkownik"
        verbose_name_plural = "Użytkownicy"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Model usługi
class Service(models.Model):
    TYPE_CHOICES = [
        ('Hotel', 'Hotel'),
        ('Restauracja', 'Restauracja'),
        ('SPA&WELLNESS', 'SPA i WELLNESS'),
        ('Wycieczka', 'Wycieczka'),
    ]
    name = models.CharField(max_length=255, verbose_name="Nazwa")
    location = models.CharField(max_length=255, verbose_name="Lokalizacja")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Typ")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    available_from = models.DateField(null=True, blank=True, verbose_name="Dostępne od")
    available_to = models.DateField(null=True, blank=True, verbose_name="Dostępne do")

    class Meta:
        verbose_name = "Usługa"
        verbose_name_plural = "Usługi"

    def get_min_price(self):
        min_price = self.service_options.aggregate(Min('price'))['price__min']
        return min_price if min_price is not None else 0

    def __str__(self):
        return self.name

# Model opcji usługi
class ServiceOption(models.Model):
    service = models.ForeignKey(Service, related_name='service_options', on_delete=models.CASCADE, verbose_name="Usługa")
    name = models.CharField(max_length=255, verbose_name="Nazwa")
    capacity = models.PositiveIntegerField(verbose_name="Ilość osób")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cena")
    available_from = models.DateField(null=True, blank=True, verbose_name="Dostępne od")
    available_to = models.DateField(null=True, blank=True, verbose_name="Dostępne do")

    class Meta:
        verbose_name = "Opcja usługi"
        verbose_name_plural = "Opcje usługi"

    def clean(self):
        if self.available_from and self.available_to and self.available_from > self.available_to:
            raise ValidationError("Data rozpoczęcia nie może być późniejsza niż data zakończenia.")

    def __str__(self):
        return f"{self.name} - {self.capacity} osób - {self.price} punktów"

# Model rezerwacji
class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Oczekująca'),
        ('confirmed', 'Potwierdzona'),
        ('cancelled', 'Anulowana'),
        ('pending cancellation', 'Oczekuje na anulowanie'),
        ('pending modification', 'Oczekuje na zmianę terminu'),
    ]

    messages = models.ManyToManyField(
        'Message',
        blank=True,
        related_name='reservations',
        verbose_name="Wiadomości"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Usługa", null=True, blank=True)
    service_name = models.CharField(max_length=255, verbose_name="Nazwa usługi", blank=True, editable=False)
    option = models.ForeignKey(ServiceOption, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Opcja")
    start_datetime = models.DateTimeField(verbose_name="Data rozpoczęcia")
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Data zakończenia")
    new_start_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Nowa data rozpoczęcia")
    new_end_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Nowa data zakończenia")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cena")

    def save(self, *args, **kwargs):
        if self.option and self.option.service:
            self.service_name = self.option.service.name  # <- tutaj uzupełniasz nazwę usługi

        if is_naive(self.start_datetime):
            self.start_datetime = make_aware(self.start_datetime)
        if self.end_datetime and is_naive(self.end_datetime):
            self.end_datetime = make_aware(self.end_datetime)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Rezerwacja"
        verbose_name_plural = "Rezerwacje"

    def clean(self):
        if self.start_datetime and self.start_datetime.date() < date.today():
            raise ValidationError("Data rozpoczęcia nie może być w przeszłości.")
        if self.end_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError("Data zakończenia musi być późniejsza niż data rozpoczęcia.")



    def __str__(self):
        return f"Rezerwacja przez {self.user} na {self.service_name}"


# Model opinii
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Usługa")
    comment = models.TextField(verbose_name="Komentarz")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5,
        verbose_name="Ocena"
    )

    class Meta:
        verbose_name = "Opinia"
        verbose_name_plural = "Opinie"

    def __str__(self):
        return f"Opinia {self.rating}/5 od {self.user.email} dla {self.service.name}"

# Model wiadomości
class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    subject = models.CharField(max_length=255, verbose_name="Temat")
    sender = models.CharField(
        max_length=50,
        choices=[('admin', 'Administrator'), ('user', 'Użytkownik')],
        default='admin',
        verbose_name="Nadawca"
    )
    content = models.TextField(verbose_name="Treść wiadomości")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data wysłania")
    is_read = models.BooleanField(default=False, verbose_name="Przeczytane")
    response = models.TextField(null=True, blank=True, verbose_name="Odpowiedź")
    response_date = models.DateTimeField(null=True, blank=True, verbose_name="Data odpowiedzi")

    class Meta:
        verbose_name = "Wiadomość"
        verbose_name_plural = "Wiadomości"

    def __str__(self):
        return f"Wiadomość od {self.user}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.sender == 'admin' and not self.reservations.exists():
            # Automatyczne powiązanie z pierwszą rezerwacją użytkownika
            reservation = Reservation.objects.filter(user=self.user).first()
            if reservation:
                self.reservations.add(reservation)

class ServiceStatus(models.Model):
    status_choices = [
        ('operational', 'Działający'),
        ('maintenance', 'W trakcie konserwacji'),
        ('down', 'Niedostępny'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='operational', verbose_name="Status serwisu")
    message = models.TextField(verbose_name="Komunikat", blank=True, null=True)
    next_available = models.DateTimeField(null=True, blank=True, verbose_name="Czas ponownej dostępności")

    class Meta:
        verbose_name = "Status serwisu"
        verbose_name_plural = "Statusy serwisu"

    def __str__(self):
        return f"Status: {self.get_status_display()} - {self.next_available if self.next_available else 'Brak daty'}"

class DataSummaryLink(Reservation):
    class Meta:
        proxy = True  # To jest model proxy, nie tworzy nowej tabeli
        verbose_name = "Podsumowanie danych"
        verbose_name_plural = "Podsumowanie danych"

