import pyagrum as gum
import networkx as nx

from itertools import combinations

def initSkeleton(learner: gum.BNLearner, alpha: float=0.05, record: bool=False, verbose: bool=False) -> tuple[nx.Graph, dict[tuple, set], list[tuple]]:
    assert 0 < alpha < 1
    
    graph: nx.Graph = nx.complete_graph(learner.names())
    d = 0
    sepsets = {}
    adjacents = { x: set(graph.neighbors(x)) for x in graph.nodes() }

    log = []

    while max(map(len, adjacents.values())) > d:

        for x, y in graph.edges():
            if len(adjacents[x]) - 1 < d:
                continue
            
            neighborsx = [z for z in adjacents[x] if z != y]
            for Z in combinations(neighborsx, d):
                _, pvalue = learner.chi2(x, y, Z)

                if record:
                    log.append((x, y, Z, pvalue))

                if pvalue >= alpha:
                    if verbose:
                        print(f"'{x}' cond ind '{y}' | {Z} with p-value={pvalue} >= {alpha}")

                    graph.remove_edge(x, y)
                    adjacents[x].remove(y)
                    adjacents[y].remove(x)

                    sepsets[(x, y)] = sepsets[(y, x)] = {*Z}
                    break
                else:
                    if verbose:
                        print(f"'{x}' cond dep '{y}' | {Z} with p-value={pvalue} < {alpha}")
        d += 1
    return graph, sepsets, log

def hasArrowheadEndpoint(graph: nx.Graph, x: str, y: str) -> bool:
    # Has x *-> y ?
    return graph.get_edge_data(x, y)[y] == ">"

def rule0(graph: nx.Graph, sepsets: dict[tuple, set], verbose: bool=False) -> nx.Graph:
    
    pag = nx.Graph()
    pag.add_edges_from((x, y, { x: "o", y: "o" }) for x, y in graph.edges())

    for x in graph.nodes():
        for y in graph.nodes():

            if x == y or graph.has_edge(x, y):
                continue
            
            for z in graph.neighbors(x):
                if graph.has_edge(y, z) and z not in sepsets.get((x, y), set()):
                    if hasArrowheadEndpoint(pag, x, z):
                        continue
                    if hasArrowheadEndpoint(pag, y, z):
                        continue

                    # We have now: x *-o z o-* y

                    xzdata = pag.get_edge_data(x, z)
                    yzdata = pag.get_edge_data(y, z)

                    if verbose:
                        xEndpoint = xzdata[x] if xzdata[x] != ">" else "<"
                        yEndpoint = yzdata[y]
                        print(f"orientes '{x}' {xEndpoint}-o '{z}' o-{yEndpoint} '{y}' as '{x}' {xEndpoint}-> {z} <-{yEndpoint} '{y}'")

                    xzdata[z] = ">"
                    yzdata[z] = ">"

    return pag
