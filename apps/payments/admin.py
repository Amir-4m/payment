# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Gateway, Order


@admin.register(Gateway)
class GatewayModelAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_enable', 'created_time', 'updated_time')
    filter_horizontal = ('services',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'service', 'gateway', 'price', 'invoice_number',
        'reference_id', 'is_paid', 'created_time', 'updated_time'
    )
