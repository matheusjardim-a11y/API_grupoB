from urllib.request import request, urlopen
from os import environ, getenv
from pathlib import Path
import json

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and key and not key.startswith("#"):
            environ.setdefault(key, value.strip().strip("\"'"))

API_KEY = getenv("API_KEY")

def get_relatorio():
    url = "https://api.example.com/relatorio"
    headers = {
        "Authorization": f"Bearer {API_KEY}"}

    response = urlopen(request(url, headers=headers))
    if response.getcode() == 200:
        return json.load(response)
    elif response.getcode() == 400:
        return {"error": "Bad Request", "message": json.load(response)}
    elif response.getcode() == 401:
        return {"error": "Unauthorized", "message": json.load(response)}
    elif response.getcode() == 403:
        return {"error": "Forbidden", "message": json.load(response)}
    elif response.getcode() == 404:
        return {"error": "Not Found", "message": json.load(response)}
    elif response.getcode() == 405:
        return {"error": "Method Not Allowed", "message": json.load(response)}
    elif response.getcode() == 409:
        return {"error": "Conflict", "message": json.load(response)}
    elif response.getcode() == 422:
        return {"error": "Unprocessable Content", "message": json.load(response)}
    elif response.getcode() == 429:
        return {"error": "Too Many Requests", "message": json.load(response)}
    elif response.getcode() == 500:
        return {"error": "Internal Server Error", "message": json.load(response)}
    elif response.getcode() == 502:
        return {"error": "Bad Gateway", "message": json.load(response)}
    elif response.getcode() == 503:
        return {"error": "Service Unavailable", "message": json.load(response)}
    else:
        return {"error": "Unknown Error", "message": json.load(response)}