from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from agno.agent import Agent
from agno.models.google import Gemini
from guardrails import (
    ContentGuardrail,
    FinancialGuardrail,
    ReplyGuardrail,
    RoleGuardrail,
)
from models.schemas import (
    ActionRecommendation,
    AdminRole,
    CustomerMessage,
    CustomerReplyDraft,
    GuardrailIssue,
    GuardrailResult,
    ProductDescription,
    ProductInfo,
    ProductRecommendations,
)
from tools import CustomerMessageTool, ProductCatalogTool

DEFAULT_ACTIONS = [
    "update stock",
    "reply to customer",
    "improve product content",
    "review pricing",
    "follow up with supplier",
]


@dataclass
class AdminSession:
    user_id: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    def get_context(self) -> str:
        lines = [
            f"{item['role']}: {item['content']}"
            for item in self.conversation_history[-10:]
        ]
        return "\n".join(lines)


class AdminAssistantAgent:
    def __init__(
        self,
        product_tool: ProductCatalogTool,
        customer_tool: CustomerMessageTool,
        session: AdminSession,
        model: str = "gemini-2.5-flash",
        role: AdminRole = AdminRole.manager,
    ):
        self.product_tool = product_tool
        self.customer_tool = customer_tool
        self.session = session
        self.model_id = model
        self.role = role
        self.api_key = os.environ.get("AGENT_API_KEY")
        self.mock_mode = self.api_key is None

        self.financial_guard = FinancialGuardrail()
        self.content_guard = ContentGuardrail()
        self.reply_guard = ReplyGuardrail()
        self.role_guard = RoleGuardrail()

    def _create_agent(self, name: str, instructions: str, output_schema: type) -> Agent:
        return Agent(
            name=name,
            model=Gemini(id=self.model_id, api_key=self.api_key),
            instructions=instructions,
            output_schema=output_schema,
        )

    @staticmethod
    def _parse_content(response, schema):
        """Parse agent response content which may be a string or Pydantic model."""
        try:
            content = response.content
            if isinstance(content, str):
                return schema.model_validate_json(content)
            if hasattr(content, "model_dump"):
                return schema.model_validate(content.model_dump())
            return schema.model_validate(content)
        except Exception as e:
            # Return mock/default response on API failure
            raise ValueError(f"Failed to parse response: {e}. API may be unavailable.")

    def _extract_field(self, prompt: str, prefix: str) -> str:
        for line in prompt.split("\n"):
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return ""

    def _extract_features(self, prompt: str) -> list[str]:
        features = []
        capturing = False
        for line in prompt.split("\n"):
            stripped = line.strip()
            if stripped.startswith("Features:"):
                capturing = True
                continue
            if capturing and stripped.startswith("- "):
                features.append(stripped[2:])
            elif capturing and not stripped.startswith("-"):
                break
        return features

    def _get_product_from_prompt(self, prompt: str) -> ProductInfo:
        name = self._extract_field(prompt, "Product: ")
        for p in self.product_tool.products.values():
            if p.name == name:
                return p
        return next(iter(self.product_tool.products.values()))

    def _mock_description(self, prompt: str) -> ProductDescription:
        product = self._get_product_from_prompt(prompt)
        features = self._extract_features(prompt)
        return ProductDescription(
            headline=product.name,
            body=f"A versatile {product.category.lower()} product featuring {', '.join(features[:2] or product.features[:2])}.",
            benefits=features or product.features,
        )

    def _mock_recommendations(self, prompt: str) -> ProductRecommendations:
        product = self._get_product_from_prompt(prompt)
        return ProductRecommendations(
            related_products=self.product_tool.find_related_products(product),
            upsell_products=self.product_tool.suggest_upsell_products(product),
        )

    def _mock_reply(self) -> CustomerReplyDraft:
        return CustomerReplyDraft(
            reply="Thanks for reaching out! We're looking into your request and will get back to you shortly with an update.",
            recommended_tone="helpful and reassuring",
        )

    def _mock_action(self) -> ActionRecommendation:
        return ActionRecommendation(
            action="reply to customer",
            reason="The customer message requires a timely response before any inventory or pricing changes.",
        )

    def generate_product_description(
        self, product_payload: dict
    ) -> tuple[ProductDescription, GuardrailResult]:
        product_info = ProductInfo.model_validate(product_payload)
        self.session.add_message("user", f"Describe product {product_info.name}")

        prompt = (
            "Create a short product description with a headline, body, and list of benefits. "
            "Use the product name, category, price, and features. "
            "Keep the tone friendly and business-ready.\n\n"
            f"{self.product_tool.format_product_summary(product_info)}"
        )

        try:
            if self.mock_mode:
                description = self._mock_description(prompt)
            else:
                agent = self._create_agent(
                    name="Product Description Agent",
                    instructions=(
                        "You generate concise, compelling product descriptions. "
                        "Return a headline, body text, and a list of 3-5 key benefits. "
                        "Do NOT mention specific prices, make comparative claims, or use prohibited advertising language."
                    ),
                    output_schema=ProductDescription,
                )
                response = agent.run(prompt)
                description = self._parse_content(response, ProductDescription)
        except Exception:
            # Fallback to mock on API failure
            description = self._mock_description(prompt)

        guardrail_result = self.content_guard.check_description(
            description, product_info
        )
        self.session.add_message("assistant", description.model_dump_json())
        return description, guardrail_result

    def suggest_product_recommendations(
        self,
        product_payload: dict,
        customer_message: str | None = None,
    ) -> tuple[ProductRecommendations, GuardrailResult]:
        product_info = ProductInfo.model_validate(product_payload)
        self.session.add_message("user", "Suggest related and upsell products")

        prompt = (
            "You are an admin assistant. Using the product metadata below, "
            "suggest related products and upsell products. "
            "If the customer message signals an upgrade opportunity, prioritize a higher-tier recommendation.\n\n"
            f"{self.product_tool.format_product_summary(product_info)}\n\n"
            f"Customer message: {customer_message or 'N/A'}"
        )

        try:
            if self.mock_mode:
                recommendations = self._mock_recommendations(prompt)
            else:
                agent = self._create_agent(
                    name="Product Recommendations Agent",
                    instructions=(
                        "You suggest related and upsell products based on the current product. "
                        "Return lists of related_products and upsell_products by name. "
                        "Only suggest products that actually exist."
                    ),
                    output_schema=ProductRecommendations,
                )
                response = agent.run(prompt)
                recommendations = self._parse_content(response, ProductRecommendations)
        except Exception:
            # Fallback to mock on API failure
            recommendations = self._mock_recommendations(prompt)

        guardrail_result = self.content_guard.check_recommendations(
            recommendations, self.product_tool.products
        )
        self.session.add_message("assistant", recommendations.model_dump_json())
        return recommendations, guardrail_result

    def draft_customer_reply(
        self,
        customer_payload: dict,
        product_payload: dict | None = None,
    ) -> tuple[CustomerReplyDraft, GuardrailResult]:
        customer_message = CustomerMessage.model_validate(customer_payload)
        self.session.add_message(
            "user", f"Draft reply to customer: {customer_message.content}"
        )

        product_summary = (
            ""
            if product_payload is None
            else self.product_tool.format_product_summary(
                ProductInfo.model_validate(product_payload)
            )
        )
        prompt = (
            "Write a customer-facing reply with a reply message and recommended_tone. "
            "Be polite, concise, and accurate. Include the customer's issue and next step. "
            "Do NOT promise refunds, credits, or specific financial commitments. "
            "Do NOT share internal processes or supplier information.\n\n"
            f"Customer message: {customer_message.content}\n\n"
            f"Product context: {product_summary}"
        )

        try:
            if self.mock_mode:
                reply = self._mock_reply()
            else:
                agent = self._create_agent(
                    name="Customer Reply Agent",
                    instructions=(
                        "You draft professional customer support replies. "
                        "Return the reply text and the recommended tone for the response. "
                        "Never promise refunds, credits, or financial commitments. "
                        "Never mention internal processes, supplier names, or cost information."
                    ),
                    output_schema=CustomerReplyDraft,
                )
                response = agent.run(prompt)
                reply = self._parse_content(response, CustomerReplyDraft)
        except Exception:
            # Fallback to mock on API failure
            reply = self._mock_reply()

        reply_guard_result = self.reply_guard.check(reply.reply)
        financial_guard_result = self.financial_guard.check_reply(reply.reply)
        all_issues = reply_guard_result.issues + financial_guard_result.issues
        combined = GuardrailResult(passed=len(all_issues) == 0, issues=all_issues)

        self.session.add_message("assistant", reply.model_dump_json())
        return reply, combined

    def recommend_next_action(
        self,
        product_payload: dict,
        customer_payload: dict | None = None,
    ) -> tuple[ActionRecommendation, GuardrailResult]:
        product_info = ProductInfo.model_validate(product_payload)
        if customer_payload is not None:
            CustomerMessage.model_validate(customer_payload)
        self.session.add_message("user", "Recommend next admin action")

        prompt = (
            "Return the recommended next admin action and reason. "
            f"Choose one of: {', '.join(DEFAULT_ACTIONS)}.\n\n"
            f"Product info: {product_payload}\n"
            f"Customer message: {customer_payload or 'N/A'}"
        )

        try:
            if self.mock_mode:
                action = self._mock_action()
            else:
                agent = self._create_agent(
                    name="Next Action Agent",
                    instructions=(
                        "You recommend the next admin action based on product and customer context. "
                        f"Choose one of: {', '.join(DEFAULT_ACTIONS)}. "
                        "Return the action and a brief reason."
                    ),
                    output_schema=ActionRecommendation,
                )
                response = agent.run(prompt)
                action = self._parse_content(response, ActionRecommendation)
        except Exception:
            # Fallback to mock on API failure
            action = self._mock_action()

        all_issues = []
        role_result = self.role_guard.check_action(action, self.role)
        financial_result = self.financial_guard.check_action(
            action, product_info, self.role
        )
        all_issues.extend(role_result.issues)
        all_issues.extend(financial_result.issues)

        requires_approval = action.action in {
            "review pricing",
            "follow up with supplier",
        }
        if requires_approval and self.role != AdminRole.manager:
            all_issues.append(
                GuardrailIssue(
                    rule="approval_required",
                    message=f"'{action.action}' requires manager approval.",
                    severity="warning",
                    layer="role",
                )
            )
        action.requires_approval = requires_approval and self.role != AdminRole.manager

        combined = GuardrailResult(
            passed=len([i for i in all_issues if i.severity == "blocked"]) == 0,
            issues=all_issues,
        )
        self.session.add_message("assistant", action.model_dump_json())
        return action, combined
