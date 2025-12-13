"""
Tests for data source configuration.

Validates FileSource, BloombergSource, APISource configuration
and provider resolution logic.
"""

import json
from pathlib import Path

import pytest

from aponyx.data.sources import (
    FileSource,
    BloombergSource,
    APISource,
    resolve_provider,
)


class TestFileSource:
    """Test FileSource configuration."""

    def test_file_source_creation(self, tmp_path: Path):
        """Test creating FileSource instance with registry."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"cdx_ig_5y": "cdx_ig_5y_abc123.parquet"}
        registry_path = data_dir / "registry.json"
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        assert source.base_dir == data_dir
        assert isinstance(source.base_dir, Path)
        assert source.security_mapping == registry

    def test_file_source_from_string(self, tmp_path: Path):
        """Test FileSource accepts string path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"vix": "vix_abc123.parquet"}
        registry_path = data_dir / "registry.json"
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(str(data_dir))

        assert isinstance(source.base_dir, Path)
        assert source.base_dir == data_dir
        assert source.security_mapping == registry

    def test_file_source_frozen(self, tmp_path: Path):
        """Test FileSource is frozen (immutable)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"vix": "vix_abc123.parquet"}
        registry_path = data_dir / "registry.json"
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(AttributeError):
            source.base_dir = Path("other")  # type: ignore

    def test_file_source_equality(self, tmp_path: Path):
        """Test FileSource equality comparison."""
        # Create two directories with same registry
        data_dir1 = tmp_path / "data1"
        data_dir1.mkdir()
        registry = {"vix": "vix_abc123.parquet"}
        with open(data_dir1 / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        data_dir2 = tmp_path / "data2"
        data_dir2.mkdir()
        with open(data_dir2 / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source1 = FileSource(data_dir1)
        source2 = FileSource(data_dir1)
        source3 = FileSource(data_dir2)

        assert source1 == source2
        assert source1 != source3  # Different base_dir


class TestBloombergSource:
    """Test BloombergSource configuration."""

    def test_bloomberg_source_creation(self):
        """Test creating BloombergSource instance."""
        source = BloombergSource()

        assert isinstance(source, BloombergSource)

    def test_bloomberg_source_frozen(self):
        """Test BloombergSource is frozen (immutable)."""
        source = BloombergSource()

        with pytest.raises(AttributeError):
            source.new_field = "value"  # type: ignore

    def test_bloomberg_source_equality(self):
        """Test BloombergSource equality comparison."""
        source1 = BloombergSource()
        source2 = BloombergSource()

        assert source1 == source2


class TestAPISource:
    """Test APISource configuration."""

    def test_api_source_creation(self):
        """Test creating APISource instance."""
        source = APISource(endpoint="http://api.example.com/data")

        assert source.endpoint == "http://api.example.com/data"
        assert source.params is None

    def test_api_source_with_params(self):
        """Test APISource with parameters."""
        params = {"key": "value", "format": "json"}
        source = APISource(
            endpoint="http://api.example.com/data",
            params=params,
        )

        assert source.endpoint == "http://api.example.com/data"
        assert source.params == params

    def test_api_source_frozen(self):
        """Test APISource is frozen (immutable)."""
        source = APISource(endpoint="http://api.example.com")

        with pytest.raises(AttributeError):
            source.endpoint = "http://other.com"  # type: ignore

    def test_api_source_equality(self):
        """Test APISource equality comparison."""
        source1 = APISource(endpoint="http://api.example.com")
        source2 = APISource(endpoint="http://api.example.com")
        source3 = APISource(endpoint="http://other.example.com")

        assert source1 == source2
        assert source1 != source3

    def test_api_source_with_different_params(self):
        """Test APISource with different params are not equal."""
        source1 = APISource(endpoint="http://api.example.com", params={"a": 1})
        source2 = APISource(endpoint="http://api.example.com", params={"b": 2})

        assert source1 != source2


class TestResolveProvider:
    """Test provider resolution logic."""

    def test_resolve_provider_file(self, tmp_path: Path):
        """Test resolving FileSource provider."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"vix": "vix_abc123.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        provider = resolve_provider(source)

        assert provider == "file"

    def test_resolve_provider_bloomberg(self):
        """Test resolving BloombergSource provider."""
        source = BloombergSource()

        provider = resolve_provider(source)

        assert provider == "bloomberg"

    def test_resolve_provider_api(self):
        """Test resolving APISource provider."""
        source = APISource(endpoint="http://api.example.com")

        provider = resolve_provider(source)

        assert provider == "api"

    def test_resolve_provider_unknown(self):
        """Test error for unknown source type."""

        # Create a mock unknown source
        class UnknownSource:
            pass

        unknown = UnknownSource()

        with pytest.raises(ValueError, match="Unknown source type"):
            resolve_provider(unknown)  # type: ignore


class TestDataSourceUnion:
    """Test DataSource union type usage."""

    def test_data_source_accepts_file(self, tmp_path: Path):
        """Test DataSource accepts FileSource."""
        from aponyx.data.sources import DataSource

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"vix": "vix_abc123.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source: DataSource = FileSource(data_dir)
        assert isinstance(source, FileSource)

    def test_data_source_accepts_bloomberg(self):
        """Test DataSource accepts BloombergSource."""
        from aponyx.data.sources import DataSource

        source: DataSource = BloombergSource()
        assert isinstance(source, BloombergSource)

    def test_data_source_accepts_api(self):
        """Test DataSource accepts APISource."""
        from aponyx.data.sources import DataSource

        source: DataSource = APISource(endpoint="http://api.example.com")
        assert isinstance(source, APISource)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_file_source_with_relative_path(self, tmp_path: Path):
        """Test FileSource with relative path can fail if registry missing."""
        # This test validates that relative paths work when registry exists
        # In practice, relative paths should be avoided in favor of absolute paths

        # FileSource requires registry.json to exist
        # Without registry, it should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Registry file not found"):
            source = FileSource(Path("../data"))

    def test_file_source_with_absolute_path(self, tmp_path: Path):
        """Test FileSource with absolute path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create registry.json
        registry = {"vix": "vix_abc123.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        assert source.base_dir == data_dir
        assert source.base_dir.is_absolute()

    def test_api_source_with_empty_params(self):
        """Test APISource with empty params dict."""
        source = APISource(endpoint="http://api.example.com", params={})

        assert source.params == {}

    def test_api_source_with_complex_params(self):
        """Test APISource with nested parameters."""
        params = {
            "filters": {"date": "2024-01-01", "instrument": "CDX"},
            "options": {"format": "json", "compress": True},
        }
        source = APISource(endpoint="http://api.example.com", params=params)

        assert source.params == params
        assert source.params["filters"]["instrument"] == "CDX"
