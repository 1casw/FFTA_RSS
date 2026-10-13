"""Flux RSS des résultats de compétitions FFTA (12 mois glissants)."""

import sys
from datetime import date, timedelta, timezone
from email.utils import parsedate_to_datetime, format_datetime
from urllib.request import Request, urlopen
from xml.etree.ElementTree import Element, ElementTree, SubElement

from ffta_site import (
    absolute_url,
    competitions_url,
    fetch_competition_articles,
    text_of,
)

OUTPUT_FILE = "FFTA_Resultats_Competitions.xml"


def recuperer_last_modified(url_pdf):
    """Récupère la date Last-Modified d'un PDF et la formate pour le RSS."""
    if not url_pdf:
        return None

    requete = Request(
        url_pdf,
        method="HEAD",
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urlopen(requete, timeout=10) as reponse:
            date_http = reponse.headers.get("Last-Modified")

        if not date_http:
            print("  Last-Modified absent :", url_pdf)
            return None

        date_modification = parsedate_to_datetime(date_http)

        if date_modification.tzinfo is None:
            date_modification = date_modification.replace(
                tzinfo=timezone.utc
            )

        return format_datetime(
            date_modification.astimezone(timezone.utc),
            usegmt=True,
        )

    except Exception as erreur:
        print(
            "  Impossible de récupérer Last-Modified :",
            url_pdf,
            "-",
            erreur,
        )
        return None


end_date = date.today()
start_date = end_date - timedelta(days=365)
url = competitions_url(start_date, end_date, sort_order="DESC")

print("URL FFTA utilisée :")
print(url)
print()


# --- Lecture des compétitions -----------------------------------------------

competitions = []
articles = fetch_competition_articles(url)

for article in articles:
    title = text_of(article, ".competition_item__title")
    event_date = text_of(article, ".competition_item__dates")

    button = article.select_one("a.competition_item__results_btn")
    link = absolute_url(button.get("href", "")) if button else ""

    # Une compétition sans titre ou sans lien de résultats est ignorée.
    if title and link:
        print("Lecture du PDF :", title)

        date_publication = recuperer_last_modified(link)

        competitions.append(
            {
                "title": title,
                "date": event_date,
                "link": link,
                "date_publication": date_publication,
            }
        )

print()
print(
    "Compétitions avec titre + lien :",
    len(competitions),
    "sur",
    len(articles),
)

if not competitions:
    print()
    print("ERREUR : aucune compétition exploitable.")
    print("Le RSS ne sera pas remplacé.")
    sys.exit(1)

print()
print("Compétitions qui seront placées dans le RSS :")
print()

for competition in competitions:
    print("-", competition["title"])
    print("  Date :", competition["date"] or "non disponible")
    print("  PDF :", competition["link"])
    print(
        "  Date de publication :",
        competition["date_publication"] or "non disponible",
    )


# --- Création du RSS ---------------------------------------------------------

rss = Element("rss", {"version": "2.0"})
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "FFTA - Résultats des compétitions"
SubElement(channel, "description").text = (
    "Résultats des compétitions FFTA pour le département 57."
)
SubElement(channel, "link").text = "https://www.ffta.fr/competitions"
SubElement(channel, "language").text = "fr"

for competition in competitions:
    item = SubElement(channel, "item")

    SubElement(item, "title").text = competition["title"]
    SubElement(item, "link").text = competition["link"]
    SubElement(item, "guid").text = competition["link"]

    # La description contient uniquement la date de la compétition.
    SubElement(item, "description").text = competition["date"] or ""

    # La date de modification du PDF sert de date de publication RSS.
    if competition["date_publication"]:
        SubElement(item, "pubDate").text = (
            competition["date_publication"]
        )

ElementTree(rss).write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True,
)

print()
print("========================================")
print("RSS généré avec succès !")
print("========================================")
print()
print("Fichier créé :", OUTPUT_FILE)
print(
    f"Période FFTA : {start_date.isoformat()} "
    f"→ {end_date.isoformat()}"
)
