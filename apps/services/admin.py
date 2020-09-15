from django.contrib import admin

from apps.services.models import Service


@admin.register(Service)
class ServiceModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_enable', 'created_time', 'updated_time')
    filter_horizontal = ('gateways',)
    list_filter = ('is_enable',)
