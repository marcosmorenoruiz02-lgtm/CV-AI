# Estrategia de Asalto — PRD

## Problem Statement
Plataforma web profesional de optimización de carrera. Los usuarios suben su CV en PDF, configuran su perfil y generan informes markdown ("Estrategia de Asalto") personalizados para cada oferta de empleo usando un Headhunter + ATS expert con GPT-5.2.

## Architecture
- **Frontend**: React 19 + Tailwind + Framer Motion + react-markdown
- **Backend**: FastAPI + Motor (Mongo async) + emergentintegrations (OpenAI GPT-5.2)
- **Database**: MongoDB (collections: `users`, `user_sessions`, `analyses`)
- **Auth**: Emergent-managed Google OAuth (cookie + Bearer)
- **AI**: GPT-5.2 via EMERGENT_LLM_KEY for (a) PDF CV parsing → JSON profile, (b) headhunter/ATS strategy report

## User Personas
- Profesionales en búsqueda activa de empleo que necesitan acelerar la calidad de sus aplicaciones.
- Candidatos senior que ya tienen CV y quieren un análisis estratégico por oferta.

## Core Requirements
- Login Google OAuth
- Perfil persistente (nombre, titular, skills, experiencia)
- Subir CV PDF → autocompleta perfil con IA
- Input de oferta de empleo → genera informe en markdown con 5 bloques
- Historial con lista, detalle, eliminar
- Diseño Soft Professional + Glassmorphism (#F8FAFC, #3B82F6, #10B981), 16px rounded, animaciones

## Implemented (v1 — 2026-02)
- Emergent Google Auth end-to-end (session cookies + Bearer)
- Profile CRUD + PDF upload + GPT-5.2 parser
- Analyses CRUD + GPT-5.2 headhunter prompt
- Landing con hero animado + features + CTA
- Dashboard con tabs (Análisis / Perfil / Historial) y transiciones
- Toaster (sonner) para feedback
- 17/17 backend tests passing

## Prioritized Backlog
- P1: Editar/duplicar un análisis, export PDF del informe
- P1: Compartir informe mediante link público de solo lectura
- P2: Comparar varios análisis lado a lado
- P2: Plantillas de mensajes LinkedIn por industria
- P2: Integración con LinkedIn API para importar perfil
- P2: Plan premium con más análisis y modelos comparativos

## Next Tasks
- Pulido visual tras primer uso real
- Añadir paywall/monetización si se valida demanda
