import enum

import networkx as nx

from fci.utils import getTriples


#################### Orientations rules ####################
class Endpoint(enum.Enum):
    TAIL = ""
    ARROW = ">"
    CIRCLE = "o"

def rule0(graph: nx.Graph, sepsets: dict[tuple, set], verbose: bool=False) -> nx.Graph:
    pag = nx.Graph()
    pag.add_edges_from((x, y, { x: Endpoint.CIRCLE, y: Endpoint.CIRCLE }) for x, y in graph.edges())

    for x, z, y in getTriples(graph):
        if not graph.has_edge(x, y) and z not in sepsets.get((x, y), set()):

            xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
            yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

            if xzData[z] == Endpoint.CIRCLE and yzData[z] == Endpoint.CIRCLE:

                if verbose:
                    xEndpoint = xzData[x].value if xzData[x] != Endpoint.ARROW  else "<"
                    print(f"[R0]     {x} {xEndpoint}-o {z} o-{yzData[y].value} {y} => {x} {xEndpoint}-> {z} <-{yzData[y].value} {y}")
            
                xzData[z] = Endpoint.ARROW
                yzData[z] = Endpoint.ARROW
    return pag

def rule1(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        # x *-> z o-* y;
        # orient z o-* y as z -> y
        if  xzData[z] == Endpoint.ARROW and \
            yzData[z] == Endpoint.CIRCLE:

            if verbose:
                xEndpoint = xzData[x].value if xzData[x] != Endpoint.ARROW else "<"
                print(f"[R1]     {x} {xEndpoint}-> {z} o-{yzData[y].value} {y}\n"
                      f"     and non edge ({x}, {y})\n"
                      f"     =>  {z} -> {y}")
            
            yzData[z] = Endpoint.TAIL
            yzData[y] = Endpoint.ARROW
            hasChange = True
    return hasChange

def rule2(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        if not pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)
        xyData: dict[str, Endpoint] = pag.get_edge_data(x, y)

        # x -> z *-> y or x *-> z -> y; x *-o y;
        # orient x *-o y as x *-> y
        if  ((xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.ARROW and yzData[y] == Endpoint.ARROW) or \
            (yzData[z] == Endpoint.TAIL and xzData[z] == Endpoint.ARROW and yzData[y] == Endpoint.ARROW)) and \
            xyData[y] == Endpoint.CIRCLE:

            if verbose:
                xEndpointFromxz = xzData[x].value if xzData[x] != Endpoint.ARROW else "<"
                xEndpointFromxy = xyData[x].value if xyData[x] != Endpoint.ARROW else "<"
                print(f"[R2]     {x} {xEndpointFromxz}-> {z} {yzData[z].value}-{yzData[y].value} {y}\n"
                      f"     and {x} {xEndpointFromxy}-o {y}\n"
                      f"     =>  {x} {xEndpointFromxy}-> {y}")
            
            xyData[y] = Endpoint.ARROW
            hasChange = True
    return hasChange

def rule3(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        if xzData[z] != Endpoint.ARROW or yzData[z] != Endpoint.ARROW:
            continue

        # x *-> z <-* y; x *-o v o-* y; v *-o z;
        # orient v *-o z as v *-> z
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
                    print(f"[R3]     {x} {xEndpointFromxz}-> {z} <-{yzData[z].value} {y}\n"
                          f"     and {x} {xEndpointFromxv}-> {v} <-{yvData[v].value} {y}\n"
                          f"     and {z} o-{zvData[v].value} {v}\n"
                          f"     and non edge ({x}, {y})\n"
                          f"     =>  {z} <-{zvData[v].value} {v}")
                zvData[z] = Endpoint.ARROW
                hasChange = True
    return hasChange

def rule4(pag: nx.Graph, verbose: bool=False) -> bool:
    ...

def rule5(pag: nx.Graph, verbose: bool=False) -> bool:
    ...

def rule6(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        # x - z o-* y;
        # orient z o-* y as z -* y
        if  xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.TAIL and \
            yzData[z] == Endpoint.CIRCLE:

            if verbose:
                print(f"[R6]     {x} - {z} o-{yzData[y].value} {y} => {z} -{yzData[y].value} {y}")

            yzData[z] = Endpoint.TAIL
            hasChange = True
    return hasChange

def rule7(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        if pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)

        # x -o z o-* y;
        # orient z o-* y as z -* y
        if  xzData[x] == Endpoint.TAIL and xzData[z] == Endpoint.CIRCLE and \
            yzData[z] == Endpoint.CIRCLE:

            if verbose:
                print(f"[R7]     {x} -o {z} o-{yzData[y].value} {y}\n"
                      f"     and non edge ({x}, {y})\n"
                      f"     =>  {z} -{yzData[y].value} {y}")
            
            yzData[z] = Endpoint.TAIL
            hasChange = True
    return hasChange

def rule8(pag: nx.Graph, verbose: bool=False) -> bool:
    hasChange = False
    for x, z, y in getTriples(pag):
        if not pag.has_edge(x, y):
            continue

        xzData: dict[str, Endpoint] = pag.get_edge_data(x, z)
        yzData: dict[str, Endpoint] = pag.get_edge_data(y, z)
        xyData: dict[str, Endpoint] = pag.get_edge_data(x, y)

        # x -> z -> y or x -o z -> y; x o-> y
        # orient x o-> y as x -> y
        if  xzData[x] == Endpoint.TAIL and (xzData[z] ==  Endpoint.ARROW or xzData[z] ==  Endpoint.CIRCLE) and \
            yzData[z] == Endpoint.TAIL and yzData[y] == Endpoint.ARROW and \
            xyData[x] == Endpoint.CIRCLE and xyData[y] == Endpoint.ARROW:

            if verbose:
                print(f"[R8]     {x} -{xzData[z].value} {z} -> {y}"
                      f"     and {x} o-> {y}"
                      f"     =>  {x} -> {y}")

            xyData[x] = Endpoint.TAIL
            hasChange = True
    return hasChange

def rule9(pag: nx.Graph, verbose: bool=False) -> bool:
    ...

def rule10(pag: nx.Graph, verbose: bool=False) -> bool:
    ...

############################################################
