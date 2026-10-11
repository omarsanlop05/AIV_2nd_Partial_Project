class Node:
    def __init__(self, label=''):
        self.label = label
        self.connections = {}  # neighbor index -> weight of the connection

    def add_connection(self, neighbor, weight):
        self.connections[neighbor] = weight


class Graph:
    def __init__(self):
        self.nodes = list()
        self.size = 0

        # State of the current Dijkstra run
        self.distances = []
        self.predecessors = []
        self.visited = []
        self.current = None

    @property
    def vertex_data(self):
        return [node.label for node in self.nodes]

    def add_edge(self, u, v, weight):
        if 0 <= u < self.size and 0 <= v < self.size:
            self.nodes[u].add_connection(v, weight)

    def add_vertex_data(self, data):
        self.nodes.append(Node(data))
        self.size += 1

    def get_path(self, predecessors, start_vertex, end_vertex):
        path = []
        current = self.vertex_data.index(end_vertex)
        while current is not None:
            path.insert(0, self.vertex_data[current])
            current = predecessors[current]
            if current == self.vertex_data.index(start_vertex):
                path.insert(0, start_vertex)
                break
        return '->'.join(path)  # Join the vertices with '->'

    def _get_path(self, predecessors, start_vertex, end_vertex):
        path = []
        current = self.vertex_data.index(end_vertex)
        while current is not None:
            path.insert(0, self.vertex_data[current])
            current = predecessors[current]
            if current == self.vertex_data.index(start_vertex):
                path.insert(0, start_vertex)
                break
        return path  # Join the vertices with '->'

    def select_min_node(self):
        """Returns the unvisited node with the lowest weight, or None if no node is reachable."""
        min_distance = float('inf')
        min_node = None
        for i in range(self.size):
            if not self.visited[i] and self.distances[i] < min_distance:
                min_distance = self.distances[i]
                min_node = i
        return min_node

    def update_current(self, node):
        """Makes the given node (the one with the lowest weight) the current node."""
        self.current = node


    def mark_visited(self, node):
        """Changes a node from unvisited to visited."""
        self.visited[node] = True
        print(f"Visited vertex: {self.vertex_data[node]}")

    def calculate_weight(self, neighbor):
        """Weight of reaching `neighbor` through the current node; keeps it if it is lower."""
        new_weight = self.distances[self.current] + self.nodes[self.current].connections[neighbor]
        if new_weight < self.distances[neighbor]:
            self.distances[neighbor] = new_weight
            self.predecessors[neighbor] = self.current
            return True
        return False

    def dijkstra(self, start_vertex_data, end_vertex_data):
        start_vertex = self.vertex_data.index(start_vertex_data)
        end_vertex = self.vertex_data.index(end_vertex_data)
        self.distances = [float('inf')] * self.size
        self.predecessors = [None] * self.size
        self.visited = [False] * self.size
        self.current = None
        self.distances[start_vertex] = 0

        for _ in range(self.size):
            next_node = self.select_min_node()

            if next_node is None:
                print("No more reachable vertices.")
                print(f"Distances: {self.distances}")
                break

            self.update_current(next_node)

            if self.current == end_vertex:
                print(f"Breaking out of loop. Current vertex: {self.vertex_data[self.current]}")
                print(f"Distances: {self.distances}")
                break

            self.mark_visited(self.current)

            for neighbor in self.nodes[self.current].connections:
                if not self.visited[neighbor]:
                    self.calculate_weight(neighbor)

        if self.distances[end_vertex] == float('inf'):
            return float('inf'), None  # end vertex is unreachable
        return self.distances[end_vertex], self.get_path(self.predecessors, start_vertex_data, end_vertex_data)

# Example usage
g = Graph()

g.add_vertex_data( 'A')
g.add_vertex_data( 'B')
g.add_vertex_data( 'C')
g.add_vertex_data( 'D')
g.add_vertex_data( 'E')
g.add_vertex_data( 'F')
g.add_vertex_data( 'G')
g.add_vertex_data( "O")
g.add_vertex_data("P")

g.add_edge(3, 0, 4)  # D - A, weight 4
g.add_edge(3, 4, 2)  # D - E, weight 2
g.add_edge(0, 2, 3)  # A - C, weight 3
g.add_edge(0, 4, 4)  # A - E, weight 4
g.add_edge(4, 2, 4)  # E - C, weight 4
g.add_edge(4, 6, 5)  # E - G, weight 5
g.add_edge(2, 5, 5)  # C - F, weight 5
g.add_edge(2, 1, 2)  # C - B, weight 2
g.add_edge(1, 5, 2)  # B - F, weight 2
g.add_edge(6, 5, 5)  # G - F, weight 5
g.add_edge(7,8,1)

distance, path = g.dijkstra('P', 'O')
print(f"Path: {path}, Distance: {distance}")
