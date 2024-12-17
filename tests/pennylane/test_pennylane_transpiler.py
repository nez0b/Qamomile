import pytest
import pennylane as qml
import numpy as np
import qamomile
from qamomile.pennylane.transpiler import PennylaneTranspiler
from qamomile.core.circuit import Parameter
from qamomile.core.circuit import QuantumCircuit, SingleQubitGate, TwoQubitGate, ParametricSingleQubitGate
from qamomile.core.operator import Hamiltonian, PauliOperator, Pauli


@pytest.fixture
def transpiler():
    """Fixture to initialize the PennylaneTranspiler."""
    return PennylaneTranspiler()

def test_transpile_hamiltonian(transpiler):
    """Test the transpilation of Qamomile Hamiltonian to Pennylane Hamiltonian."""
    # Define a Qamomile Hamiltonian
    hamiltonian = qamomile.core.operator.Hamiltonian()
    hamiltonian += qamomile.core.operator.X(0) * qamomile.core.operator.Z(1)

    # Transpile the Hamiltonian
    pennylane_hamiltonian = transpiler.transpile_hamiltonian(hamiltonian)

    # Assert the result is a Pennylane Hamiltonian
    assert isinstance(pennylane_hamiltonian, qml.Hamiltonian)

    # Validate number of qubits and terms
    assert len(pennylane_hamiltonian.operands) == 1 # Only one term
    assert np.all((pennylane_hamiltonian.coeffs , [1.0, ])) # Default coefficient is 1.0

    # Validate term content
    term_ops = pennylane_hamiltonian.terms()[1]
    # assert isinstance(term_ops, qml.operation)
    assert len(term_ops[0]) == 2  # Two operators in the term
    assert isinstance(term_ops[0][0], qml.PauliX)  # X on qubit 0
    assert isinstance(term_ops[0][1], qml.PauliZ)  # Z on qubit 1

def test_transpile_complex_hamiltonian(transpiler):
    """Test the transpilation of Qamomile Hamiltonian to Pennylane Hamiltonian."""
    # Define a Qamomile Hamiltonian
    hamiltonian = qamomile.core.operator.Hamiltonian()
    hamiltonian += qamomile.core.operator.X(0) * qamomile.core.operator.Z(1)
    hamiltonian += qamomile.core.operator.Y(0) * qamomile.core.operator.Y(1)

    # Transpile the Hamiltonian
    pennylane_hamiltonian = transpiler.transpile_hamiltonian(hamiltonian)

    # Assert the result is a Pennylane Hamiltonian
    assert isinstance(pennylane_hamiltonian, qml.Hamiltonian)

    # Validate number of qubits and terms
    assert len(pennylane_hamiltonian.operands) == 2 # Only one term
    assert np.all((pennylane_hamiltonian.coeffs , [1.0, 1.0])) # Default coefficient is 1.0

    # Validate term content
    term_ops = pennylane_hamiltonian.terms()[1]
    # assert isinstance(term_ops, qml.operation)
    assert len(term_ops[0]) == 2  # Two operators in the term
    assert len(term_ops[1]) == 2 
    assert isinstance(term_ops[0][0], qml.PauliX)  # X on qubit 0
    assert isinstance(term_ops[0][1], qml.PauliZ)  # Z on qubit 1
    assert isinstance(term_ops[1][0], qml.PauliY)  # Y on qubit 0
    assert isinstance(term_ops[1][1], qml.PauliY)  # Y on qubit 1

# def extract_gate_outputs(qnode, *args, **kwargs):
#     """
#     Extracts and prints the operations and parameters from a qnode.

#     Args:
#         qnode: A quantum node or function that represents a quantum circuit.
#         *args, **kwargs: Arguments to be passed to the qnode.

#     Returns:
#         list: A list of dictionaries, where each dictionary contains information about a gate.
#     """
#     # Execute the QNode to ensure the tape is constructed
#     qnode(*args, **kwargs)

#     # Access the internal tape
#     tape = qnode.qtape
    
#     gate_outputs = []
    
#     for op in tape.operations:
#         gate_outputs.append(op)
    
#     return gate_outputs

# def test_transpile_simple_circuit(transpiler: PennylaneTranspiler):
#     qc = QuantumCircuit(3)
#     qc.h(0)
#     qc.s(1)
#     qc.t(2)
#     qc.x(0)
#     qc.y(1)
#     qc.z(2)
#     qc.cx(0, 1)
#     qc.cx(1, 2)
#     qc.cx(2, 0)
#     qnode = transpiler.transpile_circuit(qc)
#     gate_info = extract_gate_outputs(qnode)

#     assert isinstance(qnode, qml.QNode)
#     assert len(qnode.device.wires) == 3
#     assert gate_info[0].name == "Hadamard"
#     assert gate_info[-1].name == 'CNOT'


# def test_transpile_para_circuit(transpiler: PennylaneTranspiler):
#     qc = QuantumCircuit(3)
#     theta = Parameter("theta")
#     beta = Parameter("beta")
#     gamma = Parameter("gamma")

#     qc.rx(theta, 0)
#     qc.ry(beta, 1)
#     qc.rz(gamma, 2)
#     qc.crx(gamma, 0 ,1)
#     qc.crz(theta, 1 ,2)
#     qc.cry(beta, 2 ,0)

#     qnode = transpiler.transpile_circuit(qc)
#     p= {"theta":0.1,"beta":0.2, "gamma": 0.3}
#     gate_info = extract_gate_outputs(qnode, **p)

#     assert isinstance(qnode, qml.QNode)
#     assert len(qnode.device.wires) == 3
#     assert gate_info[0].name == "RX"
#     assert gate_info[1].name == "RY"
#     assert gate_info[2].name == "RZ"
#     assert gate_info[3].name == "CRX"
#     assert gate_info[4].name == "CRZ"
#     assert gate_info[5].name == "CRY"