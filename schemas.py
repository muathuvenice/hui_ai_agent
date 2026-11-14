# schemas.py - Task 2: Pydantic schemas for strict JSON validation
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

class EduKYCResult(BaseModel):
    status: Literal["verified", "unverified", "manual_review"] = Field(description="KYC verification status")
    is_valid: bool = Field(description="Whether the student ID is valid")
    confidence: float = Field(ge=0.0, le=1.0, description="OCR confidence score between 0 and 1")
    institution: Optional[str] = Field(default=None, description="University name, e.g., HUST")

class OnChainMetrics(BaseModel):
    wallet_address: str
    tx_count: int = Field(ge=0)
    wallet_age_days: float = Field(ge=0.0)
    balance_avax: float = Field(ge=0.0)
    unique_counterparties: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    sybil_risk_flag: bool = Field(default=False, description="True if suspicious burst activity detected")
    data_status: Literal["ok", "insufficient_data", "api_error"] = Field(default="ok")

class ComponentBreakdown(BaseModel):
    onchain_score: float = Field(ge=0, le=300, description="Max 300 pts (30%)")
    hui_behavior_score: float = Field(ge=0, le=300, description="Max 300 pts (30%)")
    edu_kyc_score: float = Field(ge=0, le=200, description="Max 200 pts (20%)")
    anti_sybil_score: float = Field(ge=0, le=100, description="Max 100 pts (10%)")
    cashflow_score: float = Field(ge=0, le=100, description="Max 100 pts (10%)")

class LLMExplanation(BaseModel):
    reasons: List[str] = Field(description="List of Vietnamese reasons explaining the credit score")
    recommendation_note: str = Field(description="Short Vietnamese advisory note for the user")

class CreditScoreResult(BaseModel):
    wallet_address: str
    total_score: int = Field(ge=0, le=1000, description="Final deterministic score from 0 to 1000")
    rank: Literal["Diamond", "Gold", "Silver", "Bronze", "Unranked"]
    decision: Literal["PASS", "FAIL", "MANUAL_REVIEW"]
    breakdown: ComponentBreakdown
    reasons: List[str]
    execution_time_ms: float

class MatchmakerProfile(BaseModel):
    wallet_address: str
    total_score: int
    rank: str
    assigned_pool: Literal["Saving Pool", "Bidding Pool", "Manual Review"]
    group_id: Optional[str] = None
    routing_reason: str

class MatchmakerGroupResult(BaseModel):
    saving_pool_wallets: List[MatchmakerProfile]
    bidding_groups: Dict[str, List[MatchmakerProfile]]
    summary_note: str

class YieldPoolItem(BaseModel):
    pool_id: str
    project: str
    symbol: str
    tvl_usd: float
    apy: float

class YieldAdvisorResult(BaseModel):
    chain: str = "Avalanche"
    top_3_pools: List[YieldPoolItem]
    hitl_required: bool = True
    action_button_label: str = "Xác nhận gửi tiền (Người dùng/Admin tự ký giao dịch)"
    disclaimer: str
