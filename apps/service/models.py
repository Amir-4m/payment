import uuid as uuid
from django.db import models


# Create your models here.

class Service(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=120, null=False, blank=False)

    @property
    def is_authenticated(self):
        return Service.objects.filter(uuid=self.uuid).exists()
