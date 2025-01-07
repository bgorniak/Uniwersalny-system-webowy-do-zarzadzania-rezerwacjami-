from django import forms
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .forms import UserUpdateForm, ReviewForm, CustomSetPasswordForm, EmailChangeForm, RegistrationForm
from .forms import CustomAuthenticationForm
from .models import Service, Review, Reservation, User, ServiceOption, ServiceStatus
from datetime import timezone
from django.utils.timezone import now, localtime
from django.contrib import messages
from .models import Message
from .tokens import account_activation_token
from django.shortcuts import render
from django.conf import settings
from django.db.models import Count, Q
from datetime import datetime
from django.utils.timezone import make_aware
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordResetForm


def register(request):
    form = RegistrationForm()
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.balance = 1000  # Przyznanie 1000 punktów za rejestrację
            user.save()

            # Tworzenie wiadomości e-mail z linkiem aktywacyjnym
            mail_subject = 'Aktywacja konta'
            message = render_to_string('acc_active_email.txt', {
                'user': user,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                subject=mail_subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email]
            )
            email.send()
            messages.success(request, "Rejestracja zakończona sukcesem! Na podany adres e-mail został wysłany link aktywacyjny.")
            return redirect('login')  # Utrzymaj użytkownika na stronie rejestracji
    return render(request, 'register.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Twoje konto zostało aktywowane! Możesz się teraz zalogować.")
        return redirect('login')
    else:
        return render(request, 'activation_invalid.html')

def home(request):
    # Pobranie unikalnych lokalizacji
    cities = Service.objects.values_list('location', flat=True).distinct()
    service_status = ServiceStatus.objects.first()

    # Pobranie filtrów z request.GET
    service_type = request.GET.get('type', '')  # Rodzaj usługi
    location = request.GET.get('location', '')  # Lokalizacja
    max_price = request.GET.get('price', '')  # Maksymalna cena
    check_in = request.GET.get('check_in', '')  # Data od
    check_out = request.GET.get('check_out', '')  # Data do
    option_id = request.GET.get('option', '')  # Wybrana opcja

    # Pobieranie wszystkich usług
    services = Service.objects.annotate(option_count=Count('service_options'))

    # Filtrowanie po typie usługi
    if service_type:
        services = services.filter(type=service_type)

    # Filtrowanie po lokalizacji
    if location:
        services = services.filter(location=location)

    # Filtrowanie po cenie
    if max_price:
        try:
            max_price = float(max_price)
            services = services.filter(
                Q(service_options__price__lte=max_price) | Q(option_count=0)
            )
        except ValueError:
            pass

    # Filtrowanie po dostępności dat
    if check_in and check_out:
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            # Filtrowanie usług z opcjami dostępnych w danych datach
            available_services = services.filter(
                service_options__available_from__lte=check_out_date,
                service_options__available_to__gte=check_in_date
            ).distinct()

            # Dodanie usług bez opcji tylko, gdy wybrano typ usługi
            if service_type:
                services = available_services | services.filter(option_count=0)
            else:
                services = available_services
        except ValueError:
            pass  # Ignoruj błędne daty

    # Filtrowanie po konkretnej opcji
    if option_id:
        services = services.filter(service_options__id=option_id)

    # Pobranie listy opcji dla wybranego typu usługi
    options = []
    if service_type:
        options = ServiceOption.objects.filter(service__type=service_type)
    # Liczba nowych wiadomości
    new_messages_count = 0
    if request.user.is_authenticated:
        new_messages_count = Message.objects.filter(
            user=request.user,
            sender='admin',
            response__isnull=False,
            is_read=False
        ).count()

    # Renderowanie szablonu
    return render(request, 'home.html', {
        'services': services.distinct(),
        'cities': cities,
        'options': options,
        'new_messages_count': new_messages_count,
        'service_status': service_status,
    })


def get_service_options(request):
    service_type = request.GET.get('type')
    if not service_type:
        return JsonResponse({'options': []})

    options = ServiceOption.objects.filter(service__type=service_type).values('id', 'name')
    return JsonResponse({'options': list(options)})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "Twoje konto jest nieaktywne. Sprawdź e-mail, aby je aktywować.")
                return render(request, "login.html", {"form": form})
            login(request, user)
            return redirect('home')
    else:
        form = CustomAuthenticationForm()

    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.success(request, "Wylogowano pomyślnie!")
    return redirect('home')  # Przekierowanie na stronę główną


def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    reviews = Review.objects.filter(service=service)
    options = service.service_options.all()

    # Konwersja dat na string w formacie 'YYYY-MM-DD'
    availability = [
        {
            "option_id": option.id,
            "available_from": option.available_from.strftime('%Y-%m-%d') if option.available_from else None,
            "available_to": option.available_to.strftime('%Y-%m-%d') if option.available_to else None,
        }
        for option in options
    ]

    return render(request, 'service_detail.html', {
        'service': service,
        'options': options,
        'reviews': reviews,
        'availability': availability,  # Przekazujemy dostępność jako listę
    })

@login_required
def add_review(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.service = service
            review.save()

            # Przyznanie 300 punktów za dodanie opinii
            request.user.balance += 300
            request.user.save()

            messages.success(request, "Twoja opinia została dodana! Otrzymałeś 300 punktów.", extra_tags='review')
        else:
            messages.error(request, "Wystąpił błąd podczas dodawania opinii. Upewnij się, że wszystkie pola są poprawnie wypełnione.", extra_tags='review')

    return redirect('service_detail', service_id=service_id)

@login_required
def make_reservation(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        option_id = request.POST.get('option')
        if not option_id:
            messages.error(request, "Nie wybrano żadnej opcji rezerwacji.", extra_tags='reservation')
            return redirect('service_detail', service_id=service_id)

        try:
            option = ServiceOption.objects.get(id=option_id, service=service)
        except ServiceOption.DoesNotExist:
            messages.error(request, "Wybrana opcja nie istnieje dla tej usługi.", extra_tags='reservation')
            return redirect('service_detail', service_id=service_id)

        if service.type == 'Hotel':
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            if not start_date or not end_date:
                messages.error(request, "Proszę podać daty dla rezerwacji.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messages.error(request, "Nieprawidłowy format daty.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            today = now().date()  # Dzisiejsza data jako date
            if start_date.date() < today or end_date.date() < today:
                messages.error(request, "Nie można zarezerwować usługi w przeszłości.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            if end_date <= start_date:
                messages.error(request, "Data zakończenia musi być późniejsza niż data rozpoczęcia.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            duration = (end_date - start_date).days
            total_price = option.price * duration
        elif service.type in ['Restauracja', 'SPA&WELLNESS']:
            datetime_str = request.POST.get('datetime')
            if not datetime_str:
                messages.error(request, "Proszę podać datę i godzinę dla rezerwacji.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            try:
                start_date = make_aware(datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M'))  # Konwertuj na aware
            except ValueError:
                try:
                    start_date = make_aware(datetime.strptime(datetime_str, '%Y-%m-%d %H:%M'))  # Format z odstępem
                except ValueError:
                    messages.error(request, "Nieprawidłowy format daty i godziny.", extra_tags='reservation')
                    return redirect('service_detail', service_id=service_id)

            if start_date < now():  # Porównanie offset-aware z offset-aware
                messages.error(request, "Nie można zarezerwować usługi w przeszłości.", extra_tags='reservation')
                return redirect('service_detail', service_id=service_id)

            total_price = option.price
        else:
            start_date = now()
            total_price = option.price

        if request.user.balance < total_price:
            messages.error(request, "Nie masz wystarczających środków na koncie.", extra_tags='reservation')
            return redirect('service_detail', service_id=service_id)

        # Aktualizacja salda i zapis rezerwacji
        request.user.balance -= total_price
        request.user.save()

        reservation = Reservation(
            user=request.user,
            option=option,
            start_datetime=start_date,
            end_datetime=end_date if service.type == 'Hotel' else None,
            price=total_price,
            status='pending'
        )
        reservation.save()

        messages.success(request, "Rezerwacja została pomyślnie utworzona!", extra_tags='reservation')
        return redirect('service_detail', service_id=service_id)
@login_required
def profile(request):
    user = request.user
    return render(request, 'profile.html', {'user': user})


@login_required
def user_data(request):
    profile_message = None
    password_errors = []
    password_success = None
    email_message = None

    # Formularze
    user_form = UserUpdateForm(instance=request.user)  # Formularz dla imienia i nazwiska
    password_form = CustomPasswordChangeForm(user=request.user)
    email_form = EmailChangeForm()

    if request.method == 'POST':
        if 'update_password' in request.POST:
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                password_success = "Hasło zostało pomyślnie zmienione!"
            else:
                password_errors = password_form.errors.get('__all__', [])
        elif 'update_profile' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)  # Obsługa danych osobowych
            if user_form.is_valid():
                user_form.save()
                profile_message = "Twoje dane zostały pomyślnie zaktualizowane!"
            else:
                profile_message = "Wystąpił błąd podczas aktualizacji danych."
        elif 'update_email' in request.POST:
            email_form = EmailChangeForm(request.POST)  # Obsługa zmiany adresu e-mail
            if email_form.is_valid():
                new_email = email_form.cleaned_data['new_email']

                # Przygotowanie wiadomości e-mail
                subject = 'Potwierdzenie zmiany adresu e-mail'
                context = {
                    'user': request.user,
                    'new_email': new_email,
                    'uid': urlsafe_base64_encode(force_bytes(request.user.pk)),
                    'token': default_token_generator.make_token(request.user),
                }
                text_content = render_to_string('email_change_confirmation.txt', context)
                html_content = render_to_string('email_change_confirmation.html', context)

                email_message = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[new_email]
                )
                email_message.attach_alternative(html_content, "text/html")
                email_message.send()

                email_message = "Na nowy adres e-mail wysłano wiadomość z potwierdzeniem. Zmiana nastąpi po kliknięciu w link."

    return render(request, 'user_data.html', {
        'user_form': user_form,  # Formularz dla sekcji "Twoje dane"
        'password_form': password_form,
        'email_form': email_form,
        'profile_message': profile_message,
        'password_errors': password_errors,
        'password_success': password_success,
        'email_message': email_message,
    })


@login_required
def my_reservations(request):
    reservations = Reservation.objects.select_related('option', 'option__service').filter(user=request.user)

    formatted_reservations = []
    for reservation in reservations:
        service_type = reservation.option.service.type  # Poprawiona ścieżka do typu usługi
        start_datetime = localtime(reservation.start_datetime)  # Użyj lokalnej strefy czasowej
        end_datetime = localtime(reservation.end_datetime) if reservation.end_datetime else None

        # Pobierz dane dostępności
        available_from = reservation.option.available_from
        available_to = reservation.option.available_to

        if service_type in ['Hotel', 'Wycieczka']:
            # Wyświetl tylko daty bez godzin
            formatted_reservations.append({
                'id': reservation.id,
                'service_name': reservation.option.service.name,
                'option_name': reservation.option.name,
                'start_date': start_datetime.strftime('%d-%m-%Y'),
                'end_date': end_datetime.strftime('%d-%m-%Y') if end_datetime else None,
                'status': reservation.get_status_display(),
                'available_from': available_from.strftime('%d-%m-%Y') if available_from else None,
                'available_to': available_to.strftime('%d-%m-%Y') if available_to else None,
            })
        else:
            # Wyświetl datę i godzinę
            formatted_reservations.append({
                'id': reservation.id,
                'service_name': reservation.option.service.name,
                'option_name': reservation.option.name,
                'start_date': start_datetime.strftime('%d-%m-%Y %H:%M'),
                'end_date': end_datetime.strftime('%d-%m-%Y %H:%M') if end_datetime else None,
                'status': reservation.get_status_display(),
                'available_from': available_from.strftime('%d-%m-%Y') if available_from else None,
                'available_to': available_to.strftime('%d-%m-%Y') if available_to else None,
            })

    return render(request, 'my_reservations.html', {'reservations': formatted_reservations})


@login_required
def my_reviews(request):
    reviews = Review.objects.filter(user=request.user)
    return render(request, 'my_reviews.html', {'reviews': reviews})


@login_required
def contact_admin(request):
    return render(request, 'contact_admin.html')

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Twoje konto zostało pomyślnie usunięte.")
        return redirect('home')  # Przekierowanie na stronę główną po usunięciu konta
    return render(request, 'delete_account.html')

@login_required
def contact_admin(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('message')

        if subject and content:
            # Tworzenie wiadomości od użytkownika
            Message.objects.create(
                user=request.user,
                subject=subject,
                content=content,
                sender='user'  # Poprawnie ustaw nadawcę jako 'user'
            )
            messages.success(request, "Wiadomość została pomyślnie wysłana!")
            return redirect('contact_admin')  # Przekierowanie po sukcesie
        else:
            messages.error(request, "Wszystkie pola są wymagane.")

    return render(request, 'contact_admin.html')

@login_required
def user_messages(request):
    messages = Message.objects.filter(user=request.user).order_by('-created_at')

    # Oznacz wiadomości od administratora jako przeczytane
    Message.objects.filter(user=request.user, sender='admin', is_read=False).update(is_read=True)

    return render(request, 'user_messages.html', {'messages': messages})
@login_required
def cancel_reservation_request(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    if reservation.status != 'pending cancellation':  # Upewnij się, że nie zmieniamy statusu dwa razy
        reservation.status = 'pending cancellation'
        reservation.save()  # Zapisz zmieniony status w bazie danych

        messages.info(request, "Twoja rezerwacja została oznaczona jako oczekująca na anulowanie. Administrator musi ją zatwierdzić.")
    else:
        messages.error(request, "Ta rezerwacja jest już w trakcie anulowania.")

    return redirect('my_reservations')
# Administrator potwierdzający usunięcie rezerwacji
@login_required
def confirm_reservation_cancellation(request, reservation_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("Nie masz uprawnień do wykonania tej akcji.")

    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.status == 'pending cancellation':  # Tylko jeśli jest w stanie "oczekującym na anulowanie"
        try:
            with transaction.atomic():  # Transakcja atomowa dla bezpieczeństwa
                # Zaktualizuj status na anulowany
                reservation.status = 'cancelled'

                # Zapisz zmiany w rezerwacji
                reservation.save()

                messages.success(
                    request,
                    f"Rezerwacja została anulowana. Zwrocono połowę kosztu rezerwacji: {refund_points:.2f} punktów."
                )
        except Exception as e:
            messages.error(request, f"Wystąpił błąd podczas anulowania: {str(e)}")
    else:
        messages.error(request, "Rezerwacja nie jest w stanie oczekującym na anulowanie.")

    return redirect('admin_reservations')

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['new_password1', 'new_password2']:
            self.fields[field_name].help_text = None

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        redirect_to = request.POST.get('redirect_to', 'service_detail')  # Pobierz miejsce przekierowania
        review.delete()

        # Cofnięcie 300 punktów za usunięcie opinii
        request.user.balance -= 300
        request.user.save()

        if redirect_to == 'my_reviews':
            messages.success(request, "Opinia została pomyślnie usunięta.")
            return redirect('my_reviews')  # Przekierowanie do sekcji „Dodane opinie”
        else:
            service_id = review.service.id
            messages.success(request, "Opinia została pomyślnie usunięta.")
            return redirect('service_detail', service_id=service_id)

    return redirect('my_reviews')  # Domyślne przekierowanie

@login_required
def admin_reply(request, message_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("Nie masz uprawnień.")

    message = get_object_or_404(Message, id=message_id)

    if request.method == 'POST':
        response = request.POST.get('response')
        if response:
            message.response = response
            message.response_date = timezone.now()
            message.save()
            messages.success(request, "Odpowiedź została wysłana.")
        else:
            messages.error(request, "Treść odpowiedzi nie może być pusta.")

    return redirect('admin_messages')

@login_required
def cancel_reservation_request(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    if reservation.status != 'pending cancellation':  # Upewnij się, że nie zmieniamy statusu dwa razy
        reservation.status = 'pending cancellation'
        reservation.save()  # Zapisz zmieniony status w bazie danych

        messages.info(request, "Twoja rezerwacja została oznaczona jako oczekująca na anulowanie. Administrator musi ją zatwierdzić.")
    else:
        messages.error(request, "Ta rezerwacja jest już w trakcie anulowania.")

    return redirect('my_reservations')

def request_change_date(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    if request.method == 'POST':
        new_start_date = request.POST.get('new_start_datetime')
        new_end_date = request.POST.get('new_end_datetime')

        # Walidacja nowych dat
        new_start_date = datetime.strptime(new_start_date, '%Y-%m-%dT%H:%M')
        new_end_date = datetime.strptime(new_end_date, '%Y-%m-%dT%H:%M') if new_end_date else None

        # Ustawienie statusu rezerwacji na "pending modification"
        reservation.status = 'pending modification'
        reservation.new_start_datetime = new_start_date
        reservation.new_end_datetime = new_end_date

        reservation.save()

        messages.success(request, "Zmiana terminu została zgłoszona i czeka na zatwierdzenie przez administratora.")
        return redirect('my_reservations')

    return redirect('my_reservations')

class HotelRoomForm(forms.ModelForm):
    class Meta:
        model = ServiceOption
        fields = ['name', 'capacity', 'price']

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    form_class = CustomSetPasswordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user  # Przekazuje obiekt user do formularza
        return kwargs

    def form_valid(self, form):
        # Zapisz nowe hasło
        user = self.user
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        messages.success(self.request, "Twoje hasło zostało pomyślnie zmienione.")
        return super().form_valid(form)


def password_reset_request(request):
    form = CustomPasswordResetForm()
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            user = User.objects.filter(email=email).first()
            if user:
                # Tworzenie wiadomości e-mail
                mail_subject = 'Resetowanie hasła w systemie rezerwacji'
                message = render_to_string('password_reset_email.txt', {
                    'user': user,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                })
                email = EmailMessage(
                    subject=mail_subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                email.send()
                messages.success(request, "Na podany adres e-mail został wysłany link do zresetowania hasła.")
                return redirect('password_reset_done')
            else:
                messages.error(request, "Nie znaleziono użytkownika z tym adresem e-mail.")
    return render(request, 'password_reset.html', {'form': form})

def email_change_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        new_email = request.GET.get('email')
        if new_email:
            user.email = new_email
            user.save()
            messages.success(request, "Adres e-mail został pomyślnie zmieniony.")
            return redirect('user_data')
        else:
            messages.error(request, "Nie podano nowego adresu e-mail.")
    else:
        messages.error(request, "Link do potwierdzenia jest nieprawidłowy lub wygasł.")

    return redirect('user_data')

def service_status(request):
    status = ServiceStatus.objects.first()  # Załóżmy, że mamy tylko jeden status
    return render(request, 'service_status.html', {'status': status})


