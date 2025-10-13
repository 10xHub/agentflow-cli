from pydantic import BaseModel

from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422


class Demo(BaseModel):
    a: int


def test_generate_swagger_responses_basic():
    res = generate_swagger_responses(Demo)
    for code in (HTTP_OK, HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_UNPROCESSABLE_ENTITY):
        assert code in res
    ok = res[HTTP_OK]["model"]
    # Model class should be a pydantic model subclass
    assert hasattr(ok, "model_json_schema")


def test_generate_swagger_responses_pagination():
    res = generate_swagger_responses(Demo, show_pagination=True)
    ok = res[HTTP_OK]["model"]
    assert hasattr(ok, "model_json_schema")
