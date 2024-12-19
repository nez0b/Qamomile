"""
Qamomile to Pennylane Transpiler Module

This module provides functionality to convert Qamomile Hamiltonians to their Pennylane equivalents. It includes a `PennylaneTranspiler` class that implements the `QuantumSDKTranspiler` interface for Pennylane compatibility.

Key Features:
- Convert Qamomile Hamiltonians to Pennylane Hamiltonians.

Usage Example:
    ```python
    from qamomile.Pennylane.transpiler import PennylaneTranspiler

    transpiler = PennylaneTranspiler()
    pennylane_operator = transpiler.transpile_hamiltonian(qamomile_hamiltonian)
    ```
Requirements:
- Qamomile
- Pennylane
"""

import collections
from typing import Dict, Any
import numpy as np
import pennylane as qml
from pennylane import numpy as p_np

import qamomile.core.operator
import qamomile.core.circuit
import qamomile.core.bitssample as qm_bs
from qamomile.core.transpiler import QuantumSDKTranspiler


class PennylaneTranspiler(QuantumSDKTranspiler[tuple[collections.Counter[int], int]]):
    """
    A transpiler class for converting Qamomile Hamiltonians to Pennylane-compatible Hamiltonians.
    """

    def transpile_hamiltonian(
        self, operator: qamomile.core.operator.Hamiltonian
    ) -> qml.Hamiltonian:
        """
        Converts a Qamomile Hamiltonian to a Pennylane Hamiltonian.

        Args:
            operator (qamomile.core.operator.Hamiltonian): The Qamomile Hamiltonian to be converted.

        Returns:
            qml.Hamiltonian: The corresponding Pennylane Hamiltonian.
        """
        n = operator.num_qubits
        coeffs = []
        ops = []

        # Iteration over terms in Qamomile Hamiltonian
        for term, coeff in operator.terms.items():
            op_list = [qml.Identity(i) for i in range(n)]
            for pauli in term:

                if pauli.pauli == qamomile.core.operator.Pauli.X:
                    op_list[pauli.index] = qml.PauliX(pauli.index)
                elif pauli.pauli == qamomile.core.operator.Pauli.Y:
                    op_list[pauli.index] = qml.PauliY(pauli.index)
                elif pauli.pauli == qamomile.core.operator.Pauli.Z:
                    op_list[pauli.index] = qml.PauliZ(pauli.index)
                else:
                    raise NotImplementedError(
                        f"Unsupported Pauli operator: {pauli.pauli}. "
                        "Only X, Y, Z are supported."
                    )
            ops.append(qml.prod(*op_list))
            coeffs.append(coeff)

        return qml.Hamiltonian(np.array(coeffs), ops)

    def transpile_circuit(
        self, qamomile_circuit: qamomile.core.circuit.QuantumCircuit
    ) -> Any:
        """
        Convert a Qamomile quantum circuit to a PennyLane-compatible function (QNode construction by user).

        Args:
            qamomile_circuit (qamomile.core.circuit.QuantumCircuit): The Qamomile quantum circuit to convert.

        Returns:
            Callable: A PennyLane-compatible function which applies the circuit.
        """

        # Retrieve parameters in a defined order
        parameters = qamomile_circuit.get_parameters()

        # Create a mapping from parameter names to parameter objects
        param_mapping = self._create_param_mapping(qamomile_circuit)

        # Extract parameter names in order to establish a positional mapping
        ordered_param_names = [p.name for p in parameters]
        print("ordered_param_names: ", ordered_param_names)

        def circuit_fn(*args, **kwargs):
            # If we have exactly one positional argument
            if len(args) == 1:
                # Try to interpret it as a parameter vector if it has a shape attribute
                param_values = args[0]
                
                # Check if param_values has a shape (works for np.ndarray, p_np.tensor, and AutogradArrayBox)
                if hasattr(param_values, 'shape'):
                    # Check length
                    if param_values.size != len(ordered_param_names):
                        raise ValueError(
                            f"The number of parameters provided ({param_values.size}) does not match "
                            f"the expected number of parameters ({len(ordered_param_names)})."
                        )
                    # Map the parameters by name
                    positional_params = {
                        pname: val for pname, val in zip(ordered_param_names, param_values)
                    }
                else:
                    # If it's not array-like, fall back to empty (no positional params)
                    positional_params = {}
            else:
                # No positional argument provided
                positional_params = {}

            # Merge with keyword arguments
            final_params = {**positional_params, **kwargs}

            # Check that all required parameters are assigned
            for pname in ordered_param_names:
                if pname not in final_params:
                    raise ValueError(f"No value provided for parameter '{pname}'.")

            self._apply_gates(
                qamomile_circuit,
                param_mapping=param_mapping,
                params=final_params,
            )
        return circuit_fn


    def _create_param_mapping(
        self, qamomile_circuit: qamomile.core.circuit.QuantumCircuit
    ) -> Dict[str, qamomile.core.circuit.Parameter]:
        """
        Create a parameter mapping dictionary from parameter names to Qamomile parameters.

        Args:
            qamomile_circuit (qamomile.core.circuit.QuantumCircuit): The circuit containing parameters.

        Returns:
            Dict[str, qamomile.core.circuit.Parameter]: A mapping from parameter names to parameters.
        """
        parameters = qamomile_circuit.get_parameters()
        param_mapping = {}

        for param in parameters:
            param_name = getattr(param, "name", None)
            if param_name is None:
                raise ValueError(f"Parameter {param} has no 'name' attribute.")
            param_mapping[param_name] = param

        return param_mapping

    def _apply_gates(
        self,
        qamomile_circuit: qamomile.core.circuit.QuantumCircuit,
        param_mapping: Dict[str, qamomile.core.circuit.Parameter],
        params: Dict[str, Any],
    ):
        """
        Apply the gates from the Qamomile circuit onto the PennyLane QNode.

        Args:
            qamomile_circuit: The Qamomile quantum circuit.
            param_mapping: Mapping from parameter names to Qamomile parameters.
            params: The current set of parameters (with values) passed to the QNode.
        """
        for gate in qamomile_circuit.gates:

            if isinstance(gate, qamomile.core.circuit.SingleQubitGate):
                self._apply_single_qubit_gate(gate)

            elif isinstance(gate, qamomile.core.circuit.TwoQubitGate):
                self._apply_two_qubit_gate(gate)

            elif isinstance(gate, qamomile.core.circuit.ParametricSingleQubitGate):
                self._apply_parametric_single_qubit_gate(gate, params)

            elif isinstance(gate, qamomile.core.circuit.ParametricTwoQubitGate):
                self._apply_parametric_two_qubit_gate(gate, params)

            elif isinstance(gate, qamomile.core.circuit.Operator):
                self._apply_gates(gate.circuit, param_mapping, params)

            elif isinstance(gate, qamomile.core.circuit.MeasurementGate):
                pass


    def _apply_single_qubit_gate(self, gate: qamomile.core.circuit.SingleQubitGate):
        """
        Apply a single-qubit gate to the QNode.

        Args:
            gate: A Qamomile single-qubit gate.
        """
        gate_map = {
            qamomile.core.circuit.SingleQubitGateType.H: qml.Hadamard,
            qamomile.core.circuit.SingleQubitGateType.X: qml.PauliX,
            qamomile.core.circuit.SingleQubitGateType.Y: qml.PauliY,
            qamomile.core.circuit.SingleQubitGateType.Z: qml.PauliZ,
            qamomile.core.circuit.SingleQubitGateType.S: qml.S,
            qamomile.core.circuit.SingleQubitGateType.T: qml.T,
        }

        if gate.gate not in gate_map:
            raise NotImplementedError(f"Unsupported single-qubit gate: {gate.gate}")

        gate_map[gate.gate](wires=gate.qubit)

    def _apply_two_qubit_gate(self, gate: qamomile.core.circuit.TwoQubitGate):
        """
        Apply a two-qubit gate to the QNode.

        Args:
            gate: A Qamomile two-qubit gate.
        """
        gate_map = {
            qamomile.core.circuit.TwoQubitGateType.CNOT: qml.CNOT,
            qamomile.core.circuit.TwoQubitGateType.CZ: qml.CZ,
        }
        if gate.gate not in gate_map:
            raise NotImplementedError(f"Unsupported two-qubit gate: {gate.gate}")

        gate_map[gate.gate](wires=[gate.control, gate.target])

    def _extract_angle(self, gate, params):
        """
        Extract the angle parameter for parameterized gates from the params dictionary.

        Args:
            gate: A parameterized gate (single or two-qubit).
            params: A dictionary mapping parameter names to their numeric values.

        Returns:
            float: The numeric angle/value for the gate.
        """

        param_name = getattr(gate.parameter, "name", None)

        if param_name is not None:
            if param_name in params:
                return params[param_name]
            else:
                raise ValueError(
                    f"Parameter '{param_name}' not found in the provided params."
                )

        full_param_str = str(gate.parameter).strip()
        parts = [p.strip() for p in full_param_str.split("*")]

        if len(parts) == 2:
            coeff_str, base_param = parts
            try:
                coeff = float(coeff_str)
            except ValueError:
                raise ValueError(
                    f"Cannot parse coefficient from parameter expression: '{full_param_str}'"
                )

            if base_param in params:
                return coeff * params[base_param]
            else:
                raise ValueError(
                    f"Base parameter '{base_param}' not found in provided params."
                )
        else:
            raise ValueError(
                f"Unexpected parameter format: '{full_param_str}'. Expected 'coeff*param'."
            )

    def _apply_parametric_single_qubit_gate(
        self,
        gate: qamomile.core.circuit.ParametricSingleQubitGate,
        params: Dict[str, Any],
    ):
        """
        Apply a parameterized single-qubit gate.

        Args:
            gate: A Qamomile parameterized single-qubit gate.
            params: Parameter values dictionary.
        """
        angle = self._extract_angle(gate, params)
        gate_map = {
            qamomile.core.circuit.ParametricSingleQubitGateType.RX: qml.RX,
            qamomile.core.circuit.ParametricSingleQubitGateType.RY: qml.RY,
            qamomile.core.circuit.ParametricSingleQubitGateType.RZ: qml.RZ,
        }
        if gate.gate not in gate_map:
            raise NotImplementedError(f"Unsupported parametric single-qubit gate: {gate.gate}")

        gate_map[gate.gate](angle, wires=gate.qubit)

    def _apply_parametric_two_qubit_gate(
        self,
        gate: qamomile.core.circuit.ParametricTwoQubitGate,
        params: Dict[str, Any],
    ):
        """
        Apply a parameterized two-qubit gate.

        Args:
            gate: A Qamomile parameterized two-qubit gate.
            params: Parameter values dictionary.
        """
        angle = self._extract_angle(gate, params)

        gate_map = {
            qamomile.core.circuit.ParametricTwoQubitGateType.CRX: qml.CRX,
            qamomile.core.circuit.ParametricTwoQubitGateType.CRY: qml.CRY,
            qamomile.core.circuit.ParametricTwoQubitGateType.CRZ: qml.CRZ,
            qamomile.core.circuit.ParametricTwoQubitGateType.RXX: qml.IsingXX,
            qamomile.core.circuit.ParametricTwoQubitGateType.RYY: qml.IsingYY,
            qamomile.core.circuit.ParametricTwoQubitGateType.RZZ: qml.IsingZZ,
        }
        if gate.gate not in gate_map:
            raise NotImplementedError(f"Unsupported parametric two-qubit gate: {gate.gate}")

        gate_map[gate.gate](angle, wires=[gate.control, gate.target])

    def convert_result(self, result: Any) -> Any:
        """
        Convert the result from PennyLane execution to a Qamomile-compatible result.

        Currently not implemented.
        """
        raise NotImplementedError("convert_result is not implemented yet.")
