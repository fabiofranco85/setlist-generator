#!/usr/bin/env python3
"""
Import real history data from JSON and create history files.

This script:
1. Deletes existing fake history data
2. Parses real setlist data (format=setlist_with_moments only)
3. Maps moment names to match current system
4. Creates proper history/*.json files
"""

import json
from pathlib import Path

# Moment name mapping: external → internal
MOMENT_MAPPING = {
    "Prelúdio": "prelúdio",
    "Oferta": "ofertório",
    "Comunhão": "saudação",
    "Crianças": "crianças",
    "Louvor": "louvor",
    "Poslúdio": "poslúdio",
    # Unsupported moments (will be skipped with warning)
    "Ceia": None,
    "Intercessão": None,
}

# Expected moments in current system
VALID_MOMENTS = {"prelúdio", "ofertório", "saudação", "crianças", "louvor", "poslúdio"}


def parse_setlist_data(raw_data: dict) -> dict[str, dict]:
    """
    Parse raw JSON data and filter for setlist_with_moments entries.

    Returns:
        Dict mapping dates to parsed setlist data
    """
    parsed = {}

    for date, entry in raw_data.items():
        if entry.get("format") != "setlist_with_moments":
            continue

        service_moments = entry.get("service_moments", {})
        if not service_moments:
            continue

        parsed[date] = service_moments

    return parsed


def convert_to_history_format(date: str, service_moments: dict) -> dict:
    """
    Convert external format to internal history format.

    External format:
        {
            "Prelúdio": [{"title": "Song Name", "key": "D"}],
            ...
        }

    Internal format:
        {
            "date": "2025-12-15",
            "moments": {
                "prelúdio": ["Song Name"],
                ...
            }
        }
    """
    converted_moments = {}
    skipped_moments = []

    for external_moment, songs in service_moments.items():
        # Map moment name
        internal_moment = MOMENT_MAPPING.get(external_moment)

        if internal_moment is None:
            skipped_moments.append(external_moment)
            continue

        # Extract song titles only (ignore key information)
        song_titles = [song["title"] for song in songs]
        converted_moments[internal_moment] = song_titles

    if skipped_moments:
        print(f"  ⚠️  Skipped unsupported moments: {', '.join(skipped_moments)}")

    return {
        "date": date,
        "moments": converted_moments
    }


def main():
    # Raw data from user
    raw_data = {
        "2026-01-25": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Estamos de Pé", "key": "D"}],
                "Oferta": [{"title": "Tributo a Jehovah", "key": "E"}],
                "Comunhão": [{"title": "Brilha Jesus", "key": "A"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Entrega", "key": "G"},
                    {"title": "Lugar Secreto", "key": "C"},
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Perfeito Amor", "key": "C"}
                ],
                "Poslúdio": [{"title": "Rude Cruz", "key": "A"}]
            }
        },
        "2025-12-28": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Espírito, Enche a Minha Vida", "key": "C"}],
                "Oferta": [{"title": "Agradeço", "key": "D"}],
                "Comunhão": [{"title": "Corpo e Família", "key": "G"}],
                "Crianças": [{"title": "Homenzinho Torto", "key": "A"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Jesus Em Tua Presença", "key": "C"},
                    {"title": "Ao Único", "key": "C"},
                    {"title": "Eu Navegarei", "key": "Am"}
                ],
                "Ceia": [{"title": "Santo Pra Sempre", "key": "G"}],
                "Poslúdio": [{"title": "Noite de Paz", "key": "A"}]
            }
        },
        "2025-12-07": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Noite de Paz", "key": "A"}],
                "Oferta": [{"title": "Eu Te Busco", "key": "G"}],
                "Comunhão": [{"title": "O Nosso General É Cristo", "key": "Am"}],
                "Crianças": [{"title": "A Alegria Está No Coração", "key": "G"}],
                "Louvor": [
                    {"title": "Entrega", "key": "G"},
                    {"title": "Santo Pra Sempre", "key": "G"},
                    {"title": "Consagração", "key": "G"},
                    {"title": "Em Espirito Em Verdade", "key": "G"}
                ],
                "Poslúdio": [{"title": "Noite de Paz", "key": "A"}]
            }
        },
        "2025-11-16": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Estamos de Pé", "key": "D"}],
                "Oferta": [{"title": "Tributo a Jehovah", "key": "E"}],
                "Comunhão": [{"title": "Brilha Jesus", "key": "A"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Lugar Secreto", "key": "C"},
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Perfeito Amor", "key": "C"}
                ],
                "Poslúdio": [{"title": "Rude Cruz", "key": "A"}]
            }
        },
        "2025-11-09": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Espírito, Enche a Minha Vida", "key": "C"}],
                "Oferta": [{"title": "Agradeço", "key": "D"}],
                "Comunhão": [{"title": "Corpo e Família", "key": "G"}],
                "Crianças": [{"title": "Homenzinho Torto", "key": "A"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Jesus Em Tua Presença", "key": "C"},
                    {"title": "Ao Único", "key": "C"},
                    {"title": "Eu Navegarei", "key": "Am"}
                ],
                "Poslúdio": [{"title": "Autoridade e Poder", "key": "G"}]
            }
        },
        "2025-10-05": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Eu Te Busco", "key": "G"}],
                "Oferta": [{"title": "Te Agradeço", "key": "D"}],
                "Comunhão": [{"title": "O Nosso General É Cristo", "key": "Am"}],
                "Crianças": [{"title": "Rei Davi", "key": "Em"}],
                "Louvor": [
                    {"title": "Vim para adorar-te", "key": "G"},
                    {"title": "Mais Que Uma Voz", "key": "A"},
                    {"title": "Precioso", "key": "Gm7"},
                    {"title": "Quebrantado", "key": "Bb"}
                ],
                "Poslúdio": [{"title": "Santo de Deus", "key": "G"}]
            }
        },
        "2025-09-21": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Estamos de Pé", "key": "D"}],
                "Oferta": [{"title": "Vivemos Pra Jesus", "key": "G"}],
                "Comunhão": [{"title": "Reina em mim", "key": "Bb"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Lugar Secreto", "key": "C"},
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Perfeito Amor", "key": "C"}
                ],
                "Poslúdio": [{"title": "Tributo a Jehovah", "key": "E"}]
            }
        },
        "2025-09-14": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Espírito, Enche a Minha Vida", "key": "C"}],
                "Oferta": [{"title": "Agradeço", "key": "D"}],
                "Comunhão": [{"title": "Corpo e Família", "key": "G"}],
                "Crianças": [{"title": "Homenzinho Torto", "key": "A"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Jesus Em Tua Presença", "key": "C"},
                    {"title": "Ao Único", "key": "C"},
                    {"title": "Eu Navegarei", "key": "Am"}
                ],
                "Poslúdio": [{"title": "Autoridade e Poder", "key": "G"}]
            }
        },
        "2025-08-31": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Estamos de Pé", "key": "D"}],
                "Oferta": [{"title": "Tributo a Jehovah", "key": "E"}],
                "Comunhão": [{"title": "Reina em mim", "key": "Bb"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Lugar Secreto", "key": "C"},
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Creio que tú és a cura", "key": "E"}
                ],
                "Poslúdio": [{"title": "Santo de Deus", "key": "G"}]
            }
        },
        "2025-08-17": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Rude Cruz", "key": "A"}],
                "Oferta": [{"title": "Te Agradeço", "key": "C"}],
                "Comunhão": [{"title": "Brilha Jesus", "key": "A"}],
                "Crianças": [{"title": "A Alegria Está No Coração", "key": "G"}],
                "Louvor": [
                    {"title": "Santo de Deus", "key": "G"},
                    {"title": "Perfeito Amor", "key": "C"},
                    {"title": "Hosana", "key": "E"},
                    {"title": "Aos Pés da Cruz", "key": "E"}
                ],
                "Poslúdio": [{"title": "Santo de Deus", "key": "G"}]
            }
        },
        "2025-07-27": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Abra os olhos do meu coração", "key": "E"}],
                "Oferta": [{"title": "Tributo a Jehovah", "key": "E"}],
                "Comunhão": [{"title": "Reina em mim", "key": "Bb"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Perfeito Amor", "key": "C"},
                    {"title": "Hosana", "key": "E"},
                    {"title": "Oceanos", "key": "Bm"}
                ],
                "Poslúdio": [{"title": "Naves Imperiais", "key": "Am"}]
            }
        },
        "2025-07-06": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Estamos de Pé", "key": "D"}],
                "Oferta": [{"title": "Venho, Senhor, Minha Vida Oferecer", "key": "G"}],
                "Comunhão": [{"title": "Brilha Jesus", "key": "A"}],
                "Crianças": [{"title": "A Alegria Está No Coração", "key": "G"}],
                "Louvor": [
                    {"title": "Entrega", "key": "G"},
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Consagração", "key": "G"},
                    {"title": "Em Espírito, Em Verdade", "key": "G"}
                ],
                "Intercessão": [{"title": "Hosana", "key": "E"}],
                "Poslúdio": [{"title": "Autoridade e Poder", "key": "G"}]
            }
        },
        "2025-05-31": {
            "format": "setlist_with_moments",
            "service_moments": {
                "Prelúdio": [{"title": "Abra os olhos do meu coração", "key": "E"}],
                "Oferta": [{"title": "Tributo a Jehovah", "key": "E"}],
                "Comunhão": [{"title": "Reina em mim", "key": "Bb"}],
                "Crianças": [{"title": "Deus grandão", "key": "D"}],
                "Louvor": [
                    {"title": "Ousado Amor", "key": "D"},
                    {"title": "Perfeito Amor", "key": "C"},
                    {"title": "Hosana", "key": "E"},
                    {"title": "Oceanos", "key": "Bm"}
                ],
                "Poslúdio": [{"title": "Naves Imperiais", "key": "Am"}]
            }
        }
    }

    history_dir = Path("./history")

    print("=" * 70)
    print("  IMPORTING REAL HISTORY DATA")
    print("=" * 70)
    print()

    # Step 1: Delete existing fake data
    print("Step 1: Removing fake history data...")
    deleted_count = 0
    if history_dir.exists():
        for json_file in history_dir.glob("*.json"):
            json_file.unlink()
            deleted_count += 1
            print(f"  🗑️  Deleted: {json_file.name}")
    print(f"  ✓ Removed {deleted_count} fake history file(s)")
    print()

    # Step 2: Parse and filter data
    print("Step 2: Parsing real setlist data...")
    parsed_data = parse_setlist_data(raw_data)
    print(f"  ✓ Found {len(parsed_data)} setlists with moment structure")
    print()

    # Step 3: Convert and save
    print("Step 3: Converting and saving history files...")
    history_dir.mkdir(exist_ok=True)

    # Sort by date to process chronologically
    for date in sorted(parsed_data.keys()):
        service_moments = parsed_data[date]

        print(f"  📅 {date}")
        history_data = convert_to_history_format(date, service_moments)

        # Save to file
        history_file = history_dir / f"{date}.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        # Show moment counts
        moment_summary = ", ".join(
            f"{moment}: {len(songs)}"
            for moment, songs in history_data["moments"].items()
        )
        print(f"     → {moment_summary}")

    print()
    print("=" * 70)
    print(f"✅ SUCCESS: Imported {len(parsed_data)} real history files")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  • Run: python generate_setlist.py")
    print("  • The generator will now use real performance history")
    print("  • Songs used recently will be avoided automatically")


if __name__ == "__main__":
    main()
