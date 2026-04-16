from pathlib import Path

from django.test import SimpleTestCase

from pdf_processor.pdf_utils import PDFUtils


class PDFUtilsRegressionTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sample_pdf = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "pdfs"
            / "isms.2018.TL03.pdf"
        )
        if not cls.sample_pdf.exists():
            raise FileNotFoundError(f"Sample PDF not found: {cls.sample_pdf}")

    def test_extract_text_and_metadata_keeps_page_count_after_close(self):
        result = PDFUtils.extract_text_and_metadata(str(self.sample_pdf))

        self.assertTrue(result["success"], result.get("error"))
        self.assertGreater(result["metadata"].get("total_pages", 0), 0)
        self.assertEqual(result["metadata"]["total_pages"], len(result["pages"]))

    def test_extract_text_without_reference_filter_does_not_compare_none(self):
        result = PDFUtils.extract_text_and_metadata(
            str(self.sample_pdf),
            exclude_references=False,
        )

        self.assertTrue(result["success"], result.get("error"))
        self.assertGreater(len(result["text"]), 0)

    def test_extract_basic_metadata_does_not_use_closed_document(self):
        metadata = PDFUtils.extract_basic_metadata(str(self.sample_pdf))

        self.assertNotIn("error", metadata)
        self.assertGreater(metadata["pages"], 0)
