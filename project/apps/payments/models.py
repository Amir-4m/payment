# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.services.models import Service


class Gateway(models.Model):
    FUNCTION_SAMAN = "SAMAN"
    FUNCTION_BAZAAR = "BAZAAR"
    GATEWAY_FUNCTIONS = (
        (FUNCTION_SAMAN, _('Saman')),
        (FUNCTION_BAZAAR, _('Bazaar')),
    )

    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    display_name = models.CharField(_('display name'), max_length=120)
    title = models.CharField(_('title'), max_length=120)
    image = models.ImageField(upload_to='gateways/images')
    properties = JSONField(_("properties"), default=dict)
    code = models.CharField(_("code"), max_length=10, choices=GATEWAY_FUNCTIONS, default=FUNCTION_SAMAN)
    is_enable = models.BooleanField(default=True)

    def clean(self):
        bazaar_params = ['auth_code', 'client_id', 'redirect_uri', 'client_secret']
        bank_params = ['verify_url', 'gateway_url', 'merchant_id']

        if self.code == self.FUNCTION_BAZAAR:
            for param in bazaar_params:
                if param not in self.properties:
                    raise ValidationError(f"{param} should be provided in gateway properties!")
        else:
            for param in bank_params:
                if param not in self.properties:
                    raise ValidationError(f"{param} should be provided in gateway properties!")


class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='orders')
    gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE, related_name='orders')
    price = models.PositiveIntegerField(_('price'))
    invoice_number = models.UUIDField(_('invoice_number'), default=uuid.uuid4, unique=True, editable=False)
    service_reference = models.CharField(_("service reference"), max_length=100)
    reference_id = models.CharField(_("reference id"), max_length=100, db_index=True, blank=True)
    log = models.TextField(_("payment log"), blank=True)
    properties = JSONField(_("properties"), blank=True, default=dict)
    is_paid = models.NullBooleanField(_("is paid"))

    class Meta:
        unique_together = ('service', 'service_reference')

    def clean(self):
        if self.gateway.code == Gateway.FUNCTION_SAMAN and 'redirect_url' not in self.properties:
            raise ValidationError("redirect_url should be provided in gateway properties!")
