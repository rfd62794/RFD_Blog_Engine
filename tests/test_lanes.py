"""
tests/test_lanes.py

Tests for the category -> lane mapping (plan section 4.1).
"""

import pytest

from blog_engine.core.lanes import LANE_CATEGORIES, lane_for


@pytest.mark.parametrize("category", LANE_CATEGORIES["consulting"])
def test_consulting_categories_map_to_consulting(category):
    assert lane_for([category]) == "consulting"


@pytest.mark.parametrize("category", LANE_CATEGORIES["building"])
def test_building_categories_map_to_building(category):
    assert lane_for([category]) == "building"


def test_lane_match_is_case_insensitive():
    assert lane_for(["dev notes"]) == "building"
    assert lane_for(["CONVOSO"]) == "consulting"


def test_first_matching_category_wins():
    assert lane_for(["Misc", "Games", "Convoso"]) == "building"


def test_unknown_category_returns_none():
    assert lane_for(["Uncategorized"]) is None
    assert lane_for(["Not A Lane"]) is None


def test_empty_list_returns_none():
    assert lane_for([]) is None
