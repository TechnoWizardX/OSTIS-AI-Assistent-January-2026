import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import network


class EndpointTests(unittest.TestCase):
    def test_https_url_uses_port_443(self):
        self.assertEqual(network._endpoint("https://1.1.1.1"), ("1.1.1.1", 443))

    def test_http_url_uses_port_80(self):
        self.assertEqual(network._endpoint("http://example.com"), ("example.com", 80))

    def test_explicit_port_is_kept(self):
        self.assertEqual(
            network._endpoint("https://example.com:8443/health"),
            ("example.com", 8443),
        )

    def test_bare_host_defaults_to_https(self):
        self.assertEqual(network._endpoint("1.1.1.1"), ("1.1.1.1", 443))


class HasInternetTests(unittest.TestCase):
    def setUp(self):
        network.clear_cache()

    def tearDown(self):
        network.clear_cache()

    @staticmethod
    def _connect_mock():
        mock = MagicMock()
        mock.return_value.__enter__.return_value = MagicMock()
        return mock

    def test_reachable_host_returns_true(self):
        connect = self._connect_mock()
        with patch.object(network.socket, "create_connection", connect):
            self.assertTrue(network.has_internet())

        connect.assert_called_once_with(
            ("1.1.1.1", 443), timeout=network._DEFAULT_TIMEOUT
        )

    def test_unreachable_host_returns_false(self):
        with patch.object(
            network.socket, "create_connection", side_effect=OSError("offline")
        ):
            self.assertFalse(network.has_internet())

    def test_result_is_cached_between_calls(self):
        connect = self._connect_mock()
        with patch.object(network.socket, "create_connection", connect):
            first = network.has_internet()
            second = network.has_internet()

        self.assertTrue(first)
        self.assertTrue(second)
        connect.assert_called_once()

    def test_expired_cache_is_probed_again(self):
        connect = self._connect_mock()
        with (
            patch.object(network.socket, "create_connection", connect),
            patch.object(network, "_CACHE_TTL", 0.0),
        ):
            network.has_internet()
            network.has_internet()

        self.assertEqual(connect.call_count, 2)

    def test_clear_cache_forces_new_probe(self):
        connect = self._connect_mock()
        with patch.object(network.socket, "create_connection", connect):
            network.has_internet()
            network.clear_cache()
            network.has_internet()

        self.assertEqual(connect.call_count, 2)


if __name__ == "__main__":
    unittest.main()
