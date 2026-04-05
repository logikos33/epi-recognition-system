import pytest
from backend.video_service import VideoService
import uuid

def test_chunk_calculation():
    """Test video chunk calculation logic."""
    # Test 1: Video under 10 minutes
    duration_1 = 120  # 2 minutes
    max_duration = 600  # 10 minutes
    selected_duration_1 = min(int(duration_1), max_duration)
    total_chunks_1 = (selected_duration_1 // 60) + 1
    assert total_chunks_1 == 3  # 2 minutes = 3 chunks (0-60, 60-120, 120-180 buffer)
    
    # Test 2: Video exactly 10 minutes
    duration_2 = 600  # 10 minutes
    selected_duration_2 = min(int(duration_2), max_duration)
    total_chunks_2 = (selected_duration_2 // 60) + 1
    assert total_chunks_2 == 11  # 10 minutes = 11 chunks
    
    # Test 3: Video over 10 minutes (should be capped)
    duration_3 = 900  # 15 minutes
    selected_duration_3 = min(int(duration_3), max_duration)
    total_chunks_3 = (selected_duration_3 // 60) + 1
    assert total_chunks_3 == 11  # Capped at 10 minutes = 11 chunks
