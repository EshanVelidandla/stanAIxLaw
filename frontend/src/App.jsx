import { useState, useRef, useCallback, useEffect } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import './App.css'

cytoscape.use(dagre)

const API = 'http://localhost:8001'

const NODE_COLORS = {
  Case: '#8B5CF6',
  anchor: '#F97316',
  midpage: '#22C55E',
  Court: '#F59E0B',
  Judge: '#6B7280',
}

const DEMO_QUERIES = {
  eligibility: 'How has the Federal Circuit treated software patent eligibility under Alice after 2019? Which judges apply the two-step test most strictly?',
  claim_construction: 'What is the CAFC standard for means-plus-function construction under 35 USC 112(f)? How has it shifted since Williamson v. Citrix?',
  obviousness: 'After KSR, how do NDCA district courts handle obviousness challenges to software patents with UI claim elements?',
}

function riskColor(score) {
  if (score <= 3) return '#22C55E'
  if (score <= 6) return '#F59E0B'
  return '#EF4444'
}

function SourceBadge({ source }) {
  const colors = { graph: '#8B5CF6', midpage: '#22C55E' }
  const bg = colors[source] || '#6B7280'
  return (
    <span style={{
      background: bg, color: '#fff', fontSize: 10, fontWeight: 700,
      padding: '1px 6px', borderRadius: 4, marginLeft: 6, letterSpacing: 0.5,
    }}>{(source || 'N/A').toUpperCase()}</span>
  )
}

function TrustBadge({ verified }) {
  if (verified === true) return <span title="TrustFoundry verified" style={{ color: '#22C55E', fontSize: 13, marginRight: 4 }}>✓</span>
  if (verified === false) return <span title="Could not verify" style={{ color: '#EF4444', fontSize: 13, marginRight: 4 }}>⚠</span>
  return <span style={{ color: '#6B7280', fontSize: 11, marginRight: 4 }}>?</span>
}

export default function App() {
  const [question, setQuestion] = useState('')
  const [memo, setMemo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [demoMode, setDemoMode] = useState(false)
  const cyRef = useRef(null)
  const containerRef = useRef(null)

  const buildElements = useCallback((m) => {
    if (!m?.subgraph) return []
    const { nodes, edges } = m.subgraph
    const anchorIds = new Set(m.anchor_cases || [])

    const cyNodes = nodes.map(n => ({
      data: {
        id: n.id,
        label: (n.citation || n.id).split(',')[0].slice(0, 28),
        citation: n.citation,
        holding: n.holding_summary,
        date: n.date,
        court: n.court,
        isAnchor: anchorIds.has(n.id),
        color: anchorIds.has(n.id) ? NODE_COLORS.anchor : NODE_COLORS.Case,
      },
    }))

    const cyEdges = (edges || []).map((e, i) => ({
      data: { id: `e${i}`, source: e.source, target: e.target, type: e.type },
    }))

    return [...cyNodes, ...cyEdges]
  }, [])

  // Run dagre layout imperatively and fit after layoutstop
  const elements = memo ? buildElements(memo) : []

  useEffect(() => {
    const cy = cyRef.current
    if (!cy || elements.length === 0) return
    const lay = cy.layout({
      name: 'dagre',
      rankDir: 'BT',
      nodeSep: 60,
      rankSep: 80,
      padding: 40,
      animate: true,
      animationDuration: 600,
    })
    lay.on('layoutstop', () => {
      cy.fit(undefined, 40)
      cy.center()
    })
    lay.run()
  }, [elements])

  // ResizeObserver — keeps canvas correct on window resize
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const ro = new ResizeObserver(() => {
      if (cyRef.current) cyRef.current.resize()
    })
    ro.observe(container)
    return () => ro.disconnect()
  }, [])

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'label': 'data(label)',
        'color': '#fff',
        'font-size': 9,
        'text-valign': 'center',
        'text-halign': 'center',
        'width': 90,
        'height': 38,
        'shape': 'round-rectangle',
        'text-wrap': 'wrap',
        'text-max-width': 84,
      },
    },
    {
      selector: 'node[?isAnchor]',
      style: { 'border-width': 3, 'border-color': '#fff', 'width': 108, 'height': 46, 'font-weight': 700, 'font-size': 10 },
    },
    { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#FCD34D' } },
    {
      selector: 'edge[type = "CITES"]',
      style: { 'width': 1.5, 'line-color': '#8B5CF6', 'target-arrow-color': '#8B5CF6', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'opacity': 0.75 },
    },
    {
      selector: 'edge[type = "SIMILAR_TO"]',
      style: { 'width': 1, 'line-color': '#8B5CF6', 'line-style': 'dashed', 'curve-style': 'bezier', 'opacity': 0.4 },
    },
  ]

  async function handleQuery(q, isDemo) {
    const finalQ = q || question
    if (!finalQ.trim()) return
    setLoading(true); setError(null); setMemo(null); setSelectedNode(null); setDemoMode(!!isDemo)
    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: finalQ, demo: !!isDemo }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
      setMemo(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function highlightCase(citation) {
    if (!cyRef.current) return
    cyRef.current.nodes().forEach(n => {
      const c = n.data('citation') || ''
      if (c === citation || c.includes(citation.split(',')[0])) {
        n.select()
        cyRef.current.animate({ fit: { eles: n, padding: 100 } }, { duration: 500 })
      }
    })
  }

  return (
    <div className="app">
      <div className="header">
        <div className="logo">⬡ PatentGraph <span className="logo-sub">Patent Litigation Intelligence</span></div>
        <div className="header-right">
          {demoMode && <span className="demo-badge">DEMO MODE</span>}
          <span className="header-tag">Harvey Challenge · Stanford LLM×Law #6</span>
        </div>
      </div>

      <div className="search-row">
        <input
          className="search-input"
          placeholder="Ask a patent litigation question…"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleQuery(question, false)}
        />
        <button className="btn-primary" onClick={() => handleQuery(question, false)} disabled={loading}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      <div className="demo-pills">
        <span className="demo-label">Demo:</span>
        {Object.entries(DEMO_QUERIES).map(([key, q]) => (
          <button key={key} className="pill" onClick={() => { setQuestion(q); handleQuery(q, true) }}>
            {key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {error && <div className="error-bar">⚠ {error}</div>}

      <div className="main-content">
        {/* Graph panel */}
        <div className="graph-panel">
          <div ref={containerRef} className="cy-container">
          {elements.length > 0 ? (
            <CytoscapeComponent
              elements={elements}
              stylesheet={stylesheet}
              layout={{ name: 'preset' }}
              style={{ width: '100%', height: '100%' }}
              cy={cy => {
                cyRef.current = cy
                cy.on('tap', 'node', e => {
                  const n = e.target
                  setSelectedNode({
                    id: n.id(),
                    citation: n.data('citation'),
                    holding: n.data('holding'),
                    date: n.data('date'),
                    court: n.data('court'),
                    isAnchor: n.data('isAnchor'),
                    hops: n.data('hops'),
                  })
                })
              }}
            />
          ) : (
            <div className="graph-empty">
              {loading
                ? <div className="loading-msg">Traversing knowledge graph…</div>
                : <div className="graph-placeholder">
                    <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.3 }}>⬡</div>
                    <div>Run a query to visualize the patent citation graph</div>
                  </div>
              }
            </div>
          )}
          </div>

          {selectedNode && (
            <div className="node-drawer">
              <button className="drawer-close" onClick={() => setSelectedNode(null)}>✕</button>
              <div className="drawer-badges">
                {selectedNode.isAnchor
                  ? <span className="drawer-badge anchor">Key Case</span>
                  : <span className="drawer-badge related">Related Precedent</span>}
                {selectedNode.hops > 0 && (
                  <span className="drawer-badge hops">{selectedNode.hops === 1 ? '1 step away' : `${selectedNode.hops} steps away`}</span>
                )}
              </div>
              <div className="drawer-citation">{selectedNode.citation}</div>
              <div className="drawer-meta">
                <span className="drawer-court">{(selectedNode.court || '').toUpperCase()}</span>
                {selectedNode.date && <span> · {selectedNode.date.slice(0, 4)}</span>}
              </div>
              <div className="drawer-section-label">What the court decided</div>
              <div className="drawer-holding">{selectedNode.holding || 'No summary available.'}</div>
              <div className="drawer-section-label" style={{ marginTop: 10 }}>Why it matters</div>
              <div className="drawer-layman">
                {selectedNode.isAnchor
                  ? 'This is one of the central cases driving the analysis. The court\'s ruling here directly shapes how similar patent disputes are decided today.'
                  : `This case was cited ${selectedNode.hops === 1 ? 'directly' : `${selectedNode.hops} steps removed`} from the key cases. It supports or refines the legal rules established by those earlier decisions.`}
              </div>
            </div>
          )}

          <div className="legend">
            {[['Anchor', '#F97316'], ['Case', '#8B5CF6'], ['Court', '#F59E0B'], ['Judge', '#6B7280']].map(([l, c]) => (
              <span key={l} className="leg-item"><span className="leg-dot" style={{ background: c }} />{l}</span>
            ))}
            <span className="leg-item"><span className="leg-line solid" />Cites</span>
            <span className="leg-item"><span className="leg-line dashed" />Similar</span>
          </div>
        </div>

        {/* Memo panel */}
        <div className="memo-panel">
          {memo ? (
            <div className="memo-content">
              <div className="memo-summary">
                <div className="section-title">Executive Summary</div>
                <p>{memo.executive_summary}</p>
              </div>

              <div className="metrics-row">
                <div className="risk-block">
                  <div className="metric-label">Litigation Risk</div>
                  <div className="risk-bar-wrap">
                    <div className="risk-bar-fill" style={{ width: `${(memo.litigation_risk_score || 0) * 10}%`, background: riskColor(memo.litigation_risk_score) }} />
                  </div>
                  <div className="risk-num" style={{ color: riskColor(memo.litigation_risk_score) }}>{memo.litigation_risk_score}/10</div>
                  <div className="risk-rationale">{memo.litigation_risk_rationale}</div>
                </div>

                <div className={`circuit-split-block ${memo.circuit_split?.exists ? 'split-yes' : 'split-no'}`}>
                  <div className="metric-label">Circuit Split</div>
                  <div className="split-status">{memo.circuit_split?.exists ? '⚠ Yes' : '✓ No'}</div>
                  {memo.circuit_split?.exists && <div className="split-detail">{memo.circuit_split.description}</div>}
                </div>
              </div>

              {memo.claim_construction_trend && (
                <div className="section">
                  <div className="section-title">
                    Claim Construction
                    <span className="trend-chip">{memo.claim_construction_trend.direction}</span>
                  </div>
                  <p className="small-text">{memo.claim_construction_trend.summary}</p>
                </div>
              )}

              <div className="section">
                <div className="section-title">Precedent Chain ({(memo.precedent_chain || []).length} cases)</div>
                <div className="precedent-list">
                  {(memo.precedent_chain || []).map((p, i) => (
                    <div key={i} className="prec-item" onClick={() => highlightCase(p.citation)}>
                      <div className="prec-header">
                        <TrustBadge verified={p.trust_verified} />
                        <span className="prec-citation">{p.citation}</span>
                        <SourceBadge source={p.source} />
                        {p.hops_from_anchor > 0 && <span className="hop-chip">{p.hops_from_anchor}h</span>}
                      </div>
                      <div className="prec-holding">{p.holding}</div>
                      <div className="prec-relevance">{p.relevance}</div>
                      {p.verification_warning && <div className="verify-warn">⚠ {p.verification_warning}</div>}
                    </div>
                  ))}
                </div>
              </div>

              <div className="cite-row">
                <div className="cite-col">
                  <div className="section-title cite-for-title">Cite For</div>
                  {(memo.cases_to_cite_for || []).map((c, i) => (
                    <div key={i} className="cite-item">
                      <TrustBadge verified={typeof c === 'object' ? c.trust_verified : null} />
                      {typeof c === 'string' ? c : c.citation}
                    </div>
                  ))}
                </div>
                <div className="cite-col">
                  <div className="section-title cite-against-title">Cite Against</div>
                  {(memo.cases_to_cite_against || []).map((c, i) => (
                    <div key={i} className="cite-item">
                      <TrustBadge verified={typeof c === 'object' ? c.trust_verified : null} />
                      {typeof c === 'string' ? c : c.citation}
                    </div>
                  ))}
                </div>
              </div>

              <div className="confidence-row">
                <span className="conf-label">Confidence:</span>
                <span className="conf-score">{memo.confidence}/10</span>
                <span className="conf-rationale"> — {memo.confidence_rationale}</span>
              </div>
              {memo.trust_verification && (
                <div className="trust-status">TrustFoundry: {memo.trust_verification}</div>
              )}
            </div>
          ) : (
            <div className="memo-empty">
              {loading ? 'Generating legal memo…' : 'Legal memo will appear here after your query.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
