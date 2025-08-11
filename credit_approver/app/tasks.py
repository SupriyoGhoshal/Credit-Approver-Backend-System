from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from decimal import Decimal
from .utils import calculate_emi, round_to_nearest_lakh

@shared_task
def ingest_customer_excel(path):
    df = pd.read_excel(path)
    for _, row in df.iterrows():
        monthly_salary = Decimal(row['monthly_salary'])
        approved = round_to_nearest_lakh(36 * float(monthly_salary))
        Customer.objects.update_or_create(
            customer_id = int(row['customer_id']),
            defaults = {
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'phone_number': str(row.get('phone_number')),
                'monthly_income': monthly_salary,
                'approved_limit': approved,
                'current_debt': Decimal(row.get('current_debt', 0))
            }
        )

@shared_task
def ingest_loan_excel(path):
    df = pd.read_excel(path)
    for _, row in df.iterrows():
        cust_id = int(row['customer id'])
        try:
            customer = Customer.objects.get(customer_id=cust_id)
        except Customer.DoesNotExist:
            continue
        loan_amount = Decimal(row['loan amount'])
        interest_rate = Decimal(row['interest rate'])
        tenure = int(row['tenure'])
        emi = calculate_emi(loan_amount, interest_rate, tenure)
        Loan.objects.update_or_create(
            loan_id = int(row['loan id']),
            defaults = {
                'customer': customer,
                'loan_amount': loan_amount,
                'tenure': tenure,
                'interest_rate': interest_rate,
                'monthly_installment': emi,
                'emis_paid_on_time': int(row.get('EMIs paid on time', 0)),
                'start_date': row.get('start date'),
                'end_date': row.get('end date'),
                'approved': True
            }
        )
