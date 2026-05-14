#!/usr/bin/env python3
"""Show where a title is available by service and country."""

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Iterable

from simplejustwatchapi import offers_for_countries, search
from simplejustwatchapi.exceptions import JustWatchApiError, JustWatchHttpError

# Commonly supported JustWatch market country codes.
JUSTWATCH_COUNTRIES = {
    "AR",
    "AT",
    "AU",
    "BE",
    "BR",
    "BG",
    "CA",
    "CH",
    "CL",
    "CO",
    "CZ",
    "DE",
    "DK",
    "EC",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HU",
    "ID",
    "IE",
    "IN",
    "IT",
    "JP",
    "KR",
    "LT",
    "LU",
    "LV",
    "MX",
    "MY",
    "NL",
    "NO",
    "NZ",
    "PE",
    "PH",
    "PL",
    "PT",
    "RO",
    "RU",
    "SE",
    "SG",
    "SK",
    "TH",
    "TR",
    "US",
    "VE",
    "ZA",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search a show/movie and list availability by service and country."
    )
    parser.add_argument(
        "title",
        nargs="?",
        help="Title to search for. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--search-country",
        default="US",
        help="Country code used for the initial search (default: US).",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code used for API responses (default: en).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=8,
        help="How many search results to show (default: 8).",
    )
    return parser.parse_args()


def pick_entry(entries: list, title: str):
    if not entries:
        raise ValueError(f"No results found for: {title}")

    print("\nSearch results:")
    for i, entry in enumerate(entries, start=1):
        year = entry.release_year or "?"
        print(f"{i}. {entry.title} ({year}) [{entry.object_type}]")

    if len(entries) == 1:
        print("Only one result found, selecting it automatically.")
        return entries[0]

    while True:
        choice = input(f"Pick a result [1-{len(entries)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(entries):
            return entries[int(choice) - 1]
        print("Invalid choice, try again.")


def group_services(offers_by_country: dict[str, list]) -> dict[str, set[str]]:
    service_to_countries: dict[str, set[str]] = defaultdict(set)
    for country, offers in offers_by_country.items():
        for offer in offers:
            package = offer.package
            if package is None:
                continue
            name = package.name or package.short_name or package.technical_name
            if not name:
                continue
            service_to_countries[name].add(country.upper())
    return service_to_countries


def print_report(service_to_countries: dict[str, set[str]], title: str) -> None:
    if not service_to_countries:
        print(f"\nNo streaming offers found for '{title}' in scanned countries.")
        return

    print(f"\nAvailability for '{title}':")
    for service in sorted(service_to_countries):
        countries = ", ".join(sorted(service_to_countries[service]))
        print(f"- {service}: {countries}")


def fetch_offers(node_id: str, language: str, countries: Iterable[str]) -> dict[str, list]:
    countries_set = {code.upper() for code in countries}
    return offers_for_countries(node_id, countries_set, language=language, best_only=True)


def resolve_node_id(entry) -> str:
    # `offers_for_countries` expects the prefixed GraphQL node ID (e.g. "ts4"), not numeric object_id.
    candidate = getattr(entry, "entry_id", None) or getattr(entry, "node_id", None)
    if candidate:
        return str(candidate)
    fallback = getattr(entry, "object_id", None)
    if fallback is None:
        raise ValueError("Could not determine entry node ID for selected result.")
    return str(fallback)


def main() -> int:
    args = parse_args()
    title = (args.title or input("Show/movie title: ")).strip()
    if not title:
        print("Title cannot be empty.")
        return 1

    try:
        entries = search(
            title=title,
            country=args.search_country.upper(),
            language=args.language,
            count=args.count,
            best_only=True,
        )
        selected = pick_entry(entries, title)
        offers_by_country = fetch_offers(
            node_id=resolve_node_id(selected),
            language=args.language,
            countries=JUSTWATCH_COUNTRIES,
        )
    except ValueError as exc:
        print(exc)
        return 1
    except (JustWatchApiError, JustWatchHttpError) as exc:
        print(f"JustWatch API error: {exc}")
        return 2

    service_to_countries = group_services(offers_by_country)
    print_report(service_to_countries, selected.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
