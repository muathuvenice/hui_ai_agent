# test_agent.py - Task 12: Automated pytest suite for scoring, schemas, matchmaker, and guardrails
from tools import fetch_snowtrace_profile, verify_edu_kyc
from scorer import compute_5_component_score
from advisors import matchmake_wallets, get_top_3_avalanche_yields
from orchestrator import evaluate_wallet_full
from schemas import CreditScoreResult

def test_deterministic_scoring_reproducibility():
    """Task 6 & 12: Scoring the same wallet twice must return the exact same 0-1000 score."""
    onchain = fetch_snowtrace_profile("0xMockActive_01", use_mock=True)
    kyc = verify_edu_kyc("HUST_2026_VALID")
    s1, r1, d1, _ = compute_5_component_score(onchain, kyc)
    s2, r2, d2, _ = compute_5_component_score(onchain, kyc)
    assert s1 == s2
    assert 0 <= s1 <= 1000
    assert r1 == r2
    assert d1 == "PASS"

def test_missing_kyc_triggers_manual_review():
    """Section 5 Guardrail: Missing Edu-KYC must never fabricate data; must return MANUAL_REVIEW."""
    onchain = fetch_snowtrace_profile("0xMockActive_01", use_mock=True)
    kyc = verify_edu_kyc("MISSING")
    _, _, decision, _ = compute_5_component_score(onchain, kyc)
    assert decision == "MANUAL_REVIEW"

def test_matchmaker_8_wallets_routing():
    """Task 9 & Mốc C: New wallets route to Saving Pool, established wallets route to Bidding Pool."""
    wallets = [
        ("0xMockNew_1_000", "HUST_1"),
        ("0xMockNew_2_000", "HUST_2"),
        ("0xMockOld_3", "HUST_3"),
        ("0xMockOld_4", "HUST_4"),
        ("0xMockOld_5", "HUST_5"),
        ("0xMockOld_6", "HUST_6"),
        ("0xMockOld_7", "HUST_7"),
        ("0xMockOld_8", "HUST_8"),
    ]
    batch = []
    for addr, k_id in wallets:
        oc = fetch_snowtrace_profile(addr, use_mock=True)
        kyc = verify_edu_kyc(k_id)
        sc, rnk, dec, brk = compute_5_component_score(oc, kyc)
        c_res = CreditScoreResult(
            wallet_address=addr, total_score=sc, rank=rnk, decision=dec,
            breakdown=brk, reasons=["Test"], execution_time_ms=1.0
        )
        batch.append({"score_result": c_res, "tx_count": oc.tx_count})

    res = matchmake_wallets(batch)
    assert len(res.saving_pool_wallets) == 2
    total_bidding = sum(len(v) for v in res.bidding_groups.values())
    assert total_bidding == 6

def test_yield_advisor_hitl_and_top3():
    """Task 10 & Mốc C: Yield Advisor returns exactly 3 pools and enforces HITL flag."""
    y_res = get_top_3_avalanche_yields(use_mock=True)
    assert len(y_res.top_3_pools) == 3
    assert y_res.hitl_required is True

def test_end_to_end_latency_under_30s():
    """Mốc A: Full orchestrator in mock mode finishes well under 30s KPI."""
    out = evaluate_wallet_full("0xMockActive_99", use_mock=True)
    assert out["credit_scoring"]["execution_time_ms"] < 30000
    assert "matchmaker" in out
    assert "yield_advisor" in out
