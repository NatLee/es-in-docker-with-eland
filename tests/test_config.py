import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from elastic_tutorial import create_client, load_config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "ca.crt").write_text("test-only certificate placeholder")
        (self.root / ".env").write_text("ELASTIC_PASSWORD='file-password'\nES_PORT=19200\n")

    def test_dotenv_defaults_are_relative_to_repository(self):
        config = load_config(self.root, {})
        self.assertEqual(config.url, "https://localhost:19200")
        self.assertEqual(config.username, "elastic")
        self.assertEqual(config.ca_cert, self.root / "ca.crt")
        self.assertEqual(config.password, "file-password")

    def test_process_environment_wins_without_being_mutated(self):
        env = {"ELASTIC_PASSWORD": "process-password", "ES_PORT": "29200", "ELASTIC_USERNAME": "learner"}
        original = env.copy()
        config = load_config(self.root, env)
        self.assertEqual(config.password, "process-password")
        self.assertEqual(config.username, "learner")
        self.assertEqual(config.url, "https://localhost:29200")
        self.assertEqual(env, original)
        self.assertNotIn("process-password", repr(config))

    def test_explicit_env_file_preserves_existing_file(self):
        (self.root / ".env.v9").write_text("ELASTIC_PASSWORD=migration-password\nES_PORT=39200\n")
        config = load_config(self.root, {"ELASTIC_ENV_FILE": ".env.v9"})
        self.assertEqual(config.password, "migration-password")
        self.assertEqual(config.url, "https://localhost:39200")
        self.assertIn("file-password", (self.root / ".env").read_text())

    def test_missing_explicit_env_file_is_an_error(self):
        with self.assertRaisesRegex(FileNotFoundError, "ELASTIC_ENV_FILE"):
            load_config(self.root, {"ELASTIC_ENV_FILE": ".missing"})

    def test_url_override_and_relative_certificate(self):
        (self.root / "certs").mkdir()
        (self.root / "certs" / "custom.crt").write_text("test")
        config = load_config(self.root, {
            "ELASTICSEARCH_URL": "https://es.example.test:9243/prefix",
            "ES_PORT": "ignored-with-url",
            "ELASTIC_CA_CERT": "certs/custom.crt",
        })
        self.assertEqual(config.url, "https://es.example.test:9243/prefix")
        self.assertEqual(config.ca_cert, self.root / "certs" / "custom.crt")

    def test_password_is_literal(self):
        (self.root / ".env").write_text("ELASTIC_PASSWORD='literal-${SECRET}-with-$-signs'\n")
        config = load_config(self.root, {})
        self.assertEqual(config.password, "literal-${SECRET}-with-$-signs")

    def test_default_port_when_only_environment_is_available(self):
        (self.root / ".env").unlink()
        config = load_config(self.root, {"ELASTIC_PASSWORD": "test-password"})
        self.assertEqual(config.url, "https://localhost:9200")

    def test_missing_or_empty_password_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ELASTIC_PASSWORD"):
            load_config(self.root, {"ELASTIC_PASSWORD": ""})
        (self.root / ".env").unlink()
        with self.assertRaisesRegex(ValueError, "ELASTIC_PASSWORD"):
            load_config(self.root, {})

    def test_insecure_malformed_or_credential_urls_are_rejected(self):
        for url in (
            "http://localhost:9200", "https:///missing-host", "https://localhost:99999",
            "https://localhost:bad", "https://user:secret@localhost:9200",
            "https://localhost:9200?password=secret", "https://localhost:9200#secret",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError) as raised:
                load_config(self.root, {"ELASTICSEARCH_URL": url})
            self.assertNotIn("secret", str(raised.exception))

    def test_invalid_port_is_rejected(self):
        for port in ("0", "65536", "-1", "9200:9200", "localhost:9200", ""):
            with self.subTest(port=port), self.assertRaisesRegex(ValueError, "ES_PORT"):
                load_config(self.root, {"ES_PORT": port})

    def test_missing_certificate_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "dev-cp-cert.sh"):
            load_config(self.root, {"ELASTIC_CA_CERT": "missing.crt"})

    def test_client_always_verifies_certificates(self):
        config = load_config(self.root, {})
        with patch("elastic_tutorial.config.Elasticsearch") as constructor:
            client = create_client(config)
        self.assertIs(client, constructor.return_value)
        self.assertEqual(constructor.call_args.args, ("https://localhost:19200",))
        self.assertTrue(constructor.call_args.kwargs["verify_certs"])
        self.assertEqual(constructor.call_args.kwargs["ca_certs"], str(self.root / "ca.crt"))
        self.assertEqual(constructor.call_args.kwargs["basic_auth"], ("elastic", "file-password"))


if __name__ == "__main__":
    unittest.main()
