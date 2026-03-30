import pytest
from backend.annotation_service import AnnotationService

def test_annotation_service_initialization():
    """Test that AnnotationService can be initialized."""
    service = AnnotationService()
    assert service is not None
    assert hasattr(service, 'get_frame_annotations')
    assert hasattr(service, 'save_annotations')
    assert hasattr(service, 'copy_annotations_from_frame')
    assert hasattr(service, 'delete_annotation')
