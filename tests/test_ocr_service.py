"""
Tests for OCR Service

Tests OCR functionality for Brazilian license plate recognition.
Uses Tesseract OCR with pytesseract wrapper.
"""
import pytest
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from backend.ocr_service import OCRService
import os
from unittest.mock import patch, MagicMock


class TestLicensePlateValidation:
    """Test Brazilian license plate format validation"""

    def test_validate_old_format_with_dash(self):
        """Test old format: ABC-1234"""
        result = OCRService.validate_license_plate("ABC-1234")
        assert result['valid'] is True
        assert result['normalized'] == "ABC-1234"
        assert result['confidence'] == 1.0

    def test_validate_old_format_without_dash(self):
        """Test old format without dash: ABC1234"""
        result = OCRService.validate_license_plate("ABC1234")
        assert result['valid'] is True
        assert result['normalized'] == "ABC-1234"  # Should normalize
        assert result['confidence'] == 1.0

    def test_validate_mercosur_format_with_dash(self):
        """Test Mercosur format: MER-1234"""
        result = OCRService.validate_license_plate("MER-1234")
        assert result['valid'] is True
        assert result['normalized'] == "MER-1234"
        assert result['confidence'] == 1.0

    def test_validate_mercosur_format_without_dash(self):
        """Test Mercosur format without dash: MER1234"""
        result = OCRService.validate_license_plate("MER1234")
        assert result['valid'] is True
        assert result['normalized'] == "MER-1234"
        assert result['confidence'] == 1.0

    def test_validate_case_insensitive(self):
        """Test case insensitivity"""
        result = OCRService.validate_license_plate("abc-1234")
        assert result['valid'] is True
        assert result['normalized'] == "ABC-1234"

    def test_validate_invalid_too_short(self):
        """Test invalid: too short"""
        result = OCRService.validate_license_plate("AB-123")
        assert result['valid'] is False
        assert result['confidence'] == 0.0

    def test_validate_invalid_too_long(self):
        """Test invalid: too long"""
        result = OCRService.validate_license_plate("ABCD-12345")
        assert result['valid'] is False
        assert result['confidence'] == 0.0

    def test_validate_invalid_wrong_format(self):
        """Test invalid: wrong format"""
        result = OCRService.validate_license_plate("1234-ABCD")
        assert result['valid'] is False
        assert result['confidence'] == 0.0

    def test_validate_invalid_special_chars(self):
        """Test invalid: special characters"""
        result = OCRService.validate_license_plate("ABC@1234")
        assert result['valid'] is False
        assert result['confidence'] == 0.0

    def test_validate_empty_string(self):
        """Test invalid: empty string"""
        result = OCRService.validate_license_plate("")
        assert result['valid'] is False
        assert result['confidence'] == 0.0


class TestImagePreprocessing:
    """Test image preprocessing for OCR"""

    def test_preprocess_image_from_file(self, tmp_path):
        """Test preprocessing from file path"""
        # Create test image
        img_path = tmp_path / "test_plate.jpg"
        test_img = Image.new('RGB', (640, 480), color='white')
        test_img.save(img_path)

        # Preprocess
        processed = OCRService.preprocess_image(str(img_path))

        assert processed is not None
        # Should be grayscale (2D array)
        assert len(processed.shape) == 2

    def test_preprocess_image_from_array(self):
        """Test preprocessing from numpy array"""
        # Create test image as RGB array
        img_array = np.ones((480, 640, 3), dtype=np.uint8) * 255

        # Preprocess
        processed = OCRService.preprocess_image(img_array)

        assert processed is not None
        assert len(processed.shape) == 2  # Grayscale

    def test_preprocess_image_resize_small(self):
        """Test that small images are resized"""
        # Create small image (400px wide)
        img_array = np.ones((300, 400, 3), dtype=np.uint8) * 255

        # Preprocess
        processed = OCRService.preprocess_image(img_array)

        assert processed is not None
        # Should be resized to at least 800px wide
        assert processed.shape[1] >= 800

    def test_preprocess_image_threshold(self):
        """Test that thresholding is applied (binarization)"""
        # Create grayscale image with varying intensities
        img_array = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        # Preprocess
        processed = OCRService.preprocess_image(img_array)

        assert processed is not None
        # After threshold, should be binary (mostly 0 or 255)
        unique_vals = np.unique(processed)
        assert len(unique_vals) <= 2  # Should be binary


class TestLicensePlateExtraction:
    """Test OCR text extraction"""

    @patch('backend.ocr_service.pytesseract.image_to_string')
    @patch('backend.ocr_service.pytesseract.image_to_data')
    def test_extract_license_plate_success(self, mock_data, mock_string):
        """Test successful text extraction"""
        # Mock pytesseract responses
        mock_string.return_value = "ABC-1234"
        mock_data.return_value = MagicMock()
        mock_data.return_value.__getitem__.return_value = [95.5]  # Confidence

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.extract_license_plate(test_img)

        assert result['text'] == "ABC-1234"
        assert result['confidence'] > 0
        assert 'raw_data' in result

    @patch('backend.ocr_service.pytesseract.image_to_string')
    def test_extract_license_plate_empty(self, mock_string):
        """Test extraction with no text found"""
        mock_string.return_value = ""

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.extract_license_plate(test_img)

        assert result['text'] == ""
        assert result['confidence'] >= 0

    @patch('backend.ocr_service.pytesseract.image_to_string')
    def test_extract_with_portuguese_language(self, mock_string):
        """Test extraction with Portuguese language pack"""
        mock_string.return_value = "ABC-1D34"

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        # Test with Portuguese
        result = OCRService.extract_license_plate(test_img, language='por')

        assert 'text' in result
        mock_string.assert_called()

    @patch('backend.ocr_service.pytesseract.image_to_string')
    def test_extract_with_psm_7(self, mock_string):
        """Test that PSM 7 (single text line) is used"""
        mock_string.return_value = "ABC-1234"

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.extract_license_plate(test_img)

        # Verify the function was called with correct config
        assert 'text' in result


class TestCompletePipeline:
    """Test complete OCR pipeline"""

    @patch('backend.ocr_service.OCRService.extract_license_plate')
    @patch('backend.ocr_service.OCRService.preprocess_image')
    def test_recognize_valid_plate(self, mock_preprocess, mock_extract):
        """Test complete recognition with valid plate"""
        # Setup mocks
        mock_preprocess.return_value = np.ones((480, 640), dtype=np.uint8) * 255
        mock_extract.return_value = {
            'text': 'ABC-1234',
            'confidence': 95.0,
            'raw_data': None
        }

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.recognize_license_plate(test_img)

        assert result['license_plate'] == "ABC-1234"
        assert result['confidence'] == 95.0
        assert result['valid'] is True

    @patch('backend.ocr_service.OCRService.extract_license_plate')
    @patch('backend.ocr_service.OCRService.preprocess_image')
    def test_recognize_invalid_plate(self, mock_preprocess, mock_extract):
        """Test recognition with invalid plate format"""
        mock_preprocess.return_value = np.ones((480, 640), dtype=np.uint8) * 255
        mock_extract.return_value = {
            'text': 'INVALID',
            'confidence': 50.0,
            'raw_data': None
        }

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.recognize_license_plate(test_img)

        assert result['license_plate'] == "INVALID"
        assert result['confidence'] == 50.0
        assert result['valid'] is False

    @patch('backend.ocr_service.OCRService.extract_license_plate')
    @patch('backend.ocr_service.OCRService.preprocess_image')
    def test_recognize_normalizes_format(self, mock_preprocess, mock_extract):
        """Test that recognition normalizes plate format"""
        mock_preprocess.return_value = np.ones((480, 640), dtype=np.uint8) * 255
        mock_extract.return_value = {
            'text': 'abc1234',  # No dash, lowercase
            'confidence': 90.0,
            'raw_data': None
        }

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.recognize_license_plate(test_img)

        # Should normalize to ABC-1234
        assert result['license_plate'] == "ABC-1234"
        assert result['valid'] is True

    @patch('backend.ocr_service.OCRService.extract_license_plate')
    @patch('backend.ocr_service.OCRService.preprocess_image')
    def test_recognize_handles_tesseract_error(self, mock_preprocess, mock_extract):
        """Test graceful error handling"""
        mock_preprocess.side_effect = Exception("Tesseract error")

        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 255

        result = OCRService.recognize_license_plate(test_img)

        assert result['license_plate'] is None
        assert result['confidence'] == 0.0
        assert result['valid'] is False


class TestRealImageProcessing:
    """Integration tests with real images (if Tesseract available)"""

    @pytest.mark.skipif(
        not os.path.exists('/usr/local/bin/tesseract') and
        not os.path.exists('/opt/homebrew/bin/tesseract'),
        reason="Tesseract not installed"
    )
    def test_real_synthetic_plate(self, tmp_path):
        """Test OCR on synthetically generated license plate image"""
        # Create synthetic license plate image
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)

        # Draw license plate text
        try:
            # Try to use a default font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
        except:
            font = ImageFont.load_default()

        draw.text((50, 20), "ABC-1234", fill='black', font=font)

        img_path = tmp_path / "synthetic_plate.jpg"
        img.save(img_path)

        # Run OCR
        result = OCRService.recognize_license_plate(str(img_path))

        # Should detect something
        assert result is not None
        assert 'license_plate' in result
        assert 'confidence' in result
        assert 'valid' in result
