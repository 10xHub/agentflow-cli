from agentflow.state import Message


if __name__ == "__main__":
    res = Message.text_message("Hello")
    res_str = res.model_dump_json()
    print(res_str)

    restored = Message.model_validate_json(res_str)
    print(restored)
