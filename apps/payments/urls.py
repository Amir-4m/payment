from django.urls import path
from .views import bazaar_token_view, GetBankView, VerifyView

urlpatterns = [
    path('bazaar-token/<int:gateway_id>/', bazaar_token_view, name='bazaar-token'),
    path('gateway-bank/<int:order_id>/', GetBankView.as_view(), name='bank-gateway'),
    path('verify/<str:gateway_code>/', VerifyView.as_view(), name='verify-payment'),

]
