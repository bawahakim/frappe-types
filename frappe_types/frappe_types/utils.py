from pathlib import Path

import frappe


def create_file(path: Path, content: str | None = None):
	# Create the file if not exists
	if not path.exists():
		path.touch()

	# Write the contents (if any)
	if content:
		with path.open("w") as f:
			f.write(content)


def is_developer_mode_enabled():
	if not frappe.conf.get("developer_mode"):
		print("Developer mode not enabled - ignoring type generation")
		return False
	return True


def to_ts_type(fieldtype: str) -> str:
	return fieldtype.replace(" ", "")


def get_bench_root_path():
	"""Get the root path of the bench directory."""
	any_app = frappe.get_installed_apps()[0]
	app_path = Path(frappe.get_app_path(any_app))
	return app_path.parents[2]
