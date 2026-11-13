from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, constr

# --- Guardrail Schemas ---


class GuardrailIssue(BaseModel):
    rule: str
    message: str
    severity: Literal["blocked", "warning", "info"]
    layer: str


class GuardrailResult(BaseModel):
    passed: bool
    issues: List[GuardrailIssue] = Field(default_factory=list)


class AdminRole(str, Enum):
    junior = "junior"
    senior = "senior"
    manager = "manager"


# --- Product Schemas ---


class ProductInfo(BaseModel):
    id: str = Field(..., description="Unique product SKU or identifier")
    name: constr(min_length=3)
    category: constr(min_length=3)
    features: List[str] = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    tone: Optional[str] = Field(default="friendly and professional")


class ProductDescription(BaseModel):
    headline: str
    body: str
    benefits: List[str]


class ProductRecommendations(BaseModel):
    related_products: List[str]
    upsell_products: List[str]


class CustomerReplyDraft(BaseModel):
    reply: str
    recommended_tone: str


class ActionRecommendation(BaseModel):
    action: str
    reason: str
    requires_approval: bool = False


class AdminAssistantResponse(BaseModel):
    description: ProductDescription
    recommendations: ProductRecommendations
    reply_draft: CustomerReplyDraft
    next_action: ActionRecommendation


class CustomerMessage(BaseModel):
    sender_name: Optional[str]
    content: str
    order_reference: Optional[str]


class MorningBriefing(BaseModel):
    product_description: ProductDescription
    upsell_summary: str
    customer_alerts: str
    admin_actions: List[ActionRecommendation]


# --- Guardrail Response Wrappers ---


class GuardrailResponse(BaseModel):
    data: dict
    guardrails: GuardrailResult


def validate_schema(data: dict, schema: type[BaseModel]) -> BaseModel:
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc
