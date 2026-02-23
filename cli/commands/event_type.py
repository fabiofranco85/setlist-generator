"""
Event type management commands.

Provides CRUD operations for event types:
  songbook event-type list
  songbook event-type add <slug> --name "..." --description "..."
  songbook event-type edit <slug> [--name "..."] [--description "..."]
  songbook event-type remove <slug>
  songbook event-type moments <slug> [--set "louvor=4,prelúdio=1,..."]
  songbook event-type default [--name "..."] [--description "..."]
"""

import click

from library import get_repositories
from library.event_type import (
    DEFAULT_EVENT_TYPE_SLUG,
    EventType,
    validate_event_type_slug,
)


@click.group("event-type")
def event_type_group():
    """Manage event types for different service configurations.

    \b
    Event types define different kinds of services (e.g., Main, Youth, Christmas)
    with their own moments configuration. Songs can optionally be bound to specific
    event types; unbound songs are available for all types.
    """
    pass


@event_type_group.command("list")
def list_types():
    """List all configured event types.

    \b
    Examples:
      songbook event-type list
    """
    repos = get_repositories()
    if repos.event_types is None:
        click.secho("Event types not supported by current backend", fg="red", err=True)
        raise SystemExit(1)

    event_types = repos.event_types.get_all()

    click.echo()
    click.echo("=" * 60)
    click.echo("EVENT TYPES")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"{'Slug':<15} {'Name':<25} {'Moments'}")
    click.echo("-" * 60)

    for slug, et in event_types.items():
        moments_str = ", ".join(f"{m}={c}" for m, c in et.moments.items())
        default_marker = " (default)" if slug == DEFAULT_EVENT_TYPE_SLUG else ""
        click.echo(f"{slug:<15} {et.name:<25} {moments_str}{default_marker}")

    click.echo()


@event_type_group.command("add")
@click.argument("slug")
@click.option("--name", "-n", required=True, help="Display name for the event type")
@click.option("--description", "-d", default="", help="Human-readable description")
@click.option("--moments", "-m", default=None, help="Moments config (e.g., 'louvor=4,prelúdio=1')")
def add_type(slug, name, description, moments):
    """Add a new event type.

    \b
    Creates a new event type with the given slug. Moments are copied from the
    default type unless --moments is specified.

    \b
    Examples:
      songbook event-type add youth --name "Youth Service"
      songbook event-type add youth --name "Youth Service" --moments "louvor=5,prelúdio=1,poslúdio=1"
    """
    from cli.cli_utils import handle_error

    try:
        slug = validate_event_type_slug(slug)
    except ValueError as e:
        handle_error(str(e))

    repos = get_repositories()
    if repos.event_types is None:
        handle_error("Event types not supported by current backend")

    # Parse moments if provided
    moments_dict = None
    if moments:
        moments_dict = _parse_moments_string(moments)

    # Get default moments if none specified
    if moments_dict is None:
        default = repos.event_types.get(DEFAULT_EVENT_TYPE_SLUG)
        moments_dict = dict(default.moments) if default else {}

    event_type = EventType(
        slug=slug,
        name=name,
        description=description,
        moments=moments_dict,
    )

    try:
        repos.event_types.add(event_type)
    except ValueError as e:
        handle_error(str(e))

    click.secho(f"\nEvent type '{slug}' created successfully!", fg="green")
    click.echo(f"  Name: {name}")
    click.echo(f"  Description: {description or '(none)'}")
    moments_str = ", ".join(f"{m}={c}" for m, c in moments_dict.items())
    click.echo(f"  Moments: {moments_str}")


@event_type_group.command("edit")
@click.argument("slug")
@click.option("--name", "-n", default=None, help="New display name")
@click.option("--description", "-d", default=None, help="New description")
def edit_type(slug, name, description):
    """Edit an existing event type.

    \b
    Examples:
      songbook event-type edit youth --name "Friday Youth"
      songbook event-type edit youth --description "Friday evening service"
    """
    from cli.cli_utils import handle_error

    try:
        slug = validate_event_type_slug(slug)
    except ValueError as e:
        handle_error(str(e))

    if name is None and description is None:
        handle_error("Specify at least --name or --description to update")

    repos = get_repositories()
    if repos.event_types is None:
        handle_error("Event types not supported by current backend")

    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description

    try:
        repos.event_types.update(slug, **kwargs)
    except KeyError as e:
        handle_error(str(e))

    click.secho(f"\nEvent type '{slug}' updated!", fg="green")
    if name is not None:
        click.echo(f"  Name: {name}")
    if description is not None:
        click.echo(f"  Description: {description}")


@event_type_group.command("remove")
@click.argument("slug")
def remove_type(slug):
    """Remove an event type.

    \b
    Cannot remove the default event type.

    \b
    Examples:
      songbook event-type remove youth
    """
    from cli.cli_utils import handle_error

    try:
        slug = validate_event_type_slug(slug)
    except ValueError as e:
        handle_error(str(e))

    repos = get_repositories()
    if repos.event_types is None:
        handle_error("Event types not supported by current backend")

    try:
        repos.event_types.remove(slug)
    except (KeyError, ValueError) as e:
        handle_error(str(e))

    click.secho(f"\nEvent type '{slug}' removed!", fg="green")


@event_type_group.command("moments")
@click.argument("slug")
@click.option("--set", "moments_str", default=None, help="Moments config (e.g., 'louvor=4,prelúdio=1')")
def manage_moments(slug, moments_str):
    """View or update moments configuration for an event type.

    \b
    Without --set, displays the current moments config.
    With --set, updates the moments config.

    \b
    Examples:
      songbook event-type moments youth
      songbook event-type moments youth --set "louvor=5,prelúdio=1,poslúdio=1"
    """
    from cli.cli_utils import handle_error

    try:
        slug = validate_event_type_slug(slug)
    except ValueError as e:
        handle_error(str(e))

    repos = get_repositories()
    if repos.event_types is None:
        handle_error("Event types not supported by current backend")

    et = repos.event_types.get(slug)
    if et is None:
        handle_error(f"Event type '{slug}' not found")

    if moments_str is None:
        # Display current moments
        click.echo(f"\nMoments for '{slug}' ({et.name}):")
        click.echo()
        click.echo(f"{'Moment':<15} {'Songs'}")
        click.echo("-" * 30)
        for moment, count in et.moments.items():
            click.echo(f"{moment:<15} {count}")
        click.echo()
    else:
        # Update moments
        moments_dict = _parse_moments_string(moments_str)

        try:
            repos.event_types.update(slug, moments=moments_dict)
        except KeyError as e:
            handle_error(str(e))

        click.secho(f"\nMoments for '{slug}' updated!", fg="green")
        for moment, count in moments_dict.items():
            click.echo(f"  {moment}: {count}")


@event_type_group.command("default")
@click.option("--name", "-n", default=None, help="New display name for the default type")
@click.option("--description", "-d", default=None, help="New description for the default type")
def edit_default(name, description):
    """View or edit the default event type.

    \b
    Without flags, shows the current default type.
    With --name and/or --description, updates it.

    \b
    Examples:
      songbook event-type default
      songbook event-type default --name "Sunday Worship"
    """
    from cli.cli_utils import handle_error

    repos = get_repositories()
    if repos.event_types is None:
        handle_error("Event types not supported by current backend")

    if name is None and description is None:
        # Display default type
        et = repos.event_types.get(DEFAULT_EVENT_TYPE_SLUG)
        if et is None:
            handle_error("Default event type not found")

        click.echo(f"\nDefault event type:")
        click.echo(f"  Slug: {et.slug}")
        click.echo(f"  Name: {et.name}")
        click.echo(f"  Description: {et.description or '(none)'}")
        click.echo(f"  Moments:")
        for moment, count in et.moments.items():
            click.echo(f"    {moment}: {count}")
        click.echo()
    else:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description

        try:
            repos.event_types.update(DEFAULT_EVENT_TYPE_SLUG, **kwargs)
        except KeyError as e:
            handle_error(str(e))

        click.secho(f"\nDefault event type updated!", fg="green")
        if name is not None:
            click.echo(f"  Name: {name}")
        if description is not None:
            click.echo(f"  Description: {description}")


def _parse_moments_string(moments_str: str) -> dict[str, int]:
    """Parse a moments string like 'louvor=4,prelúdio=1' into a dict.

    Args:
        moments_str: Comma-separated moment=count pairs

    Returns:
        Dictionary mapping moment names to counts

    Raises:
        SystemExit: If format is invalid
    """
    from cli.cli_utils import handle_error

    result = {}
    for pair in moments_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            handle_error(f"Invalid moment format: '{pair}'. Use 'moment=count'")

        moment, count_str = pair.split("=", 1)
        moment = moment.strip()
        try:
            count = int(count_str.strip())
        except ValueError:
            handle_error(f"Invalid count for moment '{moment}': '{count_str.strip()}'")

        if count < 0:
            handle_error(f"Count for moment '{moment}' must be non-negative")

        result[moment] = count

    return result
