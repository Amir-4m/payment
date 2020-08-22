import json
from urllib.parse import urlencode

from django.db import transaction
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import Order, Gateway
from .services import SamanService, BazaarService


def bazaar_token_view(request, *args, **kwargs):
    return HttpResponse()


class GetBankView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(GetBankView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters
        if 'order' not in request.GET:
            return HttpResponse("")
        payment = get_object_or_404(Order, id=request.GET['order'])
        if payment.is_paid is not None or payment.properties.get('redirect_url') is None:
            raise Http404('No order has been found !')

        return render_bank_page(
            request,
            payment.invoice_number,
            payment.gateway.properties.get('gateway_url'),
            payment.gateway.properties.get('merchant_id'),
            payment.price,
            service_logo=payment.service.logo,
            service_color=payment.service.color,
            service_name=payment.service.name,
        )


class VerifyView(View):
    @transaction.atomic
    def post(self, request):
        """
        this method use for bank response posts
        """
        data = request.POST
        invoice_number = data.get("ResNum") or request.GET.get('invoice_number')

        if not invoice_number:
            return HttpResponse("")
        # check and validate parameters
        try:
            payment = Order.objects.select_related(
                'service',
                'gateway'
            ).select_for_update().get(
                invoice_number=invoice_number
            )

        except Order.DoesNotExist:
            return HttpResponse("")
        except Exception:
            return HttpResponse("")

        if payment.is_paid is None and payment.gateway.code == Gateway.FUNCTION_SAMAN:
            purchase_verified = SamanService().verify_saman(
                order=payment,
                data=data
            )
        else:
            purchase_verified = payment.is_paid
        params = {
            'purchase_verified': purchase_verified,
            'service_reference': payment.service_reference,
            'refNum': data.get("RefNum")
        }
        return redirect(payment.properties.get('redirect_url') + '?' + urlencode(params))


def render_bank_page(
        request, invoice_id, request_url,
        merchant_id, amount, phone_number='',
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
        "invoice_id": invoice_id,
        "request_url": request_url,
        "merchant_id": merchant_id,
        "redirect_url": request.build_absolute_uri(reverse('verify-payment')),
        "amount": amount * 10,
        "extra_data": kwargs,
    }
    return render(request, 'payments/pay.html', context=render_context)
