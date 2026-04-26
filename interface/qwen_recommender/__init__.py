"""Для использования отностельных импортов."""
from .QwenModel import QwenModel, QWEN_MODEL
from .QwenRequest import QwenRequest
from .RecommendationManager import RecommendationManager

__all__ = ['QwenModel', 'QWEN_MODEL', 'QwenRequest', 'RecommendationManager']