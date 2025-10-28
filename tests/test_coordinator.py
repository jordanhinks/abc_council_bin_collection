import pytest
from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator

SAMPLE_HTML = """
<div class="heading bg-black">...</div><hr></div>
<div class="col-sm-12 col-md-9">
  <h4><i class="fa fa-calendar"></i> 01/01/2025 </h4>
  <h4><i class="fa fa-calendar"></i> 15/01/2025 </h4>
</div><div class="col-sm-12 col-md-3">
"""

def test_parse_html_dates():
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)

    coord.event_summaries = {}
    result = BinCollectionDataUpdateCoordinator._parse_html(coord, SAMPLE_HTML)

    assert "Domestic Collections" in result
    assert result["Domestic Collections"][0] == "2025-01-01"