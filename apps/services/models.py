from django.db import models
from colorful.fields import RGBColorField


class Service(models.Model):
    name = models.CharField(max_length=120, null=False, blank=False)
    secret_key = models.CharField(max_length=50, null=False, blank=False, unique=True)
    logo = models.ImageField(upload_to='services/images')
    color = RGBColorField(blank=True)
    gateways = models.ManyToManyField('payments.Gateway', related_name='services')
