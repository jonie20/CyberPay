"""
URL configuration for CyberPay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from cyberpayment import views
from cyberpayment.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ipay, name="home"),
    path('v1', views.dash, name="dash"),
    path('payment_history/', views.payment_history, name="payment_history"),
    path('test', views.payment_view, name='payment'),
    path('callback/', views.payment_callback, name='payment_callback'),
    path('stk-status/', views.stk_status_view, name='stk_status'),
    path('activate/<uid>/<token>/', views.set_pass, name='set-pass'),
    path('users', views.users, name="users"),
    path('add-user/', views.add_user, name='add_user'),
    path('payments', views.payments, name="payments"),
    path('services', views.services, name="services")
]
