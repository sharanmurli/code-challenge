from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import sys
import re
from typing import List, Dict, Optional


class GoogleCarouselParser:

    """
    This Parser parses Google's Top Carousel block results for Artist - Artworks - type queries.
    For Example - Van Gogh paintings or Michelangelo sculptures.

    Output format (As per the Challenge structure):
    [
        {
            "name": "The Starry Night",
            "extensions": ["1889"],
            "link": "https://www.google.com/search?q=The+Starry+Night",
            "image": "data:image/jpeg;base64,..."
        },
        ...
    ]
    """
    GOOGLE_ORIGIN = "https://www.google.com"

    """
    Reads a local HTML file and returns the parsed carousel items.
    I am using BeautifulSoup for parsing the HTML File (lxml parser).
    """
    def parse_file(self, html_path: str) -> List[Dict]:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        return self.parse_html(html)

    """
    Parses the raw HTML content and extracts artworks information.
    Detects carousel containers dynamically using common selectors
    seen in Artist - Artworks carousels.
    """
    def parse_html(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")

        container = (
            soup.select_one("div[data-attrid*=':works']")
            or soup.select_one("div[data-attrid*='visual_artist:works']")
            or soup.select_one("div[data-attrid*='artworks']")
            or soup.select_one("g-scrolling-carousel")
            or soup.select_one("div[jscontroller='HPVvwb']")
            or soup.select_one("div[jsname='GZq3Ke']")
        )

        if not container:
            print("No carousel container found in HTML.")
            return []

        artworks = []
        for a in container.find_all("a", href=True):
            img = a.find("img")
            if not img:
                continue

            name = (a.get("aria-label") or img.get("alt") or "").strip()
            if not name:
                continue

            year = self.extract_year_from_node(a)
            image = self.find_best_thumbnail(a, img, html)
            link = self.make_absolute_url(a["href"])

            if not link.startswith(self.GOOGLE_ORIGIN):
                continue

            artworks.append({
                "name": name,
                "extensions": [year] if year else [],
                "link": link,
                "image": image
            })

        return artworks

    """
    Looks for a 4 digit year (1500–2099) in the nearby text or attributes.
    This code is used for the 'extensions' array.
    """
    def extract_year_from_node(self, node) -> Optional[str]:
        text = " ".join([
            node.get_text(" ", strip=True),
            node.get("aria-label", ""),
            node.find("img").get("alt", "") if node.find("img") else "",
        ])
        match = re.search(r"(?<!\d)(1[5-9]\d{2}|20\d{2})(?!\d)", text)
        return match.group(1) if match else None

    """
    Converts relative Google search links into full URLs.
    """
    def make_absolute_url(self, href: str) -> str:
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(self.GOOGLE_ORIGIN, href)

    """
    Determines the most suitable embedded image source.
    Checks:
    1. Direct <img src="data:image/...">
    2. Script-embedded base64 (if image ID is referenced)
    3. Closest base64 string near artworks title in HTML
    """
    def find_best_thumbnail(self, a, img, html: str) -> Optional[str]:
        src = (img.get("src") or "").strip()
        if self.is_valid_data_url(src):
            return src

        img_id = (img.get("id") or "").strip()
        if img_id:
            decoded = self.decode_thumbnail_from_script(html, img_id)
            if decoded:
                return decoded

        title = (a.get("aria-label") or img.get("alt") or a.get_text(strip=True)).strip()
        return self.find_closest_data_image(html, title)

    """
    Verifies whether the image source is a real inline base64 image
    and not a 1x1 transparent placeholder.
    """
    def is_valid_data_url(self, url: str) -> bool:
        if not url.startswith("data:image/"):
            return False
        if url.startswith("data:image/gif;base64,R0lGODlhAQABA"):
            return False
        return len(url) > 500

    """
    Some carousels define inline thumbnails inside <script> tags
    with an image ID reference. This regex attempts to capture
    and decode that base64 data.
    """
    def decode_thumbnail_from_script(self, html: str, img_id: str) -> Optional[str]:
        pattern = re.compile(
            rf"var\s*s\s*=\s*'(?P<data>data:image/[^']+)';\s*var\s*i+i\s*=\s*\['{re.escape(img_id)}'\];",
            re.IGNORECASE
        )
        m = pattern.search(html)
        if not m:
            return None

        raw = m.group("data")
        try:
            unescaped = bytes(raw, "ascii").decode("unicode_escape")
            unescaped = bytes(unescaped, "ascii").decode("unicode_escape")
        except Exception:
            unescaped = raw
        return unescaped if self.is_valid_data_url(unescaped) else None

    """
    Fallback: finds the nearest data:image base64 string in HTML
    close to where the artwork title text appears.
    """
    def find_closest_data_image(self, html: str, title: str) -> Optional[str]:
        if not title:
            return None
        title_positions = [m.start() for m in re.finditer(re.escape(title), html, re.IGNORECASE)]
        if not title_positions:
            return None

        data_urls = [
            (m.start(), m.group(0))
            for m in re.finditer(r"data:image/(?:jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=]+", html)
            if self.is_valid_data_url(m.group(0))
        ]
        if not data_urls:
            return None

        anchor = title_positions[0]
        best = min(data_urls, key=lambda x: abs(x[0] - anchor))
        return best[1]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python google_carousel_parser.py <input_html> <output_json>")
        sys.exit(1)

    input_html = sys.argv[1]
    output_json = sys.argv[2]

    parser = GoogleCarouselParser()
    results = parser.parse_file(input_html)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Extracted {len(results)} artworks -> {output_json}")



"""
General Solution :

During research, I observed similar carousel attribute patterns:

[1] kc:/visual_art/visual_artist:works -> Artworks

[2] kc:/book/author:books -> Books

[3] kc:/music/artist:albums -> Albums

[3] kc:/people/person:movies -> Filmography

These are just a few and we will have infinte numbers of queries for different attribute patterns.
A future general parser could detect these attribute types dynamically and adapt extraction logic per category.
"""
