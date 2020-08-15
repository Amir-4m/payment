from django.contrib import admin

# Register your models here.
from apps.service.models import Service


@admin.register(Service)
class ServiceModelAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name')
