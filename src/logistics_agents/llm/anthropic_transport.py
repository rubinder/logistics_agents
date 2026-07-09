from logistics_agents.llm.types import LLMRequest, RawResponse


class AnthropicTransport:
    """Transport that calls the real Anthropic Messages API via structured outputs."""

    def __init__(self, client=None, max_tokens: int = 4096):
        self._client = client
        self._max_tokens = max_tokens

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def __call__(self, request: LLMRequest) -> RawResponse:
        response = self._get_client().messages.parse(
            model=request.model,
            max_tokens=self._max_tokens,
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
            output_format=request.output_type,
        )
        return RawResponse(
            output_json=response.parsed_output.model_dump_json(),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=request.model,
        )
