__all__ = [
    "AssistentCore",
    "run_core",
    "AccessibilityRecommender",
    "RecommendationResult",
    "METHOD_LABELS",
    "MedicalAPI",
    "LocalModel",
    "NetworkChecker",
]


def __getattr__(name: str):
    if name in {"AssistentCore", "run_core"}:
        from src.core.assistant_core import AssistentCore, run_core

        return {
            "AssistentCore": AssistentCore,
            "run_core": run_core,
        }[name]
    if name in {
        "AccessibilityRecommender",
        "RecommendationResult",
        "METHOD_LABELS",
    }:
        from src.services.ai_service.recommendation import (
            METHOD_LABELS, AccessibilityRecommender, RecommendationResult)

        return {
            "AccessibilityRecommender": AccessibilityRecommender,
            "RecommendationResult": RecommendationResult,
            "METHOD_LABELS": METHOD_LABELS,
        }[name]
    if name in {"MedicalAPI", "LocalModel"}:
        from src.services.ai_service.llm_client import LocalModel, MedicalAPI

        return {"MedicalAPI": MedicalAPI, "LocalModel": LocalModel}[name]
    if name == "NetworkChecker":
        from src.core.network_monitor import NetworkChecker

        return NetworkChecker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
