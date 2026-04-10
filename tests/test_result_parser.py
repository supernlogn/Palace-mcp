"""Tests for palace_mcp.palace.result_parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from palace_mcp.palace.result_parser import (
    SimulationResults,
    _collect_complex_columns,
    _compute_directivity,
    _compute_impedances,
    _to_float,
    parse_palace_error,
    parse_results,
)


class TestToFloat:
    def test_valid_float(self):
        assert _to_float("3.14") == 3.14

    def test_integer_string(self):
        assert _to_float("42") == 42.0

    def test_scientific_notation(self):
        assert _to_float("1.5e-3") == 1.5e-3

    def test_whitespace(self):
        assert _to_float("  2.5  ") == 2.5

    def test_invalid_returns_zero(self):
        assert _to_float("abc") == 0.0

    def test_empty_string(self):
        assert _to_float("") == 0.0

    def test_none_returns_zero(self):
        assert _to_float(None) == 0.0


class TestSimulationResultsToDict:
    def test_empty_results(self):
        r = SimulationResults()
        d = r.to_dict()
        assert d["problem_type"] == ""
        # Empty lists should not appear in the dict
        assert "eigenfrequencies" not in d
        assert "s_parameters" not in d

    def test_with_eigenfrequencies(self):
        r = SimulationResults(
            problem_type="Eigenmode",
            eigenfrequencies=[{"frequency_hz": 5e9, "quality_factor": 1000}],
        )
        d = r.to_dict()
        assert d["problem_type"] == "Eigenmode"
        assert len(d["eigenfrequencies"]) == 1
        assert d["eigenfrequencies"][0]["frequency_hz"] == 5e9

    def test_with_raw_files(self):
        r = SimulationResults(raw_files=["domain-E.csv", "port-V.csv"])
        d = r.to_dict()
        assert d["raw_files"] == ["domain-E.csv", "port-V.csv"]

    def test_capacitance_matrix_included_when_set(self):
        r = SimulationResults(capacitance_matrix=[[1.0, 0.1], [0.1, 1.0]])
        d = r.to_dict()
        assert d["capacitance_matrix"] == [[1.0, 0.1], [0.1, 1.0]]


class TestParseResults:
    def test_empty_directory(self, tmp_path: Path):
        results = parse_results(tmp_path)
        assert results.eigenfrequencies == []
        assert results.s_parameters == []
        assert results.raw_files == []

    def test_enumerates_raw_files(self, tmp_path: Path):
        (tmp_path / "domain-E.csv").write_text("")
        (tmp_path / "port-V.csv").write_text("")
        results = parse_results(tmp_path)
        assert "domain-E.csv" in results.raw_files
        assert "port-V.csv" in results.raw_files

    def test_parses_domain_energy_csv(self, tmp_path: Path):
        csv_content = "freq,energy\n5e9,0.001\n6e9,0.002\n"
        (tmp_path / "domain-E.csv").write_text(csv_content)
        results = parse_results(tmp_path)
        assert len(results.domain_energies) == 2

    def test_parses_port_voltage_csv(self, tmp_path: Path):
        csv_content = "freq,V1_re,V1_im\n1e9,0.5,0.1\n2e9,0.4,0.2\n"
        (tmp_path / "port-V.csv").write_text(csv_content)
        results = parse_results(tmp_path)
        assert len(results.port_voltages) == 2

    def test_eigenmode_extracts_frequencies(self, tmp_path: Path):
        csv_content = "f,Q,EPR\n5e9,1000,0.5\n6e9,2000,0.3\n"
        (tmp_path / "domain-E.csv").write_text(csv_content)
        results = parse_results(tmp_path, problem_type="Eigenmode")
        assert len(results.eigenfrequencies) == 2
        assert results.eigenfrequencies[0]["frequency_hz"] == 5e9

    def test_driven_computes_s_parameters(self, tmp_path: Path):
        v_csv = "freq,Re_V1,Im_V1\n1e9,0.5,0.1\n"
        i_csv = "freq,Re_I1,Im_I1\n1e9,0.01,0.002\n"
        (tmp_path / "port-V.csv").write_text(v_csv)
        (tmp_path / "port-I.csv").write_text(i_csv)
        results = parse_results(tmp_path, problem_type="Driven")
        assert len(results.s_parameters) == 1

    def test_comment_lines_skipped_in_csv(self, tmp_path: Path):
        csv_content = "# This is a comment\n# Another comment\nfreq,energy\n5e9,0.001\n"
        (tmp_path / "domain-E.csv").write_text(csv_content)
        results = parse_results(tmp_path)
        assert len(results.domain_energies) == 1

    def test_electrostatic_extracts_capacitance_matrix(self, tmp_path: Path):
        csv_content = "index,C11,C12\n1,1.0,0.1\n2,0.1,1.0\n"
        (tmp_path / "surface-F.csv").write_text(csv_content)
        results = parse_results(tmp_path, problem_type="Electrostatic")
        assert results.capacitance_matrix is not None
        assert len(results.capacitance_matrix) == 2


class TestParsePalaceError:
    def test_solver_divergence(self):
        d = parse_palace_error("KSP solver not converged after 500 iterations")
        assert d["category"] == "solver_divergence"
        assert d["suggestion"]

    def test_mesh_error(self):
        d = parse_palace_error("mesh file not found: model.msh")
        assert d["category"] == "mesh_error"

    def test_config_error(self):
        d = parse_palace_error("Error parsing JSON config file")
        assert d["category"] == "config_error"

    def test_boundary_error(self):
        d = parse_palace_error("boundary attribute 5 not recognized")
        assert d["category"] == "boundary_error"

    def test_memory_error(self):
        d = parse_palace_error("failed to allocate 16GB of memory")
        assert d["category"] == "memory_error"

    def test_unknown_error(self):
        d = parse_palace_error("some random failure")
        assert d["category"] == "unknown"

    def test_empty_stderr(self):
        d = parse_palace_error("")
        assert d["category"] == "unknown"
        assert "No error output" in d["message"]

    def test_truncates_long_message(self):
        long_msg = "x" * 1000
        d = parse_palace_error(long_msg)
        assert len(d["message"]) <= 500


class TestComputeImpedances:
    def test_basic_impedance(self):
        voltages = [{"freq": "1e9", "Re_V1": "50.0", "Im_V1": "0.0"}]
        currents = [{"freq": "1e9", "Re_I1": "1.0", "Im_I1": "0.0"}]
        result = _compute_impedances(voltages, currents)
        assert len(result) == 1
        assert result[0]["Z_V1_mag"] == pytest.approx(50.0, rel=1e-6)

    def test_complex_impedance(self):
        voltages = [{"freq": "1e9", "Re_V1": "50.0", "Im_V1": "25.0"}]
        currents = [{"freq": "1e9", "Re_I1": "1.0", "Im_I1": "0.0"}]
        result = _compute_impedances(voltages, currents)
        assert result[0]["Z_V1_re"] == pytest.approx(50.0, rel=1e-6)
        assert result[0]["Z_V1_im"] == pytest.approx(25.0, rel=1e-6)

    def test_multi_port(self):
        voltages = [{"freq": "1e9", "Re_V1": "50", "Im_V1": "0", "Re_V2": "100", "Im_V2": "0"}]
        currents = [{"freq": "1e9", "Re_I1": "1", "Im_I1": "0", "Re_I2": "2", "Im_I2": "0"}]
        result = _compute_impedances(voltages, currents)
        assert result[0]["Z_V1_mag"] == pytest.approx(50.0)
        assert result[0]["Z_V2_mag"] == pytest.approx(50.0)

    def test_column_suffix_format(self):
        """Test V1_re / V1_im naming convention."""
        voltages = [{"freq": "1e9", "V1_re": "50.0", "V1_im": "0.0"}]
        currents = [{"freq": "1e9", "I1_re": "1.0", "I1_im": "0.0"}]
        result = _compute_impedances(voltages, currents)
        assert len(result) == 1
        assert result[0]["Z_V1_mag"] == pytest.approx(50.0, rel=1e-6)

    def test_frequency_extracted(self):
        voltages = [{"freq": "2e9", "Re_V1": "75", "Im_V1": "0"}]
        currents = [{"freq": "2e9", "Re_I1": "1.5", "Im_I1": "0"}]
        result = _compute_impedances(voltages, currents)
        assert result[0]["frequency_hz"] == pytest.approx(2e9)


class TestCollectComplexColumns:
    def test_re_im_prefix(self):
        row = {"freq": "1e9", "Re_V1": "3.0", "Im_V1": "4.0"}
        out: dict[str, complex] = {}
        _collect_complex_columns(row, out)
        assert "V1" in out
        assert out["V1"] == complex(3.0, 4.0)

    def test_re_im_suffix(self):
        row = {"V1_re": "3.0", "V1_im": "4.0"}
        out: dict[str, complex] = {}
        _collect_complex_columns(row, out)
        assert "V1" in out
        assert out["V1"] == complex(3.0, 4.0)

    def test_plain_real_column(self):
        row = {"V1": "5.0"}
        out: dict[str, complex] = {}
        _collect_complex_columns(row, out)
        assert "V1" in out
        assert out["V1"] == complex(5.0, 0.0)


class TestComputeDirectivity:
    def test_basic_directivity(self):
        far_field = [
            {"theta": "0", "phi": "0", "gain": "10.0"},
            {"theta": "90", "phi": "0", "gain": "1.0"},
            {"theta": "180", "phi": "0", "gain": "0.5"},
            {"theta": "90", "phi": "90", "gain": "1.0"},
        ]
        result = _compute_directivity(far_field)
        assert "max_directivity_dbi" in result
        assert result["max_gain_direction"]["theta"] == 0.0
        assert "boresight_directivity_dbi" in result

    def test_empty_returns_empty(self):
        assert _compute_directivity([]) == {}

    def test_no_gain_column(self):
        far_field = [{"theta": "0", "phi": "0", "unknown": "1"}]
        result = _compute_directivity(far_field)
        assert "error" in result

    def test_directivity_is_positive_for_directive_pattern(self):
        # Strong boresight, weak elsewhere
        far_field = [{"theta": "0", "phi": "0", "gain": "100"}]
        far_field += [{"theta": str(t), "phi": "0", "gain": "1"} for t in range(10, 181, 10)]
        result = _compute_directivity(far_field)
        assert result["max_directivity_dbi"] > 0


class TestImpedanceAndFarFieldParsing:
    def test_impedances_in_driven_results(self, tmp_path: Path):
        v_csv = "freq,Re_V1,Im_V1\n1e9,50.0,0.0\n"
        i_csv = "freq,Re_I1,Im_I1\n1e9,1.0,0.0\n"
        (tmp_path / "port-V.csv").write_text(v_csv)
        (tmp_path / "port-I.csv").write_text(i_csv)
        results = parse_results(tmp_path, problem_type="Driven")
        assert len(results.impedances) == 1
        assert "Z_V1_mag" in results.impedances[0]

    def test_farfield_csv_parsed(self, tmp_path: Path):
        ff_csv = "theta,phi,gain\n0,0,10\n90,0,1\n"
        (tmp_path / "farfield.csv").write_text(ff_csv)
        results = parse_results(tmp_path, problem_type="Driven")
        assert len(results.far_field) == 2

    def test_directivity_computed_from_farfield(self, tmp_path: Path):
        ff_csv = "theta,phi,gain\n0,0,10\n90,0,1\n180,0,0.5\n"
        (tmp_path / "farfield.csv").write_text(ff_csv)
        results = parse_results(tmp_path, problem_type="Driven")
        assert results.directivity
        assert "max_directivity_dbi" in results.directivity

    def test_to_dict_includes_new_fields(self):
        r = SimulationResults(
            impedances=[{"Z_V1_mag": 50.0}],
            far_field=[{"theta": 0, "phi": 0, "gain": 10}],
            directivity={"max_directivity_dbi": 5.0},
        )
        d = r.to_dict()
        assert "impedances" in d
        assert "far_field" in d
        assert "directivity" in d
