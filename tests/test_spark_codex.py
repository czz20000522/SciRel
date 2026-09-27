"""Credential transport and launcher behavior; uses fake credentials only."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "spark_codex", Path(__file__).resolve().parents[1] / "scripts/spark_codex.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONFIG = {"key": "invalid-test-secret", "url": "https://example.invalid/v1", "model": "test-model"}


class ModelConfigurationTests(unittest.TestCase):
    def test_credential_is_environment_only_and_existing_environment_survives(self):
        with patch.dict(os.environ, {"SCIREL_TEST_SENTINEL": "keep"}):
            argv, env = MODULE.command(CONFIG, "/bin/codex", ["exec", "hello"])
        self.assertNotIn(CONFIG["key"], " ".join(argv))
        self.assertEqual(env[MODULE.ENV_KEY], CONFIG["key"])
        self.assertEqual(env["SCIREL_TEST_SENTINEL"], "keep")
        self.assertEqual(argv[-2:], ["exec", "hello"])
        self.assertIn('model_providers.scirel_runtime.requires_openai_auth=false', argv)

    def test_legacy_flags_cannot_override_the_json_model(self):
        for args in (["-m", "old"], ["--model=old"], ["-mold"], ["-pold"],
                     ["-c", 'model_provider="old"'], ["-cmodel=old"],
                     ["--config=model_providers.other.env_key=OLD"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                MODULE.command(CONFIG, "codex", args)

    def test_configuration_rejects_unintended_credential_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            for url in ("http://example.invalid", "https://user:password@example.invalid", "https://example.invalid/?token=x"):
                path.write_text(json.dumps({**CONFIG, "url": url}), encoding="utf-8")
                with self.subTest(url=url), self.assertRaises(ValueError):
                    MODULE.load_config(path)

    def test_installer_writes_loadable_config_and_executable_launcher_without_printing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = io.StringIO()
            payload = json.dumps({"config": CONFIG, "script": "# harmless test script\n"})
            # Windows has no fchmod; the real Linux permission is checked on Spark.
            with patch.object(Path, "home", return_value=root), patch("sys.stdin", io.StringIO(payload)), \
                    patch.object(os, "fchmod", create=True), contextlib.redirect_stdout(output):
                exec(compile(MODULE.INSTALL, "<installer>", "exec"), {})
            self.assertEqual(MODULE.load_config(root / ".config/scirel/spark-model.local.json"), CONFIG)
            lines = (root / ".local/bin/scirel-codex").read_text().splitlines()
            self.assertEqual(lines[0], "#!/bin/sh")
            self.assertTrue(lines[1].startswith("exec python3 "))
            self.assertNotIn(CONFIG["key"], output.getvalue())
            self.assertTrue(json.loads(output.getvalue())["installed"])


if __name__ == "__main__":
    unittest.main()
