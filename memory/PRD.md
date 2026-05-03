# CVBoost — PRD

## Problem Statement
Plataforma AI full-stack para optimización de carrera. Los usuarios suben su CV en PDF, el sistema extrae datos estructurados, puntúa el match con ofertas y genera un informe "Headhunter" en markdown con GPT-5.2. Incluye modo anónimo (quick analyze), modo Profesional (match CV ↔ oferta), extensión de Chrome Manifest V3 y monetización **freemium con Stripe (5€/mes para Pro)**.

## Architecture
- **Frontend**: React 19 + Tailwind + Shadcn UI + Framer Motion
- **Backend**: FastAPI + Motor (Mongo async) + emergentintegrations (OpenAI GPT-5.2 / GPT-5.1 fallback + Stripe Checkout)
- **Database**: MongoDB (`users`, `user_sessions`, `analyses`, `payment_transactions`)
- **Auth**: Emergent-managed Google OAuth (cookie + Bearer)
- **Payments**: Stripe Checkout vía emergentintegrations (test proxy: `sk_test_emergent`)
- **Chrome Extension**: Manifest V3 en `/extension` + zip descargable

## Core Requirements
- Login Google OAuth
- Landing anónimo con drag-and-drop PDF → quick analyze
- Dashboard autenticado con tabs Análisis / Perfil / Historial
- Motor de scoring modular (skills, experience, education, keywords, semantic)
- **Tiers FREE / PRO**:
  - FREE: 4 análisis por mes natural (reset UTC día 1)
  - PRO: ilimitado durante 30 días (5€ vía Stripe)
- LLM dinámico: FREE → GPT-5.1, PRO → GPT-5.2
- Dark mode global + paleta cálida (indigo/teal)
- Extensión Chrome para extraer JD

## Implemented (v3 — 2026-02)
### v3.0 Stripe monetization + UX polish (NUEVO)
- Integración real de **Stripe Checkout** (5€/mes) via emergentintegrations
  - `POST /api/payments/checkout/session` crea session + fila en `payment_transactions`
  - `GET /api/payments/checkout/status/{id}` poll idempotente (DB-first, Stripe-fallback)
  - `POST /api/webhook/stripe` handler con validación de firma
  - `_grant_pro_access` usa lock atómico `pro_granted` para evitar double-extend
- Nuevo campo `pro_expires_at` (ISO datetime) en users → downgrade automático al expirar
- Nuevo campo `stripe_customer_id` (para futura gestión de suscripciones)
- Páginas frontend: `/payment/success` (con polling) y `/payment/cancel`
- Refactor **daily → monthly** en el sistema de límites:
  - `FREE_DAILY_LIMIT=3` → `FREE_MONTHLY_LIMIT=4`
  - `daily_analyses_count` → `monthly_analyses_count`
  - `last_analysis_date` → `last_analysis_month` (`YYYY-MM`)
  - Reset automático en UTC al cambiar de mes
- Paleta refrescada: indigo-600 primary (antes blue-500), teal-600 PRO badge (antes emerald),
  fondo cálido `#eef1f6` (antes `#F8FAFC` glaring), mejor contraste de texto (slate-700 body)
- Texto: "Suscribirme por 5€/mes", "Hazte Pro — 5€/mes", "Análisis este mes 4/4",
  "Renovación manual el DD de mes de YYYY" cuando eres PRO
- `/api/billing/upgrade` devuelve **410 Gone** (redirige a `/api/payments/checkout/session`)

### v2 (mantenido)
- Modular scoring engine, LLM client con fallback 5.2→5.1
- Landing anónimo, dark mode, Chrome Extension MV3, STAR optimization
- `TierUsageCard` + Plan card en ProfileTab con progress bar

## Prioritized Backlog
- **P1**: Cambiar de pago one-shot (30 días) → suscripción recurrente real de Stripe
  (requiere `stripe_price_id` + `mode='subscription'` + gestión de `customer.subscription.*`)
- **P1**: Stripe Billing Portal para que el usuario cancele/actualice tarjeta desde la app
- **P2**: Telemetría de conversión (Upload → Match → Account → Pro)
- **P2**: Export PDF del informe, share link público read-only
- **P2**: Limpiar `services/scraper.py` y `api/job_import.py` (orphaned tras remover URL scraping)
- **P2**: Editar/duplicar un análisis

## Testing Status (v3.0)
- ✅ Create checkout session → redirige a `checkout.stripe.com/c/pay/cs_test_...`
- ✅ `payment_transactions` row creada con amount=5.0 EUR, status=initiated
- ✅ Simulated paid webhook → `_grant_pro_access` flipa tier=PRO con `pro_expires_at=+30d`
- ✅ Idempotencia: segunda llamada a `_grant_pro_access` NO extiende la fecha
- ✅ Usuario PRO genera análisis sin 403 (bypass del límite mensual)
- ✅ Límite mensual 4/4 → frontend muestra warning rojo + botón "Límite mensual alcanzado" disabled
- ✅ Webhook endpoint rechaza firmas inválidas con HTTP 400
- ✅ Paleta renovada (indigo/teal) renderiza en Analysis, Profile y páginas de pago

## Stripe Configuration
- **Test key**: `sk_test_emergent` (ya en `/app/backend/.env`)
- **Producto/precio**: definidos en backend como `PRO_PACKAGE` (id=`cvboost_pro_monthly`, 5€ EUR, 30 días).
  **Jamás** aceptar amount del frontend (anti-tampering).
- **Para producción**: el usuario debe reemplazar `STRIPE_API_KEY` por su `sk_live_...` real
  y configurar webhook secret. Al pasar a live, considera migrar de `mode='payment'`
  (one-shot renovación manual) a `mode='subscription'` con un Stripe Price.
