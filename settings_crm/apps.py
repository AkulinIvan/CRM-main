from django.apps import AppConfig


class SettingsCrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'settings_crm'

    # def ready(self):
    #     # Импортируем сигналы
    #     from signals import check_password_expiration