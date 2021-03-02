# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.services.models import Service


class ServiceGateway(models.Model):
    FUNCTION_SAMAN = "SAMAN"
    FUNCTION_BAZAAR = "BAZAAR"
    FUNCTION_MELLAT = "MELLAT"
    GATEWAY_FUNCTIONS = (
        (FUNCTION_SAMAN, _('Saman')),
        (FUNCTION_BAZAAR, _('Bazaar')),
        (FUNCTION_MELLAT, _('Mellat')),
    )

    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    title = models.CharField(_('title'), max_length=120)
    display_name = models.CharField(_('display name'), max_length=120)
    image = models.ImageField(upload_to='gateways/images')
    service = models.ForeignKey('services.Service', related_name='service_gateways', on_delete=models.CASCADE)
    properties = JSONField(_("properties"), default=dict)
    code = models.CharField(_("code"), max_length=10, choices=GATEWAY_FUNCTIONS, default=FUNCTION_SAMAN)
    priority = models.PositiveSmallIntegerField(_('priority'), default=1, db_index=True)
    is_enable = models.BooleanField(_('is enable'), default=True)

    # class Meta:
    #     unique_together = ('service', 'gateway')

    def clean(self):
        bazaar_params = ['client_id', 'client_secret']
        bank_params = ['merchant_id']

        if self.code == self.FUNCTION_BAZAAR:
            for param in bazaar_params:
                if param not in self.properties:
                    raise ValidationError(f"{param} should be provided in gateway properties!")
        else:
            for param in bank_params:
                if param not in self.properties:
                    raise ValidationError(f"{param} should be provided in gateway properties!")

    def __str__(self):
        return self.display_name

    @property
    def mellat_wsdl(self):
        return 'https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl'

    @property
    def saman_verify_url(self):
        return 'https://verify.sep.ir/payments/referencepayment.asmx?WSDL'

    @property
    def gateway_url(self):
        if self.code == ServiceGateway.FUNCTION_SAMAN:
            return 'https://sep.shaparak.ir/Payment.aspx'
        elif self.code == ServiceGateway.FUNCTION_MELLAT:
            return 'https://bpm.shaparak.ir/pgwchannel/startpay.mellat'


class Order(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='orders')
    service_gateway = models.ForeignKey(ServiceGateway, on_delete=models.CASCADE, related_name='orders', null=True)
    price = models.PositiveIntegerField(_('price'))
    transaction_id = models.UUIDField(_('transaction_id'), default=uuid.uuid4, unique=True, editable=False)
    service_reference = models.CharField(_("service reference"), max_length=100)
    reference_id = models.CharField(_("reference id"), max_length=100, db_index=True, blank=True)
    log = models.TextField(_("payment log"), blank=True)
    properties = JSONField(_("properties"), blank=True, default=dict)
    is_paid = models.NullBooleanField(_("is paid"))

    class Meta:
        unique_together = ('service', 'service_reference')

    def clean(self):
        if self.service_gateway and self.service_gateway.code == ServiceGateway.FUNCTION_SAMAN and 'redirect_url' not in self.properties:
            raise ValidationError("redirect_url should be provided in gateway properties!")
