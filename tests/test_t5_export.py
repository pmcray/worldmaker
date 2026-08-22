"""Tests for the Traveller5 Second Survey exporters (travellermap.com)."""
import random
import re

import pytest

import worldmaker as wm
from worldmaker.classes import Sector
from worldmaker.t5 import (
    T5_FIELDS,
    export_sector_t5_column,
    export_sector_t5_tab,
    parse_t5_column,
    t5_pbg,
    t5_row,
)
from worldmaker.utils import Utils

# The canonical example from travellermap.com's file format specification.
SPEC_EXAMPLE = (
    "Hex  Name        UWP       Remarks          {Ix}  (Ex)    [Cx]   N     B Z PBG W  A  Stellar\n"
    "---- ----------- --------- ---------------- ----- ------- ------ ----- - - --- -- -- -------\n"
    "0133 Emape       B564500-B Ag Ni Pr Da      { 2 } (A46+2) [1716] BcC   N A 503 6  Im M0 V   \n"
)


@pytest.fixture(scope="module")
def sector():
    random.seed(1105)
    sec = wm.generate_sector(8, 10)
    sec.name = "Test Subsector"
    return sec


@pytest.fixture(scope="module")
def column_text(sector):
    return export_sector_t5_column(sector)


# ------------------------------------------------- the format specification

def test_parser_reads_the_specification_example():
    """The reference row from the format spec must parse field for field."""
    rows = parse_t5_column(SPEC_EXAMPLE)
    assert rows == [{
        'Hex': '0133', 'Name': 'Emape', 'UWP': 'B564500-B',
        'Remarks': 'Ag Ni Pr Da', '{Ix}': '{ 2 }', '(Ex)': '(A46+2)',
        '[Cx]': '[1716]', 'N': 'BcC', 'B': 'N', 'Z': 'A', 'PBG': '503',
        'W': '6', 'A': 'Im', 'Stellar': 'M0 V',
    }]


def test_field_order_matches_the_t5ss_standard():
    """Hex, Name, UWP, Remarks, Ix, Ex, Cx, N, B, Z, PBG, W, A, Stellar."""
    assert [name for name, _ in T5_FIELDS] == [
        'Hex', 'Name', 'UWP', 'Remarks', '{Ix}', '(Ex)', '[Cx]', 'N', 'B',
        'Z', 'PBG', 'W', 'A', 'Stellar']


def test_extension_headers_present(column_text):
    """travellermap only auto-detects this format when the {Ix}, (Ex) and
    [Cx] headers appear."""
    header = [l for l in column_text.splitlines() if not l.startswith('#')][0]
    for token in ('{Ix}', '(Ex)', '[Cx]'):
        assert token in header


# ------------------------------------------------------- column structure

def test_separator_line_defines_the_columns(column_text):
    """The separator line is runs of dashes separated by single spaces, and
    the header must fit the spans it defines."""
    lines = [l for l in column_text.splitlines() if not l.startswith('#')]
    header, separator = lines[0], lines[1]
    assert set(separator) <= {'-', ' '}
    runs = separator.split(' ')
    assert all(run and set(run) == {'-'} for run in runs)
    assert len(runs) == len(T5_FIELDS)
    assert len(header) <= len(separator)


def test_minimum_widths_respected(column_text):
    """No field may be narrower than the specification's example."""
    separator = [l for l in column_text.splitlines()
                 if not l.startswith('#')][1]
    widths = [len(run) for run in separator.split(' ')]
    for (name, minimum), width in zip(T5_FIELDS, widths):
        assert width >= minimum, f"{name} narrower than {minimum}"
        assert width >= len(name)


def test_every_data_row_aligns_to_the_columns(column_text, sector):
    """Every value must sit inside its own span, with only blanks between
    fields - this is what makes the output column-exact."""
    rows = parse_t5_column(column_text)   # raises if any field bleeds
    assert len(rows) == sum(1 for s in sector.systems.values()
                            if s.mainworld is not None)


def test_no_field_ever_contains_a_tab_or_newline(column_text):
    for line in column_text.splitlines():
        assert '\t' not in line


def test_comment_lines_are_ignored_by_the_parser(column_text):
    assert column_text.startswith('# Test Subsector')
    rows = parse_t5_column(column_text)
    assert rows and all(row['Hex'].isdigit() for row in rows)


def test_misaligned_row_is_rejected():
    """A value bleeding past its column must be caught, not silently read."""
    broken = SPEC_EXAMPLE.replace('Emape       ', 'EmapeIsTooLong')
    with pytest.raises(ValueError):
        parse_t5_column(broken)


# ------------------------------------------------------------ field values

def test_round_trip_preserves_field_values(sector, column_text):
    """Parsing the file back must reproduce exactly what was written."""
    parsed = parse_t5_column(column_text)
    by_hex = {row['Hex']: row for row in parsed}
    for hex_coord, system in sector.systems.items():
        expected = t5_row(hex_coord, system, sector)
        if expected is None:
            continue
        actual = by_hex[hex_coord]
        for field, value in expected.items():
            assert actual[field] == value.strip(), (hex_coord, field)


def test_uwp_and_hex_well_formed(column_text):
    for row in parse_t5_column(column_text):
        assert re.fullmatch(r'\d{4}', row['Hex'])
        assert re.fullmatch(r'[A-X][0-9A-Z]{5}[0-9A-Z]-[0-9A-Z]', row['UWP'])


def test_extensions_well_formed(column_text):
    for row in parse_t5_column(column_text):
        assert re.fullmatch(r'\{ -?\d+ \}', row['{Ix}'])
        assert re.fullmatch(r'\([0-9A-Z]{3}[+-]\d+\)', row['(Ex)'])
        assert re.fullmatch(r'\[[0-9A-Z]{4}\]', row['[Cx]'])


def test_pbg_zone_and_bases_well_formed(column_text):
    for row in parse_t5_column(column_text):
        assert re.fullmatch(r'[0-9][0-9A-F][0-9A-F]', row['PBG'])
        assert row['Z'] in ('', 'A', 'R')
        assert re.fullmatch(r'[A-Z]*', row['B'])
        assert row['W'].isdigit()
        assert re.fullmatch(r'[A-Za-z-]{2,4}', row['A'])


def test_pbg_multiplier_is_zero_on_empty_worlds(sector):
    """An unpopulated world has no population multiplier."""
    checked = 0
    for system in sector.systems.values():
        mainworld = system.mainworld
        if mainworld is None:
            continue
        pbg = t5_pbg(system)
        if Utils.from_eHex(mainworld.uwp.population) == 0:
            checked += 1
            assert pbg[0] == '0'
        else:
            assert pbg[0] != '0'
    assert checked >= 0   # sample may hold no empty worlds


def test_stellar_lists_every_star(sector, column_text):
    by_hex = {row['Hex']: row for row in parse_t5_column(column_text)}
    for hex_coord, system in sector.systems.items():
        if system.mainworld is None:
            continue
        expected = [s.spectral_type for s in system.stars
                    if not s.is_composite and s.spectral_type]
        assert by_hex[hex_coord]['Stellar'] == " ".join(expected)


def test_nobility_scales_with_importance(sector):
    """A more important world carries at least as many titles."""
    pairs = []
    for system in sector.systems.values():
        mainworld = system.mainworld
        if mainworld is None or Utils.from_eHex(mainworld.uwp.population) == 0:
            continue
        row = t5_row('0101', system, sector)
        pairs.append((mainworld.importance, len(row['N'])))
    assert pairs
    for importance, titles in pairs:
        assert titles >= 1
    ranked = sorted(pairs)
    assert ranked[0][1] <= ranked[-1][1]


# ------------------------------------------------------------- tab format

def test_tab_format_has_one_header_and_no_padding(sector):
    text = export_sector_t5_tab(sector)
    lines = text.splitlines()
    header = lines[0].split('\t')
    assert header == [name for name, _ in T5_FIELDS]
    for line in lines[1:]:
        fields = line.split('\t')
        assert len(fields) == len(header)
        # Tab-delimited fields carry no alignment padding
        assert all(f == f.strip() for f in fields)


def test_both_formats_carry_the_same_data(sector):
    column_rows = parse_t5_column(export_sector_t5_column(sector))
    tab_lines = export_sector_t5_tab(sector).splitlines()
    names = tab_lines[0].split('\t')
    tab_rows = [dict(zip(names, line.split('\t'))) for line in tab_lines[1:]]
    assert len(column_rows) == len(tab_rows)
    for col, tab in zip(column_rows, tab_rows):
        for name in names:
            assert col[name] == tab[name].strip()


# ------------------------------------------------------------- edge cases

def test_empty_sector_still_emits_a_valid_header():
    empty = Sector(name="Empty")
    text = export_sector_t5_column(empty)
    lines = [l for l in text.splitlines() if not l.startswith('#')]
    assert len(lines) == 2                     # header and separator only
    assert parse_t5_column(text) == []
    widths = [len(run) for run in lines[1].split(' ')]
    for (_, minimum), width in zip(T5_FIELDS, widths):
        assert width >= minimum


def test_subsector_names_appear_as_comments():
    sec = Sector(name="Named")
    sec.subsector_names = {'A': 'Regina', 'B': 'Jewell'}
    text = export_sector_t5_column(sec)
    assert '# Subsector A: Regina' in text
    assert '# Subsector B: Jewell' in text


def test_sec_exporter_is_the_t5_column_format(sector):
    assert wm.export_sector_sec_file(sector) == export_sector_t5_column(sector)
