from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

from agent import AdminAssistantAgent
from models.schemas import (
    ActionRecommendation,
    AdminRole,
    GuardrailResult,
    MorningBriefing,
    ProductDescription,
    ProductInfo,
)
from tools import CustomerMessageTool, ProductCatalogTool


@dataclass
class WorkflowStep:
    name: str
    status: str  # "pending", "running", "done", "blocked"


class MorningBriefingWorkflow:
    """Orchestrates multiple agents to produce a daily admin briefing."""

    def __init__(self, agent: AdminAssistantAgent, product_tool: ProductCatalogTool):
        self.agent = agent
        self.product_tool = product_tool

    def run(self, product_id: str, customer_messages: list[str]) -> dict:
        product = self.product_tool.get_product(product_id)
        if product is None:
            raise ValueError(f"Product id '{product_id}' not found")

        steps: list[dict] = []

        # Step 1 (parallel): Generate description + summarize customer messages
        with ThreadPoolExecutor(max_workers=2) as executor:
            description_future = executor.submit(
                self.agent.generate_product_description, product.model_dump()
            )
            replies_future = executor.submit(
                self._summarize_customer_messages, customer_messages
            )

            description, desc_guardrails = description_future.result()
            customer_alerts = replies_future.result()

        steps.append(
            {
                "name": "Generate product description",
                "data": description.model_dump(),
                "guardrails": desc_guardrails.model_dump(),
            }
        )

        # Step 2: Recommend next action
        action, action_guardrails = self.agent.recommend_next_action(
            product_payload=product.model_dump(),
            customer_payload={
                "sender_name": None,
                "content": customer_messages[0] if customer_messages else "",
                "order_reference": None,
            },
        )
        steps.append(
            {
                "name": "Recommend next action",
                "data": action.model_dump(),
                "guardrails": action_guardrails.model_dump(),
            }
        )

        # Step 3: Suggest upsell products
        upsell, upsell_guardrails = self.agent.suggest_product_recommendations(
            product_payload=product.model_dump(),
            customer_message=customer_messages[0] if customer_messages else None,
        )
        steps.append(
            {
                "name": "Suggest upsell products",
                "data": upsell.model_dump(),
                "guardrails": upsell_guardrails.model_dump(),
            }
        )

        summary_text = (
            f"Related products: {', '.join(upsell.related_products)}. "
            f"Upsell: {', '.join(upsell.upsell_products)}."
        )

        briefing = MorningBriefing(
            product_description=description,
            upsell_summary=summary_text,
            customer_alerts=customer_alerts,
            admin_actions=[action],
        )

        return {
            "workflow": "morning_briefing",
            "briefing": briefing.model_dump(),
            "steps": steps,
        }

    def _summarize_customer_messages(self, customer_messages: list[str]) -> str:
        if not customer_messages:
            return "No new customer conversations requiring attention."
        summaries: list[str] = []
        for message in customer_messages:
            normalized = CustomerMessageTool().normalize_message(message)
            summaries.append(f"- {normalized.content}")
        return "\n".join(summaries)


class CustomerSupportWorkflow:
    """Handles a customer message end-to-end: draft reply → recommend action → check guardrails."""

    def __init__(self, agent: AdminAssistantAgent, product_tool: ProductCatalogTool):
        self.agent = agent
        self.product_tool = product_tool

    def run(self, product_id: str, customer_message: str) -> dict:
        product = self.product_tool.get_product(product_id)
        if product is None:
            raise ValueError(f"Product id '{product_id}' not found")

        steps: list[dict] = []

        # Step 1: Draft reply to customer
        reply, reply_guardrails = self.agent.draft_customer_reply(
            customer_payload={
                "sender_name": None,
                "content": customer_message,
                "order_reference": None,
            },
            product_payload=product.model_dump(),
        )
        steps.append(
            {
                "name": "Draft reply to customer",
                "data": reply.model_dump(),
                "guardrails": reply_guardrails.model_dump(),
            }
        )

        # Step 2: Recommend next action
        action, action_guardrails = self.agent.recommend_next_action(
            product_payload=product.model_dump(),
            customer_payload={
                "sender_name": None,
                "content": customer_message,
                "order_reference": None,
            },
        )
        steps.append(
            {
                "name": "Recommend next action",
                "data": action.model_dump(),
                "guardrails": action_guardrails.model_dump(),
            }
        )

        all_blocked = any(
            any(i["severity"] == "blocked" for i in step["guardrails"]["issues"])
            for step in steps
        )

        return {
            "workflow": "customer_support",
            "status": "blocked" if all_blocked else "completed",
            "reply": reply.model_dump(),
            "action": action.model_dump(),
            "steps": steps,
        }


class ProductLaunchWorkflow:
    """Generates all content for a product launch: description → recommendations → verify guardrails."""

    def __init__(self, agent: AdminAssistantAgent, product_tool: ProductCatalogTool):
        self.agent = agent
        self.product_tool = product_tool

    def run(self, product_id: str) -> dict:
        product = self.product_tool.get_product(product_id)
        if product is None:
            raise ValueError(f"Product id '{product_id}' not found")

        steps: list[dict] = []

        # Step 1: Generate product description
        description, desc_guardrails = self.agent.generate_product_description(
            product.model_dump()
        )
        steps.append(
            {
                "name": "Generate product description",
                "data": description.model_dump(),
                "guardrails": desc_guardrails.model_dump(),
            }
        )

        # Step 2: Suggest related & upsell products
        recommendations, rec_guardrails = self.agent.suggest_product_recommendations(
            product_payload=product.model_dump(),
        )
        steps.append(
            {
                "name": "Suggest related & upsell products",
                "data": recommendations.model_dump(),
                "guardrails": rec_guardrails.model_dump(),
            }
        )

        all_blocked = any(
            any(i["severity"] == "blocked" for i in step["guardrails"]["issues"])
            for step in steps
        )

        return {
            "workflow": "product_launch",
            "status": "ready_to_publish" if not all_blocked else "blocked",
            "description": description.model_dump(),
            "recommendations": recommendations.model_dump(),
            "steps": steps,
        }


class PricingUpdateWorkflow:
    """Simulates a junior admin attempting to update product pricing — blocked by role guardrails."""

    def __init__(self, agent: AdminAssistantAgent, product_tool: ProductCatalogTool):
        self.agent = agent
        self.product_tool = product_tool

    def run(self, product_id: str) -> dict:
        from models.schemas import GuardrailIssue

        product = self.product_tool.get_product(product_id)
        if product is None:
            raise ValueError(f"Product id '{product_id}' not found")

        steps: list[dict] = []

        # Step 1: Generate product description (allowed for all roles)
        description, desc_guardrails = self.agent.generate_product_description(
            product.model_dump()
        )
        steps.append(
            {
                "name": "Generate product description",
                "data": description.model_dump(),
                "guardrails": desc_guardrails.model_dump(),
            }
        )

        # Step 2: Recommend next action (junior may suggest "review pricing")
        action, action_guardrails = self.agent.recommend_next_action(
            product_payload=product.model_dump(),
            customer_payload={
                "sender_name": None,
                "content": "The competitor lowered their price. We need to review our pricing immediately.",
                "order_reference": None,
            },
        )
        steps.append(
            {
                "name": "Recommend next action",
                "data": action.model_dump(),
                "guardrails": action_guardrails.model_dump(),
            }
        )

        # Step 3: Force a "review pricing" action attempt to show it's blocked for junior
        from guardrails import FinancialGuardrail, RoleGuardrail

        forced_action = ActionRecommendation(
            action="review pricing",
            reason="Attempting to update pricing as a junior admin",
            requires_approval=True,
        )
        role_issues = (
            RoleGuardrail().check_action(forced_action, AdminRole.junior).issues
        )
        financial_issues = (
            FinancialGuardrail()
            .check_action(forced_action, product, AdminRole.junior)
            .issues
        )
        pricing_issues = list(role_issues) + list(financial_issues)
        pricing_issues.append(
            GuardrailIssue(
                rule="approval_required",
                message="'review pricing' requires manager approval.",
                severity="warning",
                layer="role",
            )
        )
        pricing_guardrails = GuardrailResult(
            passed=len([i for i in pricing_issues if i.severity == "blocked"]) == 0,
            issues=pricing_issues,
        )
        steps.append(
            {
                "name": "Attempt pricing update (junior role)",
                "data": forced_action.model_dump(),
                "guardrails": pricing_guardrails.model_dump(),
            }
        )

        all_blocked = any(
            any(i["severity"] == "blocked" for i in step["guardrails"]["issues"])
            for step in steps
        )

        return {
            "workflow": "pricing_update_blocked",
            "status": "blocked" if all_blocked else "completed",
            "description": description.model_dump(),
            "action": action.model_dump(),
            "forced_action": forced_action.model_dump(),
            "steps": steps,
        }
