"""Tests for library.loader — parse_tags() function."""

import pytest

from library.loader import parse_tags


class TestParseTags:
    """Tests for the parse_tags() tag string parser."""

    # --- valid inputs ---

    def test_single_tag_default_weight(self):
        assert parse_tags("louvor") == {"louvor": 3}

    def test_single_tag_explicit_weight(self):
        assert parse_tags("louvor(5)") == {"louvor": 5}

    def test_multiple_tags_mixed_weights(self):
        result = parse_tags("louvor(5),prelúdio")
        assert result == {"louvor": 5, "prelúdio": 3}

    def test_multiple_tags_all_weighted(self):
        result = parse_tags("louvor(4),saudação(2),ofertório(1)")
        assert result == {"louvor": 4, "saudação": 2, "ofertório": 1}

    def test_weight_zero(self):
        assert parse_tags("louvor(0)") == {"louvor": 0}

    def test_weight_ten(self):
        assert parse_tags("louvor(10)") == {"louvor": 10}

    # --- edge cases ---

    def test_empty_string(self):
        assert parse_tags("") == {}

    def test_whitespace_only(self):
        assert parse_tags("   ") == {}

    def test_trailing_comma(self):
        result = parse_tags("louvor,")
        assert result == {"louvor": 3}

    def test_leading_comma(self):
        result = parse_tags(",louvor")
        assert result == {"louvor": 3}

    def test_spaces_around_tags(self):
        result = parse_tags(" louvor , prelúdio(5) ")
        assert result == {"louvor": 3, "prelúdio": 5}

    def test_duplicate_tag_last_wins(self):
        result = parse_tags("louvor(2),louvor(7)")
        assert result == {"louvor": 7}

    # --- malformed inputs ---

    def test_non_numeric_weight_treated_as_tag_name(self):
        # "louvor(abc)" doesn't match the regex r"^(.+?)\((\d+)\)$"
        # so the whole string becomes the tag name
        result = parse_tags("louvor(abc)")
        assert result == {"louvor(abc)": 3}

    @pytest.mark.parametrize(
        "tags_str, expected",
        [
            ("prelúdio,louvor(4),poslúdio", {"prelúdio": 3, "louvor": 4, "poslúdio": 3}),
            ("crianças", {"crianças": 1} if False else {"crianças": 3}),
            ("saudação(4),poslúdio(2)", {"saudação": 4, "poslúdio": 2}),
        ],
    )
    def test_parametrized_real_world_examples(self, tags_str, expected):
        assert parse_tags(tags_str) == expected
