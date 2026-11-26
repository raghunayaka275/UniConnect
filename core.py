
from collections import deque
import database

# In-memory graph using an adjacency list
graph = {}


# Load students and accepted connections from SQLite
def load_graph():
    global graph

    graph = {}

    # Add every student as a node
    for username in database.get_all_users():
        graph[username] = set()

    # Add accepted connections as undirected edges
    for user1, user2 in database.get_all_connections():
        if user1 in graph and user2 in graph:
            graph[user1].add(user2)
            graph[user2].add(user1)


# Get a student's connections
def get_connections(username):
    return list(graph.get(username, set()))


# Get number of direct connections
def get_degree(username):
    return len(graph.get(username, set()))


# Find mutual connections
def get_mutual_connections(user1, user2):
    if user1 not in graph or user2 not in graph:
        return []

    return list(graph[user1] & graph[user2])


# Find shortest connection path using BFS
def shortest_path(start, end):
    if start not in graph or end not in graph:
        return []

    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == end:
            return path

        for neighbour in graph[current]:
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return []


# Recommend students based on mutual connections
def recommend_students(username):
    if username not in graph:
        return []

    recommendations = {}

    for friend in graph[username]:
        for candidate in graph[friend]:
            if candidate != username and candidate not in graph[username]:
                recommendations[candidate] = (
                    recommendations.get(candidate, 0) + 1
                )

    return sorted(
        recommendations,
        key=lambda user: recommendations[user],
        reverse=True
    )


# Find the connection degree between two students
def connection_degree(user1, user2):
    path = shortest_path(user1, user2)

    if not path:
        return "Not connected"

    distance = len(path) - 1

    if distance == 0:
        return "Same user"

    return f"{distance} degree"
