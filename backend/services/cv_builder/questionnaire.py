"""Suggested questionnaire returned to the frontend per mode.

Used when the user has zero data: we tell the UI which questions to ask.
"""
from typing import Dict, List

from schemas.user_mode import UserMode


_JUNIOR_QUESTIONS: List[Dict] = [
    {"id": "name", "label": "¿Cuál es tu nombre completo?", "type": "text", "required": True},
    {"id": "email", "label": "Email de contacto", "type": "email", "required": False},
    {"id": "location", "label": "Ciudad / país", "type": "text", "required": False},
    {"id": "target_role", "label": "¿A qué puesto te gustaría apuntar?", "type": "text", "required": False},
    {
        "id": "education",
        "label": "Estudios (título, centro, periodo)",
        "type": "list",
        "fields": ["title", "institution", "period", "description"],
        "required": True,
    },
    {
        "id": "skills",
        "label": "Habilidades técnicas y blandas",
        "type": "tags",
        "required": True,
    },
    {
        "id": "interests",
        "label": "Intereses profesionales",
        "type": "tags",
        "required": False,
    },
    {
        "id": "projects",
        "label": "Proyectos personales / académicos",
        "type": "list",
        "fields": ["name", "description", "technologies", "url"],
        "required": False,
    },
    {
        "id": "experience",
        "label": "Experiencia (prácticas, voluntariado, freelance)",
        "type": "list",
        "fields": ["role", "company", "period", "description"],
        "required": False,
    },
]

_PROFESSIONAL_QUESTIONS: List[Dict] = [
    {"id": "name", "label": "Nombre completo", "type": "text", "required": True},
    {"id": "email", "label": "Email", "type": "email", "required": False},
    {"id": "target_role", "label": "Puesto objetivo", "type": "text", "required": False},
    {
        "id": "experience",
        "label": "Experiencia laboral (lo más detallado posible)",
        "type": "list",
        "fields": ["role", "company", "period", "description"],
        "required": True,
    },
    {
        "id": "skills",
        "label": "Stack técnico y skills clave",
        "type": "tags",
        "required": True,
    },
    {
        "id": "education",
        "label": "Formación",
        "type": "list",
        "fields": ["title", "institution", "period"],
        "required": False,
    },
    {
        "id": "projects",
        "label": "Proyectos destacados",
        "type": "list",
        "fields": ["name", "description", "technologies", "url"],
        "required": False,
    },
]


def questionnaire_for_mode(mode: UserMode) -> List[Dict]:
    return _JUNIOR_QUESTIONS if mode == UserMode.junior else _PROFESSIONAL_QUESTIONS
