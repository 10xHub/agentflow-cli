import requests


BASE_URL = "http://localhost:8000"

if __name__ == "__main__":
    print("Starting API tests...\n")

    # Test Checkpointer APIs
    print("=== Checkpointer APIs ===")

    # PUT /v1/threads/{thread_id}/state
    print("Testing PUT /v1/threads/1/state")
    payload = {
        "state": {
            "context_summary": "This is summary",
            "execution_meta": {"current_node": "MAIN"},
        }
    }
    response = requests.put(f"{BASE_URL}/v1/threads/1/state", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/threads/{thread_id}/state
    print("Testing GET /v1/threads/1/state")
    response = requests.get(f"{BASE_URL}/v1/threads/1/state")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # DELETE /v1/threads/{thread_id}/state
    print("Testing DELETE /v1/threads/1/state")
    response = requests.delete(f"{BASE_URL}/v1/threads/1/state")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # POST /v1/threads/{thread_id}/messages
    print("Testing POST /v1/threads/1/messages")
    payload = {
        "messages": [
            {"message_id": "1", "role": "user", "content": "Hello, how are you?"},
            {"message_id": "2", "role": "assistant", "content": "I'm doing well, thank you!"},
        ],
        "metadata": {"source": "test"},
    }
    response = requests.post(f"{BASE_URL}/v1/threads/1/messages", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/threads/{thread_id}/messages
    print("Testing GET /v1/threads/1/messages")
    response = requests.get(f"{BASE_URL}/v1/threads/1/messages")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/threads/{thread_id}/messages/{message_id} (assuming message_id=1)
    print("Testing GET /v1/threads/1/messages/1")
    response = requests.get(f"{BASE_URL}/v1/threads/1/messages/1")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # DELETE /v1/threads/{thread_id}/messages/{message_id}
    print("Testing DELETE /v1/threads/1/messages/1")
    payload = {"config": {}}
    response = requests.delete(f"{BASE_URL}/v1/threads/1/messages/1", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/threads/{thread_id}
    print("Testing GET /v1/threads/1")
    response = requests.get(f"{BASE_URL}/v1/threads/1")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/threads
    print("Testing GET /v1/threads")
    response = requests.get(f"{BASE_URL}/v1/threads")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # DELETE /v1/threads/{thread_id}
    print("Testing DELETE /v1/threads/1")
    payload = {"config": {}}
    response = requests.delete(f"{BASE_URL}/v1/threads/1", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # Test Graph APIs
    print("=== Graph APIs ===")

    # POST /v1/graph/invoke
    print("Testing POST /v1/graph/invoke")
    payload = {
        "messages": [{"role": "user", "content": "Hello world"}],
        "recursion_limit": 25,
        "response_granularity": "low",
        "include_raw": False,
    }
    response = requests.post(f"{BASE_URL}/v1/graph/invoke", json=payload)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # POST /v1/graph/stream (Note: This will stream, but for test we'll just check response)
    print("Testing POST /v1/graph/stream")
    payload = {
        "messages": [{"role": "user", "content": "Stream this"}],
        "recursion_limit": 25,
        "response_granularity": "low",
        "include_raw": False,
    }
    response = requests.post(f"{BASE_URL}/v1/graph/stream", json=payload, stream=True)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                print(f"Stream chunk: {line.decode('utf-8')}")
    else:
        print(f"Response: {response.text}\n")

    # GET /v1/graph
    print("Testing GET /v1/graph")
    response = requests.get(f"{BASE_URL}/v1/graph")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    # GET /v1/graph:StateSchema
    print("Testing GET /v1/graph:StateSchema")
    response = requests.get(f"{BASE_URL}/v1/graph:StateSchema")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}\n")
    except:
        print(f"Response: {response.text}\n")

    print("All API tests completed!")
