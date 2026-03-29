"""
OCR Service for Fueling Monitoring System

Handles license plate recognition using Tesseract OCR.
Supports Brazilian license plate formats (old and Mercosur).
"""
import pytesseract
import cv2
import numpy as np
from PIL import Image
import re
import logging
from typing import Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR-based license plate recognition"""

    # Brazilian license plate patterns
    # Old format: ABC-1234 or ABC1234 (3 letters + 4 numbers)
    # Mercosur format: MER-1234 or MER1234 (3 letters + 4 numbers)
    LICENSE_PLATE_PATTERN = re.compile(
        r'^([A-Za-z]{3})-?(\d{4})$',  # 3 letters, optional dash, 4 numbers
        re.IGNORECASE
    )

    @staticmethod
    def preprocess_image(image_path_or_array: Union[str, np.ndarray]) -> Optional[np.ndarray]:
        """
        Preprocess image for OCR by applying enhancement techniques.

        Args:
            image_path_or_array: Path to image file or numpy array (BGR or RGB)

        Returns:
            Preprocessed grayscale image as numpy array, or None if failed
        """
        try:
            # Load image
            if isinstance(image_path_or_array, str):
                # Load from file path
                img = cv2.imread(image_path_or_array)
                if img is None:
                    logger.error(f"❌ Failed to load image: {image_path_or_array}")
                    return None
            elif isinstance(image_path_or_array, np.ndarray):
                # Use numpy array directly
                img = image_path_or_array.copy()
            else:
                logger.error(f"❌ Unsupported image type: {type(image_path_or_array)}")
                return None

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Resize if too small (min width 800px for better OCR)
            height, width = gray.shape
            if width < 800:
                scale_factor = 800 / width
                new_width = 800
                new_height = int(height * scale_factor)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.debug(f"🔧 Resized image from {width}x{height} to {new_width}x{new_height}")

            # Apply mild Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)

            # Use Otsu's thresholding for binary image (better for high-contrast text)
            # This works better than adaptive threshold for license plates
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Invert if needed (Tesseract expects dark text on light background)
            # Check if most pixels are white (background)
            white_pixels = np.sum(thresh == 255)
            black_pixels = np.sum(thresh == 0)
            if black_pixels > white_pixels:
                thresh = cv2.bitwise_not(thresh)

            logger.debug("✅ Image preprocessed successfully")
            return thresh

        except Exception as e:
            logger.error(f"❌ Failed to preprocess image: {e}")
            return None

    @staticmethod
    def extract_license_plate(
        image_path_or_array: Union[str, np.ndarray],
        language: str = 'por'
    ) -> Dict[str, any]:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_path_or_array: Path to image file or numpy array
            language: Tesseract language code ('por' for Portuguese, 'eng' for English)

        Returns:
            Dictionary with:
                - text: Extracted text string
                - confidence: Average confidence score (0-100)
                - raw_data: Raw Tesseract output data
        """
        try:
            # Preprocess image first
            preprocessed = OCRService.preprocess_image(image_path_or_array)
            if preprocessed is None:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'raw_data': None
                }

            # Convert to PIL Image for Tesseract
            pil_image = Image.fromarray(preprocessed)

            # Configure Tesseract for license plate recognition
            # PSM 7: Treat image as single text line
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'

            # Extract text with confidence data
            text = pytesseract.image_to_string(
                pil_image,
                lang=language,
                config=custom_config
            )

            # Get detailed data including confidence scores
            try:
                raw_data = pytesseract.image_to_data(
                    pil_image,
                    lang=language,
                    config=custom_config,
                    output_type=pytesseract.Output.DICT
                )

                # Calculate average confidence from detected text
                confidences = [int(conf) for conf in raw_data['conf'] if str(conf) != '-1' and int(conf) > 0]
                avg_confidence = np.mean(confidences) if confidences else 0.0
            except Exception:
                # If image_to_data fails, use default confidence
                raw_data = None
                avg_confidence = 0.0

            # Clean up extracted text
            text = text.strip().upper()

            logger.debug(f"🔍 Extracted text: '{text}' (confidence: {avg_confidence:.1f}%)")

            return {
                'text': text,
                'confidence': float(avg_confidence),
                'raw_data': raw_data
            }

        except Exception as e:
            logger.error(f"❌ Failed to extract license plate: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'raw_data': None
            }

    @staticmethod
    def validate_license_plate(text: str) -> Dict[str, any]:
        """
        Validate Brazilian license plate format.

        Args:
            text: License plate text to validate

        Returns:
            Dictionary with:
                - valid: Boolean indicating if format is valid
                - normalized: Normalized format (ABC-1234)
                - confidence: Confidence score (1.0 for valid, 0.0 for invalid)
        """
        if not text or len(text) < 6:
            return {
                'valid': False,
                'normalized': text,
                'confidence': 0.0
            }

        # Remove whitespace and convert to uppercase
        cleaned = text.strip().upper()

        # Match against pattern
        match = OCRService.LICENSE_PLATE_PATTERN.match(cleaned)

        if match:
            # Normalize format: add dash if missing
            letters = match.group(1).upper()
            numbers = match.group(2)
            normalized = f"{letters}-{numbers}"

            logger.debug(f"✅ Valid license plate: {normalized}")
            return {
                'valid': True,
                'normalized': normalized,
                'confidence': 1.0
            }
        else:
            logger.debug(f"❌ Invalid license plate format: {cleaned}")
            return {
                'valid': False,
                'normalized': cleaned,
                'confidence': 0.0
            }

    @staticmethod
    def recognize_license_plate(image_path_or_array: Union[str, np.ndarray]) -> Dict[str, any]:
        """
        Complete OCR pipeline: preprocess, extract, and validate license plate.

        Args:
            image_path_or_array: Path to image file or numpy array

        Returns:
            Dictionary with:
                - license_plate: Normalized plate string or None
                - confidence: OCR confidence score (0-100)
                - valid: Boolean indicating if format is valid
        """
        try:
            # Preprocess image (this may raise exception)
            preprocessed = OCRService.preprocess_image(image_path_or_array)
            if preprocessed is None:
                logger.error("❌ Failed to preprocess image")
                return {
                    'license_plate': None,
                    'confidence': 0.0,
                    'valid': False
                }

            # Extract text from image
            extraction_result = OCRService.extract_license_plate(image_path_or_array)

            if not extraction_result['text']:
                logger.warning("⚠️ No text detected in image")
                return {
                    'license_plate': None,
                    'confidence': 0.0,
                    'valid': False
                }

            # Validate format
            validation_result = OCRService.validate_license_plate(extraction_result['text'])

            # Combine results
            result = {
                'license_plate': validation_result['normalized'] if validation_result['valid'] else extraction_result['text'],
                'confidence': extraction_result['confidence'],
                'valid': validation_result['valid']
            }

            if result['valid']:
                logger.info(f"✅ Recognized license plate: {result['license_plate']} (confidence: {result['confidence']:.1f}%)")
            else:
                logger.warning(f"⚠️ Detected text '{result['license_plate']}' but format is invalid")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to recognize license plate: {e}")
            return {
                'license_plate': None,
                'confidence': 0.0,
                'valid': False
            }
