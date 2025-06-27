import tempfile
from pathlib import Path

from frappe.tests.utils import FrappeTestCase

from frappe_types.frappe_types.whitelist_methods_generator import generate_interface


class TestWhitelistMethodsGenerator(FrappeTestCase):
	def test_generate_interface_single_function(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp) / "root"
			root.mkdir()

			# Create a test module with a whitelisted function
			file = root / "test.py"
			file.write_text(
				"import frappe\n\n" "@frappe.whitelist\n" "def my_func(a: str, b: int = 5):\n" "    pass\n",
				encoding="utf-8",
			)

			output = Path(tmp) / "out.ts"
			generate_interface(root, output)

			content = output.read_text(encoding="utf-8").splitlines()

			self.assertEqual(content[0], "// AUTO-GENERATED — do not edit by hand")
			self.assertTrue(any(line.strip() == '"test.my_func": {' for line in content))
			self.assertTrue(any(line.strip() == "a: string;" for line in content))
			self.assertTrue(any(line.strip() == "b?: number;" for line in content))
			self.assertTrue(any("};" in line for line in content))

	def test_generate_interface_no_params(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp) / "root2"
			root.mkdir()

			# Module with a whitelisted function without parameters
			file = root / "no_params.py"
			file.write_text(
				"import frappe\n\n" "@frappe.whitelist\n" "def foo():\n" "    pass\n", encoding="utf-8"
			)

			output = Path(tmp) / "out2.ts"
			generate_interface(root, output)

			content = output.read_text(encoding="utf-8").splitlines()
			self.assertTrue(any(line.strip() == '"no_params.foo": {};' for line in content))

	def test_generate_interface_class_method(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp) / "root3"
			root.mkdir()

			# Module with a whitelisted class method
			file = root / "mod.py"
			file.write_text(
				"import frappe\n\n"
				"class MyClass:\n"
				"    @frappe.whitelist\n"
				"    def method(self, x: bool):\n"
				"        pass\n",
				encoding="utf-8",
			)

			output = Path(tmp) / "out3.ts"
			generate_interface(root, output)
			content = output.read_text(encoding="utf-8").splitlines()

			self.assertTrue(any(line.strip() == '"mod.MyClass.method": {' for line in content))
			self.assertTrue(any(line.strip() == "x: boolean;" for line in content))
			self.assertTrue(any("};" in line for line in content))
