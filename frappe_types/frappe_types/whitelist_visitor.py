import ast
from pathlib import Path


class WhitelistVisitor(ast.NodeVisitor):
	def __init__(self):
		self.current_class: str | None = None
		self.whitelisted: set[str] = set()

	def visit_ClassDef(self, node: ast.ClassDef):
		prev = self.current_class
		self.current_class = node.name
		self.generic_visit(node)
		self.current_class = prev

	def visit_FunctionDef(self, node: ast.FunctionDef):
		# … your decorator logic …
		pass

	visit_AsyncFunctionDef = visit_FunctionDef  # alias

	def visit_FunctionDef(self, node: ast.FunctionDef):
		for deco in node.decorator_list:
			target = deco.func if isinstance(deco, ast.Call) else deco
			if (
				isinstance(target, ast.Attribute)
				and isinstance(target.value, ast.Name)
				and target.value.id == "frappe"
				and target.attr == "whitelist"
			):
				name = node.name
				if self.current_class:
					name = f"{self.current_class}.{name}"
				self.whitelisted.add(name)
				break


def extract_whitelisted(py_file: Path) -> set[str]:
	src = py_file.read_text(encoding="utf-8")
	tree = ast.parse(src, filename=str(py_file))
	vis = WhitelistVisitor()
	vis.visit(tree)
	return vis.whitelisted


def get_module_path(py_file: Path, base_dir: Path) -> str:
	parts = list(py_file.relative_to(base_dir).with_suffix("").parts)
	if parts and parts[-1] == "__init__":
		parts.pop()
	return ".".join(parts)


def collect_all(dir_path: str) -> set[str]:
	base = Path(dir_path)
	all_paths: set[str] = set()
	for py in base.rglob("*.py"):
		module = get_module_path(py, base)
		for fn in extract_whitelisted(py):
			full = f"{module}.{fn}" if module else fn
			all_paths.add(full)
	return all_paths


def write_ts_union(paths: set[str], out_ts: Path, type_name: str = "FrappeWhitelistedPaths"):
	with out_ts.open("w", encoding="utf-8") as f:
		f.write("// AUTO-GENERATED — do not edit by hand\n")
		f.write(f"export type {type_name} =\n")
		for p in sorted(paths):
			f.write(f'  | "{p}"\n')
		f.write(";\n")


if __name__ == "__main__":
	root = "."
	paths = collect_all(root)
	write_ts_union(paths, Path("frappe-whitelist.d.ts"))
	print(f"Wrote {len(paths)} paths into frappe-whitelist.d.ts")
