import requests
import json

url = "http://127.0.0.1:8000/query/stream" 
headers = {"x-user-id": "5148a24b-41d4-4dd8-8208-b48131cf6027"}
payload = {
    "query": "What are the dependencies in tools.py?",
    "session_id": "85e5eead-6643-4692-815b-e4595537c4a2"
}

print("Starting stream...\n")
with requests.post(url, json=payload, headers=headers, stream=True) as r:
    for line in r.iter_lines():
        if line:
            event = json.loads(line.decode('utf-8'))
            if event["type"] == "token":
                print(event["data"]["token"], end="", flush=True)
            elif event["type"] == "tool_call":
                print(f"\n\n🛠️ [TOOL CALLED]: {event['data']['tool_name']}")