"""Career Assault backend - FastAPI + MongoDB + Emergent Auth + OpenAI (via emergentintegrations)."""
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import json
import io
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import httpx
from pypdf import PdfReader

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

app = FastAPI(title="Career Assault API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ------------------------- MODELS -------------------------

class WorkExperience(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    headline: str = ""
    skills: List[str] = []
    experience: List[WorkExperience] = []
    cv_raw_text: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[WorkExperience]] = None


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


# ------------------------- AUTH HELPERS -------------------------

async def get_current_user(request: Request) -> User:
    """Authenticator helper - cookie first, then Authorization header."""
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)


# ------------------------- AUTH ROUTES -------------------------

@api_router.post("/auth/session")
async def process_session(request: Request, response: Response):
    """Receive session_id from frontend, exchange it for user data, create session."""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient(timeout=15.0) as http:
        r = await http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        data = r.json()

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
    if update:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    updated = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return updated


@api_router.post("/profile/upload-cv")
async def upload_cv(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Extract text from PDF, send to GPT-5.2 to parse structured profile data."""
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

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"cv-parse-{user.user_id}-{uuid.uuid4().hex[:6]}",
        system_message=system,
    ).with_model("openai", "gpt-5.2")

    msg = UserMessage(text=f"TEXTO DEL CV:\n\n{raw_text[:15000]}")
    response_text = await chat.send_message(msg)

    # Parse JSON (tolerant to accidental fencing)
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        logger.error("Failed to parse LLM JSON: %s | raw=%s", e, response_text[:500])
        raise HTTPException(status_code=500, detail="No se pudo interpretar el CV")

    update = {
        "name": parsed.get("name") or user.name,
        "headline": parsed.get("headline", ""),
        "skills": parsed.get("skills", [])[:20],
        "experience": parsed.get("experience", [])[:8],
        "cv_raw_text": raw_text[:20000],
    }
    await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    updated = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return updated


# ------------------------- ANALYSIS ROUTES -------------------------

HEADHUNTER_SYSTEM_PROMPT = """Actúa como un Headhunter de élite y experto en algoritmos ATS. Tu misión es cruzar el CV del usuario con la Oferta de Empleo proporcionada para generar una estrategia de asalto ganadora.

Genera un informe en MARKDOWN estructurado con los siguientes bloques, en este orden exacto. Usa ### para los títulos de bloque.

### 1. Radiografía del Puesto
El problema real que la empresa quiere resolver al contratar este puesto. No repitas la oferta, LEE entre líneas.

### 2. Análisis de Gap
- **Habilidades que faltan:** lista de habilidades explícitamente requeridas por la oferta que el CV NO menciona.
- **Habilidades Transferibles:** mapea experiencias del CV que, aunque no coincidan 1:1, demuestran la competencia requerida. Explica CÓMO argumentarlas.

### 3. Optimización de Texto (ATS-ready)
Reescribe el titular profesional y un resumen de 3-4 líneas del perfil usando las keywords críticas para superar el ATS. Entrega el texto listo para copiar.

### 4. Insider Advice
Consejos sobre la cultura de la empresa (deducida del tono de la oferta), preguntas probables en la entrevista y el tono que debe proyectar el candidato.

### 5. Estrategia de Asalto
Un mensaje de contacto directo para LinkedIn (máximo 120 palabras), altamente persuasivo, personalizado al hiring manager, con un hook claro y un CTA suave. Entrega el texto listo para copiar dentro de un bloque > citado.

Tono general: analítico, profesional, estratégico. En español. Nada de relleno. Nada de emojis."""


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

    profile_block = _format_profile_for_prompt(user)
    user_text = (
        f"{profile_block}\n\n"
        f"OFERTA DE EMPLEO:\n{payload.job_description}\n\n"
        f"Genera ahora el informe completo siguiendo la estructura indicada."
    )

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"analysis-{user.user_id}-{uuid.uuid4().hex[:6]}",
        system_message=HEADHUNTER_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-5.2")

    try:
        report = await chat.send_message(UserMessage(text=user_text))
    except Exception as e:
        logger.exception("LLM analysis failed")
        raise HTTPException(status_code=502, detail=f"El motor de IA no pudo responder: {e}")

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


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
