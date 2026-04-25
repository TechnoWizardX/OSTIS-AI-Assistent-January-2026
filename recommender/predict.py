#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import torch
import torch.nn as nn
from typing import Dict

# ---- Автоматическое определение пути к модели ----
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(_CURRENT_DIR, "model", "best_model.pth")

class RecommendationNN(nn.Module):
    def __init__(self, input_dim=16, output_dim=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, output_dim)
        )
    def forward(self, x):
        return self.net(x)

DIAGNOSES = {
    "motor_impairment": {"options": ["none", "mild", "moderate", "severe"]},
    "speech_impairment": {"options": ["none", "mild", "moderate", "severe"]},
    "vision_impairment": {"options": ["none", "mild", "moderate", "severe"]},
    "hearing_impairment": {"options": ["none", "mild", "moderate", "severe"]}
}

INPUT_METHODS = ["text_input", "gesture_input", "voice_input_vosk", "voice_input_whisper"]

def diagnosis_to_features(diagnosis_dict):
    features = []
    for diag_name, diag_info in DIAGNOSES.items():
        value = diagnosis_dict.get(diag_name, "none")
        options = diag_info["options"]
        features.extend([1.0 if value == opt else 0.0 for opt in options])
    return features

def load_model(model_path=None):
    if model_path is None:
        model_path = DEFAULT_MODEL_PATH
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Модель не найдена: {model_path}")
    model = RecommendationNN(16, 4)
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model

def predict(diagnosis_dict, model_path=None):
    model = load_model(model_path)
    features = diagnosis_to_features(diagnosis_dict)
    input_tensor = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.sigmoid(logits).numpy()[0]
    return {method: float(probs[i]) for i, method in enumerate(INPUT_METHODS)}