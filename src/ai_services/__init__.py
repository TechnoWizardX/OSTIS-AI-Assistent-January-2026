"""
AI Services — модуль для работы с AI-сервисами и рекомендациями доступности.
"""

from .services import MedicalAPI, LocalModel, NetworkChecker
from .accessibility_recommender import AccessibilityRecommender, RecommendationWorker, RecommendationParser, RecommendationResult, RecommendationCache

__all__ = [
    'MedicalAPI',
    'LocalModel',
    'NetworkChecker',
    'AccessibilityRecommender',
    'RecommendationWorker',
    'RecommendationParser',
    'RecommendationResult',
    'RecommendationCache'
]
