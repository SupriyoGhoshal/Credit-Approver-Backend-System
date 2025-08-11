from rest_framework import serializers
from .models import Customer, Loan

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'age', 'monthly_income', 'approved_limit', 'phone_number', 'current_debt']

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'tenure', 'interest_rate', 'monthly_installment', 'approved', 'start_date', 'end_date', 'repayments_done', 'emis_paid_on_time']
