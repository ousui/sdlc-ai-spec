"""Exclude proved Python syntax, never literal values, from a secret heuristic.

This is not a credential detector or a security certification. Plain text and
unparseable source retain the caller's original conservative pattern checks.
"""
from __future__ import annotations
import ast


def reference_spans(source: str) -> tuple[tuple[int, int], ...]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ()
    # A lone 'password=abcdef' can be a config secret, not source code.
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               for node in tree.body):
        return ()
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def position(line, column):
        # AST columns count UTF-8 bytes; regex positions count Unicode characters.
        return offsets[line - 1] + len(lines[line - 1].encode()[:column].decode())

    def span(node):
        return (position(node.lineno, node.col_offset),
                position(node.end_lineno, node.end_col_offset))

    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            aliases.setdefault(node.targets[0].id, []).append(node.value)

    def runtime_reference(node, seen=frozenset()):
        if isinstance(node, ast.Name):
            if node.id in seen:
                return False
            definitions = aliases.get(node.id, [])
            return not definitions or all(runtime_reference(value, seen | {node.id}) for value in definitions)
        if isinstance(node, ast.Attribute):
            return runtime_reference(node.value, seen)
        if isinstance(node, ast.Call):
            # A function call with embedded nonempty string/bytes could conceal
            # a literal credential (including decode/format helpers); keep it blocked.
            return not any(isinstance(value, ast.Constant) and
                           isinstance(value.value, (str, bytes)) and value.value
                           for value in ast.walk(node))
        return False

    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and runtime_reference(node.value):
            spans.extend(span(target) for target in node.targets)
        elif isinstance(node, ast.AnnAssign):
            if node.value is None or runtime_reference(node.value):
                spans.append(span(node.target))
        elif isinstance(node, ast.keyword) and runtime_reference(node.value):
            start, _ = span(node)
            spans.append((start, start + len(node.arg or '')))
        elif isinstance(node, ast.arg) and node.annotation is not None:
            start, _ = span(node)
            spans.append((start, start + len(node.arg)))
        elif isinstance(node, (ast.If, ast.While)):
            # A colon terminating a condition must not consume 'return' on the
            # next line as a supposed password value. Constants stay conservative.
            if not any(isinstance(value, ast.Constant) and isinstance(value.value, (str, bytes))
                       for value in ast.walk(node.test)):
                start, end = span(node.test)
                if source[end:end+1] == ':':
                    spans.append((start, end))
    return tuple(spans)
