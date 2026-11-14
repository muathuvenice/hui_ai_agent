# llm_factory.py - Task 3 & 7: Multi-provider LLM factory + Vietnamese explanation
import os
import json
from typing import List
from dotenv import load_dotenv
from schemas import OnChainMetrics, EduKYCResult, ComponentBreakdown, LLMExplanation

load_dotenv()

def _template_fallback_reasons(
    onchain: OnChainMetrics,
    kyc: EduKYCResult,
    breakdown: ComponentBreakdown,
    total_score: int,
    decision: str
) -> List[str]:
    reasons = []
    if onchain.data_status == "insufficient_data":
        reasons.append("Ví mới chưa có lịch sử giao dịch trên mạng Avalanche (0 giao dịch), khuyến nghị vào Saving Pool.")
    elif onchain.data_status == "api_error":
        reasons.append("Không thể kết nối Snowtrace API, chuyển trạng thái sang chờ duyệt thủ công (manual_review).")
    else:
        reasons.append(
            f"Lịch sử On-chain đạt {breakdown.onchain_score}/300 điểm ({onchain.tx_count} giao dịch, tuổi ví {onchain.wallet_age_days} ngày, {onchain.unique_counterparties} đối tác)."
        )

    reasons.append(f"Điểm kỷ luật đóng Hụi đạt {breakdown.hui_behavior_score}/300 điểm.")

    if kyc.status == "verified":
        reasons.append(f"Đã xác thực Edu-KYC sinh viên ({kyc.institution}) với độ tin cậy {int(kyc.confidence*100)}% (+{breakdown.edu_kyc_score} điểm).")
    elif kyc.status == "manual_review":
        reasons.append("Chưa đủ dữ liệu Edu-KYC thẻ sinh viên, hệ thống yêu cầu kiểm tra thủ công (manual_review).")
    else:
        reasons.append("Xác thực Edu-KYC không hợp lệ (+0 điểm).")

    if onchain.sybil_risk_flag:
        reasons.append("CẢNH BÁO SYBIL: Phát hiện hành vi spam giao dịch bất thường trong thời gian ngắn.")
    else:
        reasons.append(f"Kiểm tra chống Sybil an toàn (+{breakdown.anti_sybil_score}/100 điểm) và dòng tiền đạt {breakdown.cashflow_score}/100 điểm.")

    reasons.append(f"Kết luận thẩm định: {decision} ({total_score}/1000 điểm). Quyết định cuối cùng thuộc về người dùng/Admin (HITL).")
    return reasons

def generate_vietnamese_reasons(
    onchain: OnChainMetrics,
    kyc: EduKYCResult,
    breakdown: ComponentBreakdown,
    total_score: int,
    decision: str
) -> List[str]:
    provider = os.getenv("LLM_PROVIDER", "mock").lower().strip()
    api_key = os.getenv("GOOGLE_API_KEY", "")

    if provider == "mock" or not api_key or "PASTE" in api_key:
        return _template_fallback_reasons(onchain, kyc, breakdown, total_score, decision)

    prompt = (
        "Bạn là Chuyên gia Thẩm định Tín dụng cho nền tảng 'Hụi Thông Minh On-Chain' trên Avalanche.\n"
        "Viết 4-5 gạch đầu dòng bằng tiếng Việt giải thích rõ ràng lý do đạt điểm số này.\n"
        "Quy tắc: Không bịa số, nếu thiếu dữ liệu ghi rõ manual_review, nhắc nhở quyền quyết định thuộc về con người (HITL).\n\n"
        f"- Tổng điểm: {total_score}/1000 | Quyết định: {decision}\n"
        f"- Chi tiết 5 thành phần: {breakdown.model_dump_json()}\n"
        f"- Hồ sơ On-chain: {onchain.model_dump_json()}\n"
        f"- Hồ sơ Edu-KYC: {kyc.model_dump_json()}"
    )

    try:
        if provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key, http_options={"timeout": 8000})
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMExplanation,
                    temperature=0.1
                )
            )
            parsed = json.loads(resp.text)
            return parsed.get("reasons", _template_fallback_reasons(onchain, kyc, breakdown, total_score, decision))
    except Exception:
        return _template_fallback_reasons(onchain, kyc, breakdown, total_score, decision)

    return _template_fallback_reasons(onchain, kyc, breakdown, total_score, decision)
