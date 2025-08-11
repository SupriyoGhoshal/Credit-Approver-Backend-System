import decimal
from decimal import Decimal

def calculate_emi(P: Decimal, annual_rate_pct: Decimal, n: int) -> Decimal:
    if n <= 0:
        return Decimal('0')
    r = (annual_rate_pct / Decimal(100)) / Decimal(12)
    if r == 0:
        return (P / Decimal(n)).quantize(Decimal('0.01'))
    numerator = P * r * (1 + r) ** n
    denominator = ((1 + r) ** n) - 1
    emi = numerator / denominator
    return emi.quantize(Decimal('0.01'))

def round_to_nearest_lakh(amount):
    # amount numeric
    lakh = 100000
    return int(round(amount / lakh) * lakh)


def compute_credit_score(customer, loans_queryset):
    """
    Suggested heuristic — normalize to 0-100.
    loans_queryset should be ALL loans for this customer (past + current)
    """
    score = 50.0
    # component 1: percent of EMIs paid on time across loans
    total_emis = 0
    ontime_emis = 0
    for ln in loans_queryset:
        total = ln.emis_paid_on_time + (ln.repayments_done - ln.emis_paid_on_time if ln.repayments_done>ln.emis_paid_on_time else 0)
        # fallback
        total = max(ln.repayments_done, ln.tenure)
        total_emis += total
        ontime_emis += ln.emis_paid_on_time

    if total_emis > 0:
        p_ontime = ontime_emis / total_emis
        score += 30 * p_ontime  # up to +30
    else:
        score += 5  # small boost if no loan history

    # component 2: number of loans (penalize many loans)
    num_loans = loans_queryset.count()
    if num_loans == 0:
        score += 10
    else:
        score -= min(15, num_loans * 2)

    # component 3: recent activity (loans in current year)
    from django.utils.timezone import now
    current_year = now().year
    recent_loans = loans_queryset.filter(start_date__year=current_year).count()
    if recent_loans > 0:
        score -= min(10, recent_loans * 2)

    # component 4: loan approved volume (higher volume reduces score somewhat)
    total_volume = sum([float(ln.loan_amount) for ln in loans_queryset])
    # scale: if total_volume > (6 * monthly_income) penalize
    try:
        monthly_income = float(customer.monthly_income)
        if monthly_income > 0 and total_volume > 6 * monthly_income:
            score -= 20
    except:
        pass

    # clamp
    score = max(0, min(100, score))
    # special rule: if sum current loans > approved_limit -> 0
    current_loans_sum = sum([float(ln.loan_amount) for ln in loans_queryset if not ln.approved or (ln.approved and ln.repayments_done < ln.tenure)])
    if current_loans_sum > float(customer.approved_limit):
        return 0.0

    return round(score, 2)
