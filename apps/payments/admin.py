# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Gateway, Order, ServiceGateway


@admin.register(Gateway)
class GatewayModelAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'is_enable', 'created_time', 'updated_time')
    list_filter = ('is_enable',)


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'service', 'gateway', 'price',
        'reference_id', 'is_paid', 'created_time', 'updated_time'
    )
    list_filter = ('is_paid',)
    search_fields = ('service_reference', 'service_reference', 'reference_id', 'invoice_number')


@admin.register(ServiceGateway)
class ServiceGatewayModelAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'service', 'is_enable', 'created_time', 'updated_time')
    list_filter = ('is_enable',)
