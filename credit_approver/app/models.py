from django.db import models

# Create your models here.

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    age = models.IntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2)
    approved_limit = models.BigIntegerField(default=0)
    current_debt = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.customer_id} - {self.first_name} {self.last_name}"


class Loan(models.Model):
    # loan_id as AutoField
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, related_name="loans", on_delete=models.CASCADE)
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tenure = models.IntegerField(help_text="tenure in months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="annual %")
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    repayments_done = models.IntegerField(default=0)  # how many EMIs paid
    created_at = models.DateTimeField(auto_now_add=True)

    def remaining_repayments(self):
        return max(0, self.tenure - self.repayments_done)
