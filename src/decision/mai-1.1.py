import json
import os
import urllib.request

from azure.identity import DefaultAzureCredential

AZURE_ENDPOINT = os.environ["AZURE_ENDPOINT"].rstrip("/")
DEPLOYMENT_NAME = os.environ["DEPLOYMENT_NAME"]

credential = DefaultAzureCredential()

token = credential.get_token(
    "https://cognitiveservices.azure.com/.default"
).token

url = (
    f"{AZURE_ENDPOINT}"
    "/providers/microsoft/v1/systemone"
)

payload = {
    "model": DEPLOYMENT_NAME,
    "state": "The API returns 500 on every call.",
    "questions": {
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this ticket?",
            "criteria": {
                "billing": "Charges, invoices, and refunds",
                "engineering": "Bugs, errors, and outages",
                "support": "How-to and account questions"
            }
        }
    }
}

request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    method="POST",
)

with urllib.request.urlopen(request, timeout=60) as response:
    result = json.loads(response.read().decode("utf-8"))

print(json.dumps(result, indent=2))
