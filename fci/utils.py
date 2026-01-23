import graphviz
import networkx as nx

import pyagrum as gum

from fci.endpoint import Endpoint
from fci.fci import hasEndpoint

def toDot(pag: nx.Graph) -> graphviz.Digraph:
    """"""
    endpointToDotformat = {
        Endpoint.TAIL: "none",
        Endpoint.ARROW: "normal",
        Endpoint.CIRCLE: "odot"
    }

    dot = graphviz.Digraph(format="svg")
    dot.attr(rankdir="TB")
    dot.attr("node", style="filled", fillcolor="gray25", fontcolor="white")

    for node in pag.nodes:
        dot.node(node)
    
    for u, v, data in pag.edges(data=True):
        uEndpoint, vEndpoint = data[u], data[v]

        dot.edge(u, v,
                 arrowtail=endpointToDotformat[uEndpoint],
                 arrowhead=endpointToDotformat[vEndpoint],
                 dir="both",
                 penwidth="1.5")
    return dot

def toPDAG(pag: nx.Graph, names: str) -> gum.PDAG:
    nameToID = { name: ID for ID, name in enumerate(names) }

    pdag = gum.PDAG()
    pdag.addNodes(len(names))

    try:
        for u, v in pag.edges:
            if hasEndpoint(pag, u, v, Endpoint.ARROW, Endpoint.ARROW):
                continue

            if hasEndpoint(pag, u, v, Endpoint.TAIL, Endpoint.ARROW):
                pdag.addArc(nameToID[u], nameToID[v])
            elif hasEndpoint(pag, v, u, Endpoint.TAIL, Endpoint.ARROW):
                pdag.addArc(nameToID[v], nameToID[u])
            else:
                pdag.addEdge(nameToID[u], nameToID[v])
    except gum.InvalidDirectedCycle:
        return None
    return pdag
