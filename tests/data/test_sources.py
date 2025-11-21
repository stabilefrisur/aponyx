"""
Tests for data source configuration.

Validates FileSource, BloombergSource, APISource configuration
and provider resolution logic.
"""

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

    def test_file_source_creation(self):
        """Test creating FileSource instance."""
        path = Path("data/test.parquet")
        source = FileSource(path)

        assert source.path == path
        assert isinstance(source.path, Path)

    def test_file_source_from_string(self):
        """Test FileSource accepts string path."""
        source = FileSource("data/test.parquet")

        assert isinstance(source.path, Path)
        assert source.path == Path("data/test.parquet")

    def test_file_source_frozen(self):
        """Test FileSource is frozen (immutable)."""
        source = FileSource(Path("test.parquet"))

        with pytest.raises(AttributeError):
            source.path = Path("other.parquet")  # type: ignore

    def test_file_source_equality(self):
        """Test FileSource equality comparison."""
        source1 = FileSource(Path("test.parquet"))
        source2 = FileSource(Path("test.parquet"))
        source3 = FileSource(Path("other.parquet"))

        assert source1 == source2
        assert source1 != source3


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

    def test_resolve_provider_file(self):
        """Test resolving FileSource provider."""
        source = FileSource(Path("data.parquet"))

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

    def test_data_source_accepts_file(self):
        """Test DataSource accepts FileSource."""
        from aponyx.data.sources import DataSource

        source: DataSource = FileSource(Path("test.parquet"))
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

    def test_file_source_with_relative_path(self):
        """Test FileSource with relative path."""
        source = FileSource(Path("../data/test.parquet"))

        assert source.path == Path("../data/test.parquet")

    def test_file_source_with_absolute_path(self):
        """Test FileSource with absolute path."""
        import sys

        if sys.platform == "win32":
            abs_path = Path("C:/absolute/path/test.parquet")
        else:
            abs_path = Path("/absolute/path/test.parquet")

        source = FileSource(abs_path)

        assert source.path == abs_path
        assert source.path.is_absolute()

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
