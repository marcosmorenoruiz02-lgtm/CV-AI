"""Output templates / contracts for the CV builder."""
from typing import Dict


CV_BUILDER_OUTPUT_TEMPLATE: Dict = {
    "headline": "",
    "summary": "",
    "skills": [],
    "experience": [],
    "education": [],
    "projects": [],
}


def empty_output() -> Dict:
    """Safe fallback when the LLM fails."""
    return {
        "headline": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
    }
