"""
AI Services — модуль для работы с AI-сервисами и рекомендациями доступности.
"""

from .services import MedicalAPI, LocalModel, NetworkChecker
from .accessibility_recommender import AccessibilityRecommender, RecommendationWorker, RecommendationFormatter

__all__ = [
    'MedicalAPI',
    'LocalModel',
    'NetworkChecker',
    'AccessibilityRecommender',
    'RecommendationWorker',
    'RecommendationFormatter'
]
