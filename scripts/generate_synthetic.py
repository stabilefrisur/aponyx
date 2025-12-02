"""Generate synthetic data for testing."""

from pathlib import Path
from aponyx.data.sample_data import generate_for_fetch_interface

if __name__ == "__main__":
    output_dir = Path("data/raw/synthetic")
    print(f"Generating synthetic data in {output_dir}...")
    file_paths = generate_for_fetch_interface(output_dir)
    print(f"Generated {len(file_paths)} files")
    print("Registry created at:", output_dir / "registry.json")
