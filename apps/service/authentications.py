from functools import lru_cache
from django.contrib.auth.models import AnonymousUser
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _

from rest_framework import authentication, exceptions
from rest_framework.authentication import get_authorization_header

from .models import Service


class ServiceAuthentication(authentication.BaseAuthentication):
    www_authenticate_realm = 'api'

    def get_service_id_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = 'token'
        if not auth or smart_text(auth[0]).lower() != auth_header_prefix:
            return None

        if len(auth) == 1:

            msg = _('Invalid Authorization header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:

            msg = _('Invalid Authorization header. Credentials string '
                    'should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)
        return smart_text(auth[1])

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return '{0} realm="{1}"'.format('TOKEN', self.www_authenticate_realm)

    def authenticate(self, request):
        payload = {}
        uuid = self.get_service_id_value(request)
        if not uuid:  # no id passed in request headers
            raise exceptions.AuthenticationFailed('No such service')  # authentication did not succeed

        try:
            service = self.authenticate_credentials(uuid)  # get the service
        except Service.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such service')  # raise exception if user does not exist
        anonymous_user = AnonymousUser()
        payload.update({'service': service})
        return anonymous_user, payload  # authentication successful

    @lru_cache(maxsize=None)
    def authenticate_credentials(self, uuid):
        """
        Returns an user of the existing service
        """
        if not uuid:
            msg = _('Invalid payload.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            service = Service.objects.get(pk=uuid)
        except Service.DoesNotExist:
            msg = _('Invalid signature.')
            raise exceptions.AuthenticationFailed(msg)

        return service
