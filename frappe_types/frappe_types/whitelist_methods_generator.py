import ast
from pathlib import Path

# ─── Helpers for mapping Python annotations → TS types ─────────────────────────


def map_py_type(node: ast.AST) -> str:
	"""
	Given an ast annotation node, return a TS type string.
	Falls back to 'any' if unrecognized.
	"""
	if isinstance(node, ast.Name):
		return {
			"str": "string",
			"int": "number",
			"float": "number",
			"bool": "boolean",
			"dict": "Record<string, any>",
			"list": "any[]",
			"Any": "any",
		}.get(node.id, "any")

	# handles things like List[str], Optional[int], Dict[str, Any], etc.
	if isinstance(node, ast.Subscript):
		base = node.value
		sub = node.slice
		# List[T] ➔ T[]
		if isinstance(base, ast.Name) and base.id in ("List", "list"):
			elt = map_py_type(sub.value if hasattr(sub, "value") else sub)
			return f"{elt}[]"
		# Optional[T] ➔ T | undefined
		if isinstance(base, ast.Name) and base.id in ("Optional",):
			inner = map_py_type(sub.value if hasattr(sub, "value") else sub)
			return f"{inner} | undefined"
		# Dict[K, V] ➔ Record<K, V>
		if isinstance(base, ast.Name) and base.id in ("Dict", "dict"):
			# ignore key type, just V
			val = map_py_type(sub.value.elts[1]) if hasattr(sub.value, "elts") else "any"
			return f"Record<string, {val}>"
	return "any"


# ─── Visitor that also captures defaults ───────────────────────────────────────


class WhitelistVisitor(ast.NodeVisitor):
	def __init__(self):
		self.current_class: str | None = None
		# map full_path → list of (arg_name, ts_type, is_optional)
		self.methods: dict[str, list[tuple[str, str, bool]]] = {}

	def visit_ClassDef(self, node: ast.ClassDef):
		prev, self.current_class = self.current_class, node.name
		self.generic_visit(node)
		self.current_class = prev

	def visit_FunctionDef(self, node: ast.FunctionDef):
		for deco in node.decorator_list:
			target = deco.func if isinstance(deco, ast.Call) else deco
			if (
				isinstance(target, ast.Attribute)
				and isinstance(target.value, ast.Name)
				and target.value.id == "frappe"
				and target.attr == "whitelist"
			):
				# determine TS-typed args
				params: list[tuple[str, str, bool]] = []
				# pair defaults to args from the end
				defaults = (
					{
						node.args.args[-len(node.args.defaults) + i].arg: d
						for i, d in enumerate(node.args.defaults)
					}
					if node.args.defaults
					else {}
				)

				for arg in node.args.args:
					if arg.arg == "self":
						continue
					ann = arg.annotation
					ts_type = map_py_type(ann) if ann else "any"
					is_opt = arg.arg in defaults
					params.append((arg.arg, ts_type, is_opt))

				name = node.name
				if self.current_class:
					name = f"{self.current_class}.{name}"
				self.methods[name] = params
				break

	visit_AsyncFunctionDef = visit_FunctionDef


# ─── Extraction, mapping to TS interface ──────────────────────────────────────


def extract_all(root: Path) -> dict[str, list[tuple[str, str, bool]]]:
	res: dict[str, list[tuple[str, str, bool]]] = {}
	for py in root.rglob("*.py"):
		module = ".".join(py.relative_to(root).with_suffix("").parts).replace(".__init__", "")
		vis = WhitelistVisitor()
		vis.visit(ast.parse(py.read_text(), filename=str(py)))
		for fn, args in vis.methods.items():
			key = f"{module}.{fn}" if module else fn
			res[key] = args
	return res


def write_interface(mapping: dict[str, list[tuple[str, str, bool]]], out: Path):
	lines = [
		"// AUTO-GENERATED — do not edit by hand",
		"",
		"declare global {",
		"  interface FrappeWhitelistedPaths {",
	]
	for path, params in sorted(mapping.items()):
		if params:
			lines.append(f'    "{path}": ' + "{")
			for name, ts_type, is_opt in params:
				opt = "?" if is_opt else ""
				lines.append(f"      {name}{opt}: {ts_type};")
			lines.append("    };")
		else:
			lines.append(f'    "{path}": {{}};')
	lines.append("  }")
	lines.append("}")
	lines.append("")
	lines.append("export {};")
	out.write_text("\n".join(lines), encoding="utf-8")
	print(f"Wrote interface with {len(mapping)} entries to {out}")


if __name__ == "__main__":
	ROOT = Path("../")
	OUT = Path("frappe-whitelist-paths.d.ts")
	mapping = extract_all(ROOT)
	write_interface(mapping, OUT)
