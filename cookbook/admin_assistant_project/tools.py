from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from models.schemas import CustomerMessage, ProductInfo


@dataclass
class ProductCatalogTool:
    products: dict[str, ProductInfo]

    def get_product(self, product_id: str) -> Optional[ProductInfo]:
        return self.products.get(product_id)

    def find_related_products(
        self, base_product: ProductInfo, limit: int = 3
    ) -> List[str]:
        related = [
            p.name
            for p in self.products.values()
            if p.category == base_product.category and p.id != base_product.id
        ]
        return related[:limit] if related else ["No related products available"]

    def suggest_upsell_products(
        self, base_product: ProductInfo, limit: int = 2
    ) -> List[str]:
        upsells = [
            p.name
            for p in self.products.values()
            if p.price > base_product.price and p.id != base_product.id
        ]
        return upsells[:limit] if upsells else ["No higher-tier products available"]

    def format_product_summary(self, product: ProductInfo) -> str:
        return (
            f"Product: {product.name}\n"
            f"Category: {product.category}\n"
            f"Price: ${product.price:.2f}\n"
            f"Features:\n" + "\n".join(f"- {feature}" for feature in product.features)
        )


@dataclass
class CustomerMessageTool:
    def normalize_message(self, raw_text: str) -> CustomerMessage:
        content = raw_text.strip()
        order_reference = None
        for token in ["order #", "order number", "order ref", "ref"]:
            if token in content.lower():
                order_reference = content
                break
        return CustomerMessage(
            sender_name=None, content=content, order_reference=order_reference
        )

    def summarize_issue(self, message: CustomerMessage) -> str:
        return (
            message.content
            if len(message.content) < 280
            else message.content[:277] + "..."
        )
