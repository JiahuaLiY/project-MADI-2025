from itertools import combinations

import graphviz
import networkx as nx

from fci.endpoint import Endpoint

def getTriples(graph: nx.Graph):
    for z in graph.nodes():
        for x, y in combinations(graph.neighbors(z), 2):
            yield x, z, y

_endpointToDotFormat = {
    Endpoint.TAIL: "none",
    Endpoint.ARROW: "normal",
    Endpoint.CIRCLE: "odot"
}

def toDot(pag: nx.Graph) -> graphviz.Digraph:
    dot = graphviz.Digraph(format="svg")
    dot.attr(rankdir="BT")
    dot.attr("node", style="filled", fillcolor='gray25', fontcolor="white")

    for u, v, data in pag.edges(data=True):
        uEndpoint, vEndpoint = data[u], data[v]

        dot.edge(str(u), str(v),
                 arrowtail=_endpointToDotFormat[uEndpoint],
                 arrowhead=_endpointToDotFormat[vEndpoint],
                 dir="both",
                 penwidth="1.5")
    return dot
