
"""Accès à la liste des compétitions du site www.ffta.fr.

La page est lue par une simple requête HTTP, sans navigateur.
Récupération des liens Détail et Mandat PDF de l'extranet FFTA.
"""

import os
import sys
import time
from datetime import date

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = os.environ.get(
    "FFTA_BASE_URL", "https://www.ffta.fr"
).rstrip("/")

EXTRANET_MANDAT_PREFIX = (
    "https://extranet.ffta.fr/medias/documents_epreuves/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) "
        "Gecko/20100101 Firefox/156.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
}

ARTICLE_SELECTOR = "article.competition_item"


def competitions_url(
    start_date: date,
    end_date: date,
    sort_order: str
) -> str:
    """Adresse de la liste : dep=58, discipline=103, univers=299."""
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


def absolute_url(url: str, base_url: str = BASE_URL) -> str:
    """Transforme une URL relative en URL absolue."""
    if not url:
        return ""

    return urljoin(base_url.rstrip("/") + "/", url.strip())


def _articles_from_html(html: str) -> list:
    """Extrait les blocs de compétition de la page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select(ARTICLE_SELECTOR)

    # Pagination : seule la première page est lue.
    if articles and soup.select_one(
        'a[rel="next"], li.pager__item--next'
    ):
        print(
            "  Remarque : la liste a plusieurs pages, "
            "seule la première est lue."
        )

    return articles


def _fetch_http(url: str) -> list:
    """Lit la page par HTTP et renvoie les blocs de compétition."""
    last_error = "inconnue"

    for attempt in range(1, 4):
        print(f"  Requête HTTP directe : tentative {attempt}/3")

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=60,
            )
        except requests.RequestException as exc:
            last_error = str(exc)[:200]
        else:
            if response.status_code == 200:
                articles = _articles_from_html(response.text)

                if articles:
                    return articles

                preview = " ".join(response.text.split())[:300]
                last_error = (
                    "page reçue sans compétition. Début : "
                    f"{preview}"
                )
            else:
                preview = " ".join(response.text.split())[:200]
                last_error = (
                    f"HTTP {response.status_code} : {preview}"
                )

        print(f"  Échec : {last_error}")

        if attempt < 3:
            time.sleep(10 * attempt)

    return []


def fetch_competition_articles(url: str) -> list:
    """Récupère les blocs de compétition ou arrête le programme."""
    print("Lecture de la liste FFTA...")
    articles = _fetch_http(url)

    if not articles:
        print(
            "ERREUR : aucune compétition trouvée "
            "(voir les détails ci-dessus)."
        )
        print("Le RSS ne sera pas remplacé.")
        sys.exit(1)

    print("Compétitions trouvées :", len(articles))
    return articles


def link_with_text(article, wanted_text: str) -> str:
    """Retrouve un lien par son texte exact, par exemple Détail ou Mandat."""
    wanted = wanted_text.lower().strip()

    for link in article.find_all("a", href=True):
        text = " ".join(link.stripped_strings).strip().lower()

        if text == wanted:
            return absolute_url(link["href"])

    return ""


def find_mandat_link(article) -> str:
    """Retrouve le PDF du mandat, même si le texte du lien a changé.

    Priorité :
    1. Lien PDF de l'extranet FFTA dans le bloc de compétition.
    2. Lien dont le texte contient « mandat ».
    3. Lien PDF situé dans le bloc de compétition et contenant
       le chemin documents_epreuves.
    """

    links = article.find_all("a", href=True)

    # Première priorité : le chemin connu des PDF de mandats.
    for link in links:
        href = absolute_url(link.get("href", ""))
        parsed = urlparse(href)
        path = parsed.path.lower()
        host = (parsed.hostname or "").lower()

        if (
            host == "extranet.ffta.fr"
            and path.startswith("/medias/documents_epreuves/")
            and path.endswith(".pdf")
        ):
            return href

    # Deuxième priorité : un lien explicitement nommé « mandat ».
    for link in links:
        text = " ".join(link.stripped_strings).strip().lower()
        href = absolute_url(link.get("href", ""))

        if "mandat" in text and href:
            return href

    # Troisième priorité : un PDF de documents d'épreuves
    # sur un autre hôte, si le site a changé de domaine.
    for link in links:
        href = absolute_url(link.get("href", ""))
        parsed = urlparse(href)

        if (
            "/medias/documents_epreuves/" in parsed.path.lower()
            and parsed.path.lower().endswith(".pdf")
        ):
            return href

    return ""


def text_of(article, selector: str) -> str:
    """Texte nettoyé de l'élément correspondant au sélecteur."""
    element = article.select_one(selector)

    return (
        " ".join(element.stripped_strings).strip()
        if element
        else ""
    )
