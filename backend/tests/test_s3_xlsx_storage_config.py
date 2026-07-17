from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class S3XlsxStorageConfigTest(unittest.TestCase):
    def test_local_stack_declares_and_provisions_xlsx_template_bucket(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text()

        self.assertIn("STORAGE_S3_BUCKET_XLSX_TEMPLATES", compose)
        self.assertIn("docmanagement-xlsx-templates", compose)
        self.assertIn("minio-init:", compose)
        self.assertIn("mc mb --ignore-existing", compose)

    def test_example_and_helm_values_expose_xlsx_template_bucket(self) -> None:
        env_example = (ROOT / ".env.example").read_text()
        values = (ROOT / "chart" / "values.yaml").read_text()
        backend_deployment = (ROOT / "chart" / "templates" / "backend-deployment.yaml").read_text()

        self.assertIn("STORAGE_S3_BUCKET_XLSX_TEMPLATES", env_example)
        self.assertIn("bucketXlsxTemplates", values)
        self.assertIn("STORAGE_S3_BUCKET_XLSX_TEMPLATES", backend_deployment)


if __name__ == "__main__":
    unittest.main()
