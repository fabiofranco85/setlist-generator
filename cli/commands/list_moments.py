"""
List moments command - display available service moments.
"""

from library.config import MOMENTS_CONFIG


def run(event_type=""):
    """Display all available service moments.

    Args:
        event_type: Optional event type slug (shows that type's moments)
    """
    # Resolve moments config
    if event_type:
        from library import get_repositories
        from cli.cli_utils import resolve_event_type

        repos = get_repositories()
        et = resolve_event_type(repos, event_type)
        moments = et.moments
        type_label = f" ({et.name})"
    else:
        moments = MOMENTS_CONFIG
        type_label = ""

    print("\n" + "=" * 60)
    print(f"AVAILABLE SERVICE MOMENTS{type_label}")
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

    for moment, count in moments.items():
        desc = descriptions.get(moment, "")
        print(f"{moment:<15} {count:<8} {desc}")

    print()
    print("USAGE EXAMPLES:")
    print("-" * 60)
    print("  # Replace song in prelúdio")
    print("  songbook replace --moment prelúdio")
    print()
    print("  # Override songs for louvor")
    print("  songbook generate --override \"louvor:Oceanos,Hosana\"")
    print()
    print("  # Replace position 2 in louvor")
    print("  songbook replace --moment louvor --position 2")
    print()
