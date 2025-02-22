from django.db import models

# Create your models here.
class Services(models.Model):
    name = models.CharField(max_length=100)
    cost = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Payment(models.Model):
    merchant_request_id = models.CharField(max_length=100)
    checkout_request_id = models.CharField(max_length=100)
    code = models.CharField(max_length=30, null=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        db_table = 'payments'
    def __str__(self):
        return f"{self.merchant_request_id} - {self.code} - {self.amount}"

class Transaction(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_id = models.CharField(max_length=100)
    mpesa_code = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mpesa_code} - {self.amount} KES"
