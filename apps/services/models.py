from django.db import models


# Create your models here.

class Service(models.Model):
    name = models.CharField(max_length=120, null=False, blank=False)
    secret_key = models.CharField(max_length=50, null=False, blank=False, unique=True)
