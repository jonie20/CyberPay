from django.contrib import admin
from cyberpayment.models import Payment, Transaction, Services,Account
# Register your models here.

admin.site.register(Payment)
admin.site.register(Transaction)
admin.site.register(Services)
admin.site.register(Account)