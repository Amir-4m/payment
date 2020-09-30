from urllib.parse import urlencode
from datetime import datetime

from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import Order, Gateway
from .services import SamanService


def bazaar_token_view(request, *args, **kwargs):
    return HttpResponse()


class GetBankView(View):

    def get(self, request, order_id):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters

        payment = get_object_or_404(Order, id=order_id)
        if payment.is_paid is not None or payment.properties.get('redirect_url') is None:
            raise Http404('No order has been found !')

        return render_bank_page(
            request,
            payment.gateway.code,
            payment.invoice_number,
            payment.gateway.properties.get('gateway_url'),
            payment.gateway.properties.get('merchant_id'),
            payment.price,
            username=payment.gateway.properties.get('username'),
            password=payment.gateway.properties.get('password'),
            service_logo=payment.service.logo,
            service_color=payment.service.color,
            service_name=payment.service.name,
        )


class VerifyView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(VerifyView, self).dispatch(request, *args, **kwargs)

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
        if payment.is_paid is not None:
            raise Http404("No order has been found !")
        if payment.gateway.code == Gateway.FUNCTION_SAMAN:
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

        return redirect(f"{payment.properties.get('redirect_url')}?{urlencode(params)}")


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
                "terminalId": merchant_id,
                "userName": username,
                "userPassword": password,
                "callBackUrl": request.build_absolute_uri(reverse('verify-payment')),
                "amount": amount * 10,
                "orderId": invoice_id,
                "localDate": datetime.now().strftime("%Y%m%d"),
                "localTime": datetime.now().strftime("%H%M%S"),

                "extra_data": kwargs,
            },
            'request_url': f"{request_url}?RefId={str(invoice_id)}",
        })

    elif gateway_code == "SAMAN":
        render_context.update({
            "form_data": {
                "ResNum": invoice_id,
                "request_url": request_url,
                "MID": merchant_id,
                "RedirectURL": request.build_absolute_uri(reverse('verify-payment')),
                "Amount": amount * 10,
                "CellNumber": phone_number,
                "extra_data": kwargs,
            }
        })

    return render(request, 'payments/pay.html', context=render_context)
