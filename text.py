import requests


if __name__ == "__main__":
    payload = {
        "state": {
            "context_summary": "This is summary",
            "execution_meta": {"current_node": "MAIN"},
        }
    }
    response = requests.put("http://localhost:8000/v1/threads/1/state", json=payload)
    print(response.json())

    response = requests.get("http://localhost:8000/v1/threads/1/state")
    print(response.json())
