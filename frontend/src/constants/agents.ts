import type { AgentMeta } from '../types/review';

export const AGENTS: AgentMeta[] = [
  { id: 'extract',      name: 'Extract & Classify',    icon: '📂', phase: 1, description: 'Unzip, build file tree, categorize FE/BE/Config' },
  { id: 'structure',    name: 'Structure Analyzer',    icon: '🏗️', phase: 1, description: 'Parse deps, detect frameworks, evaluate organization' },
  { id: 'react',        name: 'React Evaluator',       icon: '⚛️', phase: 2, description: 'Static + LLM deep review of React code' },
  { id: 'fastapi',      name: 'FastAPI Evaluator',     icon: '🐍', phase: 2, description: 'Endpoint design, security, validation + LLM review' },
  { id: 'security',     name: 'Security Scanner',      icon: '🔒', phase: 2, description: 'OWASP checks, secrets scan, taint analysis' },
  { id: 'performance',  name: 'Performance Profiler',  icon: '⚡', phase: 2, description: 'Bundle size, re-renders, N+1 queries' },
  { id: 'codesmell',    name: 'Code Smell Detector',   icon: '🦨', phase: 2, description: 'God components, dead code, prop drilling' },
  { id: 'testcoverage', name: 'Test Coverage Analyzer',icon: '🧪', phase: 2, description: 'Test ratio, quality, gap detection' },
  { id: 'dependencies', name: 'Dependency Auditor',    icon: '📦', phase: 2, description: 'Vulnerability, licensing, freshness' },
  { id: 'accessibility',name: 'Accessibility Checker', icon: '♿', phase: 2, description: 'WCAG 2.1 AA compliance, keyboard nav' },
  { id: 'documentation',name: 'Documentation Scorer',  icon: '📝', phase: 2, description: 'README, docstrings, API docs completeness' },
  { id: 'integration',  name: 'Integration Analyzer',  icon: '🔗', phase: 3, description: 'Map FE API calls ↔ BE endpoints' },
  { id: 'requirements', name: 'Requirements Validator',icon: '📋', phase: 3, description: 'Compare impl vs problem statement' },
  { id: 'plagiarism',   name: 'Plagiarism Detector',   icon: '🔍', phase: 3, description: 'Boilerplate %, tutorial signals' },
  { id: 'complexity',   name: 'Complexity Analyzer',   icon: '🧮', phase: 3, description: 'Cyclomatic, cognitive, maintainability index' },
  { id: 'report',       name: 'Report Generator',      icon: '📊', phase: 4, description: 'Consolidate all scores, grade, executive summary' },
];

export const AGENT_MAP = Object.fromEntries(AGENTS.map(a => [a.id, a]));
