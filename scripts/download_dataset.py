"""
Download and extract the MovieLens 25M dataset.

This script automates the download of the MovieLens 25M dataset from GroupLens
and extracts it to the raw/ directory.

Usage:
    python scripts/download_dataset.py
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

# Configuration
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-25m.zip"
RAW_DIR = Path(__file__).parent.parent / "raw"
ZIP_PATH = RAW_DIR / "ml-25m.zip"
EXTRACT_DIR = RAW_DIR / "ml-25m"

# Expected files in the dataset
EXPECTED_FILES = {
    "ratings.csv",
    "movies.csv",
    "genome-scores.csv",
    "genome-tags.csv",
    "tags.csv",
    "links.csv",
    "README.html"
}


def download_file(url, destination):
    """Download a file from URL with progress bar."""
    print(f"\n📥 Downloading MovieLens 25M dataset...")
    print(f"   URL: {url}")
    print(f"   Destination: {destination}")
    
    try:
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, int(100.0 * downloaded / total_size))
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r   Progress: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")
        
        urllib.request.urlretrieve(url, destination, show_progress)
        print("\n   ✅ Download complete!")
        return True
    except Exception as e:
        print(f"\n   ❌ Download failed: {e}")
        return False


def extract_archive(zip_path, extract_to):
    """Extract ZIP archive and move files to raw/ directory."""
    print(f"\n📦 Extracting dataset...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to.parent)
        print("   ✅ Extraction complete!")
        
        # Move files from ml-25m/ subdirectory to raw/
        if extract_to.exists():
            print(f"\n📁 Organizing files...")
            for file in EXPECTED_FILES:
                src = extract_to / file
                dst = extract_to.parent / file
                
                if src.exists():
                    shutil.move(str(src), str(dst))
                    print(f"   ✅ Moved {file}")
                else:
                    print(f"   ⚠️  {file} not found (optional)")
            
            # Remove empty subdirectory
            if extract_to.exists() and not any(extract_to.iterdir()):
                extract_to.rmdir()
                print(f"   ✅ Cleaned up temporary directory")
        
        return True
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return False


def verify_dataset():
    """Verify that all required files are present."""
    print(f"\n✔️  Verifying dataset...")
    
    required = {"ratings.csv", "movies.csv", "genome-scores.csv", "genome-tags.csv"}
    optional = {"tags.csv", "links.csv"}
    
    found_required = []
    found_optional = []
    
    for file in required:
        if (RAW_DIR / file).exists():
            found_required.append(file)
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (REQUIRED)")
    
    for file in optional:
        if (RAW_DIR / file).exists():
            found_optional.append(file)
            print(f"   ✅ {file} (optional)")
    
    if len(found_required) == len(required):
        print(f"\n🎉 Dataset successfully downloaded and verified!")
        print(f"   Location: {RAW_DIR}")
        return True
    else:
        print(f"\n❌ Dataset verification failed. Missing required files.")
        return False


def main():
    """Main download workflow."""
    print("=" * 60)
    print("MovieLens 25M Dataset Downloader")
    print("=" * 60)
    
    # Create raw directory if it doesn't exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if dataset already exists
    required_files = {"ratings.csv", "movies.csv", "genome-scores.csv", "genome-tags.csv"}
    existing_files = {f.name for f in RAW_DIR.glob("*.csv")}
    
    if required_files.issubset(existing_files):
        print("\n✅ Dataset already exists in raw/ directory!")
        print(f"   Location: {RAW_DIR}")
        return True
    
    # Download dataset
    if not download_file(DATASET_URL, ZIP_PATH):
        return False
    
    # Extract dataset
    if not extract_archive(ZIP_PATH, EXTRACT_DIR):
        return False
    
    # Clean up ZIP file
    try:
        ZIP_PATH.unlink()
        print("\n🧹 Cleaned up ZIP file")
    except Exception as e:
        print(f"\n⚠️  Could not delete ZIP file: {e}")
    
    # Verify dataset
    return verify_dataset()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
