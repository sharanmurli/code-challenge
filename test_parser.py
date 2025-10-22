
from pathlib import Path
from google_carousel_parser import GoogleCarouselParser
import json
import pytest

@pytest.mark.parametrize(
    """
    The HTML Files for the test:
    [1] Van Gogh Paintings - Main Challenge
    [2] Additional Test 1
    [3] Additional Test 2
    """


    "html_file, expected_file",
    [
        ("files/van-gogh-paintings.html", "files/expected-array.json"),  
        ("files/picasso-artworks.html", None),                          
        ("files/michelangelo-scupltures.html", None),                   
    ],
)
def test_artist_to_artworks_carousels(html_file, expected_file):
    """Generic test for Artist - Artworks-type Google carousels."""
    parser = GoogleCarouselParser()
    result = parser.parse_file(html_file)
    results = result["results"] if isinstance(result, dict) else result

    """Basic structure validation"""
    assert isinstance(results, list), f"Output must be list for {html_file}"
    assert len(results) > 0, f"No artworks found in {html_file}"

    for item in results:
        assert set(item.keys()) == {"name", "extensions", "link", "image"}
        assert item["name"], "Missing name"
        assert isinstance(item["extensions"], list)
        assert item["link"].startswith("https://"), f"Invalid link: {item['link']}"


    """Check expected JSON (only for Van Gogh Paintings)"""
    if expected_file:
        with open(expected_file, "r", encoding="utf-8") as f:
            expected = json.load(f)
        expected = expected.get("artworks", expected)

        result_names = {r["name"] for r in results}
        missing = [e["name"] for e in expected if e["name"] not in result_names]
        assert not missing, f"Missing artworks: {missing}"
