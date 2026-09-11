import os
import unittest
from unittest.mock import patch

from src.config import (
    ConfigurationError,
    call_with_key_rotation,
    next_openai_key,
    reset_key_pool_for_tests,
)


class RateLimitError(Exception):
    status_code = 429


class QuotaError(Exception):
    code = "insufficient_quota"


class OpenAIKeyPoolTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_key_pool_for_tests()
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        reset_key_pool_for_tests()

    def test_repeated_calls_keep_the_current_key(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="two", OPENAI_API_KEY_3="three")
        self.assertEqual([next_openai_key() for _ in range(3)], ["one", "one", "one"])

    def test_skips_empty_keys(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="", OPENAI_API_KEY_3="three")
        self.assertEqual(next_openai_key(), "one")
        self.assertEqual(next_openai_key(RateLimitError()), "three")

    def test_rate_limit_fails_over_and_stays_on_new_key(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="two")
        self.assertEqual(next_openai_key(), "one")
        self.assertEqual(next_openai_key(RateLimitError()), "two")
        self.assertEqual(next_openai_key(), "two")

    def test_wraps_after_the_last_key(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="two")
        self.assertEqual(next_openai_key(RateLimitError()), "two")
        self.assertEqual(next_openai_key(QuotaError()), "one")

    def test_raises_without_configured_key(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "No OpenAI API key"):
            next_openai_key()

    def test_call_with_key_rotation_succeeds_first_try(self) -> None:
        os.environ["OPENAI_API_KEY"] = "one"
        self.assertEqual(call_with_key_rotation(lambda key: f"used-{key}"), "used-one")

    def test_call_with_key_rotation_succeeds_after_failover(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="two")
        calls: list[str] = []

        def request(key: str) -> str:
            calls.append(key)
            if len(calls) == 1:
                raise RateLimitError()
            return "ok"

        self.assertEqual(call_with_key_rotation(request), "ok")
        self.assertEqual(calls, ["one", "two"])

    def test_call_with_key_rotation_reraises_after_exhaustion(self) -> None:
        os.environ.update(OPENAI_API_KEY="one", OPENAI_API_KEY_2="two")
        with self.assertRaises(RateLimitError):
            call_with_key_rotation(lambda _: (_ for _ in ()).throw(RateLimitError()))


if __name__ == "__main__":
    unittest.main()
