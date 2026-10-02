"""Accès à la liste des compétitions du site www.ffta.fr.

La page est lue par une simple requête HTTP, sans navigateur.
"""

import os
import sys
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = os.environ.get("FFTA_BASE_URL", "https://www.ffta.fr").rstrip("/")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
}

ARTICLE_SELECTOR = "article.competition_item"


def competitions_url(start_date: date, end_date: date, sort_order: str) -> str:
    """Adresse de la liste (filtres : dep=58, discipline=103, univers=299)."""
    return (
        f"{BASE_URL}/competitions"
        "?search="
        f"&start={start_date.isoformat()}"
        f"&end={end_date.isoformat()}"
        "&dep%5B%5D=58"
        "&discipline=103"
        "&univers=299"
        "&inter=All"
        "&sort_by=start"
        f"&sort_order={sort_order}"
    )


def absolute_url(url: str) -> str:
    """Transforme une adresse relative (/competition/...) en adresse complète."""
    if url and url.startswith("/"):
        return BASE_URL + url
    return url or ""


def _articles_from_html(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select(ARTICLE_SELECTOR)

    # Pagination : seule la première page est lue, comme avec l'ancienne méthode.
    if articles and soup.select_one('a[rel="next"], li.pager__item--next'):
        print("  Remarque : la liste a plusieurs pages, seule la première est lue.")
    return articles


def _fetch_http(url: str) -> list:
    """Lit la page par HTTP. Renvoie la liste des blocs <article> (éventuellement vide)."""
    last_error = "inconnue"
    for attempt in range(1, 4):
        print(f"  Requête HTTP directe : tentative {attempt}/3")
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
        except requests.RequestException as exc:
            last_error = str(exc)[:200]
        else:
            if response.status_code == 200:
                articles = _articles_from_html(response.text)
                if articles:
                    return articles
                preview = " ".join(response.text.split())[:300]
                last_error = f"page reçue sans compétition. Début : {preview}"
            else:
                preview = " ".join(response.text.split())[:200]
                last_error = f"HTTP {response.status_code} : {preview}"

        print(f"  Échec : {last_error}")
        if attempt < 3:
            time.sleep(10 * attempt)

    return []


def fetch_competition_articles(url: str) -> list:
    """Blocs <article class="competition_item"> de la page. Arrête le programme
    avec un message clair si aucune compétition n'a pu être lue."""
    print("Lecture de la liste FFTA...")
    articles = _fetch_http(url)

    if not articles:
        print("ERREUR : aucune compétition trouvée (voir les détails ci-dessus).")
        print("Le RSS ne sera pas remplacé.")
        sys.exit(1)

    print("Compétitions trouvées :", len(articles))
    return articles


def link_with_text(article, wanted_text: str) -> str:
    """Adresse du lien de l'article dont le texte est exactement wanted_text
    (par exemple « Détail » ou « Mandat »)."""
    wanted = wanted_text.lower().strip()
    for link in article.find_all("a"):
        if " ".join(link.stripped_strings).strip().lower() == wanted:
            return absolute_url(link.get("href", ""))
    return ""


def text_of(article, selector: str) -> str:
    """Texte nettoyé de l'élément correspondant au sélecteur, ou chaîne vide."""
    element = article.select_one(selector)
    return " ".join(element.stripped_strings).strip() if element else ""
