import { useState } from 'react'
import { motion } from 'framer-motion'
import { PromptInputBox } from './components/PromptInputBox'
import './Landing.css'

const DEMO_QUERIES = [
  {
    key: 'eligibility',
    label: 'Software Eligibility',
    tag: 'Alice · 2019–present',
    query: 'How has the Federal Circuit treated software patent eligibility under Alice after 2019? Which judges apply the two-step test most strictly?',
  },
  {
    key: 'claim_construction',
    label: 'Claim Construction',
    tag: '35 USC 112(f) · Williamson',
    query: 'What is the CAFC standard for means-plus-function construction under 35 USC 112(f)? How has it shifted since Williamson v. Citrix?',
  },
  {
    key: 'obviousness',
    label: 'Obviousness',
    tag: 'KSR · NDCA · UI Claims',
    query: 'After KSR, how do NDCA district courts handle obviousness challenges to software patents with UI claim elements?',
  },
]

const FEATURES = [
  {
    icon: '⬡',
    title: 'Citation Graph',
    desc: 'Neo4j traversal across landmark CAFC cases with semantic similarity edges',
    color: '#8B5CF6',
    glow: 'rgba(139,92,246,0.15)',
  },
  {
    icon: '⚡',
    title: 'Live Case Law',
    desc: 'Real-time retrieval via Midpage API — never miss a recent precedent',
    color: '#4A9EDB',
    glow: 'rgba(74,158,219,0.15)',
  },
  {
    icon: '◎',
    title: 'AI Legal Memos',
    desc: 'Claude generates structured memos with risk scores, circuit splits, and verified citations',
    color: '#C9A84C',
    glow: 'rgba(201,168,76,0.15)',
  },
]

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.09 } },
}
const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] } },
}
const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } },
}

export default function Landing({ onSubmit }) {
  const [hoveredDemo, setHoveredDemo] = useState(null)

  const handleSend = (query) => {
    onSubmit(query, false)
  }

  const handleDemo = (query) => {
    onSubmit(query, true)
  }

  return (
    <motion.div
      className="landing"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.015, transition: { duration: 0.4, ease: 'easeInOut' } }}
      transition={{ duration: 0.35 }}
    >
      {/* Orbital background rings */}
      <div className="landing-rings">
        <div className="landing-ring landing-ring--1" />
        <div className="landing-ring landing-ring--2" />
        <div className="landing-ring landing-ring--3" />
      </div>

      {/* Bottom gold glow */}
      <div className="landing-glow-bottom" />

      {/* Top purple glow */}
      <div className="landing-glow-top" />

      {/* Header */}
      <motion.div className="landing-header" variants={fadeIn} initial="hidden" animate="visible">
        <div className="landing-header-logo">
          <span className="landing-hex">⬡</span>
          <span className="landing-logo-text">PatentGraph</span>
        </div>
        <a
          href="https://harvey.ai"
          target="_blank"
          rel="noreferrer"
          className="landing-header-tag"
        >
          Harvey Challenge · Stanford LLM×Law #6
        </a>
      </motion.div>

      {/* Hero */}
      <motion.div
        className="landing-hero"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Badge */}
        <motion.div variants={fadeUp} className="landing-badge">
          <span className="landing-badge-dot" />
          Patent Litigation Intelligence Platform
        </motion.div>

        {/* Title */}
        <motion.h1 variants={fadeUp} className="landing-title">
          <span className="landing-title-hex">⬡</span>
          <span className="landing-title-shimmer">PatentGraph</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p variants={fadeUp} className="landing-subtitle">
          Graph-powered precedent intelligence for patent attorneys.
          <br />
          Ask any litigation question. Get a verified legal memo in seconds.
        </motion.p>

        {/* Prompt box */}
        <motion.div variants={fadeUp} className="landing-input-wrap">
          <PromptInputBox onSend={handleSend} />
        </motion.div>

        {/* Demo pills */}
        <motion.div variants={fadeUp} className="landing-demos">
          <span className="landing-demos-label">Try a demo query:</span>
          <div className="landing-demo-cards">
            {DEMO_QUERIES.map((d) => (
              <button
                key={d.key}
                className={`landing-demo-card${hoveredDemo === d.key ? ' landing-demo-card--active' : ''}`}
                onMouseEnter={() => setHoveredDemo(d.key)}
                onMouseLeave={() => setHoveredDemo(null)}
                onClick={() => handleDemo(d.query)}
              >
                <span className="landing-demo-label">{d.label}</span>
                <span className="landing-demo-tag">{d.tag}</span>
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* Feature row */}
      <motion.div
        className="landing-features"
        variants={stagger}
        initial="hidden"
        animate="visible"
        transition={{ delay: 0.3 }}
      >
        {FEATURES.map((f) => (
          <motion.div
            key={f.title}
            variants={fadeUp}
            className="landing-feature-card"
            style={{ '--feature-glow': f.glow, '--feature-color': f.color }}
          >
            <span className="landing-feature-icon" style={{ color: f.color }}>{f.icon}</span>
            <span className="landing-feature-title">{f.title}</span>
            <span className="landing-feature-desc">{f.desc}</span>
          </motion.div>
        ))}
      </motion.div>

      {/* Footer */}
      <motion.div
        className="landing-footer"
        variants={fadeIn}
        initial="hidden"
        animate="visible"
        transition={{ delay: 0.6 }}
      >
        Powered by&nbsp;<strong>Claude</strong>&nbsp;·&nbsp;<strong>Neo4j</strong>&nbsp;·&nbsp;<strong>Midpage</strong>&nbsp;·&nbsp;<strong>voyage-law-2</strong>
      </motion.div>
    </motion.div>
  )
}
