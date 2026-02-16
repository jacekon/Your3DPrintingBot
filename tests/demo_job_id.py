#!/usr/bin/env python3
"""Demo script to show the new job ID format."""
from datetime import datetime
from pathlib import Path
import tempfile
from src.downloads.fetcher import _generate_job_id


def main():
    """Demonstrate the new job ID format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jobs_dir = Path(tmpdir)
        
        print('Job ID Format Examples:')
        print('=' * 60)
        
        # User 1 creates 3 jobs
        user1_id = 123456789
        for i in range(3):
            job_id = _generate_job_id(user1_id, jobs_dir)
            print(f'User {user1_id}, Job {i+1}: {job_id}')
            (jobs_dir / job_id).mkdir(parents=True)
        
        print()
        
        # User 2 creates 2 jobs
        user2_id = 987654321
        for i in range(2):
            job_id = _generate_job_id(user2_id, jobs_dir)
            print(f'User {user2_id}, Job {i+1}: {job_id}')
            (jobs_dir / job_id).mkdir(parents=True)
        
        print()
        print('Format: yyyy.mm.dd-userid-increment')
        print('- Date: Current date')
        print('- User ID: Telegram user ID')
        print('- Increment: Auto-incremented per user per day (001, 002, 003, ...)')


if __name__ == '__main__':
    main()
