#!/usr/bin/env python3
"""List available service moments for use with --moment arguments."""

from setlist.config import MOMENTS_CONFIG


def list_moments():
    """Display all available service moments."""
    print("\n" + "=" * 60)
    print("AVAILABLE SERVICE MOMENTS")
    print("=" * 60)
    print()
    print(f"{'Moment':<15} {'Songs':<8} {'Description'}")
    print("-" * 60)

    descriptions = {
        "prelúdio": "Opening/introductory worship",
        "ofertório": "During offering collection",
        "saudação": "Greeting/welcome",
        "crianças": "Children's ministry",
        "louvor": "Main worship block",
        "poslúdio": "Closing/sending song",
    }

    for moment, count in MOMENTS_CONFIG.items():
        desc = descriptions.get(moment, "")
        print(f"{moment:<15} {count:<8} {desc}")

    print()
    print("USAGE EXAMPLES:")
    print("-" * 60)
    print("  # Replace song in prelúdio")
    print("  python replace_song.py --moment prelúdio")
    print()
    print("  # Override songs for louvor")
    print("  python generate_setlist.py --override \"louvor:Oceanos,Hosana\"")
    print()
    print("  # Replace position 2 in louvor")
    print("  python replace_song.py --moment louvor --position 2")
    print()


if __name__ == "__main__":
    list_moments()
