"""Test job ID generation with new format."""
import re
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from src.downloads.fetcher import _generate_job_id


def test_job_id_format():
    """Test that job ID follows the yyyy.mm.dd-userid-increment format."""
    user_id = 123456
    
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = Path(tmpdir)
        
        # Generate first job ID
        job_id = _generate_job_id(user_id, jobs_dir)
        
        # Verify format
        pattern = r'^\d{4}\.\d{2}\.\d{2}-\d+-\d{3}$'
        assert re.match(pattern, job_id), f"Job ID {job_id} doesn't match pattern yyyy.mm.dd-userid-increment"
        
        # Verify it contains today's date
        today = datetime.now().strftime("%Y.%m.%d")
        assert job_id.startswith(today), f"Job ID should start with today's date {today}"
        
        # Verify user ID is in the job ID
        assert f"-{user_id}-" in job_id, f"Job ID should contain user ID {user_id}"
        
        # Verify first increment is 001
        assert job_id.endswith("-001"), "First job ID should end with -001"
        
        # Create the directory to simulate a saved job
        (jobs_dir / job_id).mkdir(parents=True)
        
        # Generate second job ID for same user
        job_id2 = _generate_job_id(user_id, jobs_dir)
        assert job_id2.endswith("-002"), "Second job ID should end with -002"
        
        # Create second directory
        (jobs_dir / job_id2).mkdir(parents=True)
        
        # Generate third job ID
        job_id3 = _generate_job_id(user_id, jobs_dir)
        assert job_id3.endswith("-003"), "Third job ID should end with -003"


def test_different_users():
    """Test that different users get independent increments."""
    user1 = 111111
    user2 = 222222
    
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = Path(tmpdir)
        
        # Generate job for user 1
        job_id1 = _generate_job_id(user1, jobs_dir)
        (jobs_dir / job_id1).mkdir(parents=True)
        
        # Generate job for user 2 - should also be 001
        job_id2 = _generate_job_id(user2, jobs_dir)
        
        assert f"-{user1}-001" in job_id1
        assert f"-{user2}-001" in job_id2
        
        # Generate another job for user 1 - should be 002
        job_id1_2 = _generate_job_id(user1, jobs_dir)
        (jobs_dir / job_id1_2).mkdir(parents=True)
        
        assert f"-{user1}-002" in job_id1_2
