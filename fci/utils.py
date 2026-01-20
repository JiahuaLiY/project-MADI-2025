from itertools import combinations

import networkx as nx

def getTriples(graph: nx.Graph):
    for z in graph.nodes():
        for x, y in combinations(graph.neighbors(z), 2):
            yield x, z, y
