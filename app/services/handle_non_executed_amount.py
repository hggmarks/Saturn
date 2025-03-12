from datetime import datetime
from typing import List

from app.models import Quota
from app.foxbit.constants import MINIMUM_BTC_TRADING

def handle_non_executed_amount(user_id: int, non_executed_amount: float, cost_price: float) -> None:
    """
    Handle non-executed amount from a PARTIALLY_CANCELED order.
    If the amount is sufficient, creates a new quota.
    If insufficient, tries to merge with other quotas.
    
    Args:
        user_id: The ID of the user who owns the order
        non_executed_amount: The amount that wasn't executed (in BTC)
        cost_price: The cost price of the non-executed amount
    """
    if non_executed_amount >= MINIMUM_BTC_TRADING:
        # Case 1: Amount is sufficient, create new quota
        quota = Quota()
        quota.user_id = user_id
        quota.amount = non_executed_amount
        quota.price = cost_price
        quota.created_at = datetime.now()
        quota.quota_state = 'ACTIVE'
        quota.save()
        return

    # Case 2: Amount is insufficient, try to merge with other quotas
    active_quotas: List[Quota] = Quota.where(user_id=[user_id], quota_state=['ACTIVE'])
    
    if not active_quotas:
        # No quotas to merge with, just return
        return
    
    # Sort quotas by creation date (oldest first) to prioritize older quotas
    active_quotas.sort(key=lambda q: q.created_at)
    
    total_amount = non_executed_amount
    merged_cost = non_executed_amount * cost_price
    quotas_to_merge = []
    
    # Find quotas to merge until we reach minimum trading amount
    for quota in active_quotas:
        total_amount += quota.amount
        merged_cost += quota.amount * quota.price
        quotas_to_merge.append(quota)
        
        if total_amount >= MINIMUM_BTC_TRADING:
            break
    
    if total_amount >= MINIMUM_BTC_TRADING:
        # Calculate weighted average price
        weighted_avg_price = merged_cost / total_amount
        
        # Create new merged quota
        new_quota = Quota()
        new_quota.user_id = user_id
        new_quota.amount = total_amount
        new_quota.price = weighted_avg_price
        new_quota.created_at = datetime.now()
        new_quota.quota_state = 'ACTIVE'
        new_quota.save()
        
        # Mark old quotas as merged
        for quota in quotas_to_merge:
            quota.quota_state = 'MERGED'
            quota.save() 