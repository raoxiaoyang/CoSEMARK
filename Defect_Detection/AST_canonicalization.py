"""AST-level canonicalization for Devign C/C++ JSONL data.

The implementation is deliberately conservative.  Tree-sitter is used to
recognise every code structure and edits are applied to byte ranges in the
original source.  If a stage cannot be validated by reparsing, that stage is
rolled back for the sample.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Optional

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser


DEFAULT_OUTPUT_DIR = "Defect_Detection/Devign/ASTCanonicalization"
DEFAULT_CLANG_FORMAT_MAJOR = 17
PREPROCESSOR_TYPES = {
    "preproc_call",
    "preproc_def",
    "preproc_defined",
    "preproc_directive",
    "preproc_elif",
    "preproc_else",
    "preproc_function_def",
    "preproc_if",
    "preproc_ifdef",
    "preproc_include",
}
LOOP_TYPES = {"for_statement", "for_range_loop", "while_statement", "do_statement"}
BUILTIN_TYPE_NODES = {"primitive_type", "sized_type_specifier"}
LITERAL_TYPES = {
    "number_literal",
    "char_literal",
    "character_literal",
}
BOOL_LITERAL_TYPES = {"true", "false"}
SIDE_EFFECT_TYPES = {
    "assignment_expression",
    "call_expression",
    "co_await_expression",
    "delete_expression",
    "new_expression",
    "throw_expression",
    "update_expression",
}
COMPARISON_OPERATORS = {
    "==": "==",
    "!=": "!=",
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
}
PREPROCESSOR_LINE_RE = re.compile(r"(?m)^[ \t]*#")
PREPROCESSOR_LINE_BYTES_RE = re.compile(rb"(?m)^[ \t]*#")
RAW_STRING_PREFIX_RE = re.compile(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\(')
STRING_PREFIX_RE = re.compile(r'(?:u8|u|U|L)?(["\'])')
EMPTY_FOR_HEADER_RE = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)")


@dataclass(frozen=True)
class Replacement:
    start: int
    end: int
    text: str


def select_non_overlapping_replacements(
    replacements: list[Replacement],
) -> list[Replacement]:
    """Keep the smallest non-overlapping byte edits for a reparsing pass."""
    selected = []
    for item in sorted(
        replacements,
        key=lambda value: (value.end - value.start, value.start),
    ):
        if not any(item.start < other.end and other.start < item.end for other in selected):
            selected.append(item)
    return selected


@dataclass
class DeclItem:
    name: str
    declaration: str
    initializer: Optional[str]
    signature: str


@dataclass
class DeclPlan:
    node: object
    items: list[DeclItem]


@dataclass
class Symbol:
    name: str
    kind: str
    scope: object
    declared_at: int
    indirection: int = 0
    type_name: Optional[str] = None


@dataclass
class SampleReport:
    changed_stages: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)
    formatted: bool = False
    semantic_parenthesis_rewrites: int = 0


@dataclass
class RunStats:
    total: int = 0
    changed: int = 0
    unchanged: int = 0
    initial_parse_failures: int = 0
    final_parse_failures: int = 0
    format_failures: int = 0
    semantic_parenthesis_rewrites: int = 0
    stage_changes: Counter = field(default_factory=Counter)
    skipped_reasons: Counter = field(default_factory=Counter)

    def add(self, original: str, result: str, report: SampleReport) -> None:
        self.total += 1
        if original == result:
            self.unchanged += 1
        else:
            self.changed += 1
        for stage in report.changed_stages:
            self.stage_changes[stage] += 1
        self.skipped_reasons.update(report.skipped)
        self.initial_parse_failures += sum(x.startswith("initial_parse:") for x in report.failures)
        self.final_parse_failures += sum(x.startswith("final_parse:") for x in report.failures)
        self.format_failures += sum(x.startswith("clang_format:") for x in report.failures)
        self.semantic_parenthesis_rewrites += report.semantic_parenthesis_rewrites

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "initial_parse_failures": self.initial_parse_failures,
            "final_parse_failures": self.final_parse_failures,
            "format_failures": self.format_failures,
            "semantic_parenthesis_rewrites": self.semantic_parenthesis_rewrites,
            "stage_changes": dict(sorted(self.stage_changes.items())),
            "skipped_reasons": dict(sorted(self.skipped_reasons.items())),
        }


def make_parser() -> Parser:
    return Parser(Language(tscpp.language()))


def node_text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8")


def walk(node) -> Iterable:
    yield node
    for child in node.children:
        yield from walk(child)


def named_children(node, ignored: set[str] | None = None) -> list:
    ignored = ignored or set()
    return [child for child in node.named_children if child.type not in ignored]


def field_child(node, *names: str):
    for name in names:
        child = node.child_by_field_name(name)
        if child is not None:
            return child
    return None


def field_name(node) -> Optional[str]:
    if node.parent is None:
        return None
    for index, child in enumerate(node.parent.children):
        if child == node:
            return node.parent.field_name_for_child(index)
    return None


def is_preprocessor(node) -> bool:
    if node.type.startswith("preproc_") or node.type in PREPROCESSOR_TYPES:
        return True
    # Some valid real-world macro bodies are recovered by tree-sitter-cpp as
    # one ERROR node whose first tokens are still preprocessor directives.
    return node.type == "ERROR" and any(child.type.startswith("#") for child in node.children)


def under_preprocessor(node) -> bool:
    current = node
    while current is not None:
        if is_preprocessor(current):
            return True
        current = current.parent
    return False


def contains_type(node, types: set[str]) -> bool:
    return any(child.type in types for child in walk(node))


def contains_comment(node) -> bool:
    return any(child.type == "comment" for child in walk(node))


def contains_preprocessor(node) -> bool:
    return any(is_preprocessor(child) for child in walk(node))


def preprocessor_logical_spans(code: str) -> list[tuple[int, int]]:
    """Return complete lexical preprocessor logical lines.

    This deliberately does not depend on Tree-sitter recovery.  Devign also
    contains macro continuations separated by empty physical lines, so those
    empty lines remain part of the protected directive after a trailing
    backslash has been seen.
    """
    spans = []
    index = 0
    length = len(code)
    while index < length:
        line_start = index
        newline = code.find("\n", index)
        line_end = length if newline < 0 else newline + 1
        cursor = line_start
        while cursor < line_end and code[cursor] in " \t":
            cursor += 1
        if cursor >= line_end or code[cursor] != "#":
            index = line_end
            continue

        end = cursor
        physical_line_start = line_start
        continued = False
        while end < length:
            newline = code.find("\n", end)
            if newline < 0:
                end = length
                break
            back = newline - 1
            if back >= physical_line_start and code[back] == "\r":
                back -= 1
            slash_count = 0
            while back >= physical_line_start and code[back] == "\\":
                slash_count += 1
                back -= 1
            blank_line = not code[physical_line_start:newline].strip()
            end = newline + 1
            if slash_count % 2 == 1:
                continued = True
                physical_line_start = end
                continue
            if continued and blank_line:
                physical_line_start = end
                continue
            break
        spans.append((line_start, end))
        index = end
    return spans


def preprocessor_logical_lines(code: str) -> tuple[str, ...]:
    """Return exact directive text used as a transformation invariant."""
    return tuple(code[start:end] for start, end in preprocessor_logical_spans(code))


def crosses_preprocessor_boundary(code: str | bytes, start: int, end: int) -> bool:
    """Return whether moving text across this range crosses a directive.

    Declarations are moved to the beginning of their compound statement.  A
    declaration that is currently before, inside, or after a conditional
    preprocessor region must not cross that region: the declaration and its
    initializer could otherwise end up in different compilation branches.
    """
    if end <= start:
        return False
    if isinstance(code, bytes):
        return PREPROCESSOR_LINE_BYTES_RE.search(code, start, end) is not None
    return PREPROCESSOR_LINE_RE.search(code, start, end) is not None


def is_parse_error_node(node) -> bool:
    return node.type == "ERROR" or node.is_missing


def under_parse_error(node) -> bool:
    current = node
    while current is not None:
        if is_parse_error_node(current):
            return True
        current = current.parent
    return False


def contains_parse_error(node) -> bool:
    return any(is_parse_error_node(child) for child in walk(node))


def parse_issues(tree) -> list[str]:
    issues = []
    for node in walk(tree.root_node):
        if node.type == "ERROR":
            issues.append(f"ERROR@{node.start_point[0] + 1}:{node.start_point[1] + 1}")
        elif node.is_missing:
            issues.append(f"MISSING({node.type})@{node.start_point[0] + 1}:{node.start_point[1] + 1}")
    return issues


def parse_issue_counts(tree) -> tuple[int, int]:
    errors = missing = 0
    for node in walk(tree.root_node):
        errors += node.type == "ERROR"
        missing += bool(node.is_missing)
    return errors, missing


def severe_parse_issues(tree, source_length: int) -> list[str]:
    """Classify errors that make safe source-to-source rewriting impossible.

    Devign contains many compiler macros that Tree-sitter represents as small,
    local ERROR nodes.  Those are tolerated and protected from edits.  Missing
    tokens, a broken root, or an ERROR spanning a substantial source region are
    treated as severe and leave the complete sample unchanged.
    """
    severe = []
    threshold = max(256, source_length // 4)
    for node in walk(tree.root_node):
        if node.is_missing:
            severe.append(f"MISSING({node.type})@{node.start_point[0] + 1}:{node.start_point[1] + 1}")
        elif node.type == "ERROR" and (
            node == tree.root_node or node.end_byte - node.start_byte >= threshold
        ):
            severe.append(f"ERROR@{node.start_point[0] + 1}:{node.start_point[1] + 1}")
    return severe


def introduces_parse_issue(before: str, after: str, parser: Parser) -> tuple[bool, list[str]]:
    before_tree = parser.parse(before.encode("utf-8"))
    after_tree = parser.parse(after.encode("utf-8"))
    before_counts = parse_issue_counts(before_tree)
    after_counts = parse_issue_counts(after_tree)
    introduced = after_counts[0] > before_counts[0] or after_counts[1] > before_counts[1]
    return introduced, parse_issues(after_tree)


def preprocessor_byte_spans(code: str) -> list[tuple[int, int]]:
    """Convert lexical preprocessor spans to UTF-8 byte offsets once."""
    char_spans = preprocessor_logical_spans(code)
    if not char_spans:
        return []
    targets = {point for span in char_spans for point in span}
    offsets = {}
    byte_offset = 0
    for index, char in enumerate(code):
        if index in targets:
            offsets[index] = byte_offset
        byte_offset += len(char.encode("utf-8"))
    if len(code) in targets:
        offsets[len(code)] = byte_offset
    return [(offsets[start], offsets[end]) for start, end in char_spans]


def parentheses_preserved(before: str, after: str) -> bool:
    """Return whether every original parenthesis survives in source order.

    This is the default guard for syntax-preserving edits, fallback processing,
    and formatting.  A rule that proves a semantics-preserving AST rewrite may
    explicitly opt out for its own replacement range.
    """
    required = [char for char in before if char in "()"]
    if not required:
        return True
    matched = 0
    for char in after:
        if char in "()" and char == required[matched]:
            matched += 1
            if matched == len(required):
                return True
    return False


def apply_replacements(
    code: str,
    replacements: list[Replacement],
    *,
    protect_preprocessor: bool = True,
    allow_semantic_parenthesis_change: bool = False,
) -> str:
    """Apply non-overlapping byte edits, excluding lexical directives by default.

    Parentheses are preserved unless the caller has already proved that the
    replacement is a complete, semantics-preserving structural rewrite.  This
    permission is for rules whose result necessarily has a different syntax
    tree (for example ``x = (x) + 1`` to ``x++`` or an expanded LoopStruct back
    to a normal ``for``), never for formatting or redundant-parenthesis cleanup.
    """
    if not replacements:
        return code
    source = code.encode("utf-8")
    if not allow_semantic_parenthesis_change:
        replacements = [
            item
            for item in replacements
            if parentheses_preserved(
                source[item.start:item.end].decode("utf-8"),
                item.text,
            )
        ]
    if not replacements:
        return code
    if protect_preprocessor:
        protected = preprocessor_byte_spans(code)

        def intersects(item: Replacement) -> bool:
            if item.start == item.end:
                return any(start <= item.start < end for start, end in protected)
            return any(item.start < end and start < item.end for start, end in protected)

        replacements = [item for item in replacements if not intersects(item)]
        if not replacements:
            return code
    ordered = sorted(replacements, key=lambda item: (item.start, item.end))
    last_end = -1
    for item in ordered:
        if item.start < last_end and not (item.start == item.end == last_end):
            raise ValueError(f"overlapping replacements at byte {item.start}")
        last_end = max(last_end, item.end)
    result = bytearray(source)
    for item in sorted(replacements, key=lambda value: (value.start, value.end), reverse=True):
        result[item.start:item.end] = item.text.encode("utf-8")
    return result.decode("utf-8")


def replace_whole_line_when_possible(source: bytes, node, text: str) -> Replacement:
    """Avoid leaving an empty source line when a declaration is hoisted."""
    line_start = source.rfind(b"\n", 0, node.start_byte) + 1
    newline = source.find(b"\n", node.end_byte)
    content_end = len(source) if newline < 0 else newline
    before = source[line_start:node.start_byte]
    after = source[node.end_byte:content_end]
    if not before.strip() and not after.strip():
        indent = before.decode("utf-8")
        rendered = ""
        if text:
            rendered = "\n".join(indent + line if line else line for line in text.splitlines())
            if newline >= 0:
                rendered += "\n"
        end = content_end + (1 if newline >= 0 else 0)
        return Replacement(line_start, end, rendered)
    return Replacement(node.start_byte, node.end_byte, text)


def unwrap_parens(node):
    current = node
    while current is not None and current.type == "parenthesized_expression":
        children = named_children(current, {"comment"})
        if len(children) != 1:
            break
        current = children[0]
    return current


def operator_text(source: bytes, node) -> Optional[str]:
    operator = node.child_by_field_name("operator")
    return node_text(source, operator) if operator is not None else None


def same_ast(left, right, source: bytes) -> bool:
    """Structural equality, ignoring only meaningless outer parentheses."""
    left = unwrap_parens(left)
    right = unwrap_parens(right)
    if left is None or right is None or left.type != right.type:
        return False
    left_children = [child for child in left.children if child.type != "comment"]
    right_children = [child for child in right.children if child.type != "comment"]
    if len(left_children) != len(right_children):
        return False
    if not left_children:
        return node_text(source, left) == node_text(source, right)
    for lhs_child, rhs_child in zip(left_children, right_children):
        if lhs_child.is_named != rhs_child.is_named:
            return False
        if lhs_child.is_named:
            if not same_ast(lhs_child, rhs_child, source):
                return False
        elif lhs_child.type != rhs_child.type:
            return False
    return True


def simple_identifier_from_declarator(node, source: bytes) -> Optional[str]:
    current = node
    while current is not None:
        if current.type in {"identifier", "field_identifier"}:
            return node_text(source, current)
        if current.type == "init_declarator":
            current = current.child_by_field_name("declarator")
            continue
        if current.type == "pointer_declarator":
            current = current.child_by_field_name("declarator")
            continue
        if current.type == "array_declarator":
            current = current.child_by_field_name("declarator")
            continue
        return None
    return None


def declarator_is_safe(node, source: bytes, has_initializer: bool) -> bool:
    if contains_type(
        node,
        {
            "abstract_function_declarator",
            "function_declarator",
            "parenthesized_declarator",
            "reference_declarator",
            "structured_binding_declarator",
        },
    ):
        return False
    arrays = [child for child in walk(node) if child.type == "array_declarator"]
    for array in arrays:
        size = array.child_by_field_name("size")
        if size is None or unwrap_parens(size).type != "number_literal":
            return False
        if has_initializer:
            return False
    allowed = {
        "identifier",
        "field_identifier",
        "pointer_declarator",
        "array_declarator",
        "number_literal",
        "parenthesized_expression",
    }
    for child in walk(node):
        if child.is_named and child.type not in allowed:
            return False
    return simple_identifier_from_declarator(node, source) is not None


def declaration_type_prefix(declaration, source: bytes, declarators: list) -> Optional[str]:
    type_node = declaration.child_by_field_name("type")
    if type_node is None or type_node.type not in BUILTIN_TYPE_NODES:
        return None
    forbidden_words = {"auto", "const", "constexpr", "static", "thread_local", "typedef", "using", "volatile", "extern"}
    prefix = source[declaration.start_byte:declarators[0].start_byte].decode("utf-8").strip()
    words = set(re.findall(r"[A-Za-z_]\w*", prefix))
    if words & forbidden_words:
        return None
    if any(
        child.type in {"storage_class_specifier", "type_qualifier", "alias_declaration", "type_definition"}
        for child in declaration.named_children
    ):
        return None
    return prefix


def parse_declaration(declaration, source: bytes, report: SampleReport) -> Optional[DeclPlan]:
    if (
        under_preprocessor(declaration)
        or contains_preprocessor(declaration)
        or under_parse_error(declaration)
        or contains_parse_error(declaration)
        or contains_comment(declaration)
    ):
        report.skipped["declaration:preprocessor_or_comment"] += 1
        return None
    declarators = [
        child
        for child in declaration.named_children
        if field_name(child) == "declarator"
    ]
    if not declarators:
        return None
    prefix = declaration_type_prefix(declaration, source, declarators)
    if prefix is None:
        report.skipped["declaration:unsafe_type_or_qualifier"] += 1
        return None

    items = []
    for outer in declarators:
        initializer = None
        declarator = outer
        if outer.type == "init_declarator":
            declarator = outer.child_by_field_name("declarator")
            value = outer.child_by_field_name("value")
            if declarator is None or value is None:
                report.skipped["declaration:incomplete_initializer"] += 1
                return None
            if value.type in {
                "argument_list",
                "initializer_list",
                "lambda_expression",
                "new_expression",
                "compound_literal_expression",
                "designated_initializer",
            } or contains_type(value, {"initializer_list", "designated_initializer"}):
                report.skipped["declaration:constructor_or_list_initialization"] += 1
                return None
            initializer = node_text(source, value)
        if not declarator_is_safe(declarator, source, initializer is not None):
            report.skipped["declaration:complex_declarator"] += 1
            return None
        name = simple_identifier_from_declarator(declarator, source)
        if name is None:
            return None
        declarator_text = node_text(source, declarator).strip()
        declaration_text = f"{prefix} {declarator_text};"
        signature = re.sub(r"\s+", " ", declaration_text).strip()
        items.append(DeclItem(name, declaration_text, initializer, signature))
    return DeclPlan(declaration, items)


def enclosing_function(node):
    current = node.parent
    while current is not None:
        if current.type == "function_definition":
            return current
        current = current.parent
    return None


def identifier_referenced_before(declaration, block, name: str, source: bytes) -> bool:
    """Return whether hoisting ``name`` would change an earlier name lookup.

    A local declaration hides declarations from surrounding scopes only from
    its declaration point onward.  Moving it to the beginning of the block is
    therefore unsafe when an earlier expression in the same block already
    refers to the same identifier (for example, a global with that name).
    """
    for node in walk(block):
        if node.start_byte >= declaration.start_byte:
            continue
        if node.type != "identifier" or under_preprocessor(node) or under_parse_error(node):
            continue
        if node_text(source, node) == name:
            return True
    return False


def transform_declarations(code: str, parser: Parser, report: SampleReport) -> str:
    source = code.encode("utf-8")
    tree = parser.parse(source)
    replacements: list[Replacement] = []

    for block in walk(tree.root_node):
        if block.type != "compound_statement" or under_preprocessor(block) or enclosing_function(block) is None:
            continue
        direct_declarations = [child for child in block.named_children if child.type == "declaration"]
        if not direct_declarations:
            continue
        plans = [parse_declaration(node, source, report) for node in direct_declarations]
        plans = [plan for plan in plans if plan is not None]
        if not plans:
            continue

        safe_plans = []
        for plan in plans:
            if crosses_preprocessor_boundary(source, block.start_byte, plan.node.start_byte):
                report.skipped["declaration:preprocessor_boundary"] += 1
                continue
            referenced_names = {
                item.name
                for item in plan.items
                if identifier_referenced_before(plan.node, block, item.name, source)
            }
            if referenced_names:
                report.skipped["declaration:earlier_name_reference"] += len(referenced_names)
                continue
            safe_plans.append(plan)
        plans = safe_plans
        if not plans:
            continue

        # A same-name declaration with a different full declarator is a conflict.
        signatures: dict[str, set[str]] = defaultdict(set)
        all_decl_names: Counter = Counter()
        for declaration in direct_declarations:
            for child in declaration.named_children:
                if field_name(child) == "declarator":
                    name = simple_identifier_from_declarator(child, source)
                    if name:
                        all_decl_names[name] += 1
        for plan in plans:
            for item in plan.items:
                signatures[item.name].add(item.signature)
        conflicts = {name for name, values in signatures.items() if len(values) > 1}
        # If an unparsed declaration uses the same name, its complete type is unknown.
        parsed_name_counts = Counter(item.name for plan in plans for item in plan.items)
        conflicts.update(
            name
            for name, count in all_decl_names.items()
            if name in signatures and count > parsed_name_counts[name]
        )
        if conflicts:
            report.skipped["declaration:conflicting_redeclaration"] += len(conflicts)
        plans = [plan for plan in plans if not any(item.name in conflicts for item in plan.items)]
        if not plans:
            continue

        hoisted: list[str] = []
        seen_uninitialized: set[tuple[str, str]] = set()
        for plan in plans:
            initializers = []
            for item in plan.items:
                key = (item.name, item.signature)
                if item.initializer is None and key in seen_uninitialized:
                    report.skipped["declaration:exact_duplicate_removed"] += 1
                else:
                    hoisted.append(item.declaration)
                    if item.initializer is None:
                        seen_uninitialized.add(key)
                if item.initializer is not None:
                    initializers.append(f"{item.name} = {item.initializer};")
            replacements.append(replace_whole_line_when_possible(source, plan.node, "\n".join(initializers)))

        if hoisted:
            open_brace = next((child for child in block.children if child.type == "{"), None)
            if open_brace is not None:
                insert_at = open_brace.end_byte
                if source[insert_at:insert_at + 2] == b"\r\n":
                    insert_at += 2
                    insertion = "\n".join(hoisted) + "\n"
                elif source[insert_at:insert_at + 1] == b"\n":
                    insert_at += 1
                    insertion = "\n".join(hoisted) + "\n"
                else:
                    insertion = "\n" + "\n".join(hoisted) + "\n"
                replacements.append(Replacement(insert_at, insert_at, insertion))

    return apply_replacements(code, replacements) if replacements else code


def lhs_is_safe(node) -> bool:
    node = unwrap_parens(node)
    if (
        node is None
        or contains_type(node, SIDE_EFFECT_TYPES)
        or contains_preprocessor(node)
        or contains_parse_error(node)
    ):
        return False
    if node.type == "identifier":
        return True
    if node.type == "field_expression":
        receiver = field_child(node, "argument", "object")
        field = field_child(node, "field")
        return receiver is not None and field is not None and lhs_receiver_is_safe(receiver)
    if node.type == "subscript_expression":
        base = field_child(node, "argument")
        indices = field_child(node, "indices")
        return base is not None and indices is not None and lhs_receiver_is_safe(base) and expression_has_no_side_effect(indices)
    return False


def lhs_receiver_is_safe(node) -> bool:
    node = unwrap_parens(node)
    if node is None or contains_type(node, SIDE_EFFECT_TYPES):
        return False
    if node.type == "identifier":
        return True
    if node.type in {"field_expression", "subscript_expression"}:
        return lhs_is_safe(node)
    return False


def expression_has_no_side_effect(node) -> bool:
    return (
        not contains_type(node, SIDE_EFFECT_TYPES)
        and not contains_preprocessor(node)
        and not contains_parse_error(node)
    )


def decimal_one(node, source: bytes) -> bool:
    node = unwrap_parens(node)
    return node is not None and node.type == "number_literal" and node_text(source, node) == "1"


def transform_assignments(code: str, parser: Parser, report: SampleReport) -> str:
    source = code.encode("utf-8")
    tree = parser.parse(source)
    symbols = collect_symbols(tree, source)
    field_types = collect_field_types(tree, source)
    replacements = []
    for statement in walk(tree.root_node):
        if (
            statement.type != "expression_statement"
            or under_preprocessor(statement)
            or under_parse_error(statement)
            or contains_parse_error(statement)
            or contains_comment(statement)
        ):
            continue
        expressions = named_children(statement, {"comment"})
        if len(expressions) != 1 or expressions[0].type != "assignment_expression":
            continue
        assignment = expressions[0]
        left = assignment.child_by_field_name("left")
        right = assignment.child_by_field_name("right")
        op = operator_text(source, assignment)
        if left is None or right is None or not lhs_is_safe(left):
            continue
        lhs_text = node_text(source, left)

        if op in {"+=", "-="} and decimal_one(right, source):
            if expression_value_kind(left, source, symbols, field_types) != ("scalar", 0):
                report.skipped["assignment:unknown_or_non_scalar_lhs"] += 1
                continue
            replacement = f"{lhs_text}{'++' if op == '+=' else '--'};"
            replacements.append(Replacement(statement.start_byte, statement.end_byte, replacement))
            continue
        if op != "=":
            continue
        binary = unwrap_parens(right)
        if binary is None or binary.type != "binary_expression" or contains_comment(binary):
            continue
        binary_op = operator_text(source, binary)
        if binary_op not in {"+", "-", "*", "/"}:
            continue
        binary_left = binary.child_by_field_name("left")
        binary_right = binary.child_by_field_name("right")
        if binary_left is None or binary_right is None or not same_ast(left, binary_left, source):
            continue
        if expression_value_kind(left, source, symbols, field_types) != ("scalar", 0):
            report.skipped["assignment:unknown_or_non_scalar_lhs"] += 1
            continue
        if decimal_one(binary_right, source) and binary_op in {"+", "-"}:
            replacement = f"{lhs_text}{'++' if binary_op == '+' else '--'};"
        else:
            replacement = f"{lhs_text} {binary_op}= {node_text(source, binary_right)};"
        replacements.append(Replacement(statement.start_byte, statement.end_byte, replacement))
    if not replacements:
        return code
    rewritten = apply_replacements(
        code,
        replacements,
        allow_semantic_parenthesis_change=True,
    )
    if rewritten != code:
        report.semantic_parenthesis_rewrites += 1
    return rewritten


def negated_break_condition(if_node, source: bytes) -> Optional[str]:
    if if_node.type != "if_statement" or if_node.child_by_field_name("alternative") is not None:
        return None
    consequence = if_node.child_by_field_name("consequence")
    if consequence is None:
        return None
    consequence = unwrap_single_statement_block(consequence)
    if consequence is None or consequence.type != "break_statement":
        return None
    condition = if_node.child_by_field_name("condition")
    if condition is None:
        return None
    if condition.type == "condition_clause":
        condition = field_child(condition, "value") or (named_children(condition, {"comment"})[0] if named_children(condition, {"comment"}) else None)
    condition = unwrap_parens(condition)
    if condition is None or condition.type != "unary_expression" or operator_text(source, condition) != "!":
        return None
    argument = field_child(condition, "argument")
    argument = unwrap_parens(argument)
    return node_text(source, argument).strip() if argument is not None else None


def unwrap_single_statement_block(node):
    if node.type != "compound_statement":
        return node
    children = named_children(node, {"comment"})
    return children[0] if len(children) == 1 else None


def contains_current_loop_continue(body) -> bool:
    def visit(node, root: bool = False) -> bool:
        if not root and node.type in LOOP_TYPES:
            return False
        if not root and node.type in {"lambda_expression", "function_definition"}:
            return False
        if node.type == "continue_statement":
            return True
        return any(visit(child) for child in node.named_children)

    return visit(body, True)


def safe_for_update_statement(node, source: bytes) -> Optional[str]:
    """Return an expression that is safe to move into a for update clause."""
    if node.type != "expression_statement" or contains_comment(node):
        return None
    expressions = named_children(node, {"comment"})
    if len(expressions) != 1:
        return None

    def safe(expression) -> bool:
        expression = unwrap_parens(expression)
        if expression is None:
            return False
        if expression.type in {"assignment_expression", "update_expression"}:
            return True
        if expression.type != "comma_expression":
            return False
        children = named_children(expression, {"comment"})
        return len(children) >= 2 and all(safe(child) for child in children)

    expression = expressions[0]
    return node_text(source, expression).strip() if safe(expression) else None


def rewritten_for_loop(
    loop,
    body,
    source: bytes,
    condition: str,
    update: str,
    removed_statement,
) -> str:
    initializer_node = loop.child_by_field_name("initializer")
    initializer = node_text(source, initializer_node).strip() if initializer_node else ""
    if initializer.endswith(";"):
        initializer = initializer[:-1].rstrip()
    interior = (
        source[body.start_byte + 1:removed_statement.start_byte].decode("utf-8")
        + source[removed_statement.end_byte:body.end_byte - 1].decode("utf-8")
    )
    return f"for ({initializer}; {condition}; {update}) {{{interior}}}"


def apply_semantic_loop_candidates(
    code: str,
    candidates: list[Replacement],
    report: SampleReport,
) -> str:
    if not candidates:
        return code
    selected = select_non_overlapping_replacements(candidates)
    rewritten = apply_replacements(
        code,
        selected,
        allow_semantic_parenthesis_change=True,
    )
    if rewritten != code:
        report.semantic_parenthesis_rewrites += len(selected)
    return rewritten


def transform_missing_for_conditions_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Move a leading ``if (!(cond)) break`` into an empty condition clause."""
    source = code.encode("utf-8")
    tree = parser.parse(source)
    candidates: list[Replacement] = []
    for loop in walk(tree.root_node):
        if (
            loop.type != "for_statement"
            or loop.child_by_field_name("condition") is not None
            or under_preprocessor(loop)
            or under_parse_error(loop)
            or contains_preprocessor(loop)
            or contains_parse_error(loop)
        ):
            continue
        update_node = loop.child_by_field_name("update")
        body = loop.child_by_field_name("body")
        if body is None or body.type != "compound_statement":
            continue
        statements = named_children(body, {"comment"})
        if not statements:
            continue
        guard = statements[0]
        condition = negated_break_condition(guard, source)
        if condition is None:
            continue
        update = node_text(source, update_node).strip() if update_node is not None else ""
        candidates.append(
            Replacement(
                loop.start_byte,
                loop.end_byte,
                rewritten_for_loop(loop, body, source, condition, update, guard),
            )
        )
    return apply_semantic_loop_candidates(code, candidates, report)


def transform_missing_for_conditions(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    return repeat_transform(
        code,
        parser,
        report,
        "for_condition",
        transform_missing_for_conditions_once,
    )


def transform_missing_for_updates_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Move a proven trailing update expression into an empty update clause."""
    source = code.encode("utf-8")
    tree = parser.parse(source)
    candidates: list[Replacement] = []
    for loop in walk(tree.root_node):
        if (
            loop.type != "for_statement"
            or loop.child_by_field_name("update") is not None
            or under_preprocessor(loop)
            or under_parse_error(loop)
            or contains_preprocessor(loop)
            or contains_parse_error(loop)
        ):
            continue
        body = loop.child_by_field_name("body")
        if body is None or body.type != "compound_statement":
            continue
        statements = named_children(body, {"comment"})
        if not statements:
            continue
        update_statement = statements[-1]
        update = safe_for_update_statement(update_statement, source)
        if update is None:
            continue
        if contains_current_loop_continue(body):
            report.skipped["for_update:continue"] += 1
            continue
        condition_node = loop.child_by_field_name("condition")
        condition = node_text(source, condition_node).strip() if condition_node else ""
        candidates.append(
            Replacement(
                loop.start_byte,
                loop.end_byte,
                rewritten_for_loop(
                    loop,
                    body,
                    source,
                    condition,
                    update,
                    update_statement,
                ),
            )
        )
    return apply_semantic_loop_candidates(code, candidates, report)


def transform_missing_for_updates(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    return repeat_transform(
        code,
        parser,
        report,
        "for_update",
        transform_missing_for_updates_once,
    )


def general_for_initializer(
    statement,
    loop,
    container,
    source: bytes,
    report: SampleReport,
) -> Optional[str]:
    """Return an adjacent statement that can safely enter an empty for header."""
    if (
        under_preprocessor(statement)
        or under_parse_error(statement)
        or contains_preprocessor(statement)
        or contains_parse_error(statement)
        or crosses_preprocessor_boundary(source, statement.end_byte, loop.start_byte)
    ):
        return None
    if statement.type == "expression_statement":
        expressions = named_children(statement, {"comment"})
        if len(expressions) != 1:
            return None
        text = node_text(source, statement).strip()
        return text[:-1].rstrip() if text.endswith(";") else None
    if statement.type != "declaration" or contains_comment(statement):
        return None

    # Moving a declaration into a for header shortens its scope.  Restrict this
    # general rule to the same built-in/simple declarations accepted by the
    # declaration canonicalizer, and reject it when any declared name is used
    # after the loop in the current container.  The exact SPBT inverse runs
    # earlier and is not subject to this ordinary-code safeguard because its
    # declaration originally came from the for header.
    plan = parse_declaration(statement, source, report)
    if plan is None:
        return None
    names = {item.name for item in plan.items}
    for node in walk(container):
        if node.start_byte <= loop.end_byte or node.type != "identifier":
            continue
        if under_preprocessor(node) or under_parse_error(node):
            continue
        if node_text(source, node) in names:
            report.skipped["for_initializer:declaration_used_after_loop"] += 1
            return None
    declaration = node_text(source, statement).strip()
    return declaration[:-1].rstrip() if declaration.endswith(";") else None


def transform_missing_for_initializers_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Merge ``init; for (; cond; update)`` without rebuilding the loop body."""
    source = code.encode("utf-8")
    tree = parser.parse(source)
    candidates: list[Replacement] = []
    for loop in walk(tree.root_node):
        if (
            loop.type != "for_statement"
            or loop.child_by_field_name("initializer") is not None
            or (
                loop.child_by_field_name("condition") is None
                and loop.child_by_field_name("update") is None
            )
            or under_preprocessor(loop)
            or under_parse_error(loop)
            or contains_parse_error(loop)
        ):
            continue
        container = loop.parent
        if container is None or container.type not in {"compound_statement", "case_statement"}:
            continue
        statements = named_children(container, {"comment"})
        position = next(
            (
                index
                for index, node in enumerate(statements)
                if node.start_byte == loop.start_byte and node.end_byte == loop.end_byte
            ),
            -1,
        )
        if position <= 0:
            continue
        statement = statements[position - 1]
        initializer = general_for_initializer(
            statement,
            loop,
            container,
            source,
            report,
        )
        if initializer is None:
            continue
        body = loop.child_by_field_name("body")
        search_end = body.start_byte if body is not None else loop.end_byte
        open_paren = source.find(b"(", loop.start_byte, search_end)
        if open_paren < 0:
            continue
        gap = source[statement.end_byte:loop.start_byte].decode("utf-8")
        for_prefix = source[loop.start_byte:open_paren + 1].decode("utf-8")
        candidates.append(
            Replacement(
                statement.start_byte,
                open_paren + 1,
                gap + for_prefix + initializer,
            )
        )
    if not candidates:
        return code
    return apply_replacements(code, candidates)


def transform_missing_for_initializers(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    return repeat_transform(
        code,
        parser,
        report,
        "for_initializer",
        transform_missing_for_initializers_once,
    )


def for_header(node, source: bytes) -> str:
    initializer = node.child_by_field_name("initializer")
    condition = node.child_by_field_name("condition")
    update = node.child_by_field_name("update")
    init_text = node_text(source, initializer).strip() if initializer is not None else ""
    if init_text.endswith(";"):
        init_text = init_text[:-1].rstrip()
    cond_text = node_text(source, condition).strip() if condition is not None else ""
    update_text = node_text(source, update).strip() if update is not None else ""
    return f"for ({init_text}; {cond_text}; {update_text})"


def braced_body(body, source: bytes) -> str:
    text = node_text(source, body)
    if body.type == "compound_statement":
        return text
    if body.type == "expression_statement" and not named_children(body, {"comment"}):
        return "{}"
    return "{\n" + text + "\n}"


def defined_macro_names(code: str) -> set[str]:
    """Return macros defined by complete preprocessor lines in this sample."""
    names = set()
    for start, end in preprocessor_logical_spans(code):
        match = re.match(
            r"[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)",
            code[start:end],
        )
        if match is not None:
            names.add(match.group(1))
    return names


def callable_declarator_name(node, source: bytes) -> Optional[str]:
    """Find the declared function or function-pointer identifier."""
    current = node
    while current is not None:
        if current.type in {"identifier", "field_identifier"}:
            return node_text(source, current)
        nested = current.child_by_field_name("declarator")
        if nested is None and current.type == "parenthesized_declarator":
            nested = next(
                (
                    child
                    for child in current.named_children
                    if child.type in {"pointer_declarator", "function_declarator", "identifier"}
                ),
                None,
            )
        if nested is None:
            return None
        current = nested
    return None


def declared_callable_symbols(tree, source: bytes) -> list[Symbol]:
    """Collect explicitly declared call targets with their lexical scopes."""
    symbols = []
    for node in walk(tree.root_node):
        if (
            node.type != "function_declarator"
            or under_preprocessor(node)
            or under_parse_error(node)
            or contains_parse_error(node)
        ):
            continue
        name = callable_declarator_name(node, source)
        if name is None:
            continue
        parameter = next(
            (ancestor for ancestor in ancestors(node) if ancestor.type == "parameter_declaration"),
            None,
        )
        function = next(
            (ancestor for ancestor in ancestors(node) if ancestor.type == "function_definition"),
            None,
        )
        declaration = next(
            (ancestor for ancestor in ancestors(node) if ancestor.type == "declaration"),
            None,
        )
        if parameter is not None:
            scope = function.child_by_field_name("body") if function is not None else None
            declared_at = scope.start_byte if scope is not None else node.start_byte
        elif declaration is not None:
            owner = next(
                (ancestor for ancestor in ancestors(declaration) if ancestor.type == "function_definition"),
                None,
            )
            if owner is None:
                # File-level declarations belong to a different function's
                # context and are intentionally not used for brace decisions.
                continue
            scope = next(
                (ancestor for ancestor in ancestors(declaration) if ancestor.type == "compound_statement"),
                None,
            )
            declared_at = declaration.start_byte
        elif function is not None:
            scope = function.child_by_field_name("body")
            declared_at = scope.start_byte if scope is not None else function.start_byte
        else:
            continue
        if scope is not None:
            symbols.append(Symbol(name, "callable", scope, declared_at))
    return symbols


def body_is_safe_to_brace(
    body,
    source: bytes,
    macro_names: set[str],
    callable_symbols: list[Symbol],
    value_symbols: list[Symbol],
) -> bool:
    """Reject bodies whose preprocessing behavior cannot be established.

    Ordinary statements remain eligible.  A locally defined macro anywhere in
    the body, a bare identifier statement, or a call target without an explicit
    declaration in this snippet is treated as macro-ambiguous.
    """
    if body.type == "compound_statement":
        return True
    for node in walk(body):
        if node.type == "identifier" and node_text(source, node) in macro_names:
            return False
        if node.type != "call_expression":
            continue
        function = unwrap_parens(node.child_by_field_name("function"))
        if function is None:
            return False
        if function.type == "lambda_expression":
            continue
        if function.type != "identifier":
            return False
        name = node_text(source, function)
        if name in macro_names:
            return False
        # A visible scalar/object declaration shadows a same-name global
        # function.  Only an in-scope callable declaration proves this token is
        # not an unresolved function-like macro invocation.
        if identifier_symbol(function, source, value_symbols) is not None:
            return False
        if identifier_symbol(function, source, callable_symbols) is None:
            return False
    expressions = named_children(body, {"comment"})
    if (
        body.type == "expression_statement"
        and len(expressions) == 1
        and expressions[0].type == "identifier"
    ):
        return False
    return True


def transform_for_loops_once(code: str, parser: Parser, report: SampleReport) -> str:
    source = code.encode("utf-8")
    tree = parser.parse(source)
    macro_names = defined_macro_names(code)
    callable_symbols = declared_callable_symbols(tree, source)
    value_symbols = [
        symbol for symbol in collect_symbols(tree, source) if symbol.scope != tree.root_node
    ]
    candidates = []
    for loop in walk(tree.root_node):
        if (
            loop.type != "for_statement"
            or under_preprocessor(loop)
            or under_parse_error(loop)
            or contains_preprocessor(loop)
            or contains_parse_error(loop)
        ):
            continue
        body = loop.child_by_field_name("body")
        if body is None:
            continue
        rendered_body = (
            braced_body(body, source)
            if body_is_safe_to_brace(
                body, source, macro_names, callable_symbols, value_symbols
            )
            else node_text(source, body)
        )
        replacement = for_header(loop, source) + " " + rendered_body
        original = node_text(source, loop)
        if replacement != original:
            candidates.append(Replacement(loop.start_byte, loop.end_byte, replacement))
    if not candidates:
        return code
    return apply_replacements(code, select_non_overlapping_replacements(candidates))


def transform_for_loops(code: str, parser: Parser, report: SampleReport) -> str:
    return repeat_transform(code, parser, report, "for_loop", transform_for_loops_once)


def control_body_nodes(node) -> list:
    if node.type == "if_statement":
        result = []
        consequence = node.child_by_field_name("consequence")
        if consequence is not None:
            result.append(consequence)
        alternative = node.child_by_field_name("alternative")
        if alternative is not None and alternative.type == "else_clause":
            alternatives = named_children(alternative, {"comment"})
            if alternatives and alternatives[-1].type != "if_statement":
                result.append(alternatives[-1])
        return result
    if node.type in {"while_statement", "do_statement", "for_statement"}:
        body = node.child_by_field_name("body")
        return [body] if body is not None else []
    return []


def transform_control_braces_once(code: str, parser: Parser, report: SampleReport) -> str:
    source = code.encode("utf-8")
    tree = parser.parse(source)
    macro_names = defined_macro_names(code)
    callable_symbols = declared_callable_symbols(tree, source)
    value_symbols = [
        symbol for symbol in collect_symbols(tree, source) if symbol.scope != tree.root_node
    ]
    candidates = []
    for control in walk(tree.root_node):
        if control.type not in {"if_statement", "while_statement", "do_statement", "for_statement"}:
            continue
        if under_preprocessor(control) or under_parse_error(control) or contains_parse_error(control):
            continue
        for body in control_body_nodes(control):
            if body.type == "compound_statement" or under_preprocessor(body) or contains_preprocessor(body):
                continue
            if not body_is_safe_to_brace(
                body, source, macro_names, callable_symbols, value_symbols
            ):
                report.skipped["control_braces:macro_ambiguous_body"] += 1
                continue
            replacement = braced_body(body, source)
            candidates.append(Replacement(body.start_byte, body.end_byte, replacement))
    if not candidates:
        return code
    return apply_replacements(code, select_non_overlapping_replacements(candidates))


def transform_control_braces(code: str, parser: Parser, report: SampleReport) -> str:
    return repeat_transform(code, parser, report, "control_braces", transform_control_braces_once)


def scope_contains(scope, node) -> bool:
    return scope.start_byte <= node.start_byte and node.end_byte <= scope.end_byte


def declarator_indirection(declarator) -> int:
    """Count pointer/array layers between a name and its declared value."""
    if declarator is None:
        return 0
    return sum(
        child.type in {"pointer_declarator", "array_declarator"}
        for child in walk(declarator)
    )


def declaration_kind(declaration, declarator=None) -> Optional[str]:
    type_node = declaration.child_by_field_name("type")
    if type_node is None:
        return None
    if type_node.type not in BUILTIN_TYPE_NODES:
        return "unknown"
    if declarator is not None and contains_type(
        declarator,
        {"function_declarator", "reference_declarator", "structured_binding_declarator"},
    ):
        return "unknown"
    text = type_node.text.decode("utf-8")
    return "bool" if text.strip() == "bool" else "scalar"


def declaration_type_name(declaration, source: bytes) -> Optional[str]:
    type_node = declaration.child_by_field_name("type")
    if type_node is None or type_node.type in BUILTIN_TYPE_NODES:
        return None
    if type_node.type == "type_identifier":
        return node_text(source, type_node)
    if type_node.type in {"struct_specifier", "class_specifier", "union_specifier"}:
        name = type_node.child_by_field_name("name")
        return node_text(source, name) if name is not None else None
    return None


def collect_field_types(tree, source: bytes) -> dict[str, dict[str, tuple[str, int, Optional[str]]]]:
    """Collect fields whose declared type is visible in a local type definition."""
    result: dict[str, dict[str, tuple[str, int, Optional[str]]]] = {}
    ambiguous: set[str] = set()
    for specifier in walk(tree.root_node):
        if specifier.type not in {"struct_specifier", "class_specifier", "union_specifier"}:
            continue
        if under_preprocessor(specifier) or under_parse_error(specifier):
            continue
        name_node = specifier.child_by_field_name("name")
        body = specifier.child_by_field_name("body")
        if name_node is None or body is None:
            continue
        fields: dict[str, tuple[str, int, Optional[str]]] = {}
        for declaration in body.named_children:
            if declaration.type != "field_declaration" or contains_parse_error(declaration):
                continue
            for child in declaration.named_children:
                if field_name(child) != "declarator":
                    continue
                field = simple_identifier_from_declarator(child, source)
                kind = declaration_kind(declaration, child)
                if field and kind:
                    fields[field] = (
                        kind,
                        declarator_indirection(child),
                        declaration_type_name(declaration, source),
                    )
        type_name = node_text(source, name_node)
        if type_name in result:
            ambiguous.add(type_name)
        else:
            result[type_name] = fields
    for type_name in ambiguous:
        result[type_name] = {}
    return result


def collect_symbols(tree, source: bytes) -> list[Symbol]:
    symbols = []
    for node in walk(tree.root_node):
        if under_preprocessor(node) or under_parse_error(node):
            continue
        if node.type == "parameter_declaration":
            declarator = node.child_by_field_name("declarator")
            kind = declaration_kind(node, declarator)
            name = simple_identifier_from_declarator(declarator, source) if declarator is not None else None
            function = next((ancestor for ancestor in ancestors(node) if ancestor.type == "function_definition"), None)
            scope = function.child_by_field_name("body") if function is not None else None
            if name and kind and scope is not None:
                symbols.append(
                    Symbol(
                        name,
                        kind,
                        scope,
                        scope.start_byte,
                        declarator_indirection(declarator),
                        declaration_type_name(node, source),
                    )
                )
        elif node.type == "declaration":
            # Declarations in for/if/switch initializers have a narrower scope
            # than the surrounding compound statement; leave them unresolved.
            if node.parent is None or node.parent.type not in {"compound_statement", "translation_unit"}:
                continue
            if node.parent.type == "compound_statement":
                function = enclosing_function(node)
                scope = next(
                    (ancestor for ancestor in ancestors(node) if ancestor.type == "compound_statement"),
                    None,
                )
                if function is None:
                    continue
            else:
                scope = tree.root_node
            if scope is None:
                continue
            for child in node.named_children:
                if field_name(child) == "declarator":
                    declarator = child.child_by_field_name("declarator") if child.type == "init_declarator" else child
                    kind = declaration_kind(node, declarator)
                    name = simple_identifier_from_declarator(child, source)
                    if name and kind:
                        symbols.append(
                            Symbol(
                                name,
                                kind,
                                scope,
                                node.start_byte,
                                declarator_indirection(declarator),
                                declaration_type_name(node, source),
                            )
                        )
    return symbols


def ancestors(node) -> Iterable:
    current = node.parent
    while current is not None:
        yield current
        current = current.parent


def identifier_symbol(node, source: bytes, symbols: list[Symbol]) -> Optional[Symbol]:
    if node.type != "identifier":
        return None
    name = node_text(source, node)
    candidates = [
        symbol
        for symbol in symbols
        if symbol.name == name and scope_contains(symbol.scope, node) and symbol.declared_at <= node.start_byte
    ]
    if not candidates:
        return None
    # Innermost scope, then latest visible declaration.
    return min(candidates, key=lambda item: (item.scope.end_byte - item.scope.start_byte, -item.declared_at))


def identifier_kind(node, source: bytes, symbols: list[Symbol]) -> Optional[str]:
    symbol = identifier_symbol(node, source, symbols)
    if symbol is None or symbol.indirection != 0:
        return None
    return symbol.kind


def expression_type(
    node,
    source: bytes,
    symbols: list[Symbol],
    field_types: dict[str, dict[str, tuple[str, int, Optional[str]]]],
) -> Optional[tuple[str, int, Optional[str]]]:
    node = unwrap_parens(node)
    if node is None:
        return None
    if node.type == "identifier":
        symbol = identifier_symbol(node, source, symbols)
        if symbol is None:
            return None
        return symbol.kind, symbol.indirection, symbol.type_name
    if node.type == "subscript_expression":
        base = field_child(node, "argument")
        indices = field_child(node, "indices")
        if base is None or indices is None or not expression_has_no_side_effect(indices):
            return None
        base_type = expression_type(base, source, symbols, field_types)
        if base_type is None or base_type[1] <= 0:
            return None
        return base_type[0], base_type[1] - 1, base_type[2]
    if node.type == "field_expression":
        receiver = field_child(node, "argument", "object")
        field = field_child(node, "field")
        operator = operator_text(source, node)
        if receiver is None or field is None or operator not in {".", "->"}:
            return None
        receiver_type = expression_type(receiver, source, symbols, field_types)
        if receiver_type is None or receiver_type[2] is None:
            return None
        required_indirection = 0 if operator == "." else 1
        if receiver_type[1] != required_indirection:
            return None
        return field_types.get(receiver_type[2], {}).get(node_text(source, field))
    return None


def expression_value_kind(
    node,
    source: bytes,
    symbols: list[Symbol],
    field_types: dict[str, dict[str, tuple[str, int, Optional[str]]]],
) -> Optional[tuple[str, int]]:
    """Resolve the conservative built-in value kind of an assignable expression.

    Fields are intentionally unresolved without semantic type information.
    Array/pointer indexing is accepted only when the base is a known built-in
    declaration and every index operation removes one known indirection layer.
    """
    resolved = expression_type(node, source, symbols, field_types)
    return (resolved[0], resolved[1]) if resolved is not None else None


def known_bool_expression(node, source: bytes, symbols: list[Symbol]) -> bool:
    node = unwrap_parens(node)
    if node is None:
        return False
    if node.type in BOOL_LITERAL_TYPES:
        return True
    if node.type == "identifier":
        return identifier_kind(node, source, symbols) == "bool"
    if node.type == "unary_expression" and operator_text(source, node) == "!":
        argument = node.child_by_field_name("argument")
        return argument is not None and known_bool_expression(argument, source, symbols)
    if node.type == "binary_expression":
        op = operator_text(source, node)
        if op in {"==", "!=", "<", "<=", ">", ">="}:
            return known_scalar_expression(node.child_by_field_name("left"), source, symbols) and known_scalar_expression(
                node.child_by_field_name("right"), source, symbols
            )
        if op in {"&&", "||"}:
            return known_bool_expression(node.child_by_field_name("left"), source, symbols) and known_bool_expression(
                node.child_by_field_name("right"), source, symbols
            )
    return False


def known_scalar_expression(node, source: bytes, symbols: list[Symbol]) -> bool:
    node = unwrap_parens(node)
    if node is None or contains_type(node, SIDE_EFFECT_TYPES):
        return False
    if node.type in LITERAL_TYPES or node.type in BOOL_LITERAL_TYPES:
        return True
    if node.type == "identifier":
        return identifier_kind(node, source, symbols) in {"bool", "scalar"}
    if node.type == "unary_expression":
        op = operator_text(source, node)
        argument = node.child_by_field_name("argument")
        return op in {"+", "-", "!", "~"} and known_scalar_expression(argument, source, symbols)
    if node.type == "binary_expression":
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        return known_scalar_expression(left, source, symbols) and known_scalar_expression(right, source, symbols)
    return False


def condition_value(control):
    condition = control.child_by_field_name("condition")
    if condition is None:
        return None
    if condition.type == "condition_clause":
        return condition.child_by_field_name("value") or next(iter(named_children(condition, {"comment"})), None)
    return unwrap_parens(condition) if control.type == "do_statement" else condition


def within_condition(node) -> bool:
    current = node.parent
    while current is not None:
        if current.type in {"if_statement", "while_statement", "do_statement", "for_statement"}:
            condition = condition_value(current)
            return condition is not None and condition.start_byte <= node.start_byte and node.end_byte <= condition.end_byte
        if current.type in {"compound_statement", "function_definition"}:
            return False
        current = current.parent
    return False


def boolean_simplification(node, source: bytes, symbols: list[Symbol]) -> Optional[str]:
    if node.type != "binary_expression" or operator_text(source, node) not in {"==", "!="}:
        return None
    left = unwrap_parens(node.child_by_field_name("left"))
    right = unwrap_parens(node.child_by_field_name("right"))
    if left is None or right is None:
        return None
    literal = expression = None
    if left.type in BOOL_LITERAL_TYPES:
        literal, expression = left, right
    elif right.type in BOOL_LITERAL_TYPES:
        literal, expression = right, left
    if literal is None or not known_bool_expression(expression, source, symbols):
        return None
    literal_value = literal.type == "true"
    keep_positive = (operator_text(source, node) == "==") == literal_value
    text = node_text(source, expression)
    if keep_positive:
        return text
    atomic = unwrap_parens(expression).type in {"identifier", "true", "false"}
    return f"!{text}" if atomic else f"!({text})"


def transform_conditions_once(code: str, parser: Parser, report: SampleReport) -> str:
    source = code.encode("utf-8")
    tree = parser.parse(source)
    symbols = collect_symbols(tree, source)
    candidates = []
    for node in walk(tree.root_node):
        if (
            node.type != "binary_expression"
            or under_preprocessor(node)
            or under_parse_error(node)
            or contains_parse_error(node)
            or contains_comment(node)
        ):
            continue
        if within_condition(node):
            simplified = boolean_simplification(node, source, symbols)
            if simplified is not None:
                candidates.append(Replacement(node.start_byte, node.end_byte, simplified))
                continue
        op = operator_text(source, node)
        if op not in COMPARISON_OPERATORS:
            continue
        left = unwrap_parens(node.child_by_field_name("left"))
        right = unwrap_parens(node.child_by_field_name("right"))
        if left is None or right is None or left.type not in LITERAL_TYPES or right.type in LITERAL_TYPES:
            continue
        if not known_scalar_expression(right, source, symbols):
            report.skipped["comparison:unknown_or_non_scalar_rhs"] += 1
            continue
        replacement = f"{node_text(source, right)} {COMPARISON_OPERATORS[op]} {node_text(source, left)}"
        candidates.append(Replacement(node.start_byte, node.end_byte, replacement))
    if not candidates:
        return code
    return apply_replacements(code, select_non_overlapping_replacements(candidates))


def transform_conditions(code: str, parser: Parser, report: SampleReport) -> str:
    return repeat_transform(code, parser, report, "conditions", transform_conditions_once)


def transform_cleanup_once(code: str, parser: Parser, report: SampleReport) -> str:
    """Remove empty statements without ever rewriting parentheses."""
    source = code.encode("utf-8")
    tree = parser.parse(source)
    candidates = []
    for node in walk(tree.root_node):
        if node.type == "compound_statement" and not under_preprocessor(node) and not under_parse_error(node):
            for statement in node.named_children:
                if statement.type == "expression_statement" and not named_children(statement, {"comment"}) and node_text(source, statement).strip() == ";":
                    candidates.append(Replacement(statement.start_byte, statement.end_byte, ""))
    if not candidates:
        return code
    return apply_replacements(code, select_non_overlapping_replacements(candidates))


def transform_cleanup(code: str, parser: Parser, report: SampleReport) -> str:
    return repeat_transform(code, parser, report, "cleanup", transform_cleanup_once)


def repeat_transform(
    code: str,
    parser: Parser,
    report: SampleReport,
    stage: str,
    transform: Callable[[str, Parser, SampleReport], str],
    limit: int = 32,
) -> str:
    current = code
    for _ in range(limit):
        updated = transform(current, parser, report)
        if updated == current:
            return current
        current = updated
    report.failures.append(f"{stage}:iteration_limit")
    return current


def run_stage(
    code: str,
    parser: Parser,
    report: SampleReport,
    name: str,
    transform: Callable[[str, Parser, SampleReport], str],
) -> str:
    before = code
    try:
        after = transform(before, parser, report)
    except Exception as error:  # A malformed sample must not stop the dataset run.
        report.failures.append(f"{name}:exception:{type(error).__name__}:{error}")
        return before
    if after == before:
        return before
    report.changed_stages.append(name)
    return after


@lru_cache(maxsize=None)
def find_clang_format(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    found = shutil.which("clang-format")
    if found:
        return found
    try:
        result = subprocess.run(
            ["xcrun", "--find", "clang-format"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


@lru_cache(maxsize=None)
def clang_format_major(executable: str) -> Optional[int]:
    try:
        result = subprocess.run(
            [executable, "--version"], check=True, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(?:version|clang-format)\s+(\d+)", result.stdout)
    return int(match.group(1)) if match else None


def outer_preprocessor_nodes(tree) -> list:
    result = []
    for node in walk(tree.root_node):
        if not is_preprocessor(node):
            continue
        if any(is_preprocessor(parent) for parent in ancestors(node)):
            continue
        result.append(node)
    return result


def format_code(
    code: str,
    parser: Parser,
    executable: Optional[str],
    required_major: int,
    project_root: Path,
) -> tuple[str, Optional[str]]:
    executable = find_clang_format(executable)
    if not executable:
        return code, "not_found"
    actual_major = clang_format_major(executable)
    if actual_major != required_major:
        return code, f"version_mismatch:expected={required_major},actual={actual_major}"

    source = code.encode("utf-8")
    tree = parser.parse(source)
    replacements = []
    protected: dict[str, str] = {}
    for index, node in enumerate(outer_preprocessor_nodes(tree)):
        # A complete line comment keeps clang-format from joining the following
        # declaration to the placeholder.  The exact directive text is restored
        # after formatting.
        original = node_text(source, node)
        marker = f"//__ASTC_PREPROCESSOR_{index:06d}__"
        placeholder = marker + ("\n" if original.endswith(("\n", "\r")) else "")
        protected[placeholder] = original
        replacements.append(Replacement(node.start_byte, node.end_byte, placeholder))
    masked = (
        apply_replacements(code, replacements, protect_preprocessor=False)
        if replacements
        else code
    )

    # Inherit the project's .clang-format when present and fall back to LLVM,
    # but never let formatting rewrite one string literal into multiple
    # adjacent literals.  ASTC promises to leave literal contents and token
    # boundaries untouched.
    style_arg = "{BasedOnStyle: InheritParentConfig, BreakStringLiterals: false}"
    assume_filename = project_root / "astc_input.cpp"
    try:
        result = subprocess.run(
            [
                executable,
                f"-style={style_arg}",
                "-fallback-style=LLVM",
                f"-assume-filename={assume_filename}",
            ],
            input=masked,
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
            cwd=project_root,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return code, f"execution_failed:{error}"
    formatted = result.stdout
    for token, original in protected.items():
        if token not in formatted:
            return code, f"preprocessor_placeholder_lost:{token}"
        formatted = formatted.replace(token, original)
    if preprocessor_logical_lines(formatted) != preprocessor_logical_lines(code):
        return code, "preprocessor_changed"
    return formatted, None


def mask_fallback_protected_text(code: str) -> str:
    """Mask text that the non-AST fallback must never inspect or rewrite.

    The mask preserves character offsets and newlines.  It recognizes ordinary
    C/C++ comments, quoted literals, raw string literals, and complete logical
    preprocessor lines (including backslash continuations).
    """
    masked = list(code)

    def hide(start: int, end: int) -> None:
        for index in range(start, end):
            if masked[index] not in {"\n", "\r"}:
                masked[index] = " "

    index = 0
    line_start = True
    length = len(code)
    while index < length:
        if line_start:
            cursor = index
            while cursor < length and code[cursor] in " \t":
                cursor += 1
            if cursor < length and code[cursor] == "#":
                end = cursor
                physical_line_start = cursor
                continued = False
                while end < length:
                    newline = code.find("\n", end)
                    if newline < 0:
                        end = length
                        break
                    back = newline - 1
                    if back >= 0 and code[back] == "\r":
                        back -= 1
                    slash_count = 0
                    while back >= physical_line_start and code[back] == "\\":
                        slash_count += 1
                        back -= 1
                    end = newline + 1
                    blank_line = not code[physical_line_start:newline].strip()
                    if slash_count % 2 == 1:
                        continued = True
                        physical_line_start = end
                        continue
                    # Devign snippets sometimes contain an empty physical line
                    # between every original macro-continuation line.  Treat
                    # those blank lines as part of the protected directive.
                    if continued and blank_line:
                        physical_line_start = end
                        continue
                    if slash_count % 2 == 0:
                        break
                hide(cursor, end)
                index = end
                line_start = True
                continue

        if code.startswith("//", index):
            end = code.find("\n", index + 2)
            end = length if end < 0 else end
            hide(index, end)
            index = end
            continue
        if code.startswith("/*", index):
            end = code.find("*/", index + 2)
            end = length if end < 0 else end + 2
            hide(index, end)
            line_start = "\n" in code[index:end]
            index = end
            continue

        raw_match = RAW_STRING_PREFIX_RE.match(code, index)
        if raw_match:
            delimiter = raw_match.group(1)
            end_token = ")" + delimiter + '"'
            end = code.find(end_token, raw_match.end())
            end = length if end < 0 else end + len(end_token)
            hide(index, end)
            line_start = "\n" in code[index:end]
            index = end
            continue

        prefix_match = STRING_PREFIX_RE.match(code, index)
        if prefix_match:
            quote = prefix_match.group(1)
            end = prefix_match.end()
            escaped = False
            while end < length:
                char = code[end]
                end += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    break
            hide(index, end)
            line_start = "\n" in code[index:end]
            index = end
            continue

        line_start = code[index] == "\n"
        index += 1
    return "".join(masked)


def apply_character_replacements(
    code: str,
    replacements: list[tuple[int, int, str]],
    *,
    allow_semantic_parenthesis_change: bool = False,
) -> str:
    if not replacements:
        return code
    if not allow_semantic_parenthesis_change:
        replacements = [
            item
            for item in replacements
            if parentheses_preserved(code[item[0]:item[1]], item[2])
        ]
    if not replacements:
        return code
    ordered = sorted(replacements, key=lambda item: (item[0], item[1]))
    if any(right[0] < left[1] for left, right in zip(ordered, ordered[1:])):
        raise ValueError("overlapping fallback replacements")
    result = code
    for start, end, text in reversed(ordered):
        result = result[:start] + text + result[end:]
    return result


def select_non_overlapping_character_replacements(
    replacements: list[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    """Keep the smallest non-overlapping character edits for a lexical pass."""
    selected = []
    for item in sorted(
        replacements,
        key=lambda value: (value[1] - value[0], value[0]),
    ):
        if not any(item[0] < other[1] and other[0] < item[1] for other in selected):
            selected.append(item)
    return selected


FALLBACK_SCALAR_DECLARATION = re.compile(
    r"\b(?:signed\s+|unsigned\s+|short\s+|long\s+)*"
    r"(?:char|int|float|double|size_t|ptrdiff_t|u?int(?:8|16|32|64)_t)"
    r"\s+([A-Za-z_]\w*)\b(?!\s*[\[(*])"
)
FALLBACK_ATOM = r"(?:[A-Za-z_]\w*|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?[uUlLfF]*)"

FALLBACK_DECLARATION_PREFIX = (
    r"(?:signed\s+|unsigned\s+|short\s+|long\s+)*"
    r"(?:char|int|float|double|bool|size_t|ptrdiff_t|u?int(?:8|16|32|64)_t)"
)


def fallback_matching_delimiters(mask: str) -> dict[int, int]:
    """Return pairs for delimiters that remain balanced in the lexical mask."""
    pairs: dict[int, int] = {}
    stack: list[tuple[str, int]] = []
    closing = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(mask):
        if char in "([{":
            stack.append((char, index))
        elif char in closing:
            if stack and stack[-1][0] == closing[char]:
                _, start = stack.pop()
                pairs[start] = index
                pairs[index] = start
            else:
                # Do not let one malformed region manufacture pairs across it.
                stack.clear()
    return pairs


def fallback_split_top_level(text: str, delimiter: str) -> list[str]:
    result = []
    start = 0
    stack = []
    closing = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(text):
        if char in "([{":
            stack.append(char)
        elif char in closing:
            if not stack or stack[-1] != closing[char]:
                return [text]
            stack.pop()
        elif char == delimiter and not stack:
            result.append(text[start:index])
            start = index + 1
    if stack:
        return [text]
    result.append(text[start:])
    return result


def fallback_function_blocks(mask: str) -> list[tuple[int, int]]:
    """Find balanced blocks lexically enclosed by a function-like body."""
    pairs = fallback_matching_delimiters(mask)
    braces = sorted((start, end) for start, end in pairs.items() if start < end and mask[start] == "{")
    roots = []
    control_words = {"if", "for", "while", "switch", "catch"}
    for start, end in braces:
        cursor = start - 1
        while cursor >= 0 and mask[cursor].isspace():
            cursor -= 1
        if cursor < 0 or mask[cursor] != ")" or cursor not in pairs:
            continue
        open_paren = pairs[cursor]
        prefix = mask[:open_paren].rstrip()
        word = re.search(r"([A-Za-z_]\w*)\s*$", prefix)
        if word is not None and word.group(1) in control_words:
            continue
        roots.append((start, end))
    return [
        (start, end)
        for start, end in braces
        if any(root_start <= start and end <= root_end for root_start, root_end in roots)
    ]


def fallback_direct_statement_spans(mask: str, block_start: int, block_end: int) -> list[tuple[int, int]]:
    """Return semicolon-terminated statements directly contained by a block."""
    pairs = fallback_matching_delimiters(mask)
    spans = []
    statement_start = block_start + 1
    index = statement_start
    while index < block_end:
        char = mask[index]
        if char in "([":
            close = pairs.get(index)
            if close is None or close >= block_end:
                index += 1
            else:
                index = close + 1
            continue
        if char == "{":
            close = pairs.get(index)
            if close is None or close >= block_end:
                index += 1
            else:
                index = close + 1
                statement_start = index
            continue
        if char == ";":
            spans.append((statement_start, index + 1))
            statement_start = index + 1
        index += 1
    return spans


def fallback_parse_declaration(text: str) -> Optional[tuple[str, list[tuple[str, str, Optional[str], bool]]]]:
    """Parse the deliberately small declaration grammar shared with the AST rule."""
    match = re.fullmatch(
        rf"\s*({FALLBACK_DECLARATION_PREFIX})\s+(.+?)\s*;\s*",
        text,
        re.DOTALL,
    )
    if match is None:
        return None
    prefix = re.sub(r"\s+", " ", match.group(1)).strip()
    items = []
    for raw_item in fallback_split_top_level(match.group(2), ","):
        item = re.fullmatch(
            r"\s*(\*+\s*)?([A-Za-z_]\w*)(\s*\[\s*\d+\s*\])?"
            r"(?:\s*=\s*(.+))?\s*",
            raw_item,
            re.DOTALL,
        )
        if item is None:
            return None
        pointer, name, array, initializer = item.groups()
        if initializer is not None and (array or "{" in initializer or "}" in initializer):
            return None
        declarator = f"{pointer or ''}{name}{array or ''}".strip()
        items.append((name, declarator, initializer.strip() if initializer else None, bool(pointer)))
    return (prefix, items) if items else None


def fallback_transform_declarations(code: str, report: SampleReport) -> str:
    """Split and hoist simple built-in declarations inside balanced function blocks."""
    mask = mask_fallback_protected_text(code)
    replacements: list[tuple[int, int, str]] = []
    insertions: dict[int, list[str]] = defaultdict(list)
    for block_start, block_end in fallback_function_blocks(mask):
        declaration_prefix = True
        for span_start, span_end in fallback_direct_statement_spans(mask, block_start, block_end):
            segment = mask[span_start:span_end]
            leading = len(segment) - len(segment.lstrip())
            parsed = fallback_parse_declaration(segment[leading:])
            if parsed is None:
                if segment.strip():
                    declaration_prefix = False
                continue
            original_segment = code[span_start + leading:span_end]
            original_parsed = fallback_parse_declaration(original_segment)
            if original_parsed is None:
                report.skipped["fallback_declaration:original_parse_failed"] += 1
                continue
            prefix, items = original_parsed
            masked_names = [name for name, *_ in parsed[1]]
            original_names = [name for name, *_ in items]
            if masked_names != original_names:
                report.skipped["fallback_declaration:original_parse_mismatch"] += 1
                continue
            if declaration_prefix and all(initializer is None for _, _, initializer, _ in items):
                continue
            declaration_start = span_start + leading
            if crosses_preprocessor_boundary(code, block_start, declaration_start):
                report.skipped["fallback_declaration:preprocessor_boundary"] += 1
                continue
            before = mask[block_start + 1:declaration_start]
            if any(re.search(rf"\b{re.escape(name)}\b", before) for name, *_ in items):
                report.skipped["fallback_declaration:earlier_name_reference"] += 1
                continue
            line_start = code.rfind("\n", span_start, declaration_start) + 1
            indent_match = re.match(r"[ \t]*", code[line_start:declaration_start])
            indent = indent_match.group(0) if indent_match else ""
            assignments = [f"{name} = {initializer};" for name, _, initializer, _ in items if initializer]
            replacement = ("\n" + indent).join(assignments)
            replacements.append((declaration_start, span_end, replacement))
            insertions[block_start].extend(f"{prefix} {declarator};" for _, declarator, _, _ in items)

    for block_start, declarations in insertions.items():
        if not declarations:
            continue
        after = block_start + 1
        if code.startswith("\r\n", after):
            after += 2
        elif code.startswith("\n", after):
            after += 1
        child_indent = "    "
        for span_start, _ in fallback_direct_statement_spans(mask, block_start, fallback_matching_delimiters(mask).get(block_start, block_start)):
            line_start = code.rfind("\n", block_start + 1, span_start) + 1
            found = re.match(r"[ \t]*", code[line_start:span_start])
            if found and found.group(0):
                child_indent = found.group(0)
                break
        insertion = "".join(child_indent + declaration + "\n" for declaration in declarations)
        replacements.append((after, after, insertion))
    if replacements:
        report.skipped["fallback:declarations"] += 1
    return apply_character_replacements(code, replacements)


def fallback_scalar_names(mask: str) -> set[str]:
    names = set(FALLBACK_SCALAR_DECLARATION.findall(mask))
    declaration = re.compile(rf"\b{FALLBACK_DECLARATION_PREFIX}\s+([^;{{}}]+);")
    for match in declaration.finditer(mask):
        parsed = fallback_parse_declaration(match.group(0))
        if parsed is None:
            continue
        names.update(name for name, _, _, pointer in parsed[1] if not pointer)
    return names


FALLBACK_LHS = r"[A-Za-z_]\w*(?:(?:\.|->)[A-Za-z_]\w*|\[[^\[\]\n;]+\])*"


def fallback_lhs_is_scalar(lhs: str, scalar_names: set[str]) -> bool:
    identifiers = re.findall(r"[A-Za-z_]\w*", lhs)
    return bool(identifiers) and (identifiers[0] in scalar_names or identifiers[-1] in scalar_names)


def fallback_rhs_binds_to_lhs_operator(rhs: str, operator: str) -> bool:
    """Check that ``lhs op rhs`` has the same root operator as the AST rule."""
    stack = []
    top_level = []
    closing = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(rhs):
        if char in "([{":
            stack.append(char)
        elif char in closing:
            if not stack or stack[-1] != closing[char]:
                return False
            stack.pop()
        elif not stack and char in "+-*/?:,=":
            # A sign at the beginning of the right operand is unary.
            if char in "+-" and not rhs[:index].strip():
                continue
            top_level.append(char)
    if stack or any(char in "?:,=" for char in top_level):
        return False
    if operator in "+-":
        return not any(char in "+-" for char in top_level)
    return not any(char in "+-*/" for char in top_level)


def fallback_transform_assignments(code: str, report: SampleReport) -> str:
    mask = mask_fallback_protected_text(code)
    scalar_names = fallback_scalar_names(mask)
    replacements: list[tuple[int, int, str]] = []
    update_pattern = re.compile(rf"(?<![A-Za-z0-9_.>])({FALLBACK_LHS})\s*(\+=|-=)\s*1\s*;")
    for match in update_pattern.finditer(mask):
        lhs, operator = match.group(1), match.group(2)
        if fallback_lhs_is_scalar(lhs, scalar_names):
            replacements.append((match.start(), match.end(), f"{lhs}{'++' if operator == '+=' else '--'};"))
    current = apply_character_replacements(code, replacements)

    mask = mask_fallback_protected_text(current)
    scalar_names = fallback_scalar_names(mask)
    replacements = []
    assignment_pattern = re.compile(
        rf"(?<![A-Za-z0-9_.>])(?P<lhs>{FALLBACK_LHS})\s*=\s*(?P=lhs)\s*"
        rf"(?P<operator>[+\-*/])\s*(?P<rhs>[^;{{}}]+?)\s*;",
        re.DOTALL,
    )
    for match in assignment_pattern.finditer(mask):
        lhs = match.group("lhs")
        operator = match.group("operator")
        rhs_mask = match.group("rhs").strip()
        if not fallback_lhs_is_scalar(lhs, scalar_names) or not fallback_rhs_binds_to_lhs_operator(rhs_mask, operator):
            continue
        rhs_start, rhs_end = match.span("rhs")
        while rhs_start < rhs_end and current[rhs_start].isspace():
            rhs_start += 1
        while rhs_end > rhs_start and current[rhs_end - 1].isspace():
            rhs_end -= 1
        rhs = current[rhs_start:rhs_end]
        replacement = (
            f"{lhs}{'++' if operator == '+' else '--'};"
            if rhs == "1" and operator in {"+", "-"}
            else f"{lhs} {operator}= {rhs};"
        )
        replacements.append((match.start(), match.end(), replacement))
    if replacements or current != code:
        report.skipped["fallback:assignments"] += 1
    return apply_character_replacements(current, replacements)


def fallback_transform_conditions(code: str, report: SampleReport) -> str:
    current = code
    mask = mask_fallback_protected_text(current)
    scalar_names = fallback_scalar_names(mask)
    replacements = []
    comparison_pattern = re.compile(
        rf"(?<![A-Za-z0-9_.>])(?P<literal>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?[uUlLfF]*)"
        rf"\s*(?P<operator>==|!=|<=|>=|<|>)\s*(?P<rhs>{FALLBACK_LHS})"
    )
    for condition_start, condition_end in fallback_condition_spans(mask):
        for match in comparison_pattern.finditer(mask, condition_start, condition_end):
            rhs = match.group("rhs")
            if not fallback_lhs_is_scalar(rhs, scalar_names):
                continue
            prefix = mask[condition_start:match.start()].rstrip()
            suffix = mask[match.end():condition_end].lstrip()
            if prefix and not prefix.endswith(("(", "&&", "||", "!")):
                continue
            if suffix and not suffix.startswith((")", "&&", "||")):
                continue
            replacements.append(
                (match.start(), match.end(), f"{rhs} {COMPARISON_OPERATORS[match.group('operator')]} {match.group('literal')}")
            )
    current = apply_character_replacements(current, replacements)

    mask = mask_fallback_protected_text(current)
    bool_names = set()
    for declaration in re.finditer(r"\bbool\s+([^;{}]+);", mask):
        parsed = fallback_parse_declaration(declaration.group(0))
        if parsed:
            bool_names.update(name for name, _, _, pointer in parsed[1] if not pointer)
    replacements = []
    boolean_pattern = re.compile(r"\b([A-Za-z_]\w*)\s*(==|!=)\s*(true|false)\b")
    for condition_start, condition_end in fallback_condition_spans(mask):
        for match in boolean_pattern.finditer(mask, condition_start, condition_end):
            name, operator, literal = match.groups()
            if name not in bool_names:
                continue
            positive = (operator == "==") == (literal == "true")
            replacements.append((match.start(), match.end(), name if positive else f"!{name}"))
    if replacements or current != code:
        report.skipped["fallback:conditions"] += 1
    return apply_character_replacements(current, replacements)


def lexical_statement_kind(text: str, parser: Parser) -> Optional[str]:
    """Classify one isolated statement without trusting the surrounding AST."""
    wrapper = f"void __astc_statement__() {{\n{text}\n}}"
    tree = parser.parse(wrapper.encode("utf-8"))
    if parse_issue_counts(tree) != (0, 0):
        return None
    function = next(
        (node for node in tree.root_node.named_children if node.type == "function_definition"),
        None,
    )
    body = function.child_by_field_name("body") if function is not None else None
    statements = named_children(body, {"comment"}) if body is not None else []
    return statements[0].type if len(statements) == 1 else None


def lexical_initializer_start(
    mask: str,
    for_start: int,
    pairs: dict[int, int],
) -> Optional[tuple[int, int]]:
    """Find the statement immediately preceding an expanded empty ``for``."""
    cursor = for_start - 1
    while cursor >= 0 and mask[cursor].isspace():
        cursor -= 1
    if cursor < 0 or mask[cursor] != ";":
        return None
    end = cursor + 1
    cursor -= 1
    while cursor >= 0:
        char = mask[cursor]
        if char in ")]":
            opening = pairs.get(cursor)
            if opening is None:
                return None
            cursor = opening - 1
            continue
        if char in ";{}":
            break
        cursor -= 1
    start = cursor + 1

    # A case/default or ordinary label may own both the initializer and loop.
    # Keep that label in place and move only the generated initializer.
    segment = mask[start:end]
    label = re.match(
        r"\s*(?:(?:case\b[^:\n]*|default|[A-Za-z_]\w*)\s*:)\s*",
        segment,
    )
    if label is not None:
        start += label.end()
    while start < end and mask[start].isspace():
        start += 1
    return (start, end) if start < end else None


def lexical_initializer_parts(
    code: str,
    mask: str,
    start: int,
    end: int,
    pairs: dict[int, int],
    parser: Parser,
) -> Optional[tuple[str, str]]:
    """Return ``(control_prefix, initializer)`` for a generated initializer.

    For an originally unbraced ``if/else`` body, the watermarker emitted two
    statements and accidentally left the expanded loop outside that control.
    Recognizing the parent prefix here lets the inverse restore the original
    single controlled ``for`` instead of preserving that watermark artifact.
    """
    text = code[start:end].strip()
    if lexical_statement_kind(text, parser) in {"expression_statement", "declaration"}:
        return "", text

    cursor = start
    while cursor < end and mask[cursor].isspace():
        cursor += 1
    if re.match(r"if\b", mask[cursor:end]):
        open_paren = mask.find("(", cursor, end)
        close_paren = pairs.get(open_paren) if open_paren >= 0 else None
        if close_paren is None or close_paren >= end:
            return None
        initializer_start = close_paren + 1
    else:
        alternative = re.match(r"else\b", mask[cursor:end])
        if alternative is None:
            return None
        initializer_start = cursor + alternative.end()
    while initializer_start < end and mask[initializer_start].isspace():
        initializer_start += 1
    initializer = code[initializer_start:end].strip()
    if lexical_statement_kind(initializer, parser) not in {
        "expression_statement",
        "declaration",
    }:
        return None
    return code[start:initializer_start], initializer


def lexical_negated_break_condition(
    code: str,
    mask: str,
    start: int,
    end: int,
) -> Optional[str]:
    guard = re.fullmatch(
        r"\s*if\s*\(\s*!\s*\(\s*(?P<condition>.*?)\s*\)\s*\)\s*"
        r"(?:\{\s*)?break\s*;\s*(?:\}\s*)?",
        mask[start:end],
        re.DOTALL,
    )
    if guard is None:
        return None
    condition_start = start + guard.start("condition")
    condition_end = start + guard.end("condition")
    return code[condition_start:condition_end].strip() or None


def lexical_update_expression(
    code: str,
    mask: str,
    start: int,
    end: int,
    parser: Parser,
) -> Optional[tuple[int, str]]:
    masked = mask[start:end]
    meaningful_start = start + len(masked) - len(masked.lstrip())
    statement = code[meaningful_start:end].strip()
    if lexical_statement_kind(statement, parser) != "expression_statement":
        return None
    return meaningful_start, statement[:-1].rstrip()


def transform_spbt_split_nested_loops_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Repair the watermarker's split form for an originally unbraced nested for.

    ``mark.py`` first expands the inner loop to two statements.  When that pair
    was the unbraced body of an outer for, the later outer expansion captured
    only the inner initializer and left the inner empty-for beside it.  The
    distinctive pair of complete LoopStruct signatures is strong enough to
    reconstruct the original nesting without matching ordinary loops.
    """
    mask = mask_fallback_protected_text(code)
    pairs = fallback_matching_delimiters(mask)
    empty_for = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)\s*(?P<brace>\{)")
    matches = list(empty_for.finditer(mask))
    replacements: list[tuple[int, int, str]] = []
    for outer in matches:
        outer_block_start = outer.start("brace")
        outer_block_end = pairs.get(outer_block_start)
        if outer_block_end is None:
            continue
        next_start = outer_block_end + 1
        while next_start < len(mask) and mask[next_start].isspace():
            next_start += 1
        inner = next((item for item in matches if item.start() == next_start), None)
        if inner is None:
            continue
        inner_block_start = inner.start("brace")
        inner_block_end = pairs.get(inner_block_start)
        if inner_block_end is None:
            continue
        if re.search(r"\bcontinue\b", mask[outer_block_start + 1:inner_block_end]):
            continue

        outer_initializer_span = lexical_initializer_start(mask, outer.start(), pairs)
        if outer_initializer_span is None:
            continue
        replacement_start, outer_init_end = outer_initializer_span
        outer_initializer_parts = lexical_initializer_parts(
            code,
            mask,
            replacement_start,
            outer_init_end,
            pairs,
            parser,
        )
        if outer_initializer_parts is None:
            continue
        control_prefix, outer_initializer_statement = outer_initializer_parts

        outer_statements = fallback_direct_statement_spans(
            mask,
            outer_block_start,
            outer_block_end,
        )
        inner_statements = fallback_direct_statement_spans(
            mask,
            inner_block_start,
            inner_block_end,
        )
        if len(outer_statements) != 3 or len(inner_statements) < 2:
            continue
        outer_condition = lexical_negated_break_condition(
            code,
            mask,
            *outer_statements[0],
        )
        inner_condition = lexical_negated_break_condition(
            code,
            mask,
            *inner_statements[0],
        )
        if outer_condition is None or inner_condition is None:
            continue

        inner_init_start, inner_init_end = outer_statements[1]
        masked_inner_init = mask[inner_init_start:inner_init_end]
        inner_init_start += len(masked_inner_init) - len(masked_inner_init.lstrip())
        inner_initializer_statement = code[inner_init_start:inner_init_end].strip()
        if lexical_statement_kind(inner_initializer_statement, parser) not in {
            "expression_statement",
            "declaration",
        }:
            continue
        outer_update = lexical_update_expression(
            code,
            mask,
            *outer_statements[2],
            parser,
        )
        inner_update = lexical_update_expression(
            code,
            mask,
            *inner_statements[-1],
            parser,
        )
        if outer_update is None or inner_update is None:
            continue
        _, outer_update_text = outer_update
        inner_update_start, inner_update_text = inner_update

        outer_initializer = outer_initializer_statement.strip()[:-1].rstrip()
        inner_initializer = inner_initializer_statement[:-1].rstrip()
        inner_guard_end = inner_statements[0][1]
        inner_middle = code[inner_guard_end:inner_update_start]
        replacement = (
            f"{control_prefix}for ({outer_initializer}; {outer_condition}; {outer_update_text}) {{"
            f"for ({inner_initializer}; {inner_condition}; {inner_update_text}) {{"
            f"{inner_middle}}}}}"
        )
        replacements.append((replacement_start, inner_block_end + 1, replacement))
    if not replacements:
        return code
    selected = select_non_overlapping_character_replacements(replacements)
    rewritten = apply_character_replacements(
        code,
        selected,
        allow_semantic_parenthesis_change=True,
    )
    if rewritten != code:
        report.semantic_parenthesis_rewrites += 2 * len(selected)
    return rewritten


def transform_spbt_macro_split_loop_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Recover a LoopStruct update inserted into a continued macro line.

    A malformed Devign macro with blank physical continuation lines can make
    Tree-sitter mistake the macro's closing brace for the source for-body end.
    ``mark.py`` then inserted the update into that macro and left the remainder
    of the original loop outside the generated empty-for.  This rule activates
    only when the complete LoopStruct prefix is present and the apparent final
    update is the final statement of a protected directive span.  Ignoring that
    one macro brace must reveal a later balanced body close.
    """
    mask = mask_fallback_protected_text(code)
    pairs = fallback_matching_delimiters(mask)
    empty_for = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)\s*(?P<brace>\{)")
    replacements: list[tuple[int, int, str]] = []
    directive_spans = preprocessor_logical_spans(code)
    for match in empty_for.finditer(mask):
        block_start = match.start("brace")
        apparent_end = pairs.get(block_start)
        if apparent_end is None:
            continue
        initializer_span = lexical_initializer_start(mask, match.start(), pairs)
        if initializer_span is None:
            continue
        replacement_start, init_end = initializer_span
        initializer_parts = lexical_initializer_parts(
            code,
            mask,
            replacement_start,
            init_end,
            pairs,
            parser,
        )
        if initializer_parts is None:
            continue
        control_prefix, initializer_statement = initializer_parts
        direct = fallback_direct_statement_spans(mask, block_start, apparent_end)
        if not direct:
            continue
        guard_start, guard_end = direct[0]
        condition = lexical_negated_break_condition(
            code,
            mask,
            guard_start,
            guard_end,
        )
        if condition is None:
            continue
        directive = next(
            (
                (start, end)
                for start, end in directive_spans
                if guard_end <= start < end <= apparent_end
            ),
            None,
        )
        if directive is None:
            continue
        directive_start, directive_end = directive
        update_match = list(
            re.finditer(r"(?m)^[ \t]*(?P<update>[^#\n;]+;)[ \t]*(?:\r?\n|$)", code[directive_start:directive_end])
        )
        if not update_match:
            continue
        last_update = update_match[-1]
        update_start = directive_start + last_update.start("update")
        update_end = directive_start + last_update.end("update")
        update_statement = code[update_start:update_end].strip()
        if lexical_statement_kind(update_statement, parser) != "expression_statement":
            continue
        if code[directive_end:apparent_end].strip():
            continue

        repaired_mask = mask[:apparent_end] + " " + mask[apparent_end + 1:]
        real_end = fallback_matching_delimiters(repaired_mask).get(block_start)
        if real_end is None or real_end <= apparent_end:
            continue
        # A continue may occur in the recovered suffix.  Tree-sitter did not
        # consider that suffix part of the loop when mark.py chose this source
        # loop, but restoring the original standard for also restores the
        # correct behavior: continue executes the header update.
        initializer = initializer_statement[:-1].rstrip()
        update = update_statement[:-1].rstrip()
        middle = (
            code[guard_end:update_start]
            + code[update_end:apparent_end]
            + code[apparent_end:real_end]
        )
        replacement = (
            f"{control_prefix}for ({initializer}; {condition}; {update}) {{"
            f"{middle}}}"
        )
        replacements.append((replacement_start, real_end + 1, replacement))
    if not replacements:
        return code
    selected = select_non_overlapping_character_replacements(replacements)
    rewritten = apply_character_replacements(
        code,
        selected,
        allow_semantic_parenthesis_change=True,
    )
    if rewritten != code:
        report.semantic_parenthesis_rewrites += len(selected)
    return rewritten


def transform_spbt_expanded_loops_once(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Invert the exact local structure emitted by ``mark.py`` LoopStruct.

    The recognizer does not trust the sample's full AST.  It requires the
    generator's complete signature: an adjacent expression/declaration
    initializer, ``for (;;)`` with a compound body, a first negated-break
    guard, a final expression update, and no ``continue`` in that loop body.
    This permits recovery inside parse-error, label/case, and ``#if`` regions
    without broadening any of the ordinary AST canonicalization rules.
    """
    if EMPTY_FOR_HEADER_RE.search(code) is None:
        return code

    macro_split = transform_spbt_macro_split_loop_once(code, parser, report)
    if macro_split != code:
        return macro_split

    split_nested = transform_spbt_split_nested_loops_once(code, parser, report)
    if split_nested != code:
        return split_nested

    mask = mask_fallback_protected_text(code)
    pairs = fallback_matching_delimiters(mask)
    empty_for = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)\s*(?P<brace>\{)")
    replacements: list[tuple[int, int, str]] = []
    for match in empty_for.finditer(mask):
        block_start = match.start("brace")
        block_end = pairs.get(block_start)
        if block_end is None:
            continue
        initializer_span = lexical_initializer_start(mask, match.start(), pairs)
        if initializer_span is None:
            continue
        init_start, init_end = initializer_span
        initializer_parts = lexical_initializer_parts(
            code,
            mask,
            init_start,
            init_end,
            pairs,
            parser,
        )
        if initializer_parts is None:
            continue
        control_prefix, init_text = initializer_parts

        body_mask = mask[block_start + 1:block_end]
        # A normal for executes its update on continue, whereas the generated
        # expanded form skipped the appended update.  The original watermarker
        # rejects such loops, so the inverse must retain that restriction.
        if re.search(r"\bcontinue\b", body_mask):
            report.skipped["expanded_loop:continue"] += 1
            continue
        direct = fallback_direct_statement_spans(mask, block_start, block_end)
        if len(direct) < 2:
            continue
        guard_start, guard_end = direct[0]
        condition = lexical_negated_break_condition(
            code,
            mask,
            guard_start,
            guard_end,
        )
        if condition is None:
            continue

        update_start, update_end = direct[-1]
        if update_start < guard_end:
            continue
        update_parts = lexical_update_expression(
            code,
            mask,
            update_start,
            update_end,
            parser,
        )
        if update_parts is None:
            continue
        update_start, update = update_parts
        initializer = init_text[:-1].rstrip()
        before_guard = code[block_start + 1:guard_start]
        after_guard = code[guard_end:update_start]
        replacement = (
            f"{control_prefix}for ({initializer}; {condition}; {update}) {{"
            f"{before_guard}{after_guard}}}"
        )
        replacements.append((init_start, block_end + 1, replacement))
    if not replacements:
        return code
    selected = select_non_overlapping_character_replacements(replacements)
    rewritten = apply_character_replacements(
        code,
        selected,
        allow_semantic_parenthesis_change=True,
    )
    if rewritten != code:
        report.semantic_parenthesis_rewrites += len(selected)
    return rewritten


def transform_spbt_expanded_loops(code: str, parser: Parser, report: SampleReport) -> str:
    return repeat_transform(
        code,
        parser,
        report,
        "spbt_expanded_loop",
        transform_spbt_expanded_loops_once,
    )


def has_spbt_controlled_initializer(code: str, parser: Parser) -> bool:
    """Detect the watermarker artifact ``if/else init; for (;;)``."""
    mask = mask_fallback_protected_text(code)
    pairs = fallback_matching_delimiters(mask)
    for match in re.finditer(r"\bfor\s*\(\s*;\s*;\s*\)\s*\{", mask):
        initializer_span = lexical_initializer_start(mask, match.start(), pairs)
        if initializer_span is None:
            continue
        parts = lexical_initializer_parts(
            code,
            mask,
            *initializer_span,
            pairs,
            parser,
        )
        if parts is not None and parts[0].strip():
            return True
    return False


def transform_spbt_structural_artifacts(
    code: str,
    parser: Parser,
    report: SampleReport,
) -> str:
    """Repair generator-created parent/macro/nesting damage before AST passes."""
    if EMPTY_FOR_HEADER_RE.search(code) is None:
        return code

    current = repeat_transform(
        code,
        parser,
        report,
        "spbt_macro_split",
        transform_spbt_macro_split_loop_once,
    )
    current = repeat_transform(
        current,
        parser,
        report,
        "spbt_nested_split",
        transform_spbt_split_nested_loops_once,
    )
    if has_spbt_controlled_initializer(current, parser):
        current = transform_spbt_expanded_loops(current, parser, report)
    return current


def fallback_transform_loops_and_braces(code: str, report: SampleReport) -> str:
    current = code
    mask = mask_fallback_protected_text(current)
    pairs = fallback_matching_delimiters(mask)
    replacements = []
    for loop in re.finditer(r"\bfor\s*\(", mask):
        open_paren = loop.end() - 1
        close_paren = pairs.get(open_paren)
        if close_paren is None:
            continue
        pieces = fallback_split_top_level(current[open_paren + 1:close_paren], ";")
        if len(pieces) != 3:
            continue
        header = "for (" + "; ".join(piece.strip() for piece in pieces) + ")"
        replacements.append((loop.start(), close_paren + 1, header))
    updated = apply_character_replacements(current, replacements)
    if updated != code:
        report.skipped["fallback:loops_and_control_braces"] += 1
    return updated


def fallback_transform_cleanup(code: str, report: SampleReport) -> str:
    # Parentheses are never rewritten in the text fallback.  Without a
    # trustworthy AST, apparently repeated parentheses can still be required
    # by GNU attributes or can keep a comma expression as one macro argument.
    mask = mask_fallback_protected_text(code)
    replacements = []
    for block_start, block_end in fallback_function_blocks(mask):
        for start, end in fallback_direct_statement_spans(mask, block_start, block_end):
            if mask[start:end].strip() == ";":
                semicolon = mask.find(";", start, end)
                replacements.append((semicolon, semicolon + 1, ""))
    updated = apply_character_replacements(code, replacements)
    if updated != code:
        report.skipped["fallback:cleanup"] += 1
    return updated


def fallback_condition_spans(mask: str) -> list[tuple[int, int]]:
    spans = []
    for control in re.finditer(r"\b(if|while|for)\s*\(", mask):
        open_paren = control.end() - 1
        depth = 0
        semicolons = []
        close_paren = None
        for index in range(open_paren, len(mask)):
            char = mask[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
            elif char == ";" and depth == 1:
                semicolons.append(index)
        if close_paren is None:
            continue
        if control.group(1) == "for":
            if len(semicolons) == 2:
                spans.append((semicolons[0] + 1, semicolons[1]))
        else:
            spans.append((open_paren + 1, close_paren))
    return spans


def fallback_transform(code: str, parser: Parser, report: SampleReport) -> str:
    """Token-aware implementation of ASTC rules for severely malformed input.

    The full file is never trusted as an AST in this branch.  Balanced lexical
    regions are transformed independently, while comments, literals and
    preprocessor logical lines remain masked and therefore immutable.
    """
    stages = [
        (
            "spbt_expanded_loops",
            lambda value, stage_report: transform_spbt_expanded_loops(
                value,
                parser,
                stage_report,
            ),
        ),
        ("declarations", fallback_transform_declarations),
        ("assignments", fallback_transform_assignments),
        ("loops_and_control_braces", fallback_transform_loops_and_braces),
        ("conditions", fallback_transform_conditions),
        ("cleanup", fallback_transform_cleanup),
    ]
    current = code
    disabled = set()
    for _ in range(16):
        changed = False
        for name, transform in stages:
            if name in disabled:
                continue
            candidate = transform(current, report)
            if candidate == current:
                continue
            if preprocessor_logical_lines(candidate) != preprocessor_logical_lines(current):
                report.skipped[f"fallback:{name}:preprocessor_change_avoided"] += 1
                disabled.add(name)
                continue
            introduced, _ = introduces_parse_issue(current, candidate, parser)
            if introduced:
                # A lexical rule can encounter an ambiguous recovery fragment.
                # Keep the other fallback stages useful instead of rolling the
                # complete sample back to its original form.
                report.skipped[f"fallback:{name}:parse_regression_avoided"] += 1
                disabled.add(name)
                continue
            current = candidate
            changed = True
        if not changed:
            break
    else:
        report.skipped["fallback:iteration_limit"] += 1

    if current != code:
        report.skipped["parse:fallback_text_transform_used"] += 1
    return current


def canonicalize_code(
    code: str,
    parser: Parser,
    clang_format: Optional[str] = None,
    clang_format_major_version: int = DEFAULT_CLANG_FORMAT_MAJOR,
    project_root: Optional[Path] = None,
) -> tuple[str, SampleReport]:
    report = SampleReport()
    initial_tree = parser.parse(code.encode("utf-8"))
    initial_issues = severe_parse_issues(initial_tree, len(code.encode("utf-8")))
    fallback_needed = bool(initial_issues)
    if initial_issues:
        report.failures.append(f"initial_parse:{';'.join(initial_issues[:5])}")
        report.skipped["parse:severe_errors_fallback"] += 1
    tolerated_initial_counts = parse_issue_counts(initial_tree)
    if tolerated_initial_counts != (0, 0) and not fallback_needed:
        report.skipped["parse:localized_errors_tolerated"] += sum(tolerated_initial_counts)

    # Repair only the generator's malformed parent/macro/nesting artifacts
    # before the three ordinary, independent header-completion passes.
    current = run_stage(
        code,
        parser,
        report,
        "spbt_structural_artifacts",
        transform_spbt_structural_artifacts,
    )

    # Complete each missing for-header clause independently.  The order is
    # deliberate: once condition/update have been proved from the body, an
    # adjacent initializer can be moved without treating arbitrary ``for (;;)``
    # loops as LoopStruct.  The exact lexical inverse remains a final recovery
    # path for malformed AST, preprocessor, and split-parent artifacts.
    for name, transform in (
        ("for_conditions", transform_missing_for_conditions),
        ("for_updates", transform_missing_for_updates),
        ("for_initializers", transform_missing_for_initializers),
    ):
        current = run_stage(current, parser, report, name, transform)
    current = run_stage(
        current,
        parser,
        report,
        "spbt_expanded_loops",
        transform_spbt_expanded_loops,
    )
    stages = [
        ("declarations", transform_declarations),
        ("assignments", transform_assignments),
        ("loops", transform_for_loops),
        ("control_braces", transform_control_braces),
        ("conditions", transform_conditions),
        ("cleanup", transform_cleanup),
    ]
    if fallback_needed:
        current = run_stage(current, parser, report, "fallback", fallback_transform)
    else:
        for name, transform in stages:
            current = run_stage(current, parser, report, name, transform)

    preformat = current
    if fallback_needed:
        # clang-format can reinterpret incomplete macros, inline assembly, or
        # recovery fragments even when it exits successfully.  Preserve the
        # fallback edits verbatim instead of risking unrelated source damage.
        report.skipped["parse:fallback_format_skipped"] += 1
    else:
        current, format_error = format_code(
            current,
            parser,
            clang_format,
            clang_format_major_version,
            project_root or Path(__file__).resolve().parent.parent,
        )
        if format_error:
            report.failures.append(f"clang_format:{format_error}")
            current = preformat
        else:
            report.formatted = True

    # Syntax-preserving edits and fallback edits retain every input parenthesis.
    # A proven semantic rewrite may necessarily consume part of its old syntax,
    # so in that case only later formatting is checked against the post-AST
    # checkpoint.  This prevents unexplained formatter loss without blocking
    # legitimate AST transformations.
    parenthesis_baseline = preformat if report.semantic_parenthesis_rewrites else code
    if not parentheses_preserved(parenthesis_baseline, current):
        report.failures.append("parentheses:original_parenthesis_lost")
        return code, report

    final_tree = parser.parse(current.encode("utf-8"))
    final_issues = parse_issues(final_tree)
    final_counts = parse_issue_counts(final_tree)
    if final_counts[0] > tolerated_initial_counts[0] or final_counts[1] > tolerated_initial_counts[1]:
        if report.formatted:
            report.failures.append(f"clang_format:produced_parse_error:{';'.join(final_issues[:5])}")
            report.formatted = False
            current = preformat
            final_tree = parser.parse(current.encode("utf-8"))
            final_issues = parse_issues(final_tree)
            final_counts = parse_issue_counts(final_tree)
        if final_counts[0] > tolerated_initial_counts[0] or final_counts[1] > tolerated_initial_counts[1]:
            report.failures.append(f"final_parse:{';'.join(final_issues[:5])}")
            return code, report
    return current, report


def build_output_name(file_path: str) -> str:
    path = Path(file_path)
    return f"{path.stem}_ast_canonicalization{path.suffix}"


def process_jsonl(config: dict) -> tuple[str, dict]:
    input_path = Path(config["jsonl_path"])
    output_path = Path(
        config.get("output_path")
        or Path(config.get("output_dir", DEFAULT_OUTPUT_DIR)) / build_output_name(str(input_path))
    )
    stats_path = Path(config.get("stats_path") or f"{output_path}.stats.json")
    failure_log_path = Path(config.get("failure_log") or f"{output_path}.failures.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    failure_log_path.parent.mkdir(parents=True, exist_ok=True)

    parser = make_parser()
    stats = RunStats()
    failures = []
    with input_path.open("r", encoding="utf-8") as reader, output_path.open("w", encoding="utf-8") as writer:
        for index, line in enumerate(reader, start=1):
            sample = json.loads(line)
            code_value = sample.get("code")
            if not isinstance(code_value, str):
                original = canonical = ""
                report = SampleReport(failures=["input:missing_or_non_string_code"])
            else:
                original = code_value
                canonical, report = canonicalize_code(
                    original,
                    parser,
                    config.get("clang_format"),
                    int(config.get("clang_format_major", DEFAULT_CLANG_FORMAT_MAJOR)),
                )
                sample["code"] = canonical
            writer.write(json.dumps(sample, ensure_ascii=False) + "\n")
            stats.add(original, canonical, report)
            if report.failures or report.skipped:
                failures.append(
                    {
                        "line": index,
                        "failures": report.failures,
                        "skipped": dict(report.skipped),
                    }
                )
            if index % 500 == 0:
                writer.flush()
                print(f"processed {index} samples")

    summary = stats.as_dict()
    summary.update(
        {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "clang_format_major": int(config.get("clang_format_major", DEFAULT_CLANG_FORMAT_MAJOR)),
        }
    )
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with failure_log_path.open("w", encoding="utf-8") as handle:
        for failure in failures:
            handle.write(json.dumps(failure, ensure_ascii=False) + "\n")
    print(f"AST-canonicalized data written to {output_path}")
    print(f"statistics written to {stats_path}")
    return str(output_path), summary


def load_config(args) -> dict:
    config = {}
    if args.config:
        import yaml

        with open(args.config, "r", encoding="utf-8") as handle:
            config = yaml.load(handle, Loader=yaml.FullLoader) or {}
    overrides = {
        "jsonl_path": args.file_path,
        "output_dir": args.output_dir,
        "output_path": args.output_path,
        "stats_path": args.stats_path,
        "failure_log": args.failure_log,
        "clang_format": args.clang_format,
        "clang_format_major": args.clang_format_major,
    }
    for key, value in overrides.items():
        if value is not None:
            config[key] = value
    config.setdefault("output_dir", DEFAULT_OUTPUT_DIR)
    config.setdefault("clang_format_major", DEFAULT_CLANG_FORMAT_MAJOR)
    if "jsonl_path" not in config:
        raise ValueError("jsonl_path must be provided through --config or --file_path")
    return config


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AST-canonicalize Devign C/C++ JSONL samples.")
    parser.add_argument("--config", type=str, default=None, help="YAML configuration path.")
    parser.add_argument("--file_path", "--jsonl_path", dest="file_path", type=str, default=None)
    parser.add_argument("--output_dir", "--dir_path", dest="output_dir", type=str, default=None)
    parser.add_argument("--output_path", type=str, default=None)
    parser.add_argument("--stats_path", type=str, default=None)
    parser.add_argument("--failure_log", type=str, default=None)
    parser.add_argument("--clang_format", type=str, default=None)
    parser.add_argument(
        "--clang_format_major",
        type=int,
        default=None,
        help=f"Required clang-format major version (default: {DEFAULT_CLANG_FORMAT_MAJOR}).",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    process_jsonl(load_config(args))


if __name__ == "__main__":
    main()
