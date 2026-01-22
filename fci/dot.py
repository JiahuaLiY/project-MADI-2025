import graphviz
import networkx as nx

from fci.endpoint import Endpoint

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
