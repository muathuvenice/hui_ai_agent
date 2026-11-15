# tools.py - Task 4, 5 & 11: Snowtrace tool, Edu-KYC tool, 5-min TTL Cache & Guardrails
import time
import requests
from typing import Dict, Any, Tuple
from schemas import OnChainMetrics, EduKYCResult

_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 300

def _get_cache(key: str) -> Any:
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return val
    return None

def _set_cache(key: str, val: Any) -> None:
    _CACHE[key] = (time.time(), val)

def fetch_snowtrace_profile(wallet_address: str, use_mock: bool = False) -> OnChainMetrics:
    cache_key = f"snowtrace_{wallet_address}_{use_mock}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    if use_mock or wallet_address.startswith("0xMock"):
        if "New" in wallet_address or wallet_address.endswith("000"):
            # Return a mock response indicating no transactions found for the wallet
            res = OnChainMetrics(
                wallet_address=wallet_address, tx_count=0, wallet_age_days=0.0,
                balance_avax=0.0, unique_counterparties=0, success_rate=0.0,
                sybil_risk_flag=False, data_status="insufficient_data"
            )
        elif "Sybil" in wallet_address:
            # Return a mock response indicating potential sybil behavior detected for the wallet
            res = OnChainMetrics(
                wallet_address=wallet_address, tx_count=45, wallet_age_days=1.5,
                balance_avax=0.2, unique_counterparties=1, success_rate=0.95,
                sybil_risk_flag=True, data_status="ok"
            )
        else:
            res = OnChainMetrics(
                wallet_address=wallet_address, tx_count=38, wallet_age_days=240.0,
                balance_avax=25.4, unique_counterparties=14, success_rate=0.97,
                sybil_risk_flag=False, data_status="ok"
            )
        _set_cache(cache_key, res)
        return res

    base_url = "https://api.routescan.io/v2/network/testnet/evm/43113/etherscan/api"
    tx_params = {"module": "account", "action": "txlist", "address": wallet_address, "sort": "asc"}
    bal_params = {"module": "account", "action": "balance", "address": wallet_address, "tag": "latest"}

    for attempt in range(2):
        try:
            tx_resp = requests.get(base_url, params=tx_params, timeout=8).json()
            bal_resp = requests.get(base_url, params=bal_params, timeout=8).json()

            txs = tx_resp.get("result", []) if tx_resp.get("status") == "1" and isinstance(tx_resp.get("result"), list) else []
            raw_bal = float(bal_resp.get("result", 0)) if bal_resp.get("status") == "1" else 0.0
            balance_avax = round(raw_bal / 1e18, 4)

            if not txs:
                res = OnChainMetrics(
                    wallet_address=wallet_address, tx_count=0, wallet_age_days=0.0,
                    balance_avax=balance_avax, unique_counterparties=0, success_rate=0.0,
                    sybil_risk_flag=False, data_status="insufficient_data"
                )
                _set_cache(cache_key, res)
                return res

            tx_count = len(txs)
            first_ts = int(txs[0].get("timeStamp", time.time()))
            wallet_age_days = round(max(0.1, (time.time() - first_ts) / 86400.0), 2)

            counterparties = set()
            success_count = 0
            for tx in txs:
                to_addr = (tx.get("to") or "").lower()
                from_addr = (tx.get("from") or "").lower()
                target = to_addr if from_addr == wallet_address.lower() else from_addr
                if target:
                    counterparties.add(target)
                if str(tx.get("isError", "0")) == "0":
                    success_count += 1

            unique_cp = len(counterparties)
            success_rate = round(success_count / tx_count, 4)
            sybil_flag = (tx_count >= 15 and wallet_age_days < 2.0) or (tx_count >= 10 and unique_cp <= 1)

            res = OnChainMetrics(
                wallet_address=wallet_address,
                tx_count=tx_count,
                wallet_age_days=wallet_age_days,
                balance_avax=balance_avax,
                unique_counterparties=unique_cp,
                success_rate=success_rate,
                sybil_risk_flag=sybil_flag,
                data_status="ok"
            )
            _set_cache(cache_key, res)
            return res
        except Exception:
            if attempt == 1:
                return OnChainMetrics(
                    wallet_address=wallet_address, tx_count=0, wallet_age_days=0.0,
                    balance_avax=0.0, unique_counterparties=0, success_rate=0.0,
                    sybil_risk_flag=False, data_status="api_error"
                )

def verify_edu_kyc(student_id_input: str = "HUST_2026_VALID") -> EduKYCResult:
    if not student_id_input or student_id_input == "MISSING":
        return EduKYCResult(status="manual_review", is_valid=False, confidence=0.0, institution=None)
    if "INVALID" in student_id_input.upper():
        return EduKYCResult(status="unverified", is_valid=False, confidence=0.35, institution="Unknown")
    return EduKYCResult(status="verified", is_valid=True, confidence=0.96, institution="HUST (ĐHBK Hà Nội)")
