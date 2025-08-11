from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer, LoanSerializer
from .utils import calculate_emi, round_to_nearest_lakh, compute_credit_score
from decimal import Decimal

class RegisterView(APIView):
    def post(self, request):
        data = request.data
        first = data.get('first_name')
        last = data.get('last_name')
        age = data.get('age')
        monthly_income = Decimal(data.get('monthly_income', 0))
        phone = data.get('phone_number')

        if not (first and last and monthly_income and phone):
            return Response({"error":"missing fields"}, status=status.HTTP_400_BAD_REQUEST)

        approved_limit = round_to_nearest_lakh(36 * float(monthly_income))
        customer = Customer.objects.create(
            first_name=first,
            last_name=last,
            age=age,
            monthly_income=monthly_income,
            phone_number=phone,
            approved_limit = approved_limit
        )
        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CheckEligibilityView(APIView):
    def post(self, request):
        # calculates credit score and checks rules, returns response described in prompt
        from django.shortcuts import get_object_or_404
        data = request.data
        customer_id = data.get('customer_id')
        loan_amount = Decimal(data.get('loan_amount'))
        interest_rate = Decimal(data.get('interest_rate'))
        tenure = int(data.get('tenure'))

        customer = get_object_or_404(Customer, pk=customer_id)
        loans = Loan.objects.filter(customer=customer)
        credit_score = compute_credit_score(customer, loans)

        # if sum current EMIs > 50% monthly salary => reject
        total_current_emi = sum([float(ln.monthly_installment) for ln in loans if ln.approved and ln.repayments_done < ln.tenure])
        if total_current_emi > 0.5 * float(customer.monthly_income):
            return Response({
                "customer_id": customer.customer_id,
                "approval": False,
                "interest_rate": float(interest_rate),
                "corrected_interest_rate": None,
                "tenure": tenure,
                "monthly_installment": None,
                "message": "Total EMI burden exceeds 50% of monthly income. Loan not approved."
            }, status=status.HTTP_200_OK)

        # slab decision
        corrected_interest_rate = float(interest_rate)
        approve = False

        if credit_score > 50:
            approve = True
        elif 30 < credit_score <= 50:
            # require interest_rate > 12%
            if interest_rate >= Decimal('12.0'):
                approve = True
            else:
                corrected_interest_rate = 12.0
                approve = False
        elif 10 < credit_score <= 30:
            if interest_rate >= Decimal('16.0'):
                approve = True
            else:
                corrected_interest_rate = 16.0
                approve = False
        else:
            approve = False

        # EMI calculation using corrected_interest_rate for repayment figure
        used_rate = Decimal(corrected_interest_rate)
        emi = calculate_emi(loan_amount, used_rate, tenure)

        return Response({
            "customer_id": customer.customer_id,
            "approval": bool(approve),
            "interest_rate": float(interest_rate),
            "corrected_interest_rate": float(corrected_interest_rate),
            "tenure": tenure,
            "monthly_installment": float(emi),
            "credit_score": float(credit_score)
        }, status=status.HTTP_200_OK)

class CreateLoanView(APIView):
    def post(self, request):
        # reuse eligibility logic and create loan if approved
        data = request.data
        customer_id = data.get('customer_id')
        customer = Customer.objects.get(pk=customer_id)
        # call CheckEligibility logic (you may refactor to helper)
        # ... (for brevity, call same pattern as above)
        # if approved create Loan() record with approved=True and set monthly_installment
        # return loan_id or null
        # (I'll implement compactly by calling CheckEligibilityView logic; in real code refactor)
        from rest_framework.request import Request
        check = CheckEligibilityView()
        response = check.post(request)
        resp_data = response.data
        if not resp_data.get('approval'):
            return Response({
                "loan_id": None,
                "customer_id": customer_id,
                "loan_approved": False,
                "message": resp_data.get("message", "Not approved"),
                "monthly_installment": None
            }, status=status.HTTP_200_OK)

        # create loan
        loan = Loan.objects.create(
            customer=customer,
            loan_amount = Decimal(data.get('loan_amount')),
            tenure = int(data.get('tenure')),
            interest_rate = Decimal(resp_data.get('corrected_interest_rate')),
            monthly_installment = Decimal(resp_data.get('monthly_installment')),
            approved = True,
            start_date = None,
            end_date = None,
            repayments_done = 0
        )
        return Response({
            "loan_id": loan.loan_id,
            "customer_id": customer_id,
            "loan_approved": True,
            "message": "Loan approved and created",
            "monthly_installment": float(loan.monthly_installment)
        }, status=status.HTTP_201_CREATED)

class ViewLoanView(APIView):
    def get(self, request, loan_id):
        loan = Loan.objects.select_related('customer').get(pk=loan_id)
        c = loan.customer
        customer_json = {
            "id": c.customer_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "phone_number": c.phone_number,
            "age": c.age
        }
        return Response({
            "loan_id": loan.loan_id,
            "customer": customer_json,
            "loan_amount": float(loan.loan_amount),
            "interest_rate": float(loan.interest_rate),
            "approved": loan.approved,
            "monthly_installment": float(loan.monthly_installment),
            "tenure": loan.tenure
        })
        
class ViewLoansByCustomer(APIView):
    def get(self, request, customer_id):
        loans = Loan.objects.filter(customer__customer_id=customer_id)
        out = []
        for ln in loans:
            out.append({
                "loan_id": ln.loan_id,
                "loan_amount": float(ln.loan_amount),
                "approved": ln.approved,
                "interest_rate": float(ln.interest_rate),
                "monthly_installment": float(ln.monthly_installment),
                "repayments_left": max(0, ln.tenure - ln.repayments_done)
            })
        return Response(out)
