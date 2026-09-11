"""Independent, finite comparison oracle for the approved naming deltas.

Do not import tools/naming.py or the mutable generator map here. A change to
this oracle needs review against docs/NAMING.md. No whitespace/paragraph/MUST
normalization is allowed; unknown names and semantic edits remain differences.
"""
from __future__ import annotations
import re

EXPECTED = {
    'init': 'sdlc-000-init', 'constitution': 'sdlc-010-rule',
    'specify': 'sdlc-100-spec', 'clarify': 'sdlc-110-clar',
    'plan': 'sdlc-200-plan', 'tasks': 'sdlc-300-task',
    'analyze': 'sdlc-310-xchk', 'checklist': 'sdlc-320-huma',
    'implement': 'sdlc-400-impl', 'converge': 'sdlc-500-conv',
}
IDENTIFIERS = {
    'SPECIFY_INIT_DIR': 'SDLC_INIT_DIR', 'SPECIFY_FEATURE': 'SDLC_FEATURE',
    'SPECIFY_FEATURE_DIRECTORY': 'SDLC_FEATURE_DIRECTORY',
    'find_specify_root': 'find_sdlc_root', 'resolve_specify_init_dir': 'resolve_sdlc_init_dir',
    'format_speckit_command': 'format_sdlc_command',
    'SPECKIT_EXTENSIONS': 'SDLC_EXTENSIONS', 'SPECKIT_REGISTRY': 'SDLC_REGISTRY',
    'SPECKIT_MANIFEST': 'SDLC_MANIFEST', 'SPECKIT_TMPL': 'SDLC_TMPL',
}


def reverse_names(text: str, *, bare: bool = False) -> str:
    for source, target in EXPECTED.items():
        for prefix in ('/sdlc-ai-spec:', '/', '$'):
            dest_prefix = '$' if prefix == '$' else '/'
            text = re.sub(re.escape(prefix + target) + r'(?![\w-])',
                          lambda m: dest_prefix + 'speckit-' + source, text)
        if bare:
            text = re.sub(r'(?<![\w:/\$-])' + re.escape(target) + r'(?![\w-])',
                          lambda m: '/speckit-' + source, text)
    for old, new in IDENTIFIERS.items():
        text = re.sub(r'\b' + re.escape(new) + r'\b', lambda m: old, text)
    for new, old in (
        ('SDLC AI SPEC', 'Spec Kit'), ('[sdlc]', '[specify]'),
        ('did not define certain details', 'did not specify certain details'),
        ('or choose a different number', 'or specify a different number'),
        ('before_spec', 'before_specify'), ('after_spec', 'after_specify'),
    ):
        text = re.sub(r'(?<![\w])' + re.escape(new) + r'(?![\w])', lambda m: old, text)
    return text


def leaf_projection(text: str) -> str:
    """Raw leaf scripts: exact bytes except the explicitly reviewed symbols."""
    text = text.replace('.specify', '.sdlc')
    for old, new in IDENTIFIERS.items():
        text = re.sub(r'\b' + re.escape(old) + r'\b', lambda m: new, text)
    for source, target in EXPECTED.items():
        text = re.sub(r'\bformat_sdlc_command ' + source + r'\b',
                      lambda m: 'format_sdlc_command ' + target, text)
    return text
