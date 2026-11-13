from __future__ import annotations

from agent import AdminAssistantAgent, AdminSession
from models.schemas import ProductInfo
from rich import print
from rich.panel import Panel
from tools import CustomerMessageTool, ProductCatalogTool
from workflow import MorningBriefingWorkflow


def build_catalog() -> ProductCatalogTool:
    products = {
        "monitor-15": ProductInfo(
            id="monitor-15",
            name='BrightChoice 15.6" Portable Monitor',
            category="Office Technology",
            price=169.00,
            features=[
                "USB-C plug-and-play",
                "Full HD 1080p resolution",
                "Lightweight travel design",
            ],
        ),
        "docking-elite": ProductInfo(
            id="docking-elite",
            name="Docking Station Elite",
            category="Office Technology",
            price=249.00,
            features=[
                "Dual 4K HDMI",
                "Six USB ports",
                "Fast charging for laptops and phones",
            ],
        ),
        "ergomouse-pro": ProductInfo(
            id="ergomouse-pro",
            name="ErgoMouse Pro",
            category="Workspace Essentials",
            price=59.00,
            features=[
                "Ergonomic vertical shape",
                "Quiet click switches",
                "Adjustable DPI for precision work",
            ],
        ),
    }
    return ProductCatalogTool(products=products)


def main() -> None:
    catalog = build_catalog()
    customer_tool = CustomerMessageTool()
    session = AdminSession(user_id="admin@example.com")
    assistant = AdminAssistantAgent(
        product_tool=catalog,
        customer_tool=customer_tool,
        session=session,
        model="gemini-2.5-flash",
    )

    primary_product = catalog.get_product("monitor-15")
    sample_message = (
        "Hello, I ordered a portable monitor but the shipment date changed. "
        "Can you tell me if I need to update stock or refund the customer?"
    )

    print(Panel("[bold yellow]Admin Assistant Prototype[/bold yellow]", expand=False))

    description, _ = assistant.generate_product_description(
        primary_product.model_dump()
    )
    print(
        Panel(
            f"[bold]Product Description[/bold]\n{description.headline}\n\n{description.body}\n\nBenefits:\n- "
            + "\n- ".join(description.benefits),
            title="1. Product Description",
        )
    )

    recommendations, _ = assistant.suggest_product_recommendations(
        primary_product.model_dump(),
        customer_message=sample_message,
    )
    print(
        Panel(
            f"Related: {', '.join(recommendations.related_products)}\n"
            f"Upsell: {', '.join(recommendations.upsell_products)}",
            title="2. Product Recommendations",
        )
    )

    reply, _ = assistant.draft_customer_reply(
        {"sender_name": "Customer", "content": sample_message, "order_reference": None},
        primary_product.model_dump(),
    )
    print(
        Panel(
            f"Tone: {reply.recommended_tone}\n\n{reply.reply}",
            title="3. Draft Customer Reply",
        )
    )

    action, _ = assistant.recommend_next_action(
        primary_product.model_dump(),
        {"sender_name": "Customer", "content": sample_message, "order_reference": None},
    )
    print(
        Panel(
            f"Action: {action.action}\nReason: {action.reason}",
            title="4. Next Action Recommendation",
        )
    )

    workflow = MorningBriefingWorkflow(assistant, catalog)
    result = workflow.run(
        product_id="monitor-15",
        customer_messages=[sample_message],
    )
    briefing = result["briefing"]
    desc = briefing["product_description"]
    actions = briefing["admin_actions"]

    print(
        Panel(
            f"{desc['headline']}\n\n{desc['body']}\n\n"
            f"Upsell summary: {briefing['upsell_summary']}\n\n"
            f"Customer alerts:\n{briefing['customer_alerts']}\n\n"
            f"Admin actions:\n- {actions[0]['action']}: {actions[0]['reason']}",
            title="5. Morning Briefing",
        )
    )


if __name__ == "__main__":
    main()
