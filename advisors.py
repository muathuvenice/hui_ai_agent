# advisors.py - Task 9 & 10: AI Matchmaker & Top-3 Yield Advisor
import requests
from typing import List, Dict, Any
from schemas import CreditScoreResult, MatchmakerProfile, MatchmakerGroupResult, YieldPoolItem, YieldAdvisorResult
from tools import _get_cache, _set_cache

SAFE_AVALANCHE_PROTOCOLS = {"aave-v3", "benqi-lending", "benqi-staked-avax", "trader-joe-dex", "gmx-v2-perps"}

def route_single_wallet(score_result: CreditScoreResult, tx_count: int) -> MatchmakerProfile:
    if score_result.decision == "MANUAL_REVIEW":
        return MatchmakerProfile(
            wallet_address=score_result.wallet_address,
            total_score=score_result.total_score,
            rank=score_result.rank,
            assigned_pool="Manual Review",
            group_id="PENDING_ADMIN_REVIEW",
            routing_reason="Hồ sơ thiếu dữ liệu Edu-KYC hoặc lỗi API, cần Admin duyệt thủ công (HITL)."
        )

    if tx_count < 5 or score_result.total_score < 500 or score_result.decision == "FAIL":
        return MatchmakerProfile(
            wallet_address=score_result.wallet_address,
            total_score=score_result.total_score,
            rank=score_result.rank,
            assigned_pool="Saving Pool",
            group_id=f"SAVING_POOL_{score_result.rank.upper()}",
            routing_reason="Ví mới (<5 giao dịch) hoặc điểm tín dụng <500: Phân luồng vào Saving Pool."
        )

    return MatchmakerProfile(
        wallet_address=score_result.wallet_address,
        total_score=score_result.total_score,
        rank=score_result.rank,
        assigned_pool="Bidding Pool",
        group_id=f"BIDDING_GROUP_{score_result.rank.upper()}",
        routing_reason=f"Ví có lịch sử uy tín ({tx_count} txs, {score_result.total_score} điểm): Đủ điều kiện tham gia Bidding Pool cùng nhóm hạng {score_result.rank}."
    )

def matchmake_wallets(scored_wallets: List[Dict[str, Any]]) -> MatchmakerGroupResult:
    saving_list: List[MatchmakerProfile] = []
    bidding_groups: Dict[str, List[MatchmakerProfile]] = {}

    for item in scored_wallets:
        profile = route_single_wallet(item["score_result"], item["tx_count"])
        if profile.assigned_pool in ("Saving Pool", "Manual Review"):
            saving_list.append(profile)
        else:
            gid = profile.group_id or "BIDDING_DEFAULT"
            bidding_groups.setdefault(gid, []).append(profile)

    return MatchmakerGroupResult(
        saving_pool_wallets=saving_list,
        bidding_groups=bidding_groups,
        summary_note="Đề xuất ghép dây Hụi từ AI Matchmaker. Người dùng/Admin bấm nút xác nhận để tham gia (HITL)."
    )

def get_top_3_avalanche_yields(use_mock: bool = False) -> YieldAdvisorResult:
    cache_key = f"defillama_top3_{use_mock}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    fallback_pools = [
        YieldPoolItem(pool_id="aave-v3-usdc", project="aave-v3", symbol="USDC", tvl_usd=85400000.0, apy=5.42),
        YieldPoolItem(pool_id="benqi-savax", project="benqi-staked-avax", symbol="sAVAX", tvl_usd=192000000.0, apy=5.85),
        YieldPoolItem(pool_id="benqi-usdt", project="benqi-lending", symbol="USDT", tvl_usd=34100000.0, apy=6.18),
    ]

    if not use_mock:
        try:
            resp = requests.get("https://yields.llama.fi/pools", timeout=10).json()
            raw_pools = resp.get("data", [])
            safe_pools = [
                p for p in raw_pools
                if p.get("chain") == "Avalanche"
                and (p.get("project") in SAFE_AVALANCHE_PROTOCOLS or p.get("tvlUsd", 0) >= 5_000_000)
                and p.get("tvlUsd", 0) >= 1_000_000
                and 0.5 <= (p.get("apy") or 0.0) <= 40.0
            ]
            safe_pools.sort(key=lambda x: x.get("tvlUsd", 0.0), reverse=True)
            if len(safe_pools) >= 3:
                fallback_pools = [
                    YieldPoolItem(
                        pool_id=str(p.get("pool")),
                        project=str(p.get("project")),
                        symbol=str(p.get("symbol")),
                        tvl_usd=round(float(p.get("tvlUsd", 0.0)), 2),
                        apy=round(float(p.get("apy", 0.0)), 2)
                    )
                    for p in safe_pools[:3]
                ]
        except Exception:
            pass

    result = YieldAdvisorResult(
        chain="Avalanche",
        top_3_pools=fallback_pools,
        hitl_required=True,
        action_button_label="Xác nhận gửi quỹ nhàn rỗi vào Pool (HITL - Yêu cầu chữ ký ví)",
        disclaimer="MIỄN TRỪ TRÁCH NHIỆM: AI Yield Advisor chỉ đọc dữ liệu APY công khai từ DefiLlama và đưa ra gợi ý. Hệ thống KHÔNG tự động gửi tiền. Mọi giao dịch đều do người dùng hoặc Admin trực tiếp bấm nút và ký xác nhận."
    )
    _set_cache(cache_key, result)
    return result
