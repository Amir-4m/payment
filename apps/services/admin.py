from django.contrib import admin

# Register your models here.
from apps.services.models import Service


@admin.register(Service)
class ServiceModelAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name')
