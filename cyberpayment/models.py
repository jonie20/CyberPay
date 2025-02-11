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
    status = models.CharField(max_length=20) # BORROWED, RETURNED, LOST
    expected_return_date = models.DateField()
    return_date = models.DateField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book} - {self.student}" 

    @property
    def total_fine(self):
        if self.return_date and self.expected_return_date and self.return_date> self.expected_return_date:
            amount = (self.return_date - self.expected_return_date).days * 10
            return amount
        return 0

    @property
    def overdue_days(self):
        if self.return_date and self.expected_return_date and self.return_date> self.expected_return_date:
            days = (self.return_date - self.expected_return_date).days
            return days
        return 0

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        db_table = 'transactions'