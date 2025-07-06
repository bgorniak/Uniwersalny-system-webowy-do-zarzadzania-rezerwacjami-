from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django_flatpickr.widgets import DatePickerInput
from pydantic import ValidationError

from .models import Message, ServiceOption, Review, User, Reservation, Service


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Adres email", widget=forms.EmailInput(attrs={"class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Adres email"  # Zamień label na 'Adres email'

    def clean(self):
        email = self.cleaned_data.get('username')  # Pobiera email z pola 'username'
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Błędny adres email lub hasło.", code='invalid_login')
            elif not self.user_cache.is_active:
                raise forms.ValidationError("To konto jest nieaktywne.", code='inactive')

        return self.cleaned_data

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Hasło",
        strip=False,
        help_text=None
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Powtórz hasło"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'email': 'Adres e-mail',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Podany adres e-mail jest już zarejestrowany.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Hasła muszą być takie same.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = False  # Konto domyślnie nieaktywne
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name']
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
        }

class ServiceOptionForm(forms.ModelForm):
    class Meta:
        model = ServiceOption
        fields = ['service', 'name', 'capacity', 'price', 'available_from', 'available_to']
        widgets = {
            'available_from': DatePickerInput(),
            'available_to': DatePickerInput(),
        }

class ServiceDetailForm(forms.Form):
    # Przykładowe pole daty
    date = forms.DateField(
        widget=forms.SelectDateWidget,
        label="Data rezerwacji"
    )

    def clean_date(self):
        selected_date = self.cleaned_data.get('date')
        if selected_date < date.today():
            raise forms.ValidationError("Nie można wybrać daty z przeszłości.")
        return selected_date

class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]  # Oceny od 1 do 5

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Ocena",
        required=True
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Opinia",
        required=True
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']

User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Podany adres e-mail nie istnieje w naszej bazie danych.")
        return email

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['new_password1', 'new_password2']:
            self.fields[field_name].help_text = None
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',  # <-- dodaj klasę do stylowania
                'placeholder': 'Wprowadź hasło'
            })

    def clean_new_password1(self):
        new_password1 = self.cleaned_data.get('new_password1')

        # Uwaga: `self.user` jest dostępny w SetPasswordForm
        if self.user.check_password(new_password1):
            raise forms.ValidationError("Nowe hasło nie może być takie samo jak poprzednie.")

        return new_password1

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("Hasła nie są takie same.")

        return cleaned_data
class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="Nowy adres e-mail",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Wprowadź nowy adres e-mail'}),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data['new_email']
        if User.objects.filter(email=new_email).exists():
            raise forms.ValidationError("Podany adres e-mail jest już zajęty.")
        return new_email

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'content']

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Adres email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        label="Hasło",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def get_invalid_login_error(self):
        """Nadpisuje domyślny komunikat o błędzie"""
        return forms.ValidationError(
            "Błędny adres email lub hasło.",
            code="invalid_login",
        )

class ServiceAdminForm(forms.ModelForm):
    available_dates = forms.CharField(required=False, widget=forms.Textarea)
    room_types = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Typy pokoi'}))

    class Meta:
        model = Service
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.type:
            service_type = self.instance.type
            if service_type == 'Hotel':
                self.fields['available_dates'].widget = forms.Textarea(
                    attrs={'placeholder': 'Dostępne daty, oddzielone przecinkami.'}
                )
            elif service_type in ['Restauracja', 'SPA&WELLNESS', 'Wycieczka']:
                self.fields['available_dates'].widget = forms.Textarea(
                    attrs={'placeholder': 'Dostępne daty i godziny w formacie ISO (np. "2024-12-31T14:00").'}
                )
            else:
                self.fields['available_dates'].widget = forms.HiddenInput()

            if service_type == 'Hotel':
                self.fields['room_types'].required = True
            else:
                self.fields['room_types'].widget = forms.HiddenInput()
                self.fields['room_types'].required = False

class ReservationAdminForm(forms.ModelForm):
    message_content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Wpisz treść wiadomości do użytkownika'
        }),
        label="Treść wiadomości"
    )

    class Meta:
        model = Reservation
        fields = '__all__'