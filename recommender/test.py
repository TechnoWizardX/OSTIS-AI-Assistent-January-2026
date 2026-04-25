import json
from predict import predict

with open("diagnosis.json", "r", encoding="utf-8") as f:
    patient = json.load(f)

result = predict(patient)
print(result)