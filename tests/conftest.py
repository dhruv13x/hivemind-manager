import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_banner(request):
    if "test_banner" in request.node.nodeid:
        yield
    else:
        with patch("hm.banner.print_logo", return_value=None):
            yield
