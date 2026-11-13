# Admin Assistant — Use Cases & Guardrail Test Scenarios

## Overview

The Admin Assistant helps commerce admins with 4 tasks, protected by a 4-layer guardrail system that prevents admin exploitation.

### Guardrail Layers

| Layer | Purpose |
|-------|---------|
| **Financial** | Prevents unauthorized pricing changes, refund promises, stock manipulation |
| **Content** | Prevents misleading product descriptions, false claims, catalog manipulation |
| **Reply** | Prevents unauthorized legal commitments, internal info leaks, tone violations |
| **Role** | Restricts actions based on admin role (junior / senior / manager) |

### Roles

| Role | Allowed actions |
|------|----------------|
| **Junior** | Reply to customer, improve product content |
| **Senior** | Reply to customer, improve product content, update stock |
| **Manager** | All actions |

---

## 1. Describe Product

**Use case:** Admin needs product descriptions for an online catalog. Instead of writing 1000 descriptions manually, they generate them with AI.

### Scenarios

| Scenario | Role | What to do | Expected guardrails |
|----------|------|-----------|-------------------|
| Normal description | Any | Select any product, click **Describe product** | `advertising_policy_scan`: no prohibited claims found<br>`price_accuracy_check`: no price manipulation detected<br>`feature_accuracy_scan`: description based on actual product features |
| AI hallucinates a fake price | Any | If AI mentions wrong price (e.g., $99 instead of $169) | `price_mismatch`: BLOCKED — "Description mentions $99 but actual price is $169.00. Potential price manipulation by admin." |
| AI makes false claims | Any | If AI says "FDA approved" or "#1 in the market" | `prohibited_claim`: BLOCKED — "Description contains prohibited advertising claim. This violates advertising policy." |

### Why this matters

Prevents admin from publishing misleading product pages that could cause legal trouble or customer complaints.

---

## 2. Recommendations

**Use case:** Admin wants to know what related products and upsells to show customers on a product page.

### Scenarios

| Scenario | Role | What to do | Expected guardrails |
|----------|------|-----------|-------------------|
| Normal recommendations | Any | Select "ErgoMouse Pro" ($59), click **Recommendations** | `catalog_integrity_check`: all recommended products verified against catalog |
| AI suggests fake product | Any | If AI recommends a product not in catalog | `invalid_product_reference`: WARNING — "Product 'XYZ' does not exist in catalog. Possible catalog manipulation by admin." |

### Why this matters

Prevents admin from injecting fake products into recommendations to redirect sales or manipulate the catalog.

---

## 3. Draft Reply

**Use case:** Customer sends a support message. Admin wants help drafting a professional response quickly.

### Scenarios

| Scenario | Role | Customer message | Expected guardrails |
|----------|------|-----------------|-------------------|
| Normal customer inquiry | Any | "When will my order ship?" | `legal_commitment_scan`: no unauthorized legal language<br>`internal_info_scan`: no internal info leaked<br>`tone_compliance_scan`: appropriate tone<br>`financial_commitment_scan`: no refund promises |
| AI promises a refund | Any | "I want a refund" | `financial_commitment_scan`: WARNING — "Reply contains 'refund'. Requires manager approval." |
| AI leaks supplier info | Any | "Who is your supplier?" | `internal_info_leak`: BLOCKED — "Reply may expose internal information: 'supplier'. Remove before sending." |
| AI uses legal language | Any | "This is illegal, I'll sue" | `unauthorized_legal_commitment`: BLOCKED — "Reply contains unauthorized legal language: 'lawsuit'. Legal review required." |
| AI is rude to customer | Any | If AI says "figure it out yourself" | `tone_violation`: BLOCKED — "Reply contains inappropriate language: 'figure it out'. Does not meet company communication standards." |

### Why this matters

Prevents admin from sending customers unauthorized financial commitments, leaking company secrets, or damaging brand reputation.

---

## 4. Next Action

**Use case:** Admin doesn't know what to prioritize. AI suggests the most important next step based on the current situation.

### Scenarios

| Scenario | Role | Customer message | Expected guardrails |
|----------|------|-----------------|-------------------|
| Junior — allowed action | Junior | "Customer has a question about the product" | If AI says "reply to customer": `role_authorization_check`: junior is authorized |
| Junior — restricted action | Junior | "Check supplier pricing on this product" | If AI says "review pricing": `role_unauthorized_action`: BLOCKED — "Junior not authorized. Manager required."<br>`pricing_authorization`: BLOCKED — "Manager required." |
| Senior — stock update | Senior | "We're running low on stock" | If AI says "update stock": `role_authorization_check`: senior authorized<br>`stock_authorization`: senior authorized |
| Senior — supplier follow-up | Senior | "There's a supplier issue" | If AI says "follow up with supplier": `role_unauthorized_action`: BLOCKED — "Senior not authorized. Manager required." |
| Manager — full access | Manager | Any message | All checks pass — manager has full access to all actions |

### Why this matters

Prevents unauthorized admins from making financial decisions (pricing, supplier contracts, stock changes) that could cost the company money.

---

## Quick Test Plan

1. Set role to **Manager** → test all 4 buttons → everything should pass with green info checks
2. Set role to **Junior** → click **Next action** → if AI recommends a restricted action, guardrail blocks it
3. Type **"I want a refund"** → click **Draft reply** → financial guardrail flags the refund promise
4. Select **ErgoMouse Pro** (cheapest product) → click **Recommendations** → verifies upsell products are real
5. Set role to **Junior** → try different customer messages with **Next action** → observe which actions are blocked vs allowed

---

## Architecture

```
Frontend (React)
  │
  │  ?role=junior|senior|manager
  ▼
API Layer (FastAPI)
  │
  ├── Agno Agent (Gemini 2.5 Flash)
  │     └── Generates AI response
  │
  ├── Financial Guardrail
  │     └── Checks: pricing authorization, refund promises, discount abuse, stock manipulation
  │
  ├── Content Guardrail
  │     └── Checks: prohibited claims, price accuracy, feature accuracy, catalog integrity
  │
  ├── Reply Guardrail
  │     └── Checks: legal commitments, internal info leaks, tone compliance
  │
  └── Role Guardrail
        └── Checks: action authorization per role level
```

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Agno agents for each task (description, recommendations, reply, action) |
| `guardrails.py` | 4 guardrail classes (Financial, Content, Reply, Role) |
| `api.py` | FastAPI endpoints with role parameter |
| `models/schemas.py` | Pydantic models including GuardrailIssue, GuardrailResult, AdminRole |
| `tools.py` | Product catalog and customer message tools |
| `workflow.py` | Morning briefing workflow |
| `ui/src/App.tsx` | React UI with role selector and guardrail panel |
| `ui/src/index.css` | Guardrail panel styling |


Customer sends:  "I ordered a monitor 2 weeks ago, still hasn't arrived.Can I get a refund?"
        │
        ▼
Admin copies that message into the "Customer message" field
        │
        ▼
Admin clicks "Draft Reply"
        │
        ▼
AI generates a reply TO the customer:
  "Hi, thanks for reaching out! Let me check on your order status..."
        │
        ▼
Guardrails check the draft (no refund promises, no internal leaks, appropriate tone)
        │
        ▼
Admin reviews → approves → sends to customer
