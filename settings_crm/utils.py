from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import SystemSettings

def validate_password_complexity(password, user=None):
    settings = SystemSettings.get_settings()
    if settings.require_complex_password:
        try:
            validate_password(password, user)
        except ValidationError as e:
            raise ValidationError(
                "Пароль должен содержать не менее {} символов, включая цифры и буквы в разных регистрах".format(
                    settings.password_min_length
                )
            )

def get_allowed_file_extensions():
    settings = SystemSettings.get_settings()
    if not settings.allow_file_attachments:
        return []
    return [ext.strip().lower() for ext in settings.allowed_file_types.split(',')]

def check_file_size(file):
    settings = SystemSettings.get_settings()
    max_size = settings.max_file_size_mb * 1024 * 1024  # в байтах
    if file.size > max_size:
        raise ValidationError(
            f"Размер файла превышает максимально допустимый ({settings.max_file_size_mb} МБ)"
        )
        
def validate_file_extension(value):
    ext = value.name.split('.')[-1].lower()
    valid_extensions = get_allowed_file_extensions()
    if not ext in valid_extensions:
        raise ValidationError(f'Недопустимое расширение файла. Разрешены: {", ".join(valid_extensions)}')

def validate_file_size(value):
    limit = 10 * 1024 * 1024  # 10MB
    if value.size > limit:
        raise ValidationError('Файл слишком большой. Максимальный размер: 10 МБ')