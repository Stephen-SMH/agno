from __future__ import annotations

from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

from agent import AdminAssistantAgent, AdminSession
from guardrails import (
    ContentGuardrail,
    FinancialGuardrail,
    ReplyGuardrail,
    RoleGuardrail,
)
from main import build_catalog
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
from tools import CustomerMessageTool

app = FastAPI(title="Admin Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

catalog = build_catalog()
session = AdminSession(user_id="web-admin")


def get_assistant(role: AdminRole) -> AdminAssistantAgent:
    return AdminAssistantAgent(
        product_tool=catalog,
        customer_tool=CustomerMessageTool(),
        session=session,
        model="gemini-2.5-flash",
        role=role,
    )


class NextActionRequest(BaseModel):
    customer_message: str | None = None


class CustomerReplyRequest(BaseModel):
    content: str
    sender_name: str | None = None
    order_reference: str | None = None


class MorningBriefingRequest(BaseModel):
    product_id: str
    customer_messages: List[str] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products")
def list_products() -> List[ProductInfo]:
    return list(catalog.products.values())


@app.get("/products/{product_id}")
def get_product(product_id: str) -> ProductInfo:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/products/{product_id}/describe")
def describe_product(
    product_id: str, role: AdminRole = Query(AdminRole.manager)
) -> dict:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    assistant = get_assistant(role)
    description, guardrails = assistant.generate_product_description(
        product.model_dump()
    )
    return {
        "data": description.model_dump(),
        "guardrails": guardrails.model_dump(),
    }


@app.post("/products/{product_id}/recommendations")
def product_recommendations(
    product_id: str,
    request: NextActionRequest,
    role: AdminRole = Query(AdminRole.manager),
) -> dict:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    assistant = get_assistant(role)
    recommendations, guardrails = assistant.suggest_product_recommendations(
        product_payload=product.model_dump(),
        customer_message=request.customer_message,
    )
    return {
        "data": recommendations.model_dump(),
        "guardrails": guardrails.model_dump(),
    }


@app.post("/products/{product_id}/reply")
def draft_reply(
    product_id: str,
    request: CustomerReplyRequest,
    role: AdminRole = Query(AdminRole.manager),
) -> dict:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    assistant = get_assistant(role)
    reply, guardrails = assistant.draft_customer_reply(
        customer_payload=request.model_dump(),
        product_payload=product.model_dump(),
    )
    return {
        "data": reply.model_dump(),
        "guardrails": guardrails.model_dump(),
    }


class NextActionRequest(BaseModel):
    customer_message: str | None = None
    force_action: str | None = None


@app.post("/products/{product_id}/next-action")
def next_action(
    product_id: str,
    request: NextActionRequest,
    role: AdminRole = Query(AdminRole.manager),
) -> dict:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if request.force_action:
        action = ActionRecommendation(
            action=request.force_action,
            reason=f"Testing guardrail for action: {request.force_action}",
            requires_approval=request.force_action
            in {"review pricing", "follow up with supplier"}
            and role != AdminRole.manager,
        )
        all_issues = []
        all_issues.extend(RoleGuardrail().check_action(action, role).issues)
        all_issues.extend(
            FinancialGuardrail().check_action(action, product, role).issues
        )
        if (
            request.force_action in {"review pricing", "follow up with supplier"}
            and role != AdminRole.manager
        ):
            all_issues.append(
                GuardrailIssue(
                    rule="approval_required",
                    message=f"'{request.force_action}' requires manager approval.",
                    severity="warning",
                    layer="role",
                )
            )
        guardrails = GuardrailResult(
            passed=len([i for i in all_issues if i.severity == "blocked"]) == 0,
            issues=all_issues,
        )
        return {
            "data": action.model_dump(),
            "guardrails": guardrails.model_dump(),
        }

    assistant = get_assistant(role)
    action, guardrails = assistant.recommend_next_action(
        product_payload=product.model_dump(),
        customer_payload={
            "sender_name": None,
            "content": request.customer_message or "",
            "order_reference": None,
        },
    )
    return {
        "data": action.model_dump(),
        "guardrails": guardrails.model_dump(),
    }


@app.post("/briefing")
def morning_briefing(
    request: MorningBriefingRequest, role: AdminRole = Query(AdminRole.manager)
) -> dict:
    from workflow import MorningBriefingWorkflow

    assistant = get_assistant(role)
    workflow = MorningBriefingWorkflow(assistant, catalog)
    result = workflow.run(
        product_id=request.product_id,
        customer_messages=request.customer_messages,
    )
    return result.model_dump()


# --- Workflow Endpoints ---


class WorkflowRequest(BaseModel):
    product_id: str
    customer_message: str | None = None


@app.post("/api/workflows/morning-briefing")
def run_morning_briefing(
    request: WorkflowRequest, role: AdminRole = Query(AdminRole.manager)
) -> dict:
    from workflow import MorningBriefingWorkflow

    assistant = get_assistant(role)
    workflow = MorningBriefingWorkflow(assistant, catalog)
    return workflow.run(
        product_id=request.product_id,
        customer_messages=[request.customer_message]
        if request.customer_message
        else [],
    )


@app.post("/api/workflows/customer-support")
def run_customer_support(
    request: WorkflowRequest, role: AdminRole = Query(AdminRole.manager)
) -> dict:
    from workflow import CustomerSupportWorkflow

    if not request.customer_message:
        raise HTTPException(
            status_code=400, detail="customer_message is required for this workflow"
        )
    assistant = get_assistant(role)
    workflow = CustomerSupportWorkflow(assistant, catalog)
    return workflow.run(
        product_id=request.product_id,
        customer_message=request.customer_message,
    )


@app.post("/api/workflows/product-launch")
def run_product_launch(
    request: WorkflowRequest, role: AdminRole = Query(AdminRole.manager)
) -> dict:
    from workflow import ProductLaunchWorkflow

    assistant = get_assistant(role)
    workflow = ProductLaunchWorkflow(assistant, catalog)
    return workflow.run(product_id=request.product_id)


@app.post("/api/workflows/pricing-update-blocked")
def run_pricing_update_blocked(request: WorkflowRequest) -> dict:
    from workflow import PricingUpdateWorkflow

    assistant = get_assistant(AdminRole.junior)
    workflow = PricingUpdateWorkflow(assistant, catalog)
    return workflow.run(product_id=request.product_id)


# --- Guardrail Demo Endpoint ---

DEMO_SCENARIOS = {
    "prohibited_claim": {
        "label": "Prohibited advertising claim",
        "description": "Description contains 'FDA approved' and 'clinically proven'",
        "layer": "content",
        "run": lambda product, role: (
            ProductDescription(
                headline=f"{product.name} — FDA Approved and Clinically Proven",
                body=f"The {product.name} is the #1 best product in the world. FDA approved and clinically proven to boost productivity by 300%.",
                benefits=[
                    "FDA approved safety",
                    "Clinically proven results",
                    "#1 in the world",
                ],
            ),
            ContentGuardrail().check_description(
                ProductDescription(
                    headline=f"{product.name} — FDA Approved and Clinically Proven",
                    body=f"The {product.name} is the #1 best product in the world. FDA approved and clinically proven to boost productivity by 300%.",
                    benefits=[
                        "FDA approved safety",
                        "Clinically proven results",
                        "#1 in the world",
                    ],
                ),
                product,
            ),
        ),
    },
    "price_mismatch": {
        "label": "Wrong price in description",
        "description": f"Description mentions a different price than the actual product",
        "layer": "content",
        "run": lambda product, role: (
            ProductDescription(
                headline=f"{product.name} — Only $9.99!",
                body=f"Get the {product.name} for just $9.99. An unbeatable deal for a {product.category.lower()} essential.",
                benefits=["Great value at $9.99", "Affordable pricing"],
            ),
            ContentGuardrail().check_description(
                ProductDescription(
                    headline=f"{product.name} — Only $9.99!",
                    body=f"Get the {product.name} for just $9.99. An unbeatable deal for a {product.category.lower()} essential.",
                    benefits=["Great value at $9.99", "Affordable pricing"],
                ),
                product,
            ),
        ),
    },
    "fake_product": {
        "label": "Fake product in recommendations",
        "description": "AI recommends products that don't exist in the catalog",
        "layer": "content",
        "run": lambda product, role: (
            ProductRecommendations(
                related_products=["Fake Product XYZ", "Nonexistent Gadget 3000"],
                upsell_products=["Scam Premium Bundle"],
            ),
            ContentGuardrail().check_recommendations(
                ProductRecommendations(
                    related_products=["Fake Product XYZ", "Nonexistent Gadget 3000"],
                    upsell_products=["Scam Premium Bundle"],
                ),
                catalog.products,
            ),
        ),
    },
    "refund_promise": {
        "label": "Unauthorized refund promise",
        "description": "Reply promises a refund without authorization",
        "layer": "financial",
        "run": lambda product, role: (
            CustomerReplyDraft(
                reply=f"We will issue a full refund to your account immediately. I'll also send you a free upgrade and a discount code for your next purchase.",
                recommended_tone="accommodating",
            ),
            FinancialGuardrail().check_reply(
                f"We will issue a full refund to your account immediately. I'll also send you a free upgrade and a discount code for your next purchase."
            ),
        ),
    },
    "internal_leak": {
        "label": "Internal information leak",
        "description": "Reply exposes supplier details and profit margins",
        "layer": "reply",
        "run": lambda product, role: (
            CustomerReplyDraft(
                reply=f"Our supplier contract with ShenzhenTech allows us a 40% margin on this product. The wholesale cost is only $29 so the markup is quite high. Internal policy says we can offer replacements.",
                recommended_tone="transparent",
            ),
            ReplyGuardrail().check(
                f"Our supplier contract with ShenzhenTech allows us a 40% margin on this product. The wholesale cost is only $29 so the markup is quite high. Internal policy says we can offer replacements."
            ),
        ),
    },
    "legal_commitment": {
        "label": "Unauthorized legal commitment",
        "description": "Reply makes legal promises to the customer",
        "layer": "reply",
        "run": lambda product, role: (
            CustomerReplyDraft(
                reply="You are entitled to a full replacement. We guarantee this outcome and we are legally obligated to compensate you. If not, you can file a class action or lawsuit against us.",
                recommended_tone="accommodating",
            ),
            ReplyGuardrail().check(
                "You are entitled to a full replacement. We guarantee this outcome and we are legally obligated to compensate you. If not, you can file a class action or lawsuit against us."
            ),
        ),
    },
    "tone_violation": {
        "label": "Inappropriate tone",
        "description": "Reply is hostile and dismissive to the customer",
        "layer": "reply",
        "run": lambda product, role: (
            CustomerReplyDraft(
                reply="That's a stupid question. Figure it out yourself. Not my problem if you can't read the product manual, idiot.",
                recommended_tone="direct",
            ),
            ReplyGuardrail().check(
                "That's a stupid question. Figure it out yourself. Not my problem if you can't read the product manual, idiot."
            ),
        ),
    },
    "junior_pricing": {
        "label": "Junior tries to change pricing",
        "description": "Junior admin attempts to review pricing — only managers can",
        "layer": "role",
        "run": lambda product, role: (
            ActionRecommendation(
                action="review pricing",
                reason="Price seems too low",
                requires_approval=True,
            ),
            RoleGuardrail().check_action(
                ActionRecommendation(
                    action="review pricing", reason="Price seems too low"
                ),
                AdminRole.junior,
            ),
        ),
    },
    "junior_supplier": {
        "label": "Junior contacts supplier",
        "description": "Junior admin attempts to follow up with supplier — only managers can",
        "layer": "role",
        "run": lambda product, role: (
            ActionRecommendation(
                action="follow up with supplier",
                reason="Need to check stock",
                requires_approval=True,
            ),
            RoleGuardrail().check_action(
                ActionRecommendation(
                    action="follow up with supplier", reason="Need to check stock"
                ),
                AdminRole.junior,
            ),
        ),
    },
}


@app.get("/api/demo/scenarios")
def list_demo_scenarios() -> dict:
    return {
        "scenarios": [
            {
                "id": key,
                "label": s["label"],
                "description": s["description"],
                "layer": s["layer"],
            }
            for key, s in DEMO_SCENARIOS.items()
        ]
    }


@app.post("/api/demo/run/{scenario_id}")
def run_demo_scenario(scenario_id: str, product_id: str = Query("monitor-15")) -> dict:
    if scenario_id not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=404, detail=f"Scenario '{scenario_id}' not found"
        )

    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    scenario = DEMO_SCENARIOS[scenario_id]
    data, guardrails = scenario["run"](product, AdminRole.manager)

    return {
        "scenario": scenario_id,
        "label": scenario["label"],
        "data": data.model_dump() if hasattr(data, "model_dump") else data,
        "guardrails": guardrails.model_dump(),
    }
