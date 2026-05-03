"""Career Assault backend - FastAPI + MongoDB + Emergent Auth + OpenAI (via emergentintegrations).

Modular layout:
- deps.py:       shared db + auth dependency
- schemas/:      Pydantic models
- services/:     scoring engine, LLM client, CV builder
- api/:          domain routers (analysis, cv_builder, job_import)
- server.py:     auth, profile, legacy /analyses (MVP), router registration
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader
from starlette.middleware.cors import CORSMiddleware

from api.analysis import router as analysis_router
from api.cv_builder import router as cv_builder_router
from api.job_import import router as job_import_router
from api.quick_analyze import router as quick_analyze_router
from deps import User, WorkExperience, db, enforce_daily_limit, get_current_user, increment_analysis_count
from services.llm.client import call_json, call_text

# ------------------------- APP SETUP -------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Career Assault API")
api_router = APIRouter(prefix="/api")


# ------------------------- LEGACY MODELS (MVP) -------------------------


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[WorkExperience]] = None
    mode: Optional[str] = None  # "junior" | "professional"


class AnalysisCreate(BaseModel):
    job_description: str
    job_title: Optional[str] = ""


class Analysis(BaseModel):
    id: str
    user_id: str
    job_title: str
    job_description: str
    report_markdown: str
    created_at: datetime


# ------------------------- AUTH ROUTES -------------------------


@api_router.post("/auth/session")
async def process_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    data = None
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.get(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                    headers={"X-Session-ID": session_id},
                )
            if r.status_code == 200:
                data = r.json()
                break
            if r.status_code in (401, 403, 404):
                # Definitive failure — don't retry.
                raise HTTPException(status_code=401, detail="Invalid session_id")
            last_err = RuntimeError(f"Emergent auth HTTP {r.status_code}")
        except HTTPException:
            raise
        except Exception as e:
            last_err = e
            logger.warning("Emergent auth call failed (attempt %s): %s", attempt + 1, e)

    if data is None:
        logger.error("Emergent auth exhausted retries: %s", last_err)
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación temporalmente no disponible. Reintenta en unos segundos.",
        )

    email = data["email"]
    name = data["name"]
    picture = data.get("picture", "")
    session_token = data["session_token"]

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = User(user_id=user_id, email=email, name=name, picture=picture)
        doc = new_user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.users.insert_one(doc)

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one(
        {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": user_doc}


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return user.model_dump()


@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"success": True}


# ------------------------- PROFILE ROUTES -------------------------


@api_router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return user.model_dump()


@api_router.put("/profile")
async def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "experience" in update:
        update["experience"] = [
            exp if isinstance(exp, dict) else exp.model_dump() for exp in update["experience"]
        ]
    if "mode" in update and update["mode"] not in {"junior", "professional"}:
        update["mode"] = "professional"
    if update:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    updated = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return updated


@api_router.post("/billing/upgrade")
async def upgrade_to_pro(user: User = Depends(get_current_user)):
    """Mock upgrade endpoint — pending real Stripe integration.

    Currently flips the user's tier to PRO so the limit logic stops blocking.
    Replace with a real checkout flow before going live.
    """
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"tier": "PRO"}},
    )
    updated = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return {"success": True, "user": updated}


@api_router.post("/profile/upload-cv")
async def upload_cv(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    content = await file.read()
    try:
        reader = PdfReader(io.BytesIO(content))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="El PDF no contiene texto extraíble")

    system = (
        "Eres un parser de CVs. Recibirás el texto extraído de un CV y devolverás "
        "EXCLUSIVAMENTE un JSON válido (sin markdown, sin texto adicional) con esta estructura exacta:\n"
        '{"name": str, "headline": str, "skills": [str], '
        '"experience": [{"role": str, "company": str, "period": str, "description": str}]}\n'
        "- name: nombre completo\n"
        "- headline: titular profesional de 1 línea (ej. 'Senior Product Designer')\n"
        "- skills: máximo 15 habilidades técnicas y blandas\n"
        "- experience: hasta 6 experiencias laborales ordenadas por recientes primero"
    )

    try:
        parsed = await call_json(
            system,
            f"TEXTO DEL CV:\n\n{raw_text[:15000]}",
            session_id=f"cv-parse-{user.user_id}",
            fallback={"name": user.name, "headline": "", "skills": [], "experience": []},
        )
    except Exception as e:
        logger.exception("CV parse failed")
        raise HTTPException(
            status_code=503,
            detail=f"El motor de IA no pudo procesar el CV ahora mismo. Intenta de nuevo en unos segundos. ({e})",
        )
    if not isinstance(parsed, dict):
        parsed = {}

    update = {
        "name": parsed.get("name") or user.name,
        "headline": parsed.get("headline", ""),
        "skills": [str(s) for s in (parsed.get("skills") or [])][:20],
        "experience": [e for e in (parsed.get("experience") or []) if isinstance(e, dict)][:8],
        "cv_raw_text": raw_text[:20000],
    }
    await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    updated = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return updated


# ------------------------- LEGACY ANALYSES (MVP markdown reports) -------------------------

HEADHUNTER_SYSTEM_PROMPT = """Eres un coach de carrera que habla claro y sin rollos. Nada de lenguaje corporativo ni de frases vacías. Escribe como si estuvieras tomando un café con la persona y le explicaras, tal cual, cómo ganar este puesto.

Tu trabajo: cruzar su perfil con la oferta y darle un plan de ataque REAL, útil y directo.

Genera un informe en MARKDOWN con estos 5 bloques exactos. Usa ### para cada título.

### 1. Lo que realmente busca la empresa
Olvida lo que dice la oferta entre líneas de marketing. ¿Qué problema están intentando resolver al contratar? ¿Por qué ahora? Dilo en 2-3 frases, como se lo contarías a un amigo.

### 2. Dónde encajas y dónde flojeas
- **Lo que tienes a favor:** 3-5 puntos concretos del perfil que son oro para esta oferta. Sin tecnicismos vacíos.
- **Lo que puede flojear:** skills que piden y no están claras en el CV. Para cada una, una frase de cómo venderla con lo que sí tiene (habilidades transferibles). Lenguaje cercano, como si lo explicaras a alguien.

### 3. Tu CV, adaptado a este puesto
Reescribe su titular profesional y un resumen de 3-4 frases usando las keywords importantes para superar el filtro ATS, pero que suene natural, no a plantilla de LinkedIn. Entrégalo listo para copiar.

### 4. Tips de la entrevista
- Qué tipo de empresa es (intuido del tono de la oferta).
- 2-3 preguntas que es MUY probable que le hagan.
- El tono que le conviene proyectar (seguro, curioso, técnico, cercano...).

### 5. Mensaje para romper el hielo en LinkedIn
Un mensaje directo al hiring manager. Máximo 100 palabras, sin parecer template, sin adulación barata. Engancha en la primera línea y cierra con un CTA suave. Ponlo dentro de un bloque de cita (>) para que se pueda copiar tal cual.

Reglas estrictas:
- Tono: cercano, humano, directo. Nada de "sinergias", "proactividad" ni bullshit corporativo.
- Escribe en español neutro, segunda persona del singular ("tú").
- Cero emojis.
- Cero relleno. Si no hay algo que decir en un bloque, dilo en una frase y punto."""


def _format_profile_for_prompt(user: User) -> str:
    exp_lines = []
    for exp in user.experience:
        d = exp if isinstance(exp, dict) else exp.model_dump()
        exp_lines.append(
            f"- {d.get('role','')} @ {d.get('company','')} ({d.get('period','')}): {d.get('description','')}"
        )
    exp_block = "\n".join(exp_lines) if exp_lines else "(Sin experiencia cargada)"
    skills = ", ".join(user.skills) if user.skills else "(Sin habilidades cargadas)"
    return (
        f"PERFIL DEL USUARIO\n"
        f"Nombre: {user.name}\n"
        f"Titular: {user.headline or '(sin titular)'}\n"
        f"Habilidades: {skills}\n"
        f"Experiencia laboral:\n{exp_block}\n"
    )


@api_router.post("/analyses", response_model=Analysis)
async def create_analysis(payload: AnalysisCreate, user: User = Depends(get_current_user)):
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="La descripción de la oferta es obligatoria")

    if not user.headline and not user.experience and not user.skills:
        raise HTTPException(
            status_code=400,
            detail="Completa tu perfil (o sube un CV) antes de generar una estrategia.",
        )

    user_doc = await enforce_daily_limit(user.user_id)
    tier = (user_doc.get("tier") or "FREE").upper()

    profile_block = _format_profile_for_prompt(user)
    chat_text = (
        f"{profile_block}\n\n"
        f"OFERTA DE EMPLEO:\n{payload.job_description}\n\n"
        f"Genera ahora el informe completo siguiendo la estructura indicada."
    )

    try:
        report = await call_text(
            HEADHUNTER_SYSTEM_PROMPT,
            chat_text,
            session_id=f"analysis-{user.user_id}",
            tier=tier,
        )
    except Exception as e:
        logger.exception("LLM analysis failed")
        raise HTTPException(
            status_code=503,
            detail=f"El motor de IA no pudo generar el informe. Intenta de nuevo en unos segundos. ({e})",
        )

    analysis_id = f"a_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": analysis_id,
        "user_id": user.user_id,
        "job_title": payload.job_title or "Análisis sin título",
        "job_description": payload.job_description,
        "report_markdown": report,
        "created_at": now.isoformat(),
    }
    await db.analyses.insert_one(doc.copy())
    await increment_analysis_count(user.user_id)
    return Analysis(**{**doc, "created_at": now})


@api_router.get("/analyses")
async def list_analyses(user: User = Depends(get_current_user)):
    cursor = db.analyses.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(200)
    for item in items:
        if isinstance(item.get("created_at"), str):
            item["created_at"] = datetime.fromisoformat(item["created_at"])
    return items


@api_router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, user: User = Depends(get_current_user)):
    doc = await db.analyses.find_one(
        {"id": analysis_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, user: User = Depends(get_current_user)):
    res = await db.analyses.delete_one({"id": analysis_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return {"success": True}


# ------------------------- HEALTH -------------------------


@api_router.get("/")
async def root():
    return {"status": "ok", "service": "career-assault"}


# ------------------------- REGISTER ROUTERS -------------------------

app.include_router(api_router)
app.include_router(analysis_router)        # /api/analyze
app.include_router(cv_builder_router)      # /api/cv/build, /api/cv/questionnaire, /api/cv/list
app.include_router(job_import_router)      # /api/job/import
app.include_router(quick_analyze_router)   # /api/quick-analyze (anonymous)

import os

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
