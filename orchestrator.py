# orchestrator.py - Task 8 & 14: Main orchestrator exposing clean functions for Streamlit UI (Đức Anh)
import time
import json
from typing import Dict, Any, List
from tools import fetch_snowtrace_profile, verify_edu_kyc
from scorer import compute_5_component_score
from llm_factory import generate_vietnamese_reasons
from advisors import route_single_wallet, matchmake_wallets, get_top_3_avalanche_yields
from schemas import CreditScoreResult

def evaluate_wallet_full(
    wallet_address: str,
    student_id_input: str = "HUST_2026_VALID",
    hui_history: Dict[str, Any] = None,
    use_mock: bool = False
) -> Dict[str, Any]:
    """
    Task 8 & 14: Single entry point for Streamlit UI.
    Executes Credit Scoring + Matchmaker Routing + Top-3 Yield Advisor in < 30 seconds.
    """
    start_ts = time.time()

    # 1. Fetch On-chain & Edu-KYC data
    onchain = fetch_snowtrace_profile(wallet_address, use_mock=use_mock)
    kyc = verify_edu_kyc(student_id_input)

    # 2. Deterministic 5-component scoring (0-1000)
    total_score, rank, decision, breakdown = compute_5_component_score(onchain, kyc, hui_history)

    # 3. Generate Vietnamese explanation via LLM Factory (or fallback template)
    reasons = generate_vietnamese_reasons(onchain, kyc, breakdown, total_score, decision)
    elapsed_ms = round((time.time() - start_ts) * 1000, 2)

    score_res = CreditScoreResult(
        wallet_address=wallet_address,
        total_score=total_score,
        rank=rank,
        decision=decision,
        breakdown=breakdown,
        reasons=reasons,
        execution_time_ms=elapsed_ms
    )

    # 4. Route wallet to Saving Pool or Bidding Pool
    matchmaker_res = route_single_wallet(score_res, onchain.tx_count)

    # 5. Fetch Top-3 Avalanche Yield Pools
    yield_res = get_top_3_avalanche_yields(use_mock=use_mock)

    return {
        "credit_scoring": score_res.model_dump(),
        "matchmaker": matchmaker_res.model_dump(),
        "yield_advisor": yield_res.model_dump()
    }

if __name__ == "__main__":
    print("=== DEMO MỐC A & B: ĐÁNH GIÁ VÍ CŨ UY TÍN (TRÊN FUJI TESTNET) ===")
    sample_wallet = "0x8db97C7cEcE249c2b98bDC0226Cc4C2A57BF52FC"
    full_report = evaluate_wallet_full(wallet_address=sample_wallet, use_mock=False)
    print(json.dumps(full_report, indent=2, ensure_ascii=False))

    print("\n=== DEMO MỐC C: TEST MATCHMAKER VỚI 8 VÍ MẪU (VÍ MỚI -> SAVING, VÍ CŨ -> BIDDING) ===")
    eight_test_wallets = [
        ("0xMockNewWallet_01_000", "HUST_01", {"on_time_payments": 0, "total_payments": 0, "defaults": 0}),
        ("0xMockNewWallet_02_000", "HUST_02", {"on_time_payments": 0, "total_payments": 0, "defaults": 0}),
        ("0xMockActive_03", "HUST_03", {"on_time_payments": 10, "total_payments": 10, "defaults": 0}),
        ("0xMockActive_04", "HUST_04", {"on_time_payments": 9, "total_payments": 10, "defaults": 0}),
        ("0xMockActive_05", "HUST_05", {"on_time_payments": 6, "total_payments": 10, "defaults": 0}),
        ("0xMockActive_06", "HUST_06", {"on_time_payments": 5, "total_payments": 10, "defaults": 0}),
        ("0xMockSybil_07", "HUST_07", {"on_time_payments": 1, "total_payments": 5, "defaults": 1}),
        ("0xMockMissingKYC_08", "MISSING", {"on_time_payments": 5, "total_payments": 5, "defaults": 0}),
    ]
    batch_input: List[Dict[str, Any]] = []
    for w_addr, kyc_id, h_hist in eight_test_wallets:
        onchain_m = fetch_snowtrace_profile(w_addr, use_mock=True)
        kyc_m = verify_edu_kyc(kyc_id)
        sc, rnk, dec, brk = compute_5_component_score(onchain_m, kyc_m, h_hist)
        c_res = CreditScoreResult(
            wallet_address=w_addr, total_score=sc, rank=rnk, decision=dec,
            breakdown=brk, reasons=["Mock test"], execution_time_ms=1.0
        )
        batch_input.append({"score_result": c_res, "tx_count": onchain_m.tx_count})

    grouped = matchmake_wallets(batch_input)
    print(json.dumps(grouped.model_dump(), indent=2, ensure_ascii=False))
