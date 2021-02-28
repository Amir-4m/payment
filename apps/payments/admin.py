# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.contrib.postgres.fields import JSONField
from django.http import HttpResponseRedirect
from django.urls import reverse

from django_json_widget.widgets import JSONEditorWidget

from .models import Order, ServiceGateway


@admin.register(Order)
class OrderModelAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'service', 'service_gateway', 'price',
        'reference_id', 'is_paid', 'created_time', 'updated_time'
    )
    list_filter = ('is_paid',)
    search_fields = ('service_reference', 'service_reference', 'reference_id', 'transaction_id')


@admin.register(ServiceGateway)
class ServiceGatewayModelAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_name', 'service', 'is_enable', 'created_time', 'updated_time')
    list_filter = ('is_enable', 'service')
    change_form_template = "payments/admin/change-form.html"
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

    def response_change(self, request, obj):
        if "update_auth_code" in request.POST:
            if 'client_id' not in obj.properties:
                messages.error(request, 'client id does not exists for this gateway.')
                return HttpResponseRedirect('.')
            url = f"https://pardakht.cafebazaar.ir/devapi/v2/auth/authorize/?response_type=code&access_type=offline&redirect_uri={request.build_absolute_uri(reverse('bazaar-token', kwargs={'gateway_id': obj.id}))}&client_id={obj.properties['client_id']}"
            return HttpResponseRedirect(url)
        return super().response_change(request, obj)
