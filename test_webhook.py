import requests
import json

url = "https://lusty-velda-wavy.ngrok-free.dev/paychangu-webhook"
payload = {
    "event_type": "api.charge.payment",
    "status": "success",
    "reference": "14319437377",
    "charge_id": "test_123",
    "amount": 1030,
    "currency": "MWK"
}

response = requests.post(url, json=payload, verify=False)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")