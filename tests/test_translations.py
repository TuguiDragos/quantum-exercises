"""Every exception-translation rule, driven by the real message it matches."""

from __future__ import annotations

import pytest

from quantum_exercises import errors


class TestEveryTableEntryIsReachable:
    """The tables are data, and a dict literal counts as covered the moment it loads.

    So a key that no longer matches anything, a typo in one, or an entry nothing
    ever reaches, all read as fully covered while helping nobody. These drive
    every entry through translate() instead.
    """

    @pytest.mark.parametrize("symbol", sorted(errors._REMOVED_FROM_QISKIT))
    def test_each_removed_symbol_is_translated_by_all_three_routes(self, symbol: str) -> None:
        expected = errors._REMOVED_FROM_QISKIT[symbol][0]

        imported = ImportError(f"cannot import name '{symbol}' from 'qiskit' (/x/__init__.py)")
        attribute = AttributeError(f"module 'qiskit' has no attribute '{symbol}'")
        undefined = NameError(f"name '{symbol}' is not defined")

        for exc in (imported, attribute, undefined):
            translation = errors.translate(exc)
            assert translation is not None, f"{symbol} via {type(exc).__name__}"
            assert translation.message == expected, f"{symbol} via {type(exc).__name__}"
            assert translation.hint

    @pytest.mark.parametrize("module", sorted(errors._REMOVED_MODULES))
    def test_each_removed_module_is_translated(self, module: str) -> None:
        exc = ModuleNotFoundError(f"No module named '{module}'")
        exc.name = module
        translation = errors.translate(exc)
        assert translation is not None
        assert translation.message == errors._REMOVED_MODULES[module][0]

    @pytest.mark.parametrize("package", sorted(errors._MISSING_PACKAGES))
    def test_each_missing_package_is_translated(self, package: str) -> None:
        exc = ModuleNotFoundError(f"No module named '{package}'")
        exc.name = package
        translation = errors.translate(exc)
        assert translation is not None
        assert translation.message == errors._MISSING_PACKAGES[package][0]

    @pytest.mark.parametrize("package", sorted(errors._MISSING_PACKAGES))
    def test_a_submodule_of_each_is_a_typo_rather_than_an_absence(self, package: str) -> None:
        exc = ModuleNotFoundError(f"No module named '{package}.nonsense'")
        exc.name = f"{package}.nonsense"
        translation = errors.translate(exc)
        assert translation is not None
        assert "no submodule" in translation.message

    @pytest.mark.parametrize("typo", sorted(errors._CIRCUIT_TYPOS))
    def test_each_circuit_typo_points_at_the_real_method(self, typo: str) -> None:
        exc = AttributeError(f"'QuantumCircuit' object has no attribute '{typo}'")
        translation = errors.translate(exc)
        assert translation is not None
        assert f"qc.{errors._CIRCUIT_TYPOS[typo]}(" in translation.hint

    def test_the_typo_table_only_maps_onto_methods_that_exist(self) -> None:
        """A typo pointing at another typo would be worse than no rule at all."""
        from qiskit import QuantumCircuit

        for typo, real in errors._CIRCUIT_TYPOS.items():
            assert not hasattr(QuantumCircuit, typo), f"{typo} is a real method now"
            assert hasattr(QuantumCircuit, real), f"{real} is not a QuantumCircuit method"


class TestTranslations:
    def test_unknown_symbol_from_qiskit(self) -> None:
        exc = ImportError("cannot import name 'widget' from 'qiskit' (/x/__init__.py)")
        assert "does not exist in `qiskit`" in errors.translate(exc).message

    def test_import_error_without_a_recognisable_shape(self) -> None:
        assert errors.translate(ImportError("something else entirely")) is None

    def test_unknown_qiskit_attribute(self) -> None:
        exc = AttributeError("module 'qiskit' has no attribute 'widget'")
        assert "`qiskit.widget` does not exist" in errors.translate(exc).message

    def test_known_removed_attribute(self) -> None:
        exc = AttributeError("module 'qiskit' has no attribute 'execute'")
        assert "removed in Qiskit 1.0" in errors.translate(exc).message

    def test_submodule_typo_is_not_a_missing_package(self) -> None:
        exc = ModuleNotFoundError("No module named 'matplotlib.pyploy'")
        exc.name = "matplotlib.pyploy"
        translation = errors.translate(exc)
        assert "is installed, but it has no submodule" in translation.message

    def test_missing_package_itself(self) -> None:
        exc = ModuleNotFoundError("No module named 'matplotlib'")
        exc.name = "matplotlib"
        assert "matplotlib is not installed" in errors.translate(exc).message

    def test_unknown_qiskit_submodule(self) -> None:
        exc = ModuleNotFoundError("No module named 'qiskit.ghost'")
        exc.name = "qiskit.ghost"
        assert "does not exist in Qiskit 2.x" in errors.translate(exc).message

    def test_unrelated_missing_module_is_left_alone(self) -> None:
        exc = ModuleNotFoundError("No module named 'pandas'")
        exc.name = "pandas"
        assert errors.translate(exc) is None

    def test_mid_circuit_measurement(self) -> None:
        exc = RuntimeError("StatevectorSampler cannot handle mid-circuit measurements")
        assert "measures partway through" in errors.translate(exc).message

    def test_circuit_attribute_typo(self) -> None:
        exc = AttributeError("'QuantumCircuit' object has no attribute 'cnot'")
        assert "qc.cx(...)" in errors.translate(exc).hint

    def test_circuit_attribute_unknown(self) -> None:
        exc = AttributeError("'QuantumCircuit' object has no attribute 'wibble'")
        assert "Gate methods are short and lowercase" in errors.translate(exc).hint

    def test_no_account(self) -> None:
        exc = type("AccountNotFoundError", (Exception,), {})()
        assert "No IBM Quantum account is saved" in errors.translate(exc).message

    def test_the_two_account_rules_match_the_classes_that_really_raise(self) -> None:
        """Both rules match on the class name, so a rename upstream disables them.

        Every case here builds its own stand-in, which proves the rule reads a name
        and nothing about that name still belonging to anything. These are the real
        classes, imported from the package that raises them.
        """
        from qiskit_ibm_runtime.accounts import AccountNotFoundError, InvalidAccountError

        assert "No IBM Quantum account is saved" in errors.translate(AccountNotFoundError()).message
        assert (
            "no longer accepted"
            in errors.translate(InvalidAccountError("Unable to retrieve instances.")).message
        )

    def test_a_saved_account_that_is_no_longer_accepted(self) -> None:
        """A revoked key is not a missing account, and the fix is a different one.

        This is the likelier of the two: a key expires on its own, while a missing
        file is something the reader can see.
        """
        exc = type("InvalidAccountError", (Exception,), {})("Unable to retrieve instances.")
        translation = errors.translate(exc)
        assert "no longer accepted" in translation.message
        assert "--save-account" in translation.hint
        assert "--online" in translation.hint

    def test_name_error_for_a_removed_symbol(self) -> None:
        exc = NameError("name 'execute' is not defined")
        assert "removed in Qiskit 1.0" in errors.translate(exc).message

    def test_name_error_generic(self) -> None:
        exc = NameError("name 'foo' is not defined")
        assert "used before it is defined" in errors.translate(exc).message

    def test_name_error_without_a_name(self) -> None:
        assert errors.translate(NameError("something odd")) is None

    def test_index_out_of_range_with_no_wires(self) -> None:
        exc = ValueError("Index 3 out of range for size 0.")
        assert "no wires of that kind" in errors.translate(exc).message

    def test_duplicate_bits(self) -> None:
        exc = ValueError("duplicate bit arguments")
        assert "same qubit more than once" in errors.translate(exc).message

    def test_primitive_pub(self) -> None:
        exc = ValueError("invalid Estimator pub-like")
        assert "instead of a list" in errors.translate(exc).message

    def test_v1_result_api(self) -> None:
        exc = AttributeError("'PrimitiveResult' object has no attribute 'get_counts'")
        assert "old V1 API" in errors.translate(exc).message

    def test_databin_field(self) -> None:
        exc = AttributeError("'DataBin' object has no attribute 'c'")
        assert "no classical register called `c`" in errors.translate(exc).message

    def test_indentation_error(self) -> None:
        exc = IndentationError("bad indent")
        exc.lineno = 4
        assert "indentation is off at line 4" in errors.translate(exc).message

    def test_syntax_error_without_a_line(self) -> None:
        exc = SyntaxError("bad syntax")
        exc.lineno = None
        assert "somewhere in the file" in errors.translate(exc).message

    def test_nothing_matches(self) -> None:
        assert errors.translate(ZeroDivisionError("division by zero")) is None

    def test_an_attribute_error_about_something_else_is_left_alone(self) -> None:
        """Four rules inspect an AttributeError. None of them may claim this one.

        Every AttributeError reaches the QuantumCircuit rule last, so a rule that
        matched too loosely would answer here with advice about gate methods.
        """
        exc = AttributeError("'list' object has no attribute 'push'")
        assert errors.translate(exc) is None
