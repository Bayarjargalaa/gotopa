"""Кирилл үсэгт тохирсон том/жижиг үсэг ялгахгүй хайлт

SQLite-ийн LIKE болон lower()/upper() нь зөвхөн ASCII үсгийг л том/жижиг гэж
ялгадаг тул "Батаа" гэсэн өгөгдлийг "батаа" гэж хайхад олддоггүй. Тиймээс
SQLite холболт үүсэх бүрд Python-ы Unicode-той `str.lower()`-г `unicode_lower`
нэрээр бүртгэж, түүнийг ашигладаг `__iucontains` lookup-ыг нэмнэ.

Хэрэглээ:
    UserProfile.objects.filter(mongolian_name__iucontains='бат')
"""

from django.db.backends.signals import connection_created
from django.db.models import CharField, Lookup, TextField
from django.dispatch import receiver


def _unicode_lower(value):
    return value.lower() if isinstance(value, str) else value


@receiver(connection_created)
def register_sqlite_unicode_functions(sender, connection, **kwargs):
    """SQLite холболтод Unicode-той `unicode_lower` функцийг бүртгэх"""
    if connection.vendor != 'sqlite':
        return
    try:
        connection.connection.create_function(
            'unicode_lower', 1, _unicode_lower, deterministic=True
        )
    except TypeError:
        # deterministic аргументыг дэмждэггүй хуучин SQLite/Python
        connection.connection.create_function('unicode_lower', 1, _unicode_lower)


class UnicodeIContains(Lookup):
    """Кирилл үсгийг ч зөв боловсруулдаг том/жижиг үсэг ялгахгүй `contains`"""

    lookup_name = 'iucontains'

    def get_prep_lookup(self):
        value = self.rhs
        if hasattr(value, 'resolve_expression'):
            return value
        value = str(value)
        # LIKE-ийн тусгай тэмдэгтүүдийг escape хийх
        value = value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        return f'%{value.lower()}%'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        lower_fn = 'unicode_lower' if connection.vendor == 'sqlite' else 'LOWER'
        return f"{lower_fn}({lhs}) LIKE {rhs} ESCAPE '\\'", lhs_params + rhs_params


CharField.register_lookup(UnicodeIContains)
TextField.register_lookup(UnicodeIContains)
