import json
import urllib.request

url = "http://localhost:11434/api/generate"

data = {
    "model": "qwen2.5-coder:7b",
    "prompt": "Write one sentence explaining what a Godot script is.",
    "stream": False
}

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))

print(result["response"])