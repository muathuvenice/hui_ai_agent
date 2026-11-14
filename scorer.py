# scorer.py - Task 6: Deterministic 5-component credit scoring engine (0 - 1000 scale)
import math
from typing import Dict, Any, Tuple
from schemas import OnChainMetrics, EduKYCResult, ComponentBreakdown

def compute_5_component_score(
    onchain: OnChainMetrics,
    kyc: EduKYCResult,
    hui_history: Dict[str, Any] = None
) -> Tuple[int, str, str, ComponentBreakdown]:
    if hui_history is None:
        hui_history = {"on_time_payments": 5, "total_payments": 5, "defaults": 0}

    # 1. On-chain Score (Max 300)
    if onchain.data_status in ("insufficient_data", "api_error") and onchain.tx_count == 0:
        onchain_pts = 0.0
    else:
        age_norm = min(1.0, math.log1p(onchain.wallet_age_days) / math.log1p(180.0))
        tx_norm = min(1.0, math.log1p(onchain.tx_count) / math.log1p(50.0))
        cp_norm = min(1.0, math.log1p(onchain.unique_counterparties) / math.log1p(15.0))
        onchain_pts = round((120.0 * age_norm + 100.0 * tx_norm + 80.0 * cp_norm) * onchain.success_rate, 2)

    # 2. Hui Behavior Score (Max 300)
    total_p = hui_history.get("total_payments", 0)
    on_time_p = hui_history.get("on_time_payments", 0)
    defaults = hui_history.get("defaults", 0)
    if total_p == 0:
        hui_pts = 150.0
    else:
        ratio = on_time_p / max(1, total_p)
        hui_pts = max(0.0, round(300.0 * ratio - (defaults * 150.0), 2))

    # 3. Edu-KYC Score (Max 200)
    if kyc.status == "verified" and kyc.is_valid:
        kyc_pts = round(200.0 * kyc.confidence, 2)
    elif kyc.status == "manual_review":
        kyc_pts = 50.0
    else:
        kyc_pts = 0.0

    # 4. Anti-Sybil Score (Max 100)
    if onchain.sybil_risk_flag:
        sybil_pts = 10.0
    elif onchain.tx_count == 0:
        sybil_pts = 50.0
    else:
        sybil_pts = 100.0

    # 5. Cashflow & Balance Score (Max 100)
    bal_norm = min(1.0, math.log1p(onchain.balance_avax) / math.log1p(20.0))
    cashflow_pts = round(100.0 * bal_norm, 2)

    breakdown = ComponentBreakdown(
        onchain_score=onchain_pts,
        hui_behavior_score=hui_pts,
        edu_kyc_score=kyc_pts,
        anti_sybil_score=sybil_pts,
        cashflow_score=cashflow_pts
    )

    total_score = int(round(onchain_pts + hui_pts + kyc_pts + sybil_pts + cashflow_pts))
    total_score = max(0, min(1000, total_score))

    if total_score >= 800:
        rank = "Diamond"
    elif total_score >= 650:
        rank = "Gold"
    elif total_score >= 500:
        rank = "Silver"
    elif total_score >= 350:
        rank = "Bronze"
    else:
        rank = "Unranked"

    if onchain.data_status == "api_error" or kyc.status == "manual_review":
        decision = "MANUAL_REVIEW"
    elif total_score >= 400 and not onchain.sybil_risk_flag:
        decision = "PASS"
    else:
        decision = "FAIL"

    return total_score, rank, decision, breakdown
