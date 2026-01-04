import requests
import os

url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {"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"}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

print(response.json())