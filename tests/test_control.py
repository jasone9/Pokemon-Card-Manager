import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from pokemon_card_manager import control

CARD = {"name": "Pikachu", "setName": "Base Set", "prices": {"market": 0}}


def response(payload):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


class CardLookupTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {control.API_KEY_ENV: "test-key"})
        environment.start()
        self.addCleanup(environment.stop)
        http = patch.object(control, "urlopen")
        self.http = http.start()
        self.addCleanup(http.stop)

    def test_supported_payload_shapes(self):
        for payload in (
            CARD, [CARD], {"data": [CARD]}, {"data": {"cards": [CARD]}},
            {"cards": [CARD]}, {"results": [CARD]}, {"items": [CARD]},
            {"data": CARD}, {"data": [], "results": [CARD]}, [None, CARD],
        ):
            with self.subTest(payload=payload):
                self.assertEqual(control._extract_first_card(payload), CARD)
        for payload in (None, [], {}, {"data": []}, "unexpected", [42]):
            with self.subTest(payload=payload):
                self.assertIsNone(control._extract_first_card(payload))

    def test_name_search_sends_authentication_encoded_query_and_timeout(self):
        self.http.return_value = response({"data": [CARD]})
        self.assertEqual(control.get_card_info("  Mr. Mime & friends  "), CARD)
        request = self.http.call_args.args[0]
        params = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(params, {"search": ["Mr. Mime & friends"], "includeHistory": ["false"], "limit": ["1"]})
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(self.http.call_args.kwargs["timeout"], 10)
        self.http.assert_called_once()

    def test_numeric_id_falls_back_to_name_only_after_an_empty_result(self):
        self.http.side_effect = [response({"data": []}), response({"results": [CARD]})]
        self.assertEqual(control.get_card_info("88086"), CARD)
        params = [parse_qs(urlparse(call.args[0].full_url).query) for call in self.http.call_args_list]
        self.assertEqual(params[0]["tcgPlayerId"], ["88086"])
        self.assertEqual(params[1]["search"], ["88086"])

    def test_name_fallback_and_no_match(self):
        self.http.side_effect = [response({"data": []}), response({"data": []})]
        self.assertIsNone(control.get_card_info("Unknown"))
        params = [parse_qs(urlparse(call.args[0].full_url).query) for call in self.http.call_args_list]
        self.assertEqual(params[0]["search"], ["Unknown"])
        self.assertEqual(params[1]["tcgPlayerId"], ["Unknown"])

    def test_empty_query_does_not_require_a_key_or_use_the_network(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(control.get_card_info("  "))
            self.assertIsNone(control.get_card_info(None))
        self.http.assert_not_called()

    def test_missing_key_has_a_configuration_error_without_network_access(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(control.CardLookupError, control.API_KEY_ENV):
                control.get_card_info("Pikachu")
        self.http.assert_not_called()

    def test_http_error_does_not_expose_response_body_or_retry(self):
        self.http.side_effect = HTTPError(control.BASE_URL, 401, "Unauthorized", {}, None)
        with self.assertRaisesRegex(control.CardLookupError, "HTTP 401") as caught:
            control.get_card_info("Pikachu")
        self.assertNotIn("test-key", str(caught.exception))
        self.http.assert_called_once()

    def test_network_failure_and_timeout_are_reported(self):
        for error in (URLError("offline"), TimeoutError("timed out")):
            with self.subTest(error=error):
                self.http.reset_mock()
                self.http.side_effect = error
                with self.assertRaisesRegex(control.CardLookupError, "Unable to reach"):
                    control.get_card_info("Pikachu")
                self.http.assert_called_once()

    def test_invalid_json_is_reported(self):
        self.http.return_value = io.BytesIO(b"not JSON")
        with self.assertRaisesRegex(control.CardLookupError, "invalid JSON"):
            control.get_card_info("Pikachu")
        self.http.assert_called_once()


if __name__ == "__main__":
    unittest.main()
