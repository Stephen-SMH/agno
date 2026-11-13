import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type AdminRole = 'junior' | 'senior' | 'manager'

type ProductInfo = {
  id: string
  name: string
  category: string
  features: string[]
  price: number
}

type ProductDescription = {
  headline: string
  body: string
  benefits: string[]
}

type ProductRecommendations = {
  related_products: string[]
  upsell_products: string[]
}

type CustomerReplyDraft = {
  reply: string
  recommended_tone: string
}

type ActionRecommendation = {
  action: string
  reason: string
  requires_approval: boolean
}

type GuardrailIssue = {
  rule: string
  message: string
  severity: 'blocked' | 'warning' | 'info'
  layer: string
}

type GuardrailResult = {
  passed: boolean
  issues: GuardrailIssue[]
}

type MorningBriefing = {
  product_description: ProductDescription
  upsell_summary: string
  customer_alerts: string
  admin_actions: ActionRecommendation[]
}

type ActionResult<T> = {
  data: T
  guardrails: GuardrailResult
}

type DemoScenario = {
  id: string
  label: string
  description: string
  layer: string
}

type DemoResult = {
  scenario: string
  label: string
  data: Record<string, unknown>
  guardrails: GuardrailResult
}

const LAYER_LABELS: Record<string, string> = {
  financial: 'Financial abuse',
  content: 'Content manipulation',
  reply: 'Unauthorized reply',
  role: 'Role-based access',
}

const SEVERITY_ICONS: Record<string, string> = {
  blocked: 'BLOCKED',
  warning: 'WARNING',
  info: 'PASSED',
}

function GuardrailPanel({ result }: { result: GuardrailResult }) {
  if (!result) return null
  return (
    <div className={`guardrail-panel ${result.passed ? 'guardrail-pass' : 'guardrail-flagged'}`}>
      <h4>{result.passed ? 'All safety checks passed' : 'Safety checks found issues'}</h4>
      {result.issues.length === 0 && result.passed && (
        <p className="guardrail-summary">No issues detected. AI output is safe to use.</p>
      )}
      {result.issues.map((issue, i) => (
        <div key={i} className={`guardrail-check guardrail-${issue.severity}`}>
          <span className={`guardrail-icon icon-${issue.severity}`}>{SEVERITY_ICONS[issue.severity]}</span>
          <div className="guardrail-detail">
            <span className="guardrail-layer">{issue.layer}</span>
            <span className="guardrail-rule">{issue.rule.replace(/_/g, ' ')}</span>
            <p className="guardrail-message">{issue.message}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function App() {
  const [products, setProducts] = useState<ProductInfo[]>([])
  const [selectedProductId, setSelectedProductId] = useState<string>('')
  const [customerMessage, setCustomerMessage] = useState('')
  const [role, setRole] = useState<AdminRole>('manager')
  const [description, setDescription] = useState<ActionResult<ProductDescription> | null>(null)
  const [recommendations, setRecommendations] = useState<ActionResult<ProductRecommendations> | null>(null)
  const [reply, setReply] = useState<ActionResult<CustomerReplyDraft> | null>(null)
  const [action, setAction] = useState<ActionResult<ActionRecommendation> | null>(null)
  const [briefing, setBriefing] = useState<MorningBriefing | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [forceAction, setForceAction] = useState<string>('')

  // Workflow state
  const [workflowResult, setWorkflowResult] = useState<Record<string, unknown> | null>(null)
  const [workflowLoading, setWorkflowLoading] = useState(false)

  // Demo state
  const [demoScenarios, setDemoScenarios] = useState<DemoScenario[]>([])
  const [demoResult, setDemoResult] = useState<DemoResult | null>(null)
  const [demoLoading, setDemoLoading] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/products`)
      .then((res) => res.json())
      .then(setProducts)
      .catch((err) => setError(String(err)))
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/api/demo/scenarios`)
      .then((res) => res.json())
      .then((data) => setDemoScenarios(data.scenarios))
      .catch(() => {})
  }, [])

  async function runAction(endpoint: string, body: Record<string, unknown>) {
    if (!selectedProductId) {
      setError('Please select a product first.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/products/${selectedProductId}/${endpoint}?role=${role}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        const text = await response.text()
        throw new Error(`${response.status}: ${text}`)
      }
      return await response.json()
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const runDescribe = async () => {
    const result = await runAction('describe', {})
    if (result) setDescription(result)
  }

  const runRecommendations = async () => {
    const result = await runAction('recommendations', { customer_message: customerMessage || null })
    if (result) setRecommendations(result)
  }

  const runReply = async () => {
    const result = await runAction('reply', { content: customerMessage, sender_name: null, order_reference: null })
    if (result) setReply(result)
  }

  const runNextAction = async () => {
    const result = await runAction('next-action', {
      customer_message: customerMessage || null,
      ...(forceAction ? { force_action: forceAction } : {}),
    })
    if (result) setAction(result)
  }

  const runBriefing = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/briefing?role=${role}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: selectedProductId, customer_messages: customerMessage ? [customerMessage] : [] }),
      })
      if (!response.ok) {
        const text = await response.text()
        throw new Error(`${response.status}: ${text}`)
      }
      setBriefing(await response.json())
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const runDemo = async (scenarioId: string) => {
    setDemoLoading(true)
    setDemoResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/demo/run/${scenarioId}?product_id=${selectedProductId || 'monitor-15'}`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      setDemoResult(await res.json())
    } catch (err) {
      setError(String(err))
    } finally {
      setDemoLoading(false)
    }
  }

  const runWorkflow = async (workflowType: string) => {
    if (!selectedProductId) {
      setError('Please select a product first.')
      return
    }
    setWorkflowLoading(true)
    setWorkflowResult(null)
    setError(null)
    try {
      const body: Record<string, unknown> = { product_id: selectedProductId }
      if (customerMessage) body.customer_message = customerMessage
      const res = await fetch(`${API_BASE}/api/workflows/${workflowType}?role=${role}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      setWorkflowResult(await res.json())
    } catch (err) {
      setError(String(err))
    } finally {
      setWorkflowLoading(false)
    }
  }

  const hasBlock = (gr: GuardrailResult | undefined) => gr && !gr.passed && gr.issues.some(i => i.severity === 'blocked')

  return (
    <div className="app-shell">
      <header>
        <h1>Commerce Admin Assistant</h1>
        <p>AI-powered assistant that helps commerce admins manage products and customer support, protected by a 4-layer guardrail system.</p>
      </header>

      <section className="panel capabilities-panel">
        <h2>What this assistant can do</h2>
        <div className="capabilities-grid">

          <div className="capability-card">
            <div className="capability-icon">📝</div>
            <h3>Generate product description</h3>
            <p className="capability-what">
              Creates a marketing-ready product description with headline, body text, and key benefits.
            </p>
            <p className="capability-how">
              <strong>How:</strong> An Agno Agent (powered by Gemini 2.5 Flash) receives the product's name, category, price, and features as a structured prompt. It uses <code>output_schema</code> to guarantee the response matches a Pydantic model with headline, body, and benefits fields.
            </p>
            <p className="capability-why">
              <strong>Why:</strong> Writing descriptions manually for thousands of products is slow and inconsistent. AI generates them in seconds with a consistent brand voice, while guardrails prevent false advertising claims and price manipulation.
            </p>
            <div className="capability-guard">
              <strong>Guardrails:</strong> Scans for prohibited claims (FDA approved, #1 in market), verifies any mentioned prices match the actual product price, and confirms description is grounded in real product features.
            </div>
          </div>

          <div className="capability-card">
            <div className="capability-icon">🛒</div>
            <h3>Suggest related &amp; upsell products</h3>
            <p className="capability-what">
              Recommends products the customer might also want — related items and premium upgrades.
            </p>
            <p className="capability-how">
              <strong>How:</strong> The agent receives the current product's metadata (category, price) and optional customer message context. It cross-references products in the same category (related) and higher-priced items (upsell). The ProductCatalogTool provides the product data.
            </p>
            <p className="capability-why">
              <strong>Why:</strong> Cross-selling and upselling increase average order value, but admins don't always know the best pairings. AI identifies opportunities based on product relationships and customer intent.
            </p>
            <div className="capability-guard">
              <strong>Guardrails:</strong> Verifies every recommended product actually exists in the catalog — prevents an admin from injecting fake products into recommendations.
            </div>
          </div>

          <div className="capability-card">
            <div className="capability-icon">💬</div>
            <h3>AI drafts reply to customer</h3>
            <p className="capability-what">
              Writes a professional customer support reply based on the customer's incoming message.
            </p>
            <p className="capability-how">
              <strong>How:</strong> The admin pastes the customer's message into the input field. The agent combines it with product context (if available) and generates a reply with a suggested tone. The reply is returned as structured data (reply text + recommended tone).
            </p>
            <p className="capability-why">
              <strong>Why:</strong> Customer support teams handle hundreds of messages daily. AI drafts save time and maintain a consistent professional tone, while guardrails prevent the admin from using AI to make unauthorized promises or leak company information.
            </p>
            <div className="capability-guard">
              <strong>Guardrails:</strong> 4 checks run on every reply — scans for unauthorized refund/discount promises (financial), legal commitments like "you are entitled to" (reply), internal info leaks like supplier names or profit margins (reply), and inappropriate tone (reply).
            </div>
          </div>

          <div className="capability-card">
            <div className="capability-icon">🎯</div>
            <h3>Recommend next admin action</h3>
            <p className="capability-what">
              Suggests what the admin should prioritize next based on the current product and customer situation.
            </p>
            <p className="capability-how">
              <strong>How:</strong> The agent analyzes the product data and customer message to choose from 5 possible actions: reply to customer, update stock, improve product content, review pricing, or follow up with supplier. It returns the recommended action with a reason.
            </p>
            <p className="capability-why">
              <strong>Why:</strong> Admins juggle many tasks and may not know what's most urgent. AI prioritizes based on context, while role-based guardrails ensure the admin is actually authorized to perform the recommended action.
            </p>
            <div className="capability-guard">
              <strong>Guardrails:</strong> Checks the admin's role against the action — juniors can only reply and improve content, seniors can also update stock, only managers can review pricing and contact suppliers. Financial guardrails add an extra layer for pricing and stock authorization.
            </div>
          </div>

          <div className="capability-card">
            <div className="capability-icon">📋</div>
            <h3>Generate morning briefing</h3>
            <p className="capability-what">
              Compiles a daily summary with product description, upsell opportunities, customer alerts, and recommended actions.
            </p>
            <p className="capability-how">
              <strong>How:</strong> A workflow orchestrates multiple agents in sequence — it generates a product description, summarizes customer messages, suggests upsell products, and recommends admin actions. Results are combined into a single MorningBriefing object.
            </p>
            <p className="capability-why">
              <strong>Why:</strong> Gives the admin a complete overview of their day in one click — what to focus on, which customers need attention, and what actions to take.
            </p>
            <div className="capability-guard">
              <strong>Guardrails:</strong> Each sub-agent runs its own guardrails independently, so the briefing inherits all content, reply, and role protections.
            </div>
          </div>

        </div>
      </section>

      <section className="panel">
        <div className="config-row">
          <label className="config-label">
            Your role
            <select value={role} onChange={(e) => setRole(e.target.value as AdminRole)}>
              <option value="manager">Manager (full access)</option>
              <option value="senior">Senior Admin</option>
              <option value="junior">Junior Admin (limited)</option>
            </select>
          </label>
          <div className="role-badge">
            Logged in as: <strong>{role}</strong>
          </div>
        </div>

        <label>
          Select a product to manage
          <select value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)}>
            <option value="">-- choose a product --</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} — ${product.price}
              </option>
            ))}
          </select>
        </label>

        <label>
          Incoming customer message (paste what the customer sent)
          <textarea
            value={customerMessage}
            onChange={(event) => setCustomerMessage(event.target.value)}
            placeholder="e.g. I ordered a monitor 2 weeks ago and it still hasn't arrived. Can I get a refund?"
          />
        </label>

        <div className="button-row">
          <button onClick={runDescribe} disabled={!selectedProductId || loading}>
            Generate product description
          </button>
          <button onClick={runRecommendations} disabled={!selectedProductId || loading}>
            Suggest related &amp; upsell products
          </button>
          <button onClick={runReply} disabled={!selectedProductId || !customerMessage || loading}>
            AI drafts reply to customer
          </button>
          <div className="action-group">
            <button onClick={runNextAction} disabled={!selectedProductId || loading}>
              {forceAction ? `Test: ${forceAction}` : 'Recommend next action'}
            </button>
            <select
              className="force-action-select"
              value={forceAction}
              onChange={(e) => setForceAction(e.target.value)}
            >
              <option value="">AI picks the action</option>
              <option value="reply to customer">Test: reply to customer</option>
              <option value="update stock">Test: update stock</option>
              <option value="improve product content">Test: improve product content</option>
              <option value="review pricing">Test: review pricing</option>
              <option value="follow up with supplier">Test: follow up with supplier</option>
            </select>
          </div>
          <button onClick={runBriefing} disabled={!selectedProductId || loading}>
            Generate morning briefing
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="output-grid">
        {description && (
          <article>
            <h2>AI-generated product description</h2>
            <p className="output-context">The AI generated this description from the product data. Guardrails verified it contains no false claims or price manipulation.</p>
            {!hasBlock(description.guardrails) && (
              <>
                <h3>{description.data.headline}</h3>
                <p>{description.data.body}</p>
                <ul>{description.data.benefits.map((benefit) => <li key={benefit}>{benefit}</li>)}</ul>
              </>
            )}
            <GuardrailPanel result={description.guardrails} />
          </article>
        )}

        {recommendations && (
          <article>
            <h2>AI-suggested related &amp; upsell products</h2>
            <p className="output-context">The AI suggests these products based on the selected product. Guardrails verified all products exist in the catalog.</p>
            {!hasBlock(recommendations.guardrails) && (
              <>
                <p><strong>Customers who bought this also bought:</strong> {recommendations.data.related_products.join(', ')}</p>
                <p><strong>Premium upgrades to suggest:</strong> {recommendations.data.upsell_products.join(', ')}</p>
              </>
            )}
            <GuardrailPanel result={recommendations.guardrails} />
          </article>
        )}

        {reply && (
          <article>
            <h2>AI-drafted reply to customer</h2>
            <p className="output-context">The AI drafted this reply based on the customer's message. Review before sending. Guardrails checked for unauthorized promises, info leaks, and tone.</p>
            {!hasBlock(reply.guardrails) && (
              <>
                <p><strong>Suggested tone:</strong> {reply.data.recommended_tone}</p>
                <div className="reply-preview">
                  <p><strong>Suggested reply:</strong></p>
                  <p>{reply.data.reply}</p>
                </div>
              </>
            )}
            <GuardrailPanel result={reply.guardrails} />
          </article>
        )}

        {action && (
          <article>
            <h2>AI-recommended next action</h2>
            <p className="output-context">The AI recommends what you should do next based on the product and customer context. Guardrails checked your role is authorized for this action.</p>
            {!hasBlock(action.guardrails) && (
              <>
                <p><strong>Recommended action:</strong> {action.data.action}</p>
                <p><strong>Reason:</strong> {action.data.reason}</p>
                {action.data.requires_approval && (
                  <div className="approval-banner">
                    This action requires manager approval before it can be executed.
                  </div>
                )}
              </>
            )}
            <GuardrailPanel result={action.guardrails} />
          </article>
        )}

        {briefing && (
          <article>
            <h2>AI-generated morning briefing</h2>
            <p className="output-context">The AI compiled this briefing from product data, customer messages, and recommendations.</p>
            <h3>{briefing.product_description.headline}</h3>
            <p>{briefing.product_description.body}</p>
            <p><strong>Upsell summary:</strong> {briefing.upsell_summary}</p>
            <p><strong>Customer alerts:</strong></p>
            <pre>{briefing.customer_alerts}</pre>
            <p><strong>Admin action:</strong> {briefing.admin_actions[0]?.action}</p>
            <p>{briefing.admin_actions[0]?.reason}</p>
          </article>
        )}
      </section>

      {/* Workflow Section */}
      <section className="panel workflow-panel">
        <h2>Workflows — Multi-Step AI Processes</h2>
        <p className="workflow-description">
          Workflows chain multiple AI agents together to complete complex tasks. Each step runs independently
          with its own guardrails, and the full result is assembled into a single output.
        </p>

        <div className="workflow-cards">
          <div className="workflow-card">
            <div className="workflow-card-header">
              <h3>Morning Briefing</h3>
              <span className="workflow-steps-badge">3 steps</span>
            </div>
            <p className="workflow-card-desc">
              Generates a complete daily summary: product description, customer alerts, upsell opportunities, and recommended actions.
            </p>
            <div className="workflow-step-list">
              <span className="workflow-step-tag">1. Generate product description</span>
              <span className="workflow-step-tag">2. Recommend next action</span>
              <span className="workflow-step-tag">3. Suggest upsell products</span>
            </div>
            <button onClick={() => runWorkflow('morning-briefing')} disabled={!selectedProductId || workflowLoading}>
              Run Morning Briefing
            </button>
          </div>

          <div className="workflow-card">
            <div className="workflow-card-header">
              <h3>Customer Support</h3>
              <span className="workflow-steps-badge">2 steps</span>
            </div>
            <p className="workflow-card-desc">
              Handles a customer message end-to-end: drafts a reply and recommends the next admin action.
            </p>
            <div className="workflow-step-list">
              <span className="workflow-step-tag">1. Draft reply to customer</span>
              <span className="workflow-step-tag">2. Recommend next action</span>
            </div>
            <button onClick={() => runWorkflow('customer-support')} disabled={!selectedProductId || !customerMessage || workflowLoading}>
              Run Customer Support
            </button>
          </div>

          <div className="workflow-card">
            <div className="workflow-card-header">
              <h3>Product Launch</h3>
              <span className="workflow-steps-badge">2 steps</span>
            </div>
            <p className="workflow-card-desc">
              Generates all content needed to launch a product: marketing description and cross-sell/upsell recommendations.
            </p>
            <div className="workflow-step-list">
              <span className="workflow-step-tag">1. Generate product description</span>
              <span className="workflow-step-tag">2. Suggest related &amp; upsell products</span>
            </div>
            <button onClick={() => runWorkflow('product-launch')} disabled={!selectedProductId || workflowLoading}>
              Run Product Launch
            </button>
          </div>

          <div className="workflow-card workflow-card-danger">
            <div className="workflow-card-header">
              <h3>Junior Pricing Update (Blocked)</h3>
              <span className="workflow-steps-badge workflow-steps-badge-danger">3 steps</span>
            </div>
            <p className="workflow-card-desc">
              Demonstrates a junior admin attempting to update pricing. The workflow generates a description, recommends an action, then forces a "review pricing" action that gets <strong>blocked</strong> by role guardrails.
            </p>
            <div className="workflow-step-list">
              <span className="workflow-step-tag">1. Generate product description</span>
              <span className="workflow-step-tag">2. Recommend next action</span>
              <span className="workflow-step-tag workflow-step-tag-danger">3. Force pricing update — BLOCKED</span>
            </div>
            <button className="btn-danger" onClick={() => runWorkflow('pricing-update-blocked')} disabled={!selectedProductId || workflowLoading}>
              Run Junior Pricing Update
            </button>
          </div>
        </div>

        {workflowResult && (
          <div className="workflow-result">
            <div className="workflow-result-header">
              <h3>Workflow: {(workflowResult.workflow as string)?.replace(/_/g, ' ')}</h3>
              <span className={`workflow-status-badge ${workflowResult.status === 'blocked' || workflowResult.status === 'ready_to_publish' ? (workflowResult.status === 'blocked' ? 'badge-fail' : 'badge-pass') : 'badge-pass'}`}>
                {String(workflowResult.status || 'completed').toUpperCase()}
              </span>
            </div>

            <div className="workflow-steps-result">
              {((workflowResult.steps as Array<Record<string, unknown>>) || []).map((step, i) => {
                const stepData = step.data as Record<string, unknown>
                const stepGuardrails = step.guardrails as GuardrailResult
                return (
                  <div key={i} className="workflow-step-result">
                    <div className="workflow-step-header">
                      <span className="workflow-step-number">Step {i + 1}</span>
                      <h4>{step.name as string}</h4>
                    </div>
                    <pre className="workflow-step-data">{JSON.stringify(stepData, null, 2)}</pre>
                    {stepGuardrails && <GuardrailPanel result={stepGuardrails} />}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>

      {/* Guardrail Demo Panel */}
      <section className="panel demo-panel">
        <h2>Guardrail Demo — Simulate Admin Attacks</h2>
        <p className="demo-description">
          Each button below simulates a malicious AI response that an admin could exploit.
          The real guardrail code checks the response and shows what it catches.
          Use this to demonstrate how the system protects against admin abuse.
        </p>

        <div className="demo-scenarios">
          {['financial', 'content', 'reply', 'role'].map(layer => {
            const layerScenarios = demoScenarios.filter(s => s.layer === layer)
            if (layerScenarios.length === 0) return null
            return (
              <div key={layer} className="demo-layer">
                <h3>{LAYER_LABELS[layer] || layer}</h3>
                <div className="demo-buttons">
                  {layerScenarios.map(scenario => (
                    <button
                      key={scenario.id}
                      className="demo-btn"
                      onClick={() => runDemo(scenario.id)}
                      disabled={demoLoading}
                      title={scenario.description}
                    >
                      {scenario.label}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {demoResult && (
          <div className="demo-result">
            <div className="demo-result-header">
              <h3>Simulated attack: {demoResult.label}</h3>
              <span className={`demo-badge ${demoResult.guardrails.passed ? 'badge-pass' : 'badge-fail'}`}>
                {demoResult.guardrails.passed ? 'GUARDRAIL PASSED' : 'ATTACK BLOCKED'}
              </span>
            </div>

            <div className="demo-section">
              <h4>What the malicious AI tried to output</h4>
              <pre className="demo-output">{JSON.stringify(demoResult.data, null, 2)}</pre>
            </div>

            <div className="demo-section">
              <h4>What the guardrails caught</h4>
              <GuardrailPanel result={demoResult.guardrails} />
            </div>
          </div>
        )}
      </section>

      <footer>
        <p>Backend: {API_BASE} | Role: {role}</p>
      </footer>
    </div>
  )
}

export default App
