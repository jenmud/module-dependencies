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
    "scrape_pkg",
    "map_filename",
    "map_functions",
    "map_method",
    "map_classes",
    "map_modules",
    "run_server",
    "EXCLUDES"
]


GRAPH = Graph()
GRAPH.add_vertex_constraint("class", "name")
GRAPH.add_vertex_constraint("method", "name")
GRAPH.add_vertex_constraint("file", "name")
GRAPH.add_vertex_constraint("function", "name")
GRAPH.add_vertex_constraint("module", "name")

EXCLUDES = []
SEEN = set()


def _skip(name, excludes=None):
    """
    Skip over names that match any of the given regex expressions.

    :param name: Name that you are applying regex against.
    :type name: :class:`str`
    :param excludes: Regular expressions to apply against ``name``. If omitted,
        then defaults will be applied.
    :type excludes: Iterable of :class:`re.SRE_Pattern` or :obj:`None`
    :returns: True if the ``name`` was matched by one of the regular
        expressions.
    :rtype: :class:`bool`
    """
    if excludes is None:
        excludes = EXCLUDES

    for exclude in excludes:
        if exclude.search(name):
            logging.info(
                "%r match exclude %r, skipping...",
                name,
                exclude.pattern
            )
            return True
    return False


def should_skip(excludes=None):
    """
    Decorate a function checking if the object name should be skipped.

    This decorator expects that the first argument of the function is an
    object with a ``__name__`` attribute.

    :param excludes: Regular expressions to apply against ``name``. If omitted,
        then defaults will be applied.
    :type excludes: Iterable of :class:`re.SRE_Pattern` or :obj:`None`
    """
    def decorator(func):
        """
        Outer function.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """
            Wraping of the actual function you are decorating.
            """
            name = args[0].__name__
            if _skip(name, excludes):
                return
            return func(*args, **kwargs)
        return wrapper
    return decorator


def import_error_decorator(func):
    """
    Function decorator that will catch import errors and log them.

    :param func: Function that you are decorating and should take an obj
        as the first parameter.
    :type func: callbable
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wraping of the actual function you are decorating.
        """
        try:
            return func(*args, **kwargs)
        except ImportError:
            logging.exception("Could not import %s", args[0].__name__)
    return wrapper


def catch_all_errors_decorator(func):
    """
    Function decorator that will catch all types of exceptions and log them.

    :param func: Function that you are decorating and should take an obj
        as the first parameter.
    :type func: callbable
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wraping of the actual function you are decorating.
        """
        try:
            return func(*args, **kwargs)
        except Exception:  # pylint: disable=broad-except
            logging.exception("Hmmm something went wrong here")
    return wrapper


@catch_all_errors_decorator
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
        logging.debug(
            "Buildin %r does not have a file, skipping",
            obj.__name__
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


@should_skip()
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
    for _, obj in inspect.getmembers(obj, inspect.ismodule):

        _id = id(obj) + id(parent)
        if _id in SEEN:
            continue
        SEEN.add(_id)

        node = GRAPH.get_or_create_vertex("module", name=obj.__name__)
        node.set_property(abstract=inspect.isabstract(obj))
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


@should_skip()
@catch_all_errors_decorator
@import_error_decorator
def scrape_pkg(pkg):
    """
    Srape a package for interesting information..

    :param pkg: Package that you are scrapping.
    :type pkg: :types:`ModuleType`
    :param excludes: Skip over names that match the given regular expressions.
    :type excludes: Iterable of :class:`re.SRE_Pattern`
    """
    module_dirname = os.path.dirname(inspect.getsourcefile(pkg))
    pkg_node = GRAPH.get_or_create_vertex("module", name=pkg.__name__)
    scrape(pkg)

    for _, name, is_pkg in pkgutil.iter_modules([module_dirname]):
        full_name = "{}.{}".format(pkg.__name__, name)

        # because of this extra inner create, we need to add in a skip/exclude
        # check here.
        if _skip(full_name) or _skip(name):
            continue

        logging.debug("Importing %s", full_name)
        module = importlib.import_module(full_name)
        node = GRAPH.get_or_create_vertex("module", name=full_name)
        GRAPH.get_or_create_edge(pkg_node, "contains", node)

        logging.debug(
            "(%s)-[:contains]->(%s)",
            pkg_node.properties["name"],
            node.properties["name"]
        )

        if is_pkg is True:
            scrape_pkg(module)
        scrape(module)


@should_skip()
@import_error_decorator
def scrape(module):
    """
    Srape a module for interesting information..

    :param module: Module that you are scrapping.
    :type module: :types:`ModuleType`
    """
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


def dump(filename):
    """
    Dump the graph to a file on disk.

    .. note::

        Dump will overwrite existing filenames.

    :param filename: Filename to dumpt the file.
    :type filename: :class:`str`
    """
    logging.info("Dumping graph to %s", filename)
    with open(filename, "w") as file_handler:
        GRAPH.dump(file_handler)
