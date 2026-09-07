"""Bounded lexical exclusions for Python declarations and runtime references.

No code is executed. This is not whole-program credential analysis. Unknown
expressions keep the original conservative text check; imports and parameters
are runtime inputs, not embedded credential bytes. Literal-bearing expressions
and locally resolvable aliases/return values are never excluded.
"""
from __future__ import annotations
import ast


def reference_spans(source: str) -> tuple[tuple[int, int], ...]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ()
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in tree.body):
        return ()
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def offset(line, col):
        return offsets[line - 1] + len(lines[line - 1].encode('utf-8')[:col].decode('utf-8'))
    def span(node):
        return offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset)
    definitions, functions, imports = {}, {}, set()
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    parameters = {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    def bind(target, value):
        if isinstance(target, ast.Name):
            definitions.setdefault(target.id, []).append(value)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for part in target.elts:
                bind(part, value)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                bind(target, n.value)
        elif isinstance(n, (ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
            bind(n.target, n.value)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.setdefault(n.name, []).append(n)
        elif isinstance(n, ast.Import):
            imports.update(a.asname or a.name.split('.')[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            imports.update(a.asname or a.name for a in n.names if a.name != '*')
    def literal(node):
        return any(isinstance(n, (ast.JoinedStr, ast.Dict)) or
                   (isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)) and bool(n.value))
                   for n in ast.walk(node))
    def reference(node, seen=frozenset()):
        if isinstance(node, ast.Name):
            if node.id in seen:
                return False
            values = definitions.get(node.id)
            if values:
                return all(reference(v, seen | {node.id}) for v in values)
            return node.id in parameters or node.id in imports
        if isinstance(node, ast.Attribute):
            return reference(node.value, seen)
        if isinstance(node, ast.Call):
            if literal(node):
                return False
            if isinstance(node.func, ast.Name) and node.func.id in functions:
                name = node.func.id
                if name in seen:
                    return False
                returns = [n.value for f in functions[name] for n in ast.walk(f)
                           if isinstance(n, ast.Return) and n.value is not None]
                return bool(returns) and all(reference(v, seen | {name}) for v in returns)
            # Only statically imported callables, not arbitrary unresolved names.
            root = node.func
            while isinstance(root, ast.Attribute):
                root = root.value
            if not isinstance(root, ast.Name) or root.id not in (imports | classes) or root.id in definitions:
                return False
            return all(not literal(arg) for arg in [*node.args, *(k.value for k in node.keywords)])
        return False
    result = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and reference(n.value):
            result.extend(span(t) for t in n.targets)
        elif isinstance(n, ast.AnnAssign) and (n.value is None or reference(n.value)):
            result.append(span(n.target))
        elif isinstance(n, ast.keyword) and reference(n.value):
            start, _ = span(n)
            result.append((start, start + len(n.arg or '')))
        elif isinstance(n, ast.arg) and n.annotation is not None:
            start, _ = span(n)
            result.append((start, start + len(n.arg)))
        elif isinstance(n, (ast.If, ast.While)) and not literal(n.test):
            start, end = span(n.test)
            if source[end:end + 1] == ':':
                result.append((start, end))
    return tuple(result)
