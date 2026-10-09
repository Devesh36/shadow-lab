import json
from types import SimpleNamespace as NS

import pytest

from packages.agents.llm import prioritize
from packages.core.models import Settings


def provider(arguments, name="select_tests"):
    async def completion(**kwargs):
        assert kwargs["tools"][0]["function"]["name"] == "select_tests"
        assert kwargs["num_retries"] == 0 and kwargs["max_tokens"] == 1000
        return NS(choices=[NS(message=NS(tool_calls=[NS(function=NS(name=name, arguments=json.dumps(arguments)))]))])
    return completion


async def test_typed_prioritization():
    assert await prioritize([{"title": "a"}, {"title": "b"}], Settings(), provider({"indices": [1, 0, 1]})) == [{"title": "b"}, {"title": "a"}]


@pytest.mark.parametrize("payload", [{"indices": [999]}, {"indices": [-1]}, {"indices": [True]}, {"indices": [0], "shell": "whoami"}])
async def test_model_cannot_create_arbitrary_actions(payload):
    with pytest.raises(ValueError):
        await prioritize([{"title": "a"}], Settings(), provider(payload))
