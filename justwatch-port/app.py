#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from flask import Flask, render_template, request, send_from_directory
from simplejustwatchapi import offers_for_countries, search
from simplejustwatchapi.exceptions import JustWatchApiError, JustWatchHttpError

app = Flask(__name__)
DEFAULT_SEARCH_COUNTRY = "US"
DEFAULT_LANGUAGE = "en"

JUSTWATCH_COUNTRIES = {
    "AR", "AT", "AU", "BE", "BR", "BG", "CA", "CH", "CL", "CO", "CZ", "DE", "DK",
    "EC", "EE", "ES", "FI", "FR", "GB", "GR", "HU", "ID", "IE", "IN", "IT", "JP",
    "KR", "LT", "LU", "LV", "MX", "MY", "NL", "NO", "NZ", "PE", "PH", "PL", "PT",
    "RO", "RU", "SE", "SG", "SK", "TH", "TR", "US", "VE", "ZA",
}

COUNTRY_NAMES = {
    "AR": "Argentina", "AT": "Austria", "AU": "Australia", "BE": "Belgium",
    "BG": "Bulgaria", "BR": "Brazil", "CA": "Canada", "CH": "Switzerland",
    "CL": "Chile", "CO": "Colombia", "CZ": "Czech Republic", "DE": "Germany",
    "DK": "Denmark", "EC": "Ecuador", "EE": "Estonia", "ES": "Spain",
    "FI": "Finland", "FR": "France", "GB": "United Kingdom", "GR": "Greece",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IN": "India",
    "IT": "Italy", "JP": "Japan", "KR": "South Korea", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MX": "Mexico", "MY": "Malaysia",
    "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand", "PE": "Peru",
    "PH": "Philippines", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "RU": "Russia", "SE": "Sweden", "SG": "Singapore", "SK": "Slovakia",
    "TH": "Thailand", "TR": "Turkey", "US": "United States", "VE": "Venezuela",
    "ZA": "South Africa",
}

# Display order — FI/Nordics first, then Europe, Americas, APAC.
COUNTRY_DISPLAY_ORDER = [
    "FI", "SE", "NO", "DK", "EE", "LV", "LT",
    "GB", "IE", "DE", "AT", "CH", "NL", "BE", "LU",
    "FR", "ES", "PT", "IT", "GR",
    "PL", "CZ", "SK", "HU", "RO", "BG", "TR", "RU",
    "US", "CA", "MX", "BR", "AR", "CL", "CO", "PE", "EC", "VE",
    "AU", "NZ", "JP", "KR", "IN", "ID", "MY", "PH", "SG", "TH", "ZA",
]
COUNTRY_ORDER_INDEX = {code: idx for idx, code in enumerate(COUNTRY_DISPLAY_ORDER)}

LANGUAGE_TO_FLAG_COUNTRY = {
    "EN": "US", "ES": "ES", "FI": "FI", "SV": "SE", "DA": "DK", "NO": "NO",
    "NL": "NL", "DE": "DE", "FR": "FR", "IT": "IT", "PT": "PT", "PL": "PL",
    "CS": "CZ", "SK": "SK", "HU": "HU", "RO": "RO", "TR": "TR", "ID": "ID",
    "TH": "TH", "MS": "MY", "JA": "JP", "KO": "KR", "ZH": "CN",
}


def country_sort_key(code: str) -> tuple[int, str]:
    upper = code.upper()
    return (COUNTRY_ORDER_INDEX.get(upper, 999), upper)


def country_flag(code: str) -> str:
    upper = (code or "").upper()
    if len(upper) != 2 or not upper.isalpha():
        return upper
    return "".join(chr(127397 + ord(ch)) for ch in upper)


def language_flag(language_code: str) -> str:
    lang = (language_code or "").strip().upper()
    if not lang:
        return ""
    country = LANGUAGE_TO_FLAG_COUNTRY.get(lang)
    if country:
        return country_flag(country)
    if len(lang) >= 2 and lang[:2].isalpha():
        return country_flag(lang[:2])
    return ""


def is_preferred_language(language_code: str) -> bool:
    lang = (language_code or "").strip().upper()
    return lang == "FI" or lang.startswith("EN")


def monetization_label(value: str) -> str:
    key = (value or "").strip().upper()
    labels = {
        "FLATRATE": "Subscription",
        "ADS": "Free (Ads)",
        "FREE": "Free",
        "RENT": "Rent",
        "BUY": "Buy",
    }
    return labels.get(key, key.title() if key else value)


def svc_initials(name: str) -> str:
    """Two-letter mark used in service tiles."""
    cleaned = "".join(ch for ch in (name or "") if ch.isalpha() or ch == " ")
    words = cleaned.split()
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def country_highlight(audio_languages, subtitle_languages) -> str:
    """Class suffix added to per-country detail boxes."""
    audio = {(l or "").upper() for l in (audio_languages or [])}
    subs = {(l or "").upper() for l in (subtitle_languages or [])}
    if "FI" in subs:
        return "has-fi-subs"
    if "EN" in audio and "EN" in subs:
        return "has-en-pair"
    return ""


def resolve_node_id(entry) -> str:
    candidate = getattr(entry, "entry_id", None) or getattr(entry, "node_id", None)
    if candidate:
        return str(candidate)
    fallback = getattr(entry, "object_id", None)
    if fallback is None:
        raise ValueError("Could not determine entry node ID for selected result.")
    return str(fallback)


def fetch_offers(node_id: str, language: str, countries: Iterable[str]) -> dict[str, list]:
    countries_set = {code.upper() for code in countries}
    return offers_for_countries(node_id, countries_set, language=language, best_only=True)


def group_services(
    offers_by_country: dict[str, list],
    selected_monetization_types: set[str] | None = None,
    selected_services: set[str] | None = None,
    selected_audio_languages: set[str] | None = None,
    selected_subtitle_languages: set[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Group offers into services with per-country language detail.

    Each service entry includes:
      countries:           list[str]   — country codes available
      audio_languages:     list[str]
      subtitle_languages:  list[str]
      monetization_types:  list[str]   — which offer types this service exposes
      by_country:          list[{country, audio_languages, subtitle_languages,
                                 highlight}]
    """
    service_to_countries: dict[str, set[str]] = defaultdict(set)
    service_to_audio_languages: dict[str, set[str]] = defaultdict(set)
    service_to_subtitle_languages: dict[str, set[str]] = defaultdict(set)
    service_to_monetizations: dict[str, set[str]] = defaultdict(set)
    service_country_audio: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    service_country_subtitles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for country, offers in offers_by_country.items():
        for offer in offers:
            monetization_type = (offer.monetization_type or "").upper()
            if selected_monetization_types and monetization_type not in selected_monetization_types:
                continue
            audio_languages = {lang.upper() for lang in (offer.audio_languages or []) if lang}
            subtitle_languages = {lang.upper() for lang in (offer.subtitle_languages or []) if lang}
            if selected_audio_languages and not (audio_languages & selected_audio_languages):
                continue
            if selected_subtitle_languages and not (subtitle_languages & selected_subtitle_languages):
                continue
            package = offer.package
            if package is None:
                continue
            name = package.name or package.short_name or package.technical_name
            if not name:
                continue
            if selected_services and name not in selected_services:
                continue

            cu = country.upper()
            service_to_countries[name].add(cu)
            service_to_audio_languages[name].update(audio_languages)
            service_to_subtitle_languages[name].update(subtitle_languages)
            if monetization_type:
                service_to_monetizations[name].add(monetization_type)
            service_country_audio[name][cu].update(audio_languages)
            service_country_subtitles[name][cu].update(subtitle_languages)

    result: dict[str, dict[str, object]] = {}
    # Sort services: subscription first (FLATRATE), then free, then rent, then buy, then alpha
    rank = {"FLATRATE": 0, "FREE": 1, "ADS": 2, "RENT": 3, "BUY": 4}

    def svc_sort_key(item):
        name, _ = item
        mts = service_to_monetizations.get(name, set())
        mt_rank = min((rank.get(m, 5) for m in mts), default=5)
        in_fi = 0 if "FI" in service_to_countries.get(name, set()) else 1
        return (in_fi, mt_rank, name.lower())

    for service, countries in sorted(service_to_countries.items(), key=svc_sort_key):
        by_country = []
        for country in sorted(countries, key=country_sort_key):
            audio = sorted(service_country_audio.get(service, {}).get(country, set()))
            subs = sorted(service_country_subtitles.get(service, {}).get(country, set()))
            by_country.append({
                "country": country,
                "audio_languages": audio,
                "subtitle_languages": subs,
                "highlight": country_highlight(audio, subs),
            })
        result[service] = {
            "countries": sorted(countries, key=country_sort_key),
            "audio_languages": sorted(service_to_audio_languages.get(service, set())),
            "subtitle_languages": sorted(service_to_subtitle_languages.get(service, set())),
            "monetization_types": sorted(service_to_monetizations.get(service, set()), key=lambda m: rank.get(m, 5)),
            "by_country": by_country,
        }
    return result


def collect_filter_options(
    offers_by_country: dict[str, list],
) -> tuple[list[str], list[str], list[str], list[str]]:
    service_names: set[str] = set()
    monetization_types: set[str] = set()
    audio_languages: set[str] = set()
    subtitle_languages: set[str] = set()
    for offers in offers_by_country.values():
        for offer in offers:
            monetization = (offer.monetization_type or "").upper()
            if monetization:
                monetization_types.add(monetization)
            for lang in offer.audio_languages or []:
                if lang:
                    audio_languages.add(lang.upper())
            for lang in offer.subtitle_languages or []:
                if lang:
                    subtitle_languages.add(lang.upper())
            package = offer.package
            if package is None:
                continue
            name = package.name or package.short_name or package.technical_name
            if name:
                service_names.add(name)
    return (
        sorted(service_names),
        sorted(monetization_types),
        sorted(audio_languages),
        sorted(subtitle_languages),
    )


def summarize_finland(availability: dict[str, dict[str, object]]) -> dict | None:
    """Pull out a Finland-specific summary used by the hero feature card."""
    if not availability:
        return None
    fi_services = []
    for name, info in availability.items():
        fi = next((c for c in info["by_country"] if c["country"] == "FI"), None)
        if not fi:
            continue
        fi_services.append({
            "name": name,
            "audio_languages": fi["audio_languages"],
            "subtitle_languages": fi["subtitle_languages"],
            "monetization_types": info.get("monetization_types", []),
        })
    if not fi_services:
        return {"services": [], "audio_languages": [], "subtitle_languages": []}
    audio = sorted({l for s in fi_services for l in s["audio_languages"]})
    subs = sorted({l for s in fi_services for l in s["subtitle_languages"]})
    return {
        "services": fi_services,
        "audio_languages": audio,
        "subtitle_languages": subs,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "title_query": "",
        "search_country": DEFAULT_SEARCH_COUNTRY,
        "language": DEFAULT_LANGUAGE,
        "results": [],
        "selected_title": None,
        "selected_node_id": None,
        "availability": None,
        "total_country_count": 0,
        "service_options": [],
        "monetization_options": [],
        "selected_services": [],
        "selected_monetizations": [],
        "audio_language_options": [],
        "subtitle_language_options": [],
        "selected_audio_languages": [],
        "selected_subtitle_languages": [],
        "finland_summary": None,
        "error": None,
    }

    if request.method == "POST":
        action = request.form.get("action", "search")
        context["title_query"] = request.form.get("title", "").strip()
        context["search_country"] = DEFAULT_SEARCH_COUNTRY
        context["language"] = DEFAULT_LANGUAGE

        try:
            if action == "search":
                if not context["title_query"]:
                    raise ValueError("Please enter a title.")

                entries = search(
                    title=context["title_query"],
                    country=context["search_country"],
                    language=context["language"],
                    count=8,
                    best_only=True,
                )
                if not entries:
                    raise ValueError("No results found.")

                context["results"] = [
                    {
                        "index": i,
                        "title": entry.title,
                        "year": entry.release_year or "?",
                        "object_type": entry.object_type,
                        "entry_id": getattr(entry, "entry_id", ""),
                        "object_id": getattr(entry, "object_id", ""),
                    }
                    for i, entry in enumerate(entries, start=1)
                ]

            elif action == "availability":
                selected_node_id = request.form.get("selected_node_id", "").strip()
                selected_title = request.form.get("selected_title", "").strip()
                if not selected_node_id:
                    raise ValueError("No result selected.")

                selected_services = set(request.form.getlist("services"))
                selected_monetizations = {
                    value.strip().upper()
                    for value in request.form.getlist("monetizations")
                    if value.strip()
                }
                selected_audio_languages = {
                    value.strip().upper()
                    for value in request.form.getlist("audio_languages")
                    if value.strip()
                }
                selected_subtitle_languages = {
                    value.strip().upper()
                    for value in request.form.getlist("subtitle_languages")
                    if value.strip()
                }

                offers_by_country = fetch_offers(
                    node_id=selected_node_id,
                    language=context["language"],
                    countries=JUSTWATCH_COUNTRIES,
                )
                (
                    service_options,
                    monetization_options,
                    audio_language_options,
                    subtitle_language_options,
                ) = collect_filter_options(offers_by_country)

                if not selected_monetizations:
                    selected_monetizations = set(monetization_options)

                availability = group_services(
                    offers_by_country,
                    selected_monetization_types=selected_monetizations,
                    selected_services=selected_services,
                    selected_audio_languages=selected_audio_languages,
                    selected_subtitle_languages=selected_subtitle_languages,
                )

                total_country_count = len(
                    {c for info in availability.values() for c in info["countries"]}
                )

                context["selected_title"] = selected_title or context["title_query"]
                context["selected_node_id"] = selected_node_id
                context["service_options"] = service_options
                context["monetization_options"] = monetization_options
                context["audio_language_options"] = audio_language_options
                context["subtitle_language_options"] = subtitle_language_options
                context["selected_services"] = sorted(selected_services)
                context["selected_monetizations"] = sorted(selected_monetizations)
                context["selected_audio_languages"] = sorted(selected_audio_languages)
                context["selected_subtitle_languages"] = sorted(selected_subtitle_languages)
                context["availability"] = availability
                context["total_country_count"] = total_country_count
                context["finland_summary"] = summarize_finland(availability)

        except ValueError as exc:
            context["error"] = str(exc)
        except (JustWatchApiError, JustWatchHttpError) as exc:
            context["error"] = f"JustWatch API error: {exc}"

    return render_template(
        "index.html",
        country_names=COUNTRY_NAMES,
        country_order=COUNTRY_DISPLAY_ORDER,
        country_flag=country_flag,
        language_flag=language_flag,
        is_preferred_language=is_preferred_language,
        monetization_label=monetization_label,
        svc_initials=svc_initials,
        **context,
    )


# ── PWA routes — serve manifest + service worker from root so SW scope covers "/"

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js", mimetype="application/javascript")
    # Allow the SW to control the entire origin, not just /static/
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory("static", "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/offline")
def offline_fallback():
    return render_template("offline.html")


if __name__ == "__main__":
    app.run(debug=True)
