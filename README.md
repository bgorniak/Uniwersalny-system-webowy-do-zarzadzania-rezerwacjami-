# 🏨 System Rezerwacji Usługowych

Skalowalna aplikacja webowa umożliwiająca zarządzanie rezerwacjami w różnych typach obiektów usługowych — takich jak **hotele**, **restauracje**, **salony SPA & Wellness**. Projekt został zaprojektowany z myślą o **elastyczności**, co pozwala łatwo dostosować go do różnych branż usługowych.

---

## 🚀 Kluczowe funkcjonalności

- 🔐 **Rejestracja i logowanie użytkowników** z różnymi rolami:  
  - Administrator  
  - Klient

- 🛠️ **Panel administracyjny**:  
  - Zarządzanie rezerwacjami  
  - Zarządzanie dostępnością i kalendarzami  
  - Obsługa zasobów i konfiguracji systemu

- 📅 **Interaktywny kalendarz rezerwacji**:  
  - Intuicyjna wizualizacja zajętości  
  - Obsługa wielu dni i lokalizacji

- 🏢 **Obsługa wielu obiektów i lokalizacji** w jednym systemie

- ✉️ **System powiadomień e-mail**:  
  - Potwierdzenia rezerwacji  
  - Zmiany i anulacje

---

## 🧱 Technologie

- **Backend**:  
  - [Django](https://www.djangoproject.com/) (ORM, Django Admin, system szablonów)

- **Baza danych**:  
  - MySQL z dobrze zaprojektowanym modelem relacyjnym

- **Frontend**:  
  - HTML / CSS (szablony Django)

---

## 📦 Wymagania systemowe

- Python 3.10+
- Django 4.x
- MySQL 8.x
- Virtualenv lub Docker (opcjonalnie)

---

## ⚙️ Uruchomienie projektu (lokalnie)

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/twoje-repozytorium/rezerwacje.git
cd rezerwacje

# 2. Utwórz i aktywuj środowisko
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Skonfiguruj bazę danych (MySQL) i plik .env

# 5. Uruchom migracje
python manage.py migrate

# 6. Uruchom serwer
python manage.py runserver
