"""
Find all interesting information for a given installed module.
"""
import functools
import importlib
import inspect
import logging
import os
import pkgutil
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
GRAPH.add_vertex_constraint("package", "name")

SEEN = set()


def import_error_decorator(func):
    """
    Function decorator that will catch import errors and log them.

    :param func: Function that you are decorating and should take an obj
        as the first parameter.
    :type func: callbable
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ImportError as err:
            logging.error("Could not import %s", args[0].__name__)
    return inner


def catch_all_errors_decorator(func):
    """
    Function decorator that will catch all types of exceptions and log them.

    :param func: Function that you are decorating and should take an obj
        as the first parameter.
    :type func: callbable
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            logging.debug("Hmmm something went wrong here: %s", err)
    return inner


@catch_all_errors_decorator
def map_filename(obj, parent):
    """
    Find and map all the file names that the obj comes from.

    :param obj: Find all files which the object comes from.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    filename = inspect.getsourcefile(obj)
    if filename:
        node = GRAPH.get_or_create_vertex("file", name=filename)
        GRAPH.get_or_create_edge(parent, "found-in", node)

        logging.debug(
            "(%s)-[:found-in]->(%s)",
            parent.properties["name"],
            filename,
        )


@import_error_decorator
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


@import_error_decorator
def map_method(obj, parent):
    """
    Find and map all the methods recursively.

    :param obj: Find all methods from the object.
    :type obj: :class:`object`
    :param parent: Parent node which you are searching in.
    :type parent: :class:`ruruki.interfaces.IVertex`
    """
    for name, obj in inspect.getmembers(obj, inspect.ismethod):
        node = GRAPH.get_or_create_vertex("method", name=name)
        GRAPH.get_or_create_edge(parent, "has-method", node)

        logging.debug(
            "(%s)-[:has-method]->(%s)",
            parent.properties["name"],
            name
        )


@import_error_decorator
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

        for name in inspect.getmro(obj)[1:]:
            sub_node = GRAPH.get_or_create_vertex(
                "class",
                name=name.__name__
            )

            GRAPH.get_or_create_edge(node, "subclasses", sub_node)

            map_filename(obj, sub_node)

            logging.debug(
                "(%s)-[:subclasses]->(%s)",
                parent.properties["name"],
                name
            )

            map_method(name, sub_node)


@import_error_decorator
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
        node = GRAPH.get_or_create_vertex("module", name=obj.__name__)
        GRAPH.get_or_create_edge(parent, "imports", node)
        map_filename(obj, node)

        logging.debug(
            "(%s)-[:imports]->(%s)",
            parent.properties["name"],
            obj.__name__
        )

        map_classes(obj, node)
        map_functions(obj, node)
        map_modules(obj, node)


@catch_all_errors_decorator
@import_error_decorator
def scrape_pkg(pkg):
    module_dirname = os.path.dirname(inspect.getsourcefile(pkg))
    pkg_node = GRAPH.get_or_create_vertex("module", name=pkg.__name__)
    scrape(pkg)
    for _, name, isPkg in pkgutil.iter_modules([module_dirname]):
        full_name = "{}.{}".format(pkg.__name__, name)
        m = importlib.import_module(full_name)
        node = GRAPH.get_or_create_vertex("module", name=full_name)
        GRAPH.get_or_create_edge(pkg_node, "contains", node)
        if isPkg is True:
            scrape_pkg(m)
        scrape(m)


@import_error_decorator
def scrape(module):
    """
    Start scrapping interesting information about a module.

    :param module: Module that you are scrapping.
    :type module: :types:`ModuleType`
    """
    logging.info("Scrapping %r", module.__name__)
    parent = GRAPH.get_or_create_vertex("module", name=module.__name__)
    map_filename(module, parent)
    map_modules(module, parent)
    map_functions(module, parent)



def run_server(address="0.0.0.0", port=8000):
    """
    Start a web server serving up all scrapped information.

    :param address: Address to bind on.
    :type address: :class:`str`
    :param port: Port number to listen on.
    :type port: :class:`int`
    """
    logging.info("Vertices: %d", len(GRAPH.vertices))
    logging.info("Edges: %d", len(GRAPH.edges))
    logging.info("Modules: %d", len(GRAPH.get_vertices("module")))
    logging.info("Classes: %d", len(GRAPH.get_vertices("class")))
    logging.info("Methods: %d", len(GRAPH.get_vertices("method")))
    logging.info("Function: %d", len(GRAPH.get_vertices("function")))
    logging.info("Files: %d", len(GRAPH.get_vertices("file")))

    run(address, port, False, GRAPH)
