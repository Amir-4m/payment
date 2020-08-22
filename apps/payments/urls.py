from django.urls import path
from .views import bazaar_token_view, BankView, BazaarView

urlpatterns = [
    path('bazaar-token/', bazaar_token_view, name='bazaar-token'),
    path('gateway-bank/', BankView.as_view(), name='bank-gateway'),
    path('gateway-bazaar/', BazaarView.as_view(), name='bazaar-gateway')

]
