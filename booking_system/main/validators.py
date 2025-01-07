from pydantic import ValidationError


class PreventReusePasswordValidator:
    """
    Walidator, który uniemożliwia ustawienie nowego hasła identycznego z poprzednim.
    """
    def validate(self, password, user=None):
        if user and user.check_password(password):
            raise ValidationError(
                "Nowe hasło nie może być takie samo jak poprzednie.",
                code='password_reuse'
            )

    def get_help_text(self):
        return "Twoje nowe hasło nie może być takie samo jak poprzednie."