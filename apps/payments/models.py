# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.services.models import Service


class Gateway(models.Model):
    FUNCTION_SAMAN = 1
    FUNCTION_BAZAAR = 2
    GATEWAY_FUNCTIONS = (
        (FUNCTION_SAMAN, _('Saman')),
        (FUNCTION_BAZAAR, _('Bazaar')),
    )

    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    display_name = models.CharField(_('display name'), max_length=120)
    title = models.CharField(_('title'), max_length=120)
    image = models.ImageField(upload_to='gateways/images', blank=True)
    properties = JSONField(_("properties"), null=True, blank=True)
    code = models.PositiveSmallIntegerField(_("code"), choices=GATEWAY_FUNCTIONS, default=FUNCTION_SAMAN)
    services = models.ManyToManyField(Service, related_name='gateways', through='ServiceGateway')
    is_enable = models.BooleanField(default=True)


class ServiceGateway(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_gateways')
    gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE, related_name='service_gateways')
    is_enable = models.BooleanField(default=True)
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
