from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        # Кирилл үсэгт зориулсан том/жижиг үсэг ялгахгүй хайлтын lookup бүртгэх
        from . import db_lookups  # noqa: F401
