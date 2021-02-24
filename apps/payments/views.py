import logging

from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.core.cache import caches

from .models import Order, Gateway, ServiceGateway
from .services import SamanService, MellatService, BazaarService
from .utils import url_parser

logger = logging.getLogger(__name__)


def bazaar_token_view(request, *args, **kwargs):
    gateway_id = kwargs.get('gateway_id')
    code = request.GET.get('code')
    if gateway_id:
        try:
            gateway = ServiceGateway.objects.get(id=gateway_id)
            gateway.properties['auth_code'] = code
            gateway.properties['token_data'] = {}
            cache = caches['payments']
            cache.delete(f'bazaar_access_code_{gateway_id}')
            gateway.save()
            BazaarService().get_access_token(
                gateway,
                request.build_absolute_uri(reverse('bazaar-token', kwargs={'gateway_id': gateway_id}))
            )
            return HttpResponseRedirect(reverse('admin:payments_servicegateway_change', args=gateway.id))
        except Exception as e:
            logger.error(f'updating gateway {gateway_id} auth code failed: {e}')
    return HttpResponse('')


class GetBankView(View):

    def get(self, request, order_id):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters

        payment = get_object_or_404(Order, id=order_id)
        ref_id = None
        if payment.is_paid is not None or payment.service_gateway is None:
            raise Http404('No order has been found !')
        if payment.service_gateway.code == ServiceGateway.FUNCTION_MELLAT:
            ref_id = MellatService().request_mellat(
                payment, request.build_absolute_uri(
                    reverse('verify-payment', kwargs={'gateway_code': ServiceGateway.FUNCTION_MELLAT})
                )
            )
        return render_bank_page(
            request,
            payment.service_gateway.code,
            payment.transaction_id,
            payment.service_gateway.gateway_url,
            payment.service_gateway.properties.get('merchant_id'),
            payment.price,
            username=payment.service_gateway.properties.get('username'),
            password=payment.service_gateway.properties.get('password'),
            service_logo=payment.service.logo,
            service_color=payment.service.color,
            service_name=payment.service.name,
            ref_id=ref_id,
        )


class VerifyView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(VerifyView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        this method use for bank response posts
        """
        data = request.POST
        filter_data = {}
        gateway_code = kwargs['gateway_code']
        if gateway_code == ServiceGateway.FUNCTION_SAMAN:
            filter_data = {"transaction_id": data.get("ResNum") or request.GET.get('transaction_id')}
        elif gateway_code == ServiceGateway.FUNCTION_MELLAT:
            filter_data = {"reference_id": data.get('RefId')}

        # check and validate parameters
        try:
            payment = Order.objects.select_related(
                'service',
                'gateway'
            ).select_for_update(of=('self',)).get(
                **filter_data
            )
        except Order.DoesNotExist:
            logger.error(f'order with {filter_data} does not exists!')
            return HttpResponse("")

        except Exception as e:
            logger.error(
                f'error occurred for verifying bank transaction for order with transaction_id {filter_data}'
            )
            return HttpResponseBadRequest(e)

        if payment.is_paid is not None:
            logger.error(f'order with  {filter_data} is_paid status is not None!')
            raise Http404("No order has been found !")
        if payment.service_gateway.code == ServiceGateway.FUNCTION_SAMAN:
            purchase_verified = SamanService().verify_saman(
                order=payment,
                data=data
            )
        elif payment.service_gateway.code == ServiceGateway.FUNCTION_MELLAT:
            purchase_verified = MellatService().verify_mellat(
                order=payment,
                data=data
            )

        else:
            purchase_verified = payment.is_paid

        params = {
            'purchase_verified': purchase_verified,
            'transaction_id': payment.transaction_id,
            'refNum': data.get("RefNum") or payment.reference_id
        }

        return redirect(url_parser(payment.properties.get('redirect_url'), params=params))


def render_bank_page(
        request, gateway_code, invoice_id, request_url,
        merchant_id, amount, phone_number='', username=None, password=None,
        service_logo=None, service_color=None, service_name=None, **kwargs
):
    """
    send parameters to a template ... template contain a form include these parameters
    this form automatically submit to bank url
    """

    render_context = {
        'service_logo': service_logo,
        'service_color': service_color,
        'service_name': service_name,
        'request_url': request_url,
    }
    if gateway_code == "MELLAT":
        render_context.update({
            "form_data": {
                "RefId": kwargs.get('ref_id')
            },
        })

    elif gateway_code == "SAMAN":
        render_context.update({
            "form_data": {
                "ResNum": invoice_id,
                "MID": merchant_id,
                "RedirectURL": request.build_absolute_uri(
                    reverse('verify-payment', kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
                ),
                "Amount": amount * 10,
                "CellNumber": phone_number,
            }
        })

    return render(request, 'payments/pay.html', context=render_context)
