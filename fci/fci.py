from itertools import combinations, permutations
from collections import deque
from typing import Generator

import networkx as nx
import pyagrum as gum

from fci.endpoint import Endpoint

#=================== auxiliary functions ===================#
def getTriplets(graph: nx.Graph) -> Generator[tuple[str, str, str], None, None]:
    """Return the permutation of all triplets in the graph."""
    for z in graph.nodes:
        for x, y in permutations(graph.neighbors(z), 2):
            yield x, z, y

def hasEndpoint(pag: nx.Graph,
                x: str, y: str,
                xEndpoint: Endpoint, yEndpoint: Endpoint) -> bool:
    """Return true if the edge x-y has the required endpoint; otherwise return false."""
    if not pag.has_edge(x, y):
        raise Exception(f"The graph does not contain the {x}-{y} edge.")
    xyData = pag.get_edge_data(x, y)
    return xyData[x] == xEndpoint and xyData[y] == yEndpoint

def isCollider(pag: nx.Graph, x: str, z: str, y: str) -> bool:
    # x *-> z <-* y ?
    return  pag.get_edge_data(x, z)[z] == Endpoint.ARROW and \
            pag.get_edge_data(y, z)[z] == Endpoint.ARROW

def isTriangle(pag: nx.Graph, x: str, z: str, y: str) -> bool:
    # x *-* z *-*y; x *-* y ?
    return pag.has_edge(x, z) and pag.has_edge(z, y) and pag.has_edge(x, y)

def isParent(pag: nx.Graph, x: str, y: str) -> bool:
    # Has x -> y ?
    return hasEndpoint(pag, x, y, Endpoint.TAIL, Endpoint.ARROW)

def isSpouse(pag: nx.Graph, x: str, y: str) -> bool:
    # Has x <-> y ?
    return hasEndpoint(pag, x, y, Endpoint.ARROW, Endpoint.ARROW)

def isPDEdge(pag: nx.Graph, x: str, y: str) -> bool:
    xyData = pag.get_edge_data(x, y)
    return  (xyData[x] == Endpoint.CIRCLE or xyData[x] == Endpoint.TAIL) and \
            (xyData[y] == Endpoint.CIRCLE or xyData[y] == Endpoint.ARROW)



def getPDSep(pag: nx.Graph, x: str) -> set:
    pdsep = set()
    stack = []
    visited = set()

    for z in pag.neighbors(x):
        pdsep.add(z)
        stack.append((x, z))
    
    while stack:
        edge = stack.pop()
        if edge in visited:
            continue
        visited.add(edge)
        u, v = edge

        for z in pag.neighbors(v):
            if z == x or z == u:
                continue

            if isCollider(pag, u, v, z) or isTriangle(pag, u, v, z):
                pdsep.add(z)
                stack.append((v, z))
    return pdsep

def reconstructPath(links: dict[str, str | None], tar: str) -> list[str]:
    path = [tar]
    u = tar
    while links[u] is not None:
        u = links[u]
        path.append(u)
    path.reverse()
    return path

# TODO, improve this function.
def getDiscriminatingPath(pag: nx.Graph, x: str, z: str, y: str) -> list[str]:
    queue = deque()
    queue.append(x)

    visited = set()
    # visited.remove(z)
    # visited.remove(y)

    links = { u: None for u in pag.nodes }
    links[z] = y
    links[x] = z

    while queue:
        u = queue.popleft()

        if u in visited:
            continue
        visited.add(u)

        for v in pag.neighbors(u):
            if v == x or v == z or v == y:
                continue

            if pag.has_edge(v, y):
                if isParent(pag, v, y) and isSpouse(pag, u, v):
                    queue.append(v)
                    links[v] = u
            else:
                uvData = pag.get_edge_data(u, v)
                if uvData[u] == Endpoint.ARROW:
                    links[v] = u
                    return reconstructPath(links, v)
                    
    return None

def getUncoveredCirclePath(pag: nx.Graph, x: str, y: str) -> Generator[list[str], None, None]:
    path = [x]
    visited = { u: False for u in pag.nodes }
    visited[x] = True
    stack = []

    for z in pag.neighbors(x):
        if z != y and hasEndpoint(pag, x, z, Endpoint.CIRCLE, Endpoint.CIRCLE):
            stack.append((x, z))
    
    while stack:
        u, v = stack.pop()
        while path[-1] != u:
            visited[path.pop()] = False
        
        path.append(v)
        visited[v] = True

        if v == y:
            isUncoveredCirclePath = True
            for i in range(len(path) - 1):
                ui, vi = path[i], path[i + 1]
                if not hasEndpoint(pag, ui, vi, Endpoint.CIRCLE, Endpoint.CIRCLE):
                    isUncoveredCirclePath = False
                    break
            if isUncoveredCirclePath:
                yield path[:]

        for w in pag.neighbors(v):
            if  not visited[w] and \
                not pag.has_edge(u, w) and \
                hasEndpoint(pag, v, w, Endpoint.CIRCLE, Endpoint.CIRCLE):
                stack.append((v, w))

def existUncoveredPDPath(pag: nx.Graph, x: str, y: str, z: str) -> bool:
    visited = {x}
    stack = [(x, z)]

    while stack:
        u, v = stack.pop()
        if v in visited:
            continue
        visited.add(u)

        if v == y:
            return True

        for w in pag.neighbors(v):
            if w != x and not pag.has_edge(u, w) and isPDEdge(pag, u, v):
                stack.append((v, w))
    return False

#=================== skeleton discovery ===================#
def initialSkeleton(learner: gum.BNLearner,
                    alpha: float=0.05,
                    record: bool=False,
                    verbose: bool=False) -> tuple[nx.Graph, dict[tuple, set], list[tuple]]:
    graph = nx.complete_graph(learner.names())
    sepsets = {}
    adjacents = { x: set(graph.neighbors(x)) for x in graph.nodes }
    d = 0

    log = []
    
    while max(map(len, adjacents.values())) > d:
        for x, y in graph.edges:
            if len(adjacents[x]) - 1 < d:
                continue

            for Z in combinations(adjacents[x] - {y}, d):
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

def finalSkeleton(learner: gum.BNLearner,
                  pag: nx.Graph,
                  sepsets: dict[tuple, set],
                  alpha: float=0.05,
                  record: bool=False,
                  verbose: bool=False) -> list[tuple]:
    pdseps = { x: getPDSep(pag, x) for x in pag.nodes }

    log = []

    for x, y in list(pag.edges):
        if not pag.has_edge(x, y):
            continue
        
        d = 0
        pdsXMinusY = pdseps[x] - {y}
        done = False
        while not done and len(pdsXMinusY) > d:
            for Z in combinations(pdsXMinusY, d):
                _, pvalue = learner.chi2(x, y, Z)

                if record:
                    log.append((x, y, Z, pvalue))

                if pvalue >= alpha:
                    if verbose:
                        print(f"'{x}' cond ind '{y}' | {Z} with p-value={pvalue} >= {alpha}")
                    
                    pag.remove_edge(x, y)

                    sepsets[(x, y)] = sepsets[(y, x)] = sepsets.get((x, y), set()) | {*Z}
                    done = True
                    break
                else:
                    if verbose:
                        print(f"'{x}' cond dep '{y}' | {Z} with p-value={pvalue} < {alpha}")
            d += 1
    return log

#=================== orientation rules ===================#
def rule0(graph: nx.Graph, sepsets: dict[tuple, set], verbose: bool=False) -> nx.Graph:
    pag = nx.Graph()
    pag.add_nodes_from(graph.nodes)
    pag.add_edges_from((x, y, { x: Endpoint.CIRCLE, y: Endpoint.CIRCLE }) for x, y in graph.edges())

    for x, z, y in getTriplets(pag):
        if pag.has_edge(x, y) or z in sepsets.get((x, y), set()):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        if xzData[z] == Endpoint.CIRCLE and yzData[z] == Endpoint.CIRCLE:
            if verbose:
                xEndpoint = xzData[x].value if xzData[x] != Endpoint.ARROW  else "<"
                print(f"[R0]         '{x}' {xEndpoint}-o '{z}' o-{yzData[y].value} '{y}'\n"
                        f"             '{z}' not in sepset('{x}', '{y}') = {sepsets.get((x, y), set())}\n"
                        f"      orient '{x}' {xEndpoint}-> '{z}' <-{yzData[y].value} '{y}'")
        
            xzData[z] = Endpoint.ARROW
            yzData[z] = Endpoint.ARROW
    return pag




def rule1(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        # x *-> z o-* y.
        # Orient z o-* y as z -> y.
        if  xzData[z] == Endpoint.ARROW and \
            yzData[z] == Endpoint.CIRCLE:

            if verbose:
                xEndpoint = xzData[x].value if xzData[x] != Endpoint.ARROW else "<"
                print(f"[R1]         '{x}' {xEndpoint}-> '{z}' o-{yzData[y].value} '{y}'\n"
                      f"             '{x}' and '{y}' are not adjacent\n"
                      f"      orient '{z}' -> '{y}'")
            
            yzData[z] = Endpoint.TAIL
            yzData[y] = Endpoint.ARROW
            hasChange = True
    return hasChange

def rule2(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if not pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)
        xyData: dict[str, Endpoint] = pag.get_edge_data(x, y)

        # x -> z *-> y or x *-> z -> y; and x *-o y.
        # Orient x *-o y as x *-> y.
        if  ((xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.ARROW and yzData[y] == Endpoint.ARROW) or \
            (yzData[z] == Endpoint.TAIL and xzData[z] == Endpoint.ARROW and yzData[y] == Endpoint.ARROW)) and \
            xyData[y] == Endpoint.CIRCLE:

            if verbose:
                xEndpointFromxz = xzData[x].value if xzData[x] != Endpoint.ARROW else "<"
                xEndpointFromxy = xyData[x].value if xyData[x] != Endpoint.ARROW else "<"
                print(f"[R2]         '{x}' {xEndpointFromxz}-> '{z}' {yzData[z].value}-{yzData[y].value} '{y}'\n"
                      f"             '{x}' {xEndpointFromxy}-o '{y}'\n"
                      f"      orient '{x}' {xEndpointFromxy}-> '{y}'")
            
            xyData[y] = Endpoint.ARROW
            hasChange = True
    return hasChange

def rule3(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        if xzData[z] != Endpoint.ARROW or yzData[z] != Endpoint.ARROW:
            continue

        # x *-> z <-* y and x *-o v o-* y and v *-o z.
        # Orient v *-o z as v *-> z.
        for v in pag.neighbors(z):
            if not pag.has_edge(x, v) or not pag.has_edge(y, v):
                continue

            xvData: dict[str, Endpoint] = pag.get_edge_data(x, v)
            yvData: dict[str, Endpoint] = pag.get_edge_data(y, v)
            zvData: dict[str, Endpoint] = pag.get_edge_data(z, v)

            if  xvData[v] == Endpoint.CIRCLE and \
                yvData[v] == Endpoint.CIRCLE and \
                zvData[z] == Endpoint.CIRCLE:

                if verbose:
                    xEndpointFromxz = xzData[x].value if xzData[x] != Endpoint.ARROW else "<"
                    xEndpointFromxv = xvData[x].value if xvData[x] != Endpoint.ARROW else "<"
                    print(f"[R3]         '{x}' {xEndpointFromxz}-> '{z}' <-{yzData[z].value} '{y}'\n"
                          f"             '{x}' {xEndpointFromxv}-> '{v}' <-{yvData[v].value} '{y}'\n"
                          f"             '{z}' o-{zvData[v].value} '{v}'\n"
                          f"             '{x}' and '{y}' are not adjacent\n"
                          f"      orient '{z}' <-{zvData[v].value} '{v}'")
                zvData[z] = Endpoint.ARROW
                hasChange = True
    return hasChange

def rule4(pag: nx.Graph, sepsets: dict[tuple, set], verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if not pag.has_edge(x, y):
            continue
        
        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        # x <-* z o-* y and x -> y.
        if  xzData[x] == Endpoint.ARROW and \
            yzData[z] == Endpoint.CIRCLE and \
            isParent(pag, x, y):

            path = getDiscriminatingPath(pag, x, z, y)
            if path is not None:
                hasChange = True
                if verbose:
                    print(f"[R4]         '{x}' <-{xzData[z].value} '{z}' o-{yzData[y].value} '{y}'\n"
                          f"             '{x}' -> '{y}'\n"
                          f"             find discriminating path = {path}")
                
                if z not in sepsets.get((path[-1], y), set()):
                    if verbose:
                        print(f"      orient '{x}' <-> '{z}' <-> '{y}'")
                    xzData[z] = Endpoint.ARROW
                    yzData[z] = Endpoint.ARROW
                    yzData[y] = Endpoint.ARROW
                else:
                    if verbose:
                        print(f"      orient '{z}' -> '{y}'")
                    yzData[z] = Endpoint.TAIL
                    yzData[y] = Endpoint.ARROW
    return hasChange




def rule5(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, y, xyData in pag.edges(data=True):
        # We assure x o-o y.
        if xyData[x] != Endpoint.CIRCLE or xyData[y] != Endpoint.CIRCLE:
            continue

        # Path : x o-o u o-o ... o-o v o-o y.
        for path in getUncoveredCirclePath(pag, x, y):
            # path.length > 3
            # u and y are not adjacent.
            # v and x are not adjacent.
            if  path[1] != path[-2] and \
                not pag.has_edge(path[1], path[-1]) and \
                not pag.has_edge(path[0], path[-2]):

                if verbose:
                    print(f"[R5]         '{x}' o-o '{y}'\n"
                        f"             find uncovered circle path = {path}\n"
                        f"      orient '{x}' - '{y}' and '{x}' - ... - '{y}'")
                hasChange = True

                # Orient x o-o u o-o ... o-o v o-o y as x - u - ... - v - y.
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    pag[u][v][u] = Endpoint.TAIL
                    pag[u][v][v] = Endpoint.TAIL
                
                xyData[x] = Endpoint.TAIL
                xyData[y] = Endpoint.TAIL
    return hasChange

def rule6(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        xzData: dict[str, Endpoint] = pag[x][z]
        yzData: dict[str, Endpoint] = pag[y][z]
        
        if  xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.TAIL and \
            yzData[z] == Endpoint.CIRCLE:
            if verbose:
                print(f"[R6]         '{x}' - '{z}' o-{yzData[y].value} '{y}'\n"
                      f"      orient '{z}' -{yzData[y].value} '{y}'")
            
            yzData[z] = Endpoint.TAIL
            hasChange = True
    return hasChange

def rule7(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag[x][z]
        yzData: dict[str, Endpoint] = pag[y][z]
        
        if  xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.CIRCLE and \
            yzData[z] == Endpoint.CIRCLE:
            if verbose:
                print(f"[R7]         '{x}' -o '{z}' o-{yzData[y].value} '{y}'\n"
                      f"             '{x}' and '{y}' are not adjacent\n"
                      f"      orient '{z}' -{yzData[y].value} '{y}'")
            
            yzData[z] = Endpoint.TAIL
            hasChange = True
    return hasChange




def rule8(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriplets(pag):
        if not pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)
        xyData: dict[str, Endpoint] = pag.get_edge_data(x, y)

        # x -> z -> y or x -o z -> y; and x o-> y.
        # Orient x o-> y as x -> y.
        if  xzData[x] == Endpoint.TAIL and (xzData[z] ==  Endpoint.ARROW or xzData[z] ==  Endpoint.CIRCLE) and \
            yzData[z] == Endpoint.TAIL and yzData[y] == Endpoint.ARROW and \
            xyData[x] == Endpoint.CIRCLE and xyData[y] == Endpoint.ARROW:
            if verbose:
                print(f"[R8]         '{x}' -{xzData[z].value} '{z}' -> '{y}'"
                      f"             '{x}' o-> '{y}'"
                      f"      orient '{x}' -> '{y}'")

            xyData[x] = Endpoint.TAIL
            hasChange = True
    return hasChange

def rule9(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, y, xyData in pag.edges(data=True):
        if not hasEndpoint(pag, x, y, Endpoint.CIRCLE, Endpoint.ARROW):
            continue

        for z in pag.neighbors(x):
            if  not pag.has_edge(z, y) and isPDEdge(pag, x, z) and \
                existUncoveredPDPath(pag, x, y, z):
                    if verbose:
                        print(f"[R9]         '{x}' o-> '{y}'\n"
                              f"             exist uncovered p.d. path = ('{x}', '{z}', ..., '{y}')\n"
                              f"      orient '{x}' -> '{y}'")
                    xyData[x] = Endpoint.TAIL
                    hasChange = True
                    break
    return hasChange

def rule10(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, y, xyData in pag.edges(data=True):
        if not hasEndpoint(pag, x, y, Endpoint.CIRCLE, Endpoint.ARROW):
            continue

        neighborsXMinusY = set(pag.neighbors(x)) - {y}

        done = False
        for u, v in permutations(pag.neighbors(y), 2):
            # We assume u -> y <- v.
            if  not hasEndpoint(pag, u, y, Endpoint.TAIL, Endpoint.ARROW) or \
                not hasEndpoint(pag, v, y, Endpoint.TAIL, Endpoint.ARROW):
                continue

            for uPrime, vPrime in combinations(neighborsXMinusY, 2):
                if  isPDEdge(pag, x, uPrime) and isPDEdge(pag, x, vPrime) and \
                    existUncoveredPDPath(pag, x, u, uPrime) and existUncoveredPDPath(pag, x, v, vPrime):
                    if verbose:
                        print(f"[R10]        '{x}' o-> '{y}'\n"
                              f"             '{u}' -> '{y}' <- '{v}'\n"
                              f"             exist uncovered p.d. path = ('{x}', '{u}', ..., '{uPrime}')\n"
                              f"             exist uncovered p.d. path = ('{x}', '{v}', ..., '{vPrime}')\n"
                              f"      orient '{x}' -> '{y}'")
                    xyData[x] = Endpoint.TAIL
                    hasChange = True

                    done = True
                if done:
                    break
            if done:
                break
    return hasChange
