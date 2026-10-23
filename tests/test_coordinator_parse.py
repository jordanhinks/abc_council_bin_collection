import pytest
from custom_components.abc_council_bin_collection.coordinator import BinCollectionDataUpdateCoordinator


def test_parse_html_single_and_multiple_dates():
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    html = '''
    <div class="heading bg-black">Domestic</div><hr></div>
    <div class="col-sm-12 col-md-9">
      <h4><i class="fa fa-calendar"></i> 01/01/2025 </h4>
      <h4><i class="fa fa-calendar"></i> 15/01/2025 </h4>
    </div><div class="col-sm-12 col-md-3">
    '''

    result = BinCollectionDataUpdateCoordinator._parse_html(coord, html)
    assert "Domestic Collections" in result
    assert result["Domestic Collections"][0] == "2025-01-01"
    assert result["Domestic Collections"][1] == "2025-01-15"


def test_parse_html_malformed_html():
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    html = '<div>no relevant markers here</div>'
    result = BinCollectionDataUpdateCoordinator._parse_html(coord, html)
    # Should still include keys but with default "No collection scheduled"
    assert result["Domestic Collections"] == ["No collection scheduled"]
    assert result["Recycling Collections"] == ["No collection scheduled"]
    assert result["Garden/Food Collections"] == ["No collection scheduled"]


def test_parse_html_uk_date_format():
    coord = BinCollectionDataUpdateCoordinator.__new__(BinCollectionDataUpdateCoordinator)
    # Test an ambiguous date like 04/11/2026 (Nov 4th). If parsed as US, it becomes April 11th.
    html = '''
    <div class="heading bg-green">Recycling</div><hr></div>
    <div class="col-sm-12 col-md-9">
      <h4><i class="fa fa-calendar"></i> 04/11/2026 </h4>
    </div><div class="col-sm-12 col-md-3">
    '''
    result = BinCollectionDataUpdateCoordinator._parse_html(coord, html)
    assert "Recycling Collections" in result
    # We expect 2026-11-04 (Nov 4th). If the bug existed, it would return 2026-04-11.
    assert result["Recycling Collections"][0] == "2026-11-04"
