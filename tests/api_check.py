import requests
from datetime import datetime
from typing import Any


BASE_URL = "http://localhost:8000"


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class TestResult:
    """Store test results"""

    def __init__(self):
        self.tests = []
        self.total = 0
        self.passed = 0
        self.failed = 0

    def add(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        expected: int,
        response_time: float,
        error: str = None,
    ):
        self.total += 1
        is_pass = status_code == expected
        if is_pass:
            self.passed += 1
        else:
            self.failed += 1

        self.tests.append(
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "expected": expected,
                "passed": is_pass,
                "response_time": response_time,
                "error": error,
            }
        )

    def print_summary(self):
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}\n")

        # Overall stats
        pass_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"{Colors.BOLD}Total Tests:{Colors.RESET} {self.total}")
        print(f"{Colors.BOLD}{Colors.GREEN}Passed:{Colors.RESET} {self.passed}")
        print(f"{Colors.BOLD}{Colors.RED}Failed:{Colors.RESET} {self.failed}")
        print(f"{Colors.BOLD}Pass Rate:{Colors.RESET} {pass_rate:.1f}%\n")

        # Detailed results
        print(f"{Colors.BOLD}DETAILED RESULTS:{Colors.RESET}\n")

        for i, test in enumerate(self.tests, 1):
            status_icon = (
                f"{Colors.GREEN}✓{Colors.RESET}"
                if test["passed"]
                else f"{Colors.RED}✗{Colors.RESET}"
            )
            status_text = (
                f"{Colors.GREEN}PASS{Colors.RESET}"
                if test["passed"]
                else f"{Colors.RED}FAIL{Colors.RESET}"
            )

            print(
                f"{status_icon} Test #{i}: {Colors.BOLD}{test['method']} {test['endpoint']}{Colors.RESET}"
            )
            print(
                f"   Status: {status_text} (Expected: {test['expected']}, Got: {test['status_code']})"
            )
            print(f"   Response Time: {test['response_time']:.3f}s")

            if not test["passed"] and test.get("error"):
                print(f"   {Colors.RED}Error: {test['error']}{Colors.RESET}")
            print()

        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}\n")


def test_endpoint(
    method: str,
    url: str,
    expected_status: int,
    results: TestResult,
    payload: dict = None,
    stream: bool = False,
    description: str = "",
):
    """Test a single endpoint and record results"""
    endpoint = url.replace(BASE_URL, "")
    print(f"{Colors.CYAN}Testing {method} {endpoint}{Colors.RESET}")
    if description:
        print(f"  {Colors.MAGENTA}Description: {description}{Colors.RESET}")

    start_time = datetime.now()
    error_msg = None

    try:
        if method == "GET":
            response = requests.get(url, stream=stream)
        elif method == "POST":
            response = requests.post(url, json=payload, stream=stream)
        elif method == "PUT":
            response = requests.put(url, json=payload)
        elif method == "DELETE":
            response = requests.delete(url, json=payload)
        else:
            raise ValueError(f"Unsupported method: {method}")

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()

        status_code = response.status_code

        if stream and status_code == 200:
            # For streaming endpoints, just consume the stream
            for line in response.iter_lines():
                if line:
                    pass  # Just consume the stream

        # Try to get error message from response
        if status_code != expected_status:
            try:
                resp_json = response.json()
                if "error" in resp_json:
                    error_msg = resp_json["error"].get("message", str(resp_json["error"]))
            except:
                error_msg = response.text[:200]

        results.add(endpoint, method, status_code, expected_status, response_time, error_msg)

        status_color = Colors.GREEN if status_code == expected_status else Colors.RED
        print(f"  {status_color}Status: {status_code}{Colors.RESET} (Expected: {expected_status})")
        print(f"  Response Time: {response_time:.3f}s")

        if error_msg:
            print(f"  {Colors.RED}Error: {error_msg}{Colors.RESET}")

        print()

    except Exception as e:
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        error_msg = str(e)
        results.add(endpoint, method, 0, expected_status, response_time, error_msg)
        print(f"  {Colors.RED}Exception: {error_msg}{Colors.RESET}\n")


if __name__ == "__main__":
    results = TestResult()

    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.BLUE}API TEST SUITE - Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")
    print(f"{Colors.BOLD}Base URL:{Colors.RESET} {BASE_URL}\n")

    # Test Graph APIs
    print(f"{Colors.BOLD}{Colors.YELLOW}=== GRAPH APIs ==={Colors.RESET}\n")

    # POST /v1/graph/invoke
    test_endpoint(
        "POST",
        f"{BASE_URL}/v1/graph/invoke",
        200,
        results,
        payload={
            "messages": [{"role": "user", "content": "Hello world"}],
            "recursion_limit": 25,
            "response_granularity": "low",
            "include_raw": False,
            "config": {
                "thread_id": "test_thread_1",
            },
        },
        description="Invoke graph with a simple message",
    )

    # POST /v1/graph/stream
    test_endpoint(
        "POST",
        f"{BASE_URL}/v1/graph/stream",
        200,
        results,
        payload={
            "messages": [{"role": "user", "content": "Stream this"}],
            "recursion_limit": 25,
            "response_granularity": "low",
            "include_raw": False,
        },
        stream=True,
        description="Stream graph execution",
    )

    # GET /v1/graph
    test_endpoint(
        "GET", f"{BASE_URL}/v1/graph", 200, results, description="Get graph structure information"
    )

    # GET /v1/graph:StateSchema
    test_endpoint(
        "GET",
        f"{BASE_URL}/v1/graph:StateSchema",
        200,
        results,
        description="Get graph state schema",
    )

    # Test Checkpointer APIs
    print(f"{Colors.BOLD}{Colors.YELLOW}=== CHECKPOINTER APIs ==={Colors.RESET}\n")

    # PUT /v1/threads/test_thread_2/state
    test_endpoint(
        "PUT",
        f"{BASE_URL}/v1/threads/test_thread_2/state",
        200,
        results,
        payload={
            "state": {
                "context_summary": "This is summary",
                "execution_meta": {"current_node": "MAIN"},
            }
        },
        description="Put state for a thread",
    )

    # GET /v1/threads/test_thread_2/state
    test_endpoint(
        "GET",
        f"{BASE_URL}/v1/threads/test_thread_2/state",
        200,
        results,
        description="Get state for a thread",
    )

    # DELETE /v1/threads/test_thread_2/state
    test_endpoint(
        "DELETE",
        f"{BASE_URL}/v1/threads/test_thread_2/state",
        200,
        results,
        description="Clear state for a thread",
    )

    # POST /v1/threads/test_thread_3/messages
    test_endpoint(
        "POST",
        f"{BASE_URL}/v1/threads/test_thread_3/messages",
        200,
        results,
        payload={
            "messages": [
                {
                    "message_id": "msg_1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello, how are you?"}],
                    "timestamp": datetime.now().timestamp(),
                    "metadata": {},
                },
                {
                    "message_id": "msg_2",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "I'm doing well, thank you!"}],
                    "timestamp": datetime.now().timestamp(),
                    "metadata": {},
                },
            ],
            "metadata": {"source": "test"},
        },
        description="Post messages to a thread",
    )

    # GET /v1/threads/test_thread_3/messages
    test_endpoint(
        "GET",
        f"{BASE_URL}/v1/threads/test_thread_3/messages",
        200,
        results,
        description="List messages for a thread",
    )

    # GET /v1/threads/test_thread_3/messages/msg_1
    test_endpoint(
        "GET",
        f"{BASE_URL}/v1/threads/test_thread_3/messages/msg_1",
        200,
        results,
        description="Get a specific message",
    )

    # DELETE /v1/threads/test_thread_3/messages/msg_1
    test_endpoint(
        "DELETE",
        f"{BASE_URL}/v1/threads/test_thread_3/messages/msg_1",
        200,
        results,
        payload={"config": {}},
        description="Delete a specific message",
    )

    # GET /v1/threads/test_thread_3
    test_endpoint(
        "GET",
        f"{BASE_URL}/v1/threads/test_thread_3",
        200,
        results,
        description="Get thread information",
    )

    # GET /v1/threads
    test_endpoint("GET", f"{BASE_URL}/v1/threads", 200, results, description="List all threads")

    # DELETE /v1/threads/test_thread_3
    test_endpoint(
        "DELETE",
        f"{BASE_URL}/v1/threads/test_thread_3",
        200,
        results,
        payload={"config": {}},
        description="Delete a thread",
    )

    # Print summary
    results.print_summary()
