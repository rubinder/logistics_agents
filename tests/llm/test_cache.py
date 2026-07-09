import pytest

from logistics_agents.llm.cache import CacheMissError, RecordReplayCache, request_key


def test_key_stable_and_input_sensitive(make_request):
    assert request_key(make_request()) == request_key(make_request())
    assert request_key(make_request(model="claude-opus-4-8")) != request_key(make_request(model="claude-haiku-4-5"))
    assert request_key(make_request(user="a")) != request_key(make_request(user="b"))


def test_live_records_then_replay_reads(make_request, fake_transport_factory, tmp_path):
    transport, calls = fake_transport_factory(label="positive")
    req = make_request()

    live = RecordReplayCache(transport, mode="live", fixtures_dir=tmp_path)
    recorded = live(req)
    assert len(calls) == 1
    assert (tmp_path / f"{request_key(req)}.json").exists()

    # A fresh transport that would explode if called proves replay does not call through.
    def exploding(_request):
        raise AssertionError("replay must not call the transport")

    replay = RecordReplayCache(exploding, mode="replay", fixtures_dir=tmp_path)
    replayed = replay(req)
    assert replayed == recorded


def test_replay_miss_raises(make_request, tmp_path):
    def unused(_request):
        raise AssertionError("should not be called")

    replay = RecordReplayCache(unused, mode="replay", fixtures_dir=tmp_path)
    with pytest.raises(CacheMissError):
        replay(make_request())


def test_key_varies_by_max_tokens(make_request):
    import dataclasses

    a = make_request()
    b = dataclasses.replace(a, max_tokens=a.max_tokens + 1)
    assert request_key(a) != request_key(b)


def test_invalid_mode_raises(make_request, fake_transport_factory, tmp_path):
    transport, _ = fake_transport_factory()
    with pytest.raises(ValueError):
        RecordReplayCache(transport, mode="bogus", fixtures_dir=tmp_path)
