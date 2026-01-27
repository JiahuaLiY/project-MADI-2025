import graphviz
import networkx as nx

import pyagrum as gum

from fci.endpoint import Endpoint
from fci.fci import hasEndpoint

def toDot(pag: nx.Graph) -> graphviz.Digraph:
    """"""
    endpointToDotformat = {
        Endpoint.TAIL: "none",
        Endpoint.ARROWHEAD: "normal",
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

def showCausalDifferences(pag: nx.Graph, pdag: gum.PDAG, names: str) -> graphviz.Digraph:
    nameToID = { name: ID for ID, name in enumerate(names) }
    edges = set()
    arcs = set()

    dot = graphviz.Digraph(format="svg")
    dot.attr(rankdir="TB")
    dot.attr("node", style="filled", fillcolor="white", fontcolor="black")
    
    # Draw causal graph.
    for node in pag.nodes:
        dot.node(node)
    
    for u, v in pag.edges:
        if hasEndpoint(pag, u, v, Endpoint.ARROWHEAD, Endpoint.ARROWHEAD):
            continue
        
        uID, vID = nameToID[u], nameToID[v]
        if hasEndpoint(pag, u, v, Endpoint.TAIL, Endpoint.ARROWHEAD):
            arcs.add((uID, vID))
            if pdag.existsArc(uID, vID):
                color = "green"
                style = "solid"
            else:
                color = "black"
                style = "dashed"
            dot.edge( u, v,
                     arrowtail="none",
                     arrowhead="normal",
                     dir="both",
                     penwidth="1.5",
                     color=color,
                     style=style)
        elif hasEndpoint(pag, v, u, Endpoint.TAIL, Endpoint.ARROWHEAD):
            arcs.add((vID, uID))
            if pdag.existsArc(vID, uID):
                color = "green"
                style = "solid"
            else:
                color = "black"
                style = "dashed"
            dot.edge(v, u,
                     arrowtail="none",
                     arrowhead="normal",
                     dir="both",
                     penwidth="1.5",
                     color=color,
                     style=style)
        else:
            edges.add((uID, vID))
            edges.add((vID, uID))
            if pdag.existsEdge(uID, vID):
                color = "green"
                style = "solid"
            else:
                color = "black"
                style = "dashed"
            dot.edge(u, v,
                     arrowtail="none",
                     arrowhead="none",
                     dir="both",
                     penwidth="1.5",
                     color=color,
                     style=style)
    
    # Draw causal differences.
    for u, v in pdag.edges():
        if (u, v) not in edges:
            dot.edge(names[u], names[v],
                     arrowtail="none",
                     arrowhead="none",
                     dir="both",
                     penwidth="1.5",
                     color="red",
                     style="dashed")
    for u, v in pdag.arcs():
        if (u, v) not in arcs:
            dot.edge(names[u], names[v],
                     arrowtail="none",
                     arrowhead="normal",
                     dir="both",
                     penwidth="1.5",
                     color="red",
                     style="dashed")
    return dot
