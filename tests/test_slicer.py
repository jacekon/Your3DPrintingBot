"""
Test script for OrcaSlicer integration.
Run with: python -m tests.test_slicer

This script tests the slicer module independently before bot integration.
"""
import asyncio
import logging
from pathlib import Path

from src.slicer import OrcaSlicer

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_slicer():
    """Test OrcaSlicer with sample STL files."""
    
    logger.info("=" * 60)
    logger.info("OrcaSlicer Integration Test")
    logger.info("=" * 60)
    
    # Initialize slicer
    try:
        slicer = OrcaSlicer()
        logger.info("✅ Slicer initialized successfully")
        logger.info(f"   Binary: {slicer.orca_bin}")
        logger.info(f"   Preset: {slicer.preset_path}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize slicer: {e}")
        return
    
    # Find test STL files in data/jobs/
    data_dir = Path(__file__).resolve().parent.parent / "data" / "jobs"
    stl_files = []
    
    if data_dir.exists():
        for job_dir in data_dir.iterdir():
            if job_dir.is_dir():
                job_stls = list(job_dir.glob("*.stl"))
                stl_files.extend(job_stls)
                if stl_files:
                    break  # Use files from first job with STLs
    
    if not stl_files:
        logger.warning("⚠️  No STL files found in data/jobs/")
        logger.info("To test properly:")
        logger.info("1. Download a model using the bot, OR")
        logger.info("2. Place sample STL files in data/jobs/test/")
        return
    
    logger.info(f"\n📁 Found {len(stl_files)} STL file(s):")
    for stl in stl_files[:3]:  # Show first 3
        size_mb = stl.stat().st_size / (1024 * 1024)
        logger.info(f"   • {stl.name} ({size_mb:.2f} MB)")
    if len(stl_files) > 3:
        logger.info(f"   ... and {len(stl_files) - 3} more")
    
    # Create test output directory
    output_dir = Path(__file__).resolve().parent.parent / "data" / "test_gcode"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test slicing
    logger.info(f"\n🔧 Starting slicing process...")
    logger.info(f"   Output directory: {output_dir}")
    
    try:
        # Test with first file only to save time
        test_file = stl_files[0]
        logger.info(f"\n⏳ Slicing: {test_file.name}")
        
        gcode_path = await slicer.slice_file(test_file, output_dir)
        
        # Verify output
        if gcode_path.exists():
            size_kb = gcode_path.stat().st_size / 1024
            logger.info(f"✅ Slicing successful!")
            logger.info(f"   Output: {gcode_path.name}")
            logger.info(f"   Size: {size_kb:.1f} KB")
            
            # Show first few lines of G-code
            logger.info(f"\n📄 G-code preview (first 10 lines):")
            with open(gcode_path, 'r') as f:
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    logger.info(f"   {line.rstrip()}")
            
            logger.info(f"\n✅ Test completed successfully!")
            logger.info(f"   G-code saved to: {gcode_path}")
        else:
            logger.error(f"❌ G-code file not created")
            
    except Exception as e:
        logger.exception(f"❌ Slicing failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Verify OrcaSlicer is installed: brew install --cask orcaslicer")
        logger.info("2. Check preset file exists at: config/printers/Elegoo-Centauri-Carbon-PLA-CF-Fine.3mf")
        logger.info("3. Try running OrcaSlicer manually to verify it works")


async def test_batch_slicing():
    """Test slicing multiple files at once."""
    logger.info("\n" + "=" * 60)
    logger.info("Batch Slicing Test")
    logger.info("=" * 60)
    
    # Find STL files
    data_dir = Path(__file__).resolve().parent.parent / "data" / "jobs"
    stl_files = []
    
    if data_dir.exists():
        for job_dir in data_dir.iterdir():
            if job_dir.is_dir():
                job_stls = list(job_dir.glob("*.stl"))
                if len(job_stls) >= 2:  # Need at least 2 files for batch test
                    stl_files = job_stls[:3]  # Test with max 3 files
                    break
    
    if len(stl_files) < 2:
        logger.info("⚠️  Skipping batch test (need at least 2 STL files)")
        return
    
    logger.info(f"Testing with {len(stl_files)} files...")
    
    output_dir = Path(__file__).resolve().parent.parent / "data" / "test_gcode_batch"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        slicer = OrcaSlicer()
        gcode_paths = await slicer.slice_files(stl_files, output_dir)
        
        logger.info(f"✅ Batch slicing successful!")
        logger.info(f"   Generated {len(gcode_paths)} G-code files:")
        for gcode in gcode_paths:
            size_kb = gcode.stat().st_size / 1024
            logger.info(f"   • {gcode.name} ({size_kb:.1f} KB)")
            
    except Exception as e:
        logger.exception(f"❌ Batch slicing failed: {e}")


def main():
    """Run all tests."""
    asyncio.run(test_slicer())
    
    # Uncomment to also test batch slicing
    # asyncio.run(test_batch_slicing())


if __name__ == "__main__":
    main()
