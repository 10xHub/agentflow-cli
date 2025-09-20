import requests


BASE_URL = "http://localhost:8000"


if __name__ == "__main__":
    print("Testing POST /v1/graph/invoke")
    payload = {
        "messages": [{"role": "user", "content": "Hello world"}],
        "recursion_limit": 25,
        "response_granularity": "low",
        "include_raw": False,
        "config": {
            "thread_id": 1,
        },
    }
    response = requests.post(f"{BASE_URL}/v1/graph/invoke", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")
