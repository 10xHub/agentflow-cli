"""Rate-limit bucket derivation (audit H5).

The headline bug: with `trusted_proxy_headers: true`, the key came from
`X-Forwarded-For.split(",")[0]` -- the LEFTMOST entry, which the caller controls
outright. Sending a different value on every request minted a fresh bucket each
time, so the rate limit could be bypassed entirely.
"""

from types import SimpleNamespace

import pytest

from agentflow_cli.src.app.core.config.graph_config import RateLimitConfig
from agentflow_cli.src.app.core.middleware.rate_limit.keying import client_key_for


def _cfg(**overrides) -> RateLimitConfig:
    base = {
        "enabled": True,
        "requests": 100,
        "window": 60,
        "by": "ip",
        "backend": "redis",
        "redis_url": None,
        "redis_prefix": "p",
        "exclude_paths": (),
        "trusted_proxy_headers": True,
        "trusted_proxy_hops": 1,
        "fail_open": False,
    }
    base.update(overrides)
    return RateLimitConfig(**base)


def _conn(xff: str | None = None, peer: str = "10.0.0.9", user=None):
    return SimpleNamespace(
        headers={"X-Forwarded-For": xff} if xff else {},
        client=SimpleNamespace(host=peer),
        state=SimpleNamespace(user=user),
    )


class TestForwardedForSpoofing:
    def test_forged_leading_entries_cannot_mint_new_buckets(self):
        """The bypass: forge a different XFF per request, never get limited."""
        cfg = _cfg()
        # Our proxy appends the true peer on the right; everything left is forged.
        keys = {
            client_key_for(_conn(f"{forged}, 203.0.113.7"), cfg)
            for forged in ("1.1.1.1", "2.2.2.2", "3.3.3.3")
        }
        # All must collapse to the SAME bucket -- the real peer.
        assert keys == {"203.0.113.7"}

    def test_uses_nth_from_right_for_multiple_trusted_hops(self):
        # LB -> nginx -> app: the client is 2 back from the right.
        cfg = _cfg(trusted_proxy_hops=2)
        key = client_key_for(_conn("1.1.1.1, 203.0.113.7, 10.0.0.2"), cfg)
        assert key == "203.0.113.7"

    def test_short_header_is_not_trusted(self):
        # Fewer entries than our infrastructure should have appended -> ignore it
        # and fall back to the real peer address.
        cfg = _cfg(trusted_proxy_hops=2)
        assert client_key_for(_conn("1.1.1.1"), cfg) == "10.0.0.9"

    def test_header_ignored_entirely_when_not_trusted(self):
        cfg = _cfg(trusted_proxy_headers=False)
        assert client_key_for(_conn("1.1.1.1, 203.0.113.7"), cfg) == "10.0.0.9"


class TestByUser:
    def test_authenticated_user_gets_own_bucket(self):
        cfg = _cfg(by="user")
        key = client_key_for(_conn(user={"user_id": "u42"}), cfg)
        assert key == "user:u42"

    def test_two_users_do_not_share_a_bucket(self):
        cfg = _cfg(by="user")
        a = client_key_for(_conn(user={"user_id": "a"}), cfg)
        b = client_key_for(_conn(user={"user_id": "b"}), cfg)
        assert a != b

    def test_anonymous_falls_back_to_ip_not_one_shared_bucket(self):
        # Otherwise a single anonymous caller could exhaust the bucket for everyone.
        cfg = _cfg(by="user")
        key = client_key_for(_conn("1.1.1.1, 203.0.113.7", user=None), cfg)
        assert key == "ip:203.0.113.7"


class TestConfigValidation:
    def test_by_user_is_accepted(self):
        cfg = RateLimitConfig.from_dict({"by": "user", "backend": "redis"})
        assert cfg.by == "user"

    def test_invalid_by_rejected(self):
        with pytest.raises(ValueError, match="rate_limit.by"):
            RateLimitConfig.from_dict({"by": "nonsense"})

    def test_zero_proxy_hops_rejected(self):
        with pytest.raises(ValueError, match="trusted_proxy_hops"):
            RateLimitConfig.from_dict({"trusted_proxy_hops": 0})

    def test_global_still_supported(self):
        cfg = _cfg(by="global")
        assert client_key_for(_conn(), cfg) == "__global__"
