# schemas.py - Task 2: Pydantic schemas for strict JSON validation
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

class EduKYCResult(BaseModel): # Represents the result of an educational KYC verification process
    status: Literal["verified", "unverified", "manual_review"] = Field(description="KYC verification status")
    is_valid: bool = Field(description="Whether the student ID is valid")

    # Credibility score based on the quality of the OCR and other factors, ranging from 0 to 1
    # >= 0.96 : the student ID image ís very clear and the OCR result is highly reliable
    # 0.35 <= confidence < 0.96 : the student ID image is moderately clear and the OCR result is reasonably reliable
    # < 0.35 : the student ID image is blurry or unclear, and the OCR result is not reliable, requiring manual review
    confidence: float = Field(ge=0.0, le=1.0, description="OCR confidence score between 0 and 1") 

    institution: Optional[str] = Field(default=None, description="University name, e.g., HUST")

class OnChainMetrics(BaseModel):
    wallet_address: str

    # Total number of transactions associated with the wallet, must be non-negative
    tx_count: int = Field(ge=0)

    # Total number of unique smart contracts the wallet has interacted with, 
    wallet_age_days: float = Field(ge=0.0)

    # Total AVAX balance in the wallet, must be non-negative
    balance_avax: float = Field(ge=0.0)

    # Total number of unique counterparties the wallet has interacted with, must be non-negative
    unique_counterparties: int = Field(ge=0)

    # success rate of transactions, ranging from 0 to 1
    success_rate: float = Field(ge=0.0, le=1.0)

    # flag indicating whether suspicious burst activity (potential sybil behavior) has been detected, defualting to False
    sybil_risk_flag: bool = Field(default=False, description="True if suspicious burst activity detected")

    # ok, insufficient_data : no transactions before metrics failed, and the data is not available
    data_status: Literal["ok", "insufficient_data", "api_error"] = Field(default="ok")

    # api_error : indicates that the API call to fetch on-chain
class ComponentBreakdown(BaseModel):
    # Each component score is a float between 0 and its respective maximum, representing the contribution to the total credit score
    onchain_score: float = Field(ge=0, le=300, description="Max 300 pts (30%)")
    hui_behavior_score: float = Field(ge=0, le=300, description="Max 300 pts (30%)")
    edu_kyc_score: float = Field(ge=0, le=200, description="Max 200 pts (20%)")
    anti_sybil_score: float = Field(ge=0, le=100, description="Max 100 pts (10%)")
    cashflow_score: float = Field(ge=0, le=100, description="Max 100 pts (10%)")

class LLMExplanation(BaseModel): # LLM-generated explanation of the credit score, including reasons and a recommendation note

    reasons: List[str] = Field(description="List of Vietnamese reasons explaining the credit score")
    recommendation_note: str = Field(description="Short Vietnamese advisory note for the user")

class CreditScoreResult(BaseModel):
    wallet_address: str
    total_score: int = Field(ge=0, le=1000, description="Final deterministic score from 0 to 1000")
    rank: Literal["Diamond", "Gold", "Silver", "Bronze", "Unranked"]
    decision: Literal["PASS", "FAIL", "MANUAL_REVIEW"]
    breakdown: ComponentBreakdown
    reasons: List[str]

    # KPI < 30s : The total execution time of the credit scoring process in milliseconds, must be non-negative
    execution_time_ms: float

class MatchmakerProfile(BaseModel):
    wallet_address: str
    total_score: int

    # rank : Diamond, Gold, Silver, Bronze, Unranked
    rank: str
    assigned_pool: Literal["Saving Pool", "Bidding Pool", "Manual Review"]

    # group id for example : BIDDING_GROUP_DIAMOND, SAVING_POOL_GOLD
    group_id: Optional[str] = None
    routing_reason: str

class MatchmakerGroupResult(BaseModel):
    # list include wallet_1, wallet_2, wallet_3, wallet_4, wallet_5, et cetera 
    saving_pool_wallets: List[MatchmakerProfile]
    bidding_groups: Dict[str, List[MatchmakerProfile]]
    summary_note: str

class YieldPoolItem(BaseModel):

    # pool_id : unique identifier for the pool on DefiLlama (eg., "aave-v3-usdc") used for exact tracking or depp-linking
    pool_id: str

    # project : The name of the DeFi protocol hosting the pool (e.g., "aave-v3", "benqi-lending", "benqi-staked-avax").
    project: str

    # symbol :  The ticker symbol of the deposited asset (eg., "USDC", "USDT", "DAI", "AVAX", "WETH").
    symbol: str

    # tvl_usd : The total value locked in the pool, denominated in USD, must be non-negative
    tvl_usd: float

    # apy : The annual percentage yield offered by the pool, expressed as a decimal (e.g., 0.05 for 5%), must be non-negative
    apy: float

class YieldAdvisorResult(BaseModel):
    chain: str = "Avalanche"
    # top_3_pools : A list of the top 3 recommended yield pools for the user, sorted by APY in descending order
    top_3_pools: List[YieldPoolItem]
    # A boolean flag permanently set to True (Human-in-the-Loop). 
    # This enforces a strict security guardrail: the AI Agent is strictly read-only/advisory and can never autonomously sign transactions or move user funds.
    hitl_required: bool = True
    # action_button_lable : The UI button text rendered on Streamlit so the user or pool administrator can manually trigger wallet signing if they choose to deposit.
    action_button_label: str = "Xác nhận gửi tiền (Người dùng/Admin tự ký giao dịch)"

    # The UI button text rendered on Streamlit so the user or pool administrator can manually trigger wallet signing if they choose to deposit.
    disclaimer: str
