"""
Find all interesting information for a given installed module.
"""
import inspect
import logging
from ruruki.graphs import Graph
from ruruki_eye.server import run


__all__ = [
    "scrape",
    "map_filename",
    "map_functions",
    "map_method",
    "map_classes",
    "map_modules",
    "run_server",
]

GRAPH = Graph()
GRAPH.add_vertex_constraint("class", "name")
GRAPH.add_vertex_constraint("method", "name")
GRAPH.add_vertex_constraint("file", "name")
GRAPH.add_vertex_constraint("function", "name")
GRAPH.add_vertex_constraint("module", "name")

SEEN = set()


def map_filename(obj, parent):
    """
    Find and map all the file names that the obj comes from.

    :param obj: Find all files which the object comes from.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    try:
        filename = inspect.getsourcefile(obj)
        if filename:
            node = GRAPH.get_or_create_vertex("file", name=filename)
            GRAPH.get_or_create_edge(parent, "found-in", node)

            logging.debug(
                "(%s)-[:found-in]->(%s)",
                parent.properties["name"],
                filename,
            )
    except TypeError:
        logging.debug("Could not find file for: %s", obj.__name__)


def map_functions(obj, parent):
    """
    Find and map all the functions recursively.

    :param obj: Find all functions from the object.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    for name, obj in inspect.getmembers(obj, inspect.isfunction):
        node = GRAPH.get_or_create_vertex("function", name=name)
        GRAPH.get_or_create_edge(parent, "has-function", node)
        map_filename(obj, node)

        logging.debug(
            "(%s)-[:has-function]->(%s)",
            parent.properties["name"],
            name,
        )


def map_method(obj, parent):
    """
    Find and map all the methods recursively.

    :param obj: Find all methods from the object.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    try:
        for name, obj in inspect.getmembers(obj, inspect.ismethod):
            node = GRAPH.get_or_create_vertex("method", name=name)
            GRAPH.get_or_create_edge(parent, "has-method", node)
            map_filename(obj, node)

            logging.debug(
                "(%s)-[:has-method]->(%s)",
                parent.properties["name"],
                name
            )

    except ImportError:
        logging.error("Could not import %s", obj.__name__)


def map_classes(obj, parent):
    """
    Find and map all the classes and the methods for the class recursively.

    :param obj: Find all classes from the object.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    for name, obj in inspect.getmembers(obj, inspect.isclass):
        node = GRAPH.get_or_create_vertex("class", name=name)
        GRAPH.get_or_create_edge(parent, "has-class", node)
        map_filename(obj, node)

        logging.debug(
            "(%s)-[:has-class]->(%s)",
            parent.properties["name"],
            name
        )

        map_method(obj, node)

        last = node
        for name in inspect.getmro(obj)[1:]:
            node = GRAPH.get_or_create_vertex("class", name=name.__name__)
            GRAPH.get_or_create_edge(last, "subclasses", node)
            map_filename(obj, node)

            logging.debug(
                "(%s)-[:subclasses]->(%s)",
                parent.properties["name"],
                name
            )

            last = node
            map_method(obj, node)


def map_modules(obj, parent):
    """
    Find and map all the modules recursively.

    :param obj: Find all modules from the object.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    # get all the functions in the module
    for name, obj in inspect.getmembers(obj, inspect.ismodule):
        _id = id(obj) + id(parent)
        if _id in SEEN:
            continue
        SEEN.add(_id)
        node = GRAPH.get_or_create_vertex("module", name=name)
        GRAPH.get_or_create_edge(parent, "imports", node)
        map_filename(obj, node)

        logging.debug(
            "(%s)-[:imports]->(%s)",
            parent.properties["name"],
            name
        )

        map_classes(obj, node)
        map_functions(obj, node)
        map_modules(obj, node)


def scrape(module):
    """
    Start scrapping interesting information about a module.

    :param module: Module that you are scrapping.
    :type module: :types:`ModuleType`
    """
    logging.info("Scrapping %r", module)
    parent = GRAPH.get_or_create_vertex("module", name=module.__name__)
    map_filename(module, parent)
    map_modules(module, parent)
    map_functions(module, parent)

    logging.info("Vertices: %d", len(GRAPH.vertices))
    logging.info("Edges: %d", len(GRAPH.edges))
    logging.info("Modules: %d", len(GRAPH.get_vertices("module")))
    logging.info("Classes: %d", len(GRAPH.get_vertices("class")))
    logging.info("Methods: %d", len(GRAPH.get_vertices("method")))
    logging.info("Function: %d", len(GRAPH.get_vertices("function")))
    logging.info("Files: %d", len(GRAPH.get_vertices("file")))


def run_server(address="0.0.0.0", port=8000):
    """
    Start a web server serving up all scrapped information.

    :param address: Address to bind on.
    :type address: :class:`str`
    :param port: Port number to listen on.
    :type port: :class:`int`
    """
    run(address, port, False, GRAPH)
