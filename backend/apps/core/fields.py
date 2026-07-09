# fields.py
from django.utils import timezone
from rest_framework import serializers

class CustomDateTimeField(serializers.DateTimeField):
    def __init__(self, *a, **kw):
        kw.setdefault('format', None)  # ISO-8601
        kw.setdefault('input_formats', ['iso-8601'])
        kw.setdefault('default_timezone', timezone.get_current_timezone())
        kw.setdefault('read_only', True)
        super().__init__(*a, **kw)

class UnixTimestampField(serializers.DateTimeField):
    def to_representation(self, value):
        if value is None: return None
        return int(value.astimezone(timezone.utc).timestamp())
