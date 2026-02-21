from pathlib import Path
import tempfile
import unittest

from nocode_android_builder import generate_project, parse_prompt


class BuilderTests(unittest.TestCase):
    def test_generate_project_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = generate_project(
                Path(tmp),
                app_name="Shop App",
                package_name="com.example.shopapp",
                start_url="https://example.com",
            )

            self.assertTrue((project / "settings.gradle.kts").exists())
            self.assertTrue((project / "app" / "build.gradle.kts").exists())
            self.assertTrue(
                (project / "app" / "src" / "main" / "java" / "com" / "example" / "shopapp" / "MainActivity.kt").exists()
            )

            manifest = (project / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
            self.assertIn("android.permission.INTERNET", manifest)

    def test_parse_prompt(self):
        spec = parse_prompt(
            """
            app name: Demo App
            package: com.example.demo
            start url: https://example.com
            """
        )
        self.assertEqual(spec.app_name, "Demo App")
        self.assertEqual(spec.package_name, "com.example.demo")
        self.assertEqual(spec.start_url, "https://example.com")


if __name__ == "__main__":
    unittest.main()
