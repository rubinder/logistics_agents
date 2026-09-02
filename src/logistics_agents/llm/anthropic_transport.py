from logistics_agents.llm.types import LLMRequest, RawResponse


class AnthropicTransport:
    """Transport that calls the real Anthropic Messages API via structured outputs."""

    def __init__(self, client=None):
        self._client = client

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def __call__(self, request: LLMRequest) -> RawResponse:
        response = self._get_client().messages.parse(
            model=request.model,
            max_tokens=request.max_tokens,
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
            output_format=request.output_type,
        )
        if response.parsed_output is None:
            raise RuntimeError(
                f"Model returned no structured output "
                f"(stop_reason={getattr(response, 'stop_reason', None)!r})"
            )
        usage = response.usage
        return RawResponse(
            output_json=response.parsed_output.model_dump_json(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=request.model,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
