from pathlib import Path
import frappe


def create_file(path: Path, content: str = None):
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