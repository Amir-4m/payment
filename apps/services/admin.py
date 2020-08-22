from django.contrib import admin

from apps.services.models import Service


@admin.register(Service)
class ServiceModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'secret_key')

    filter_horizontal = ('gateways',)
