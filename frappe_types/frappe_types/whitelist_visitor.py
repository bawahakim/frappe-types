import ast
from collections.abc import Iterator
from pathlib import Path


class WhitelistVisitor(ast.NodeVisitor):
	def __init__(self):
		self.current_class: str | None = None
		self.whitelisted: list[str] = []

	def visit_ClassDef(self, node: ast.ClassDef):
		prev = self.current_class
		self.current_class = node.name
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
				name = node.name
				if self.current_class:
					name = f"{self.current_class}.{name}"
				self.whitelisted.append(name)
				break

	visit_AsyncFunctionDef = visit_FunctionDef  # alias for async fns


def extract_whitelisted_from_file(py_file: Path) -> list[str]:
	tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
	vis = WhitelistVisitor()
	vis.visit(tree)
	return vis.whitelisted


def get_module_path(py_file: Path, base_dir: Path) -> str:
	# e.g. src/app/foo.py  →  ['src','app','foo']
	parts = list(py_file.relative_to(base_dir).with_suffix("").parts)
	# drop the "foo/__init__.py" → module "foo"
	if parts and parts[-1] == "__init__":
		parts.pop()
	return ".".join(parts)


def walk_and_extract(dir_path: str) -> Iterator[tuple[str, str]]:
	base = Path(dir_path)
	for py_file in base.rglob("*.py"):
		module = get_module_path(py_file, base)
		for func in extract_whitelisted_from_file(py_file):
			full_name = f"{module}.{func}" if module else func
			yield str(py_file), full_name


if __name__ == "__main__":
	for _path, full_name in walk_and_extract("."):
		print(full_name)
