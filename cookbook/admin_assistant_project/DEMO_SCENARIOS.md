# Admin Assistant Demo Scenarios

## Overview
This document outlines key demo scenarios to showcase the Admin Assistant's capabilities to clients. Each demo highlights different features, workflows, and guardrail protections.

## Core Features Demos

### 1. Product Content Generation
**Demo: Automated Product Descriptions**
- **Scenario**: Generate compelling product descriptions from catalog metadata
- **Steps**:
  1. Select "BrightChoice 15.6" Portable Monitor" product
  2. Click "Describe product"
  3. Show generated headline, body copy, and benefits list
- **Key Points**: AI generates professional, consistent product content instantly

### 2. Smart Product Recommendations
**Demo: Context-Aware Upselling**
- **Scenario**: Customer inquiry about portable monitor triggers upgrade suggestions
- **Steps**:
  1. Select monitor product
  2. Enter customer message: "I need a portable monitor for travel"
  3. Click "Recommendations"
  4. Show related products and upsell suggestions
- **Key Points**: AI understands customer intent and suggests appropriate upgrades

### 3. Customer Service Automation
**Demo: Professional Customer Replies**
- **Scenario**: Customer reports shipping delay
- **Steps**:
  1. Select monitor product
  2. Enter customer message: "My order is delayed, can you update me?"
  3. Click "Draft reply"
  4. Show generated response with recommended tone
- **Key Points**: Consistent, professional customer communication

### 4. Actionable Intelligence
**Demo: Smart Next Action Recommendations**
- **Scenario**: Customer requests refund consideration
- **Steps**:
  1. Select monitor product
  2. Enter customer message: "The monitor arrived damaged, I want a refund"
  3. Click "Next action"
  4. Show recommended admin action with reasoning
- **Key Points**: AI prioritizes tasks and suggests appropriate responses

## Workflow Demos

### 5. Morning Briefing Automation
**Demo: Daily Admin Summary**
- **Scenario**: Start-of-day briefing for operations team
- **Steps**:
  1. Select monitor product
  2. Enter sample customer messages
  3. Click "Morning briefing"
  4. Show complete briefing with product info, alerts, and action items
- **Key Points**: Comprehensive daily overview in seconds

### 6. End-to-End Customer Support
**Demo: Complete Support Workflow**
- **Scenario**: Handle customer complaint from start to finish
- **Steps**:
  1. Use Customer Support workflow endpoint
  2. Enter customer complaint
  3. Show drafted reply + recommended action + guardrail checks
- **Key Points**: Streamlined customer issue resolution

### 7. Product Launch Preparation
**Demo: Launch Content Generation**
- **Scenario**: Prepare all content for new product launch
- **Steps**:
  1. Use Product Launch workflow
  2. Show generated description + recommendations + approval status
- **Key Points**: Complete launch package generation

## Security & Compliance Demos

### 8. Content Guardrails Protection
**Demo: Advertising Compliance**
- **Scenario**: Prevent prohibited advertising claims
- **Steps**:
  1. Use demo scenario "prohibited_claim"
  2. Show how system blocks "FDA approved" and "clinically proven" claims
  3. Demonstrate guardrail warnings and blocks
- **Key Points**: Automated compliance prevents legal risks

### 9. Financial Guardrails Protection
**Demo: Financial Commitment Prevention**
- **Scenario**: Block unauthorized refund promises
- **Steps**:
  1. Try to generate reply promising refund
  2. Show guardrail blocks financial commitments
- **Key Points**: Prevents unauthorized financial exposure

### 10. Role-Based Access Control
**Demo: Junior Admin Restrictions**
- **Scenario**: Junior admin attempts pricing changes
- **Steps**:
  1. Use "pricing-update-blocked" workflow
  2. Show how junior role is blocked from pricing actions
  3. Demonstrate approval requirement warnings
- **Key Points**: Enforces organizational hierarchy and approval processes

### 11. Price Mismatch Detection
**Demo: Pricing Inconsistency Prevention**
- **Scenario**: Detect when description doesn't match catalog price
- **Steps**:
  1. Use "price_mismatch" demo scenario
  2. Show guardrail flags price discrepancies
- **Key Points**: Maintains pricing accuracy across all content

## Advanced Scenarios

### 12. Multi-Role Demonstration
**Demo: Role-Based Behavior**
- **Scenario**: Same task with different admin roles
- **Steps**:
  1. Generate content as junior admin
  2. Repeat as senior admin
  3. Repeat as manager
  4. Show how guardrails change based on role permissions
- **Key Points**: Flexible role-based access control

### 13. Error Handling & Resilience
**Demo: API Failure Graceful Degradation**
- **Scenario**: System continues working when AI service is unavailable
- **Steps**:
  1. Simulate API outage (remove API key)
  2. Show system falls back to mock responses
  3. Demonstrate continued functionality
- **Key Points**: Reliable operation even during service disruptions

### 14. Batch Processing Simulation
**Demo: Multiple Product Processing**
- **Scenario**: Process multiple products simultaneously
- **Steps**:
  1. Generate descriptions for all three products
  2. Show recommendations for each
  3. Demonstrate workflow efficiency
- **Key Points**: Scales to handle multiple products efficiently

## Demo Flow Recommendations

### Quick 5-Minute Demo
1. Product description generation (Demo 1)
2. Customer reply drafting (Demo 3)
3. Guardrail protection (Demo 8)

### Comprehensive 15-Minute Demo
1. Morning briefing workflow (Demo 5)
2. Customer support end-to-end (Demo 6)
3. Role-based restrictions (Demo 10)
4. Content compliance (Demo 8)

### Technical Deep Dive (30+ minutes)
1. All workflow demos (5-7)
2. All guardrail demos (8-11)
3. Multi-role demonstration (12)
4. Error handling (13)

## Preparation Notes

- Ensure backend is running: `uvicorn api:app --reload --port 8000`
- Start React UI: `cd ui && npm run dev`
- Have sample customer messages ready
- Test all endpoints before demo
- Prepare fallback mock mode if API is unavailable

## Key Selling Points to Emphasize

1. **Speed**: Instant content generation vs manual writing
2. **Consistency**: Standardized, professional outputs
3. **Compliance**: Automated guardrails prevent costly mistakes
4. **Scalability**: Handle multiple products/workflows simultaneously
5. **Security**: Role-based access prevents unauthorized actions
6. **Reliability**: Graceful degradation during service issues</content>
<parameter name="filePath">/Users/soemoehtet/agno/agno/cookbook/admin_assistant_project/DEMO_SCENARIOS.md