from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Union, Optional, Callable
import networkx as nx
import numpy as np
from .core import Node, ONE_INSTANCE

@dataclass
class CopyLine:
    """
    Represents a T-shaped path in the grid for each vertex in the original graph.
    
    Attributes:
        vertex: The vertex ID from the original graph
        vslot: Vertical slot position (column position)
        hslot: Horizontal slot position (row position)
        vstart: Starting point of the vertical segment
        vstop: Ending point of the vertical segment
        hstop: Ending point of the horizontal segment (there is no hstart)
    """
    vertex: int
    vslot: int
    hslot: int
    vstart: int
    vstop: int
    hstop: int
    
    def __str__(self):
        return f"CopyLine {self.vertex}: vslot → [{self.vstart}:{self.vstop},{self.vslot}], hslot → [{self.hslot},{self.vslot}:{self.hstop}]"

@dataclass
class Block:
    """
    Represents a block in the crossing lattice.
    
    Attributes:
        top: Top connection (-1 means no line)
        bottom: Bottom connection (-1 means no line)
        left: Left connection (-1 means no line)
        right: Right connection (-1 means no line)
        connected: -1 for not exist, 0 for not connected, 1 for connected
    """
    top: int = -1
    bottom: int = -1
    left: int = -1
    right: int = -1
    connected: int = -1
    
    def __str__(self):
        rows = self.get_row_strings()
        return "\n".join(rows)
    
    def get_row_strings(self):
        """Return a 3-row string representation of the block."""
        rows = []
        rows.append(f" ⋅ {self._symbol(self.top)} ⋅")
        
        conn_symbol = '⋅' if self.connected == -1 else ('●' if self.connected == 1 else '○')
        rows.append(f" {self._symbol(self.left)} {conn_symbol} {self._symbol(self.right)}")
        
        rows.append(f" ⋅ {self._symbol(self.bottom)} ⋅")
        return rows
    
    def _symbol(self, x):
        """Convert a number to a symbol."""
        if x == -1:
            return '⋅'
        if x < 10:
            return str(x)
        return chr(ord('a') + (x - 10))


class CrossingLattice:
    """
    Represents a crossing lattice of lines with potential crossing points.
    
    Attributes:
        width: Width of the lattice
        height: Height of the lattice
        lines: List of CopyLine objects
        graph: The original graph
    """
    def __init__(self, width, height, lines, graph):
        self.width = width
        self.height = height
        self.lines = lines
        self.graph = graph
    
    def __getitem__(self, indices):
        """Access a block in the lattice."""
        if isinstance(indices, tuple) and len(indices) == 2:
            i, j = indices
            
            if not (1 <= i <= self.height and 1 <= j <= self.width):
                raise IndexError(f"Index {(i, j)} out of bounds.")
            
            # Determine connections at this position
            left = right = top = bottom = -1
            
            for line in self.lines:
                # Check vertical slot
                if line.vslot == j:
                    if line.vstart == line.vstop == i:
                        # A row (no vertical connection)
                        pass
                    elif line.vstart == i:
                        # Starting point
                        bottom = line.vertex
                    elif line.vstop == i:
                        # Stopping point
                        top = line.vertex
                    elif line.vstart < i < line.vstop:
                        # Middle of a line
                        top = bottom = line.vertex
                
                # Check horizontal slot
                if line.hslot == i:
                    if line.vslot == line.hstop == j:
                        # A column (no horizontal connection)
                        pass
                    elif line.vslot == j:
                        # Starting point
                        right = line.vertex
                    elif line.hstop == j:
                        # Stopping point
                        left = line.vertex
                    elif line.vslot < j < line.hstop:
                        # Middle of a line
                        left = right = line.vertex
            
            # Determine if there's a connection
            h = left if left != -1 else right
            v = top if top != -1 else bottom
            
            connected = -1
            if v != -1 and h != -1:
                connected = 1 if self.graph.has_edge(h, v) else 0
            
            return Block(top, bottom, left, right, connected)
        else:
            raise TypeError("Indices must be a tuple of (i, j)")
    
    def shape(self):
        """Return the shape of the lattice."""
        return (self.height, self.width)
    
    def __str__(self):
        """Return a string representation of the entire lattice."""
        result = []
        for i in range(1, self.height + 1):
            for k in range(3):  # 3 rows per block
                row = []
                for j in range(1, self.width + 1):
                    block = self[i, j]
                    row.append(block.get_row_strings()[k])
                result.append(" ".join(row))
        return "\n".join(result)

def create_copylines(g, vertex_order: List[int]) -> List[CopyLine]:
    """
    Create copy lines for a graph with a given vertex order.
    
    Args:
        g: The input graph
        vertex_order: The order of vertices
        
    Returns:
        A list of CopyLine objects
    """
    n = len(vertex_order)
    copylines = []
    
    # For each vertex in the order
    for i, v in enumerate(vertex_order):
        # Create T-shaped paths where:
        # - hslot is the position in the vertex_order (row)
        # - vslot is the position in the vertex_order (column)
        # - vstart/vstop define the vertical span
        # - hstop defines the horizontal span
        copyline = CopyLine(
            vertex=v,
            vslot=i+1,  # 1-based indexing
            hslot=i+1,  # 1-based indexing
            vstart=1,   # Start from the top
            vstop=n,    # Go to the bottom
            hstop=n     # Go to the right
        )
        copylines.append(copyline)
    
    return copylines

def center_location(tc: CopyLine, padding: int) -> Tuple[int, int]:
    """
    Calculate the center location of a copy line on the grid.
    
    Args:
        tc: The copy line
        padding: Grid padding amount
        
    Returns:
        (I, J) coordinates of the center
    """
    s = 4  # spacing factor
    I = s * (tc.hslot - 1) + padding + 2
    J = s * (tc.vslot - 1) + padding + 1
    return I, J

def node_from_type(node_type, i, j, w):
    """Create a node of the specified type with position (i,j) and weight w."""
    # For UnWeightedNode (with ONE weight)
    if node_type == "UnWeightedNode":
        return Node(i, j)
    # For WeightedNode (with numeric weight)
    else:
        return Node(i, j, w)

def copyline_locations(node_type: str, tc: CopyLine, padding: int) -> List[Node]:
    """
    Get all locations for a copy line.
    
    Args:
        node_type: "WeightedNode" or "UnWeightedNode"
        tc: The copy line
        padding: Grid padding amount
        
    Returns:
        List of Node objects representing the copy line
    """
    s = 4  # spacing factor
    nline = 0
    I, J = center_location(tc, padding=padding)
    locations = []
    
    # Grow up
    start = I + s * (tc.vstart - tc.hslot) + 1
    if tc.vstart < tc.hslot:
        nline += 1
    
    for i in range(I, start-1, -1):  # Even number of nodes up
        weight = 1 + (1 if i != start else 0)  # Half weight on last node
        locations.append(node_from_type(node_type, i, J, weight))
    
    # Grow down
    stop = I + s * (tc.vstop - tc.hslot) - 1
    if tc.vstop > tc.hslot:
        nline += 1
    
    for i in range(I, stop+1):  # Even number of nodes down
        if i == I:
            locations.append(node_from_type(node_type, i+1, J+1, 2))
        else:
            weight = 1 + (1 if i != stop else 0)
            locations.append(node_from_type(node_type, i, J, weight))
    
    # Grow right
    stop = J + s * (tc.hstop - tc.vslot) - 1
    if tc.hstop > tc.vslot:
        nline += 1
    
    for j in range(J+2, stop+1):  # Even number of nodes right
        weight = 1 + (1 if j != stop else 0)  # Half weight on last node
        locations.append(node_from_type(node_type, I, j, weight))
    
    # Center node
    locations.append(node_from_type(node_type, I, J+1, nline))
    
    return locations