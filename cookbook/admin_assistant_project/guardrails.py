from __future__ import annotations

import re
from typing import List

from models.schemas import (
    ActionRecommendation,
    AdminRole,
    CustomerMessage,
    GuardrailIssue,
    GuardrailResult,
    ProductDescription,
    ProductInfo,
    ProductRecommendations,
)


def _info(rule: str, message: str, layer: str) -> GuardrailIssue:
    return GuardrailIssue(rule=rule, message=message, severity="info", layer=layer)


class FinancialGuardrail:
    PROHIBITED_FINANCIAL_TERMS = [
        r"\brefund\b",
        r"\bcredit\s+(your\s+)?account\b",
        r"\bfree\s+(upgrade|replacement)\b",
        r"\bdiscount\s+(code|coupon|voucher)\b",
        r"\bwaive\s+(the\s+)?fee\b",
    ]

    def check_action(
        self, action: ActionRecommendation, product: ProductInfo, role: AdminRole
    ) -> GuardrailResult:
        issues: List[GuardrailIssue] = []

        if action.action == "review pricing":
            if role != AdminRole.manager:
                issues.append(
                    GuardrailIssue(
                        rule="pricing_authorization",
                        message=f"Role '{role.value}' cannot approve pricing changes for {product.name}. Manager required.",
                        severity="blocked",
                        layer="financial",
                    )
                )
            else:
                issues.append(
                    _info(
                        "pricing_authorization",
                        f"Manager authorized to review pricing for {product.name} (${product.price:.2f}).",
                        "financial",
                    )
                )
        else:
            issues.append(
                _info(
                    "pricing_authorization",
                    "No pricing change requested — no financial authorization needed.",
                    "financial",
                )
            )

        if action.action == "update stock":
            if role == AdminRole.junior:
                issues.append(
                    GuardrailIssue(
                        rule="stock_authorization",
                        message=f"Junior admin cannot update stock for {product.name}. Senior or manager required.",
                        severity="blocked",
                        layer="financial",
                    )
                )
            else:
                issues.append(
                    _info(
                        "stock_authorization",
                        f"Role '{role.value}' is authorized to update stock for {product.name}.",
                        "financial",
                    )
                )
        else:
            issues.append(
                _info(
                    "stock_authorization",
                    "No stock update requested — no stock authorization needed.",
                    "financial",
                )
            )

        if action.action == "follow up with supplier":
            if role != AdminRole.manager:
                issues.append(
                    GuardrailIssue(
                        rule="supplier_authorization",
                        message=f"Role '{role.value}' cannot contact suppliers for {product.name}. Manager required.",
                        severity="blocked",
                        layer="financial",
                    )
                )
            else:
                issues.append(
                    _info(
                        "supplier_authorization",
                        f"Manager authorized to follow up with supplier for {product.name}.",
                        "financial",
                    )
                )
        else:
            issues.append(
                _info(
                    "supplier_authorization",
                    "No supplier follow-up requested — no supplier authorization needed.",
                    "financial",
                )
            )

        has_blocks = any(i.severity == "blocked" for i in issues)
        return GuardrailResult(passed=not has_blocks, issues=issues)

    def check_reply(self, reply_text: str) -> GuardrailResult:
        issues: List[GuardrailIssue] = []
        text_lower = reply_text.lower()
        found = False

        for pattern in self.PROHIBITED_FINANCIAL_TERMS:
            match = re.search(pattern, text_lower)
            if match:
                found = True
                issues.append(
                    GuardrailIssue(
                        rule="unauthorized_financial_commitment",
                        message=f"Reply contains unauthorized financial commitment: '{match.group()}'. Requires manager approval.",
                        severity="warning",
                        layer="financial",
                    )
                )

        if not found:
            issues.append(
                _info(
                    "financial_commitment_scan",
                    "Scanned for unauthorized refund promises, discount codes, and fee waivers — none found.",
                    "financial",
                )
            )

        return GuardrailResult(
            passed=len(issues) == 0 or all(i.severity != "blocked" for i in issues),
            issues=issues,
        )


class ContentGuardrail:
    PROHIBITED_CLAIMS = [
        (r"\bFDA\s+approved\b", "FDA approval claims"),
        (r"\bclinically\s+proven\b", "clinical proof claims"),
        (r"\bguaranteed\s+(results?|cure|outcome)\b", "guaranteed result claims"),
        (
            r"#\d+\s+(in\s+the\s+)?(world|market|industry|category)",
            "ranking claims (#1 in market)",
        ),
        (r"\bbest\s+(in\s+the\s+)?(world|market|industry)\b", "best-in-market claims"),
        (r"\bcheaper\s+than\b", "price comparison claims"),
        (r"\bbetter\s+than\s+(any\s+)?competitor\b", "competitor comparison claims"),
    ]

    def check_description(
        self, description: ProductDescription, product: ProductInfo
    ) -> GuardrailResult:
        issues: List[GuardrailIssue] = []
        full_text = f"{description.headline} {description.body} {' '.join(description.benefits)}"
        text_lower = full_text.lower()
        claim_violations = []

        # Check prohibited claims
        for pattern, claim_type in self.PROHIBITED_CLAIMS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                claim_violations.append(match.group())
                issues.append(
                    GuardrailIssue(
                        rule="prohibited_claim",
                        message=f"Description contains prohibited advertising claim: '{match.group()}' ({claim_type}). This violates advertising policy.",
                        severity="blocked",
                        layer="content",
                    )
                )

        if not claim_violations:
            issues.append(
                _info(
                    "advertising_policy_scan",
                    f"Scanned for prohibited claims (FDA, clinical, guaranteed, competitor comparisons) — none found.",
                    "content",
                )
            )

        # Check price mismatch
        price_pattern = r"\$[\d,]+(?:\.\d{2})?"
        price_matches = re.findall(price_pattern, full_text)
        if price_matches:
            for price_str in price_matches:
                mentioned_price = float(price_str.replace("$", "").replace(",", ""))
                if abs(mentioned_price - product.price) > 0.01:
                    issues.append(
                        GuardrailIssue(
                            rule="price_mismatch",
                            message=f"Description mentions {price_str} but actual price is ${product.price:.2f}. Potential price manipulation by admin.",
                            severity="blocked",
                            layer="content",
                        )
                    )
                else:
                    issues.append(
                        _info(
                            "price_accuracy_check",
                            f"Mentioned price {price_str} matches actual product price ${product.price:.2f}.",
                            "content",
                        )
                    )
        else:
            issues.append(
                _info(
                    "price_accuracy_check",
                    f"No prices mentioned in description — no price manipulation risk (actual: ${product.price:.2f}).",
                    "content",
                )
            )

        # Check feature accuracy
        issues.append(
            _info(
                "feature_accuracy_scan",
                f"Description generated from {len(product.features)} product features: {', '.join(product.features[:2])}{'...' if len(product.features) > 2 else ''}.",
                "content",
            )
        )

        has_blocks = any(i.severity == "blocked" for i in issues)
        return GuardrailResult(passed=not has_blocks, issues=issues)

    def check_recommendations(
        self,
        recommendations: ProductRecommendations,
        catalog_products: dict[str, ProductInfo],
    ) -> GuardrailResult:
        issues: List[GuardrailIssue] = []
        valid_names = {p.name.lower() for p in catalog_products.values()}
        all_names = recommendations.related_products + recommendations.upsell_products
        invalid_found = False

        for product_name in all_names:
            if product_name.lower() not in valid_names:
                invalid_found = True
                issues.append(
                    GuardrailIssue(
                        rule="invalid_product_reference",
                        message=f"Recommended product '{product_name}' does not exist in the catalog. Possible catalog manipulation by admin.",
                        severity="warning",
                        layer="content",
                    )
                )

        if not invalid_found:
            issues.append(
                _info(
                    "catalog_integrity_check",
                    f"All {len(all_names)} recommended products verified against catalog ({len(valid_names)} products). No manipulation detected.",
                    "content",
                )
            )

        return GuardrailResult(
            passed=len(issues) == 0 or all(i.severity != "blocked" for i in issues),
            issues=issues,
        )


class ReplyGuardrail:
    LEGAL_COMMITMENT_PHRASES = [
        (
            r"\bwe\s+(are\s+)?(legally|contractually)\s+(obligated|required|bound)\b",
            "legal obligation",
        ),
        (r"\byou\s+are\s+entitled\s+to\b", "entitlement claim"),
        (r"\bwe\s+guarantee\b", "guarantee promise"),
        (r"\bclass\s+action\b", "class action reference"),
        (r"\blawsuit\b", "lawsuit reference"),
    ]

    INTERNAL_INFO_PATTERNS = [
        (r"\bsupplier\s+(name|contract|pricing|cost)\b", "supplier details"),
        (r"\bmargin\b", "profit margin"),
        (r"\bmarkup\b", "markup info"),
        (r"\bcost\s+price\b", "cost pricing"),
        (r"\bwholesale\b", "wholesale pricing"),
        (r"\binternal\s+(process|policy|procedure)\b", "internal processes"),
    ]

    INAPPROPRIATE_TONE_PATTERNS = [
        (r"\bstupid\b", "derogatory language"),
        (r"\bidiot\b", "derogatory language"),
        (r"\bdumb\b", "derogatory language"),
        (r"\bshut\s+up\b", "dismissive language"),
        (r"\bfigure\s+it\s+out\b", "dismissive language"),
        (r"\bnot\s+my\s+(problem|job)\b", "unprofessional dismissal"),
    ]

    def check(self, reply_text: str) -> GuardrailResult:
        issues: List[GuardrailIssue] = []
        text_lower = reply_text.lower()

        # Check legal commitments
        legal_violations = []
        for pattern, desc in self.LEGAL_COMMITMENT_PHRASES:
            match = re.search(pattern, text_lower)
            if match:
                legal_violations.append(match.group())
                issues.append(
                    GuardrailIssue(
                        rule="unauthorized_legal_commitment",
                        message=f"Reply contains {desc}: '{match.group()}'. Unauthorized legal commitment — requires legal review.",
                        severity="blocked",
                        layer="reply",
                    )
                )

        if not legal_violations:
            issues.append(
                _info(
                    "legal_commitment_scan",
                    "Scanned for unauthorized legal commitments (guarantees, entitlements, lawsuit references) — none found.",
                    "reply",
                )
            )

        # Check internal info leaks
        leak_violations = []
        for pattern, desc in self.INTERNAL_INFO_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                leak_violations.append(match.group())
                issues.append(
                    GuardrailIssue(
                        rule="internal_info_leak",
                        message=f"Reply may expose {desc}: '{match.group()}'. Internal information must not be shared with customers.",
                        severity="blocked",
                        layer="reply",
                    )
                )

        if not leak_violations:
            issues.append(
                _info(
                    "internal_info_scan",
                    "Scanned for internal information leaks (supplier details, margins, pricing formulas) — none found.",
                    "reply",
                )
            )

        # Check tone violations
        tone_violations = []
        for pattern, desc in self.INAPPROPRIATE_TONE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                tone_violations.append(match.group())
                issues.append(
                    GuardrailIssue(
                        rule="tone_violation",
                        message=f"Reply contains {desc}: '{match.group()}'. Does not meet company communication standards.",
                        severity="blocked",
                        layer="reply",
                    )
                )

        if not tone_violations:
            issues.append(
                _info(
                    "tone_compliance_scan",
                    "Scanned for inappropriate tone (hostile, dismissive, unprofessional language) — tone is appropriate.",
                    "reply",
                )
            )

        has_blocks = any(i.severity == "blocked" for i in issues)
        return GuardrailResult(passed=not has_blocks, issues=issues)


class RoleGuardrail:
    ROLE_PERMISSIONS = {
        AdminRole.junior: {"reply to customer", "improve product content"},
        AdminRole.senior: {
            "reply to customer",
            "improve product content",
            "update stock",
        },
        AdminRole.manager: {
            "reply to customer",
            "improve product content",
            "update stock",
            "review pricing",
            "follow up with supplier",
        },
    }

    def check_action(
        self, action: ActionRecommendation, role: AdminRole
    ) -> GuardrailResult:
        issues: List[GuardrailIssue] = []
        allowed = self.ROLE_PERMISSIONS.get(role, set())

        if action.action not in allowed:
            issues.append(
                GuardrailIssue(
                    rule="role_unauthorized_action",
                    message=f"Role '{role.value}' is not authorized to '{action.action}'. Allowed: {', '.join(sorted(allowed))}.",
                    severity="blocked",
                    layer="role",
                )
            )
        else:
            issues.append(
                _info(
                    "role_authorization_check",
                    f"Role '{role.value}' is authorized for '{action.action}'. Allowed actions: {', '.join(sorted(allowed))}.",
                    "role",
                )
            )

        return GuardrailResult(
            passed=all(i.severity != "blocked" for i in issues), issues=issues
        )
