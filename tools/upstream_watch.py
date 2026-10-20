"""Finite, reviewed upstream source locations; never infer renames or execute code."""
from __future__ import annotations

from pathlib import Path


# These are source-provenance alternatives, not product/runtime path aliases.
WATCHED_RELOCATIONS = (
    ('src/specify_cli/commands/init.py', 'src/specify_cli/command_init.py'),
    ('src/specify_cli/events.py', 'src/specify_cli/events/__init__.py'),
)

# Reviewed dependencies of the reorganized init/event/integration producers.
# Presence adds evidence, not support for external adapters, events or CLI dispatch.
REVIEWED_DEPENDENCIES = (
    # Core init still resolves/materializes templates through these modules
    # when presets/extensions are empty; the directory name is not a scope gate.
    'src/specify_cli/__init__.py',
    'src/specify_cli/_agent_config.py',
    'src/specify_cli/_assets.py',
    'src/specify_cli/_utils.py',
    'src/specify_cli/extensions/__init__.py',
    'src/specify_cli/presets/__init__.py',
    'src/specify_cli/presets/_manager.py',
    'src/specify_cli/presets/_resolver.py',
    'src/specify_cli/presets/_registry.py',
    'src/specify_cli/presets/_manifest.py',
    'src/specify_cli/integrations/__init__.py',
    'src/specify_cli/integrations/_helpers.py',
    'src/specify_cli/integrations/_commands.py',
    'src/specify_cli/_file_policy.py',
    'src/specify_cli/file_helper.py',
    'src/specify_cli/_init_options.py',
    'src/specify_cli/integration_runtime.py',
    'src/specify_cli/integration_state.py',
    'src/specify_cli/integrations/_capture.py',
    'src/specify_cli/integrations/_file_changes.py',
    'src/specify_cli/integrations/_lifecycle.py',
    'src/specify_cli/integrations/_registration.py',
    'src/specify_cli/integrations/installer.py',
    'src/specify_cli/integrations/manifest.py',
)


def resolve_watch_paths(upstream: Path, previous: dict) -> tuple[str, ...]:
    """Keep every prior watch; resolve only the two approved, exclusive moves.

    Returned keys are actual upstream paths. candidate_lock records a relocation
    as a reviewed removal plus addition, even when the file bytes did not change.
    Newly present reviewed dependencies are added for the reorganized layout;
    once locked, their disappearance remains an error like any other watch.
    """
    paths = set()
    for name in previous:
        alternatives = next((group for group in WATCHED_RELOCATIONS if name in group), None)
        if alternatives is None:
            if not (upstream / name).is_file():
                raise ValueError('Watched source missing; review upstream scope: ' + name)
            paths.add(name)
            continue
        present = [path for path in alternatives if (upstream / path).is_file()]
        if len(present) != 1:
            raise ValueError('Expected exactly one reviewed watched source: '
                             + repr(alternatives) + '; found ' + repr(present))
        paths.add(present[0])
    if any(group[1] in paths for group in WATCHED_RELOCATIONS):
        paths.update(name for name in REVIEWED_DEPENDENCIES if (upstream / name).is_file())
    return tuple(sorted(paths))
