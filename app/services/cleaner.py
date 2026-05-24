import re
from bs4 import BeautifulSoup

_NOISE_TAGS = ["script", "style", "nav", "header", "footer", "aside", "iframe",
               "noscript", "form", "button", "input", "meta", "link"]


def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def extract_article_text(raw: str, max_length: int = 2000) -> str:
    if raw and ("<" in raw and ">" in raw):
        text = clean_html(raw)
    else:
        text = re.sub(r"\s+", " ", raw or "").strip()
    return text[:max_length]
