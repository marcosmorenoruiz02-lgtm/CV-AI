# CVBoost — PRD

## Problem Statement
Plataforma AI full-stack para optimización de carrera. Los usuarios suben su CV en PDF, el sistema extrae datos estructurados, puntúa el match con ofertas y genera un informe "Headhunter" en markdown con GPT-5.2. Incluye modo anónimo (quick analyze), modo Profesional (match CV ↔ oferta) y extensión de Chrome Manifest V3.

## Architecture
- **Frontend**: React 19 + Tailwind + Shadcn UI + Framer Motion
- **Backend**: FastAPI + Motor (Mongo async) + emergentintegrations (OpenAI GPT-5.2 / GPT-5.1 fallback)
- **Database**: MongoDB (`users`, `user_sessions`, `analyses`)
- **Auth**: Emergent-managed Google OAuth (cookie + Bearer)
- **Chrome Extension**: Manifest V3 en `/extension` + zip descargable en `frontend/public/cvboost-extension.zip`

## Core Requirements
- Login Google OAuth (Emergent)
- Landing anónimo con drag-and-drop PDF → quick analyze
- Dashboard autenticado con tabs Análisis / Perfil / Historial
- Motor de scoring modular (skills, experience, education, keywords, semantic)
- Sistema de Tiers FREE / PRO con límite diario 3 análisis (reset UTC)
- LLM dinámico: FREE → GPT-5.1, PRO → GPT-5.2
- Dark mode global
- Extensión Chrome para extraer JD

## Implemented (v2 — 2026-02)
- Modular scoring engine (`services/scoring`, `services/llm`, `schemas`)
- LLM client con timeout 45s y fallback GPT-5.2 → GPT-5.1
- Landing anónimo + `/api/quick-analyze`
- Dark mode via `ThemeContext`
- Chrome Extension Manifest V3 descargable
- STAR optimization via `/api/optimize-cv`
- Backend Tier logic (`enforce_daily_limit`, `increment_analysis_count` en deps.py)
- `/api/billing/upgrade` (mock) — activa tier PRO
- **Frontend Tier UI** (✅ NUEVO):
  - `TierUsageCard` reutilizable (progress bar + CTA upgrade)
  - AnalysisTab muestra "Créditos diarios X/3" y bloquea el botón cuando FREE agota cuota
  - ProfileTab añade "Plan card" con badge FREE/PRO y botón "Subir a Pro"
  - Refresco automático de `checkAuth()` tras cada análisis/upgrade
- Fix: `api/analysis.py` ahora llama `increment_analysis_count` tras generar análisis (antes se podía evadir el límite vía endpoint nuevo)

## Prioritized Backlog
- **P1**: Integración real de Stripe para `/api/billing/upgrade` (precio, moneda, webhook)
- **P1**: Telemetría de conversión (Upload → Match → Account → Pro)
- **P2**: Export PDF del informe de estrategia
- **P2**: Share link público read-only del informe
- **P2**: Limpiar `services/scraper.py` y `api/job_import.py` (orphaned tras remover URL scraping)
- **P2**: Editar/duplicar un análisis

## Testing Status
- Flujo tier FREE/PRO validado end-to-end (curl + Playwright screenshot):
  - Estado normal 1/3 → progress 33%, "Te quedan 2…" ✔
  - Estado límite 3/3 → warning rojo + botón "Límite diario alcanzado" disabled ✔
  - `POST /api/analyses` retorna 403 con mensaje claro al llegar a 3 ✔
  - `POST /api/billing/upgrade` activa tier PRO ✔
  - `/api/auth/me` expone `tier`, `daily_analyses_count`, `last_analysis_date` ✔
