import argparse
import inspect
import importlib
import logging
from ruruki.graphs import Graph
from ruruki_eye.server import run


GRAPH = Graph()
GRAPH.add_vertex_constraint("class", "name")
GRAPH.add_vertex_constraint("method", "name")
GRAPH.add_vertex_constraint("file", "name")
GRAPH.add_vertex_constraint("function", "name")
GRAPH.add_vertex_constraint("module", "name")


SEEN = set()


def map_filename(obj, parent):
    filename = inspect.getsourcefile(obj)
    if filename:
        node = GRAPH.get_or_create_vertex("file", name=filename)
        GRAPH.get_or_create_edge(parent, "found-in", node)

        logging.debug(
            "(%s)-[:found-in]->(%s)",
            parent.properties["name"],
            filename,
        )


def map_functions(obj, parent):
    # get all the functions in the module
    for name, obj in inspect.getmembers(obj, inspect.isfunction):
        node = GRAPH.get_or_create_vertex("function", name=name)
        GRAPH.get_or_create_edge(parent, "has-function", node)

        logging.debug(
            "(%s)-[:has-function]->(%s)",
            parent.properties["name"],
            name,
        )


def map_method(obj, parent):
    try:
        for name, obj in inspect.getmembers(obj, inspect.ismethod):
            node = GRAPH.get_or_create_vertex("method", name=name)
            GRAPH.get_or_create_edge(parent, "has-method", node)

            logging.debug(
                "(%s)-[:has-method]->(%s)",
                parent.properties["name"],
                name
            )

    except ImportError:
        logging.error("Could not import %s", obj.__name__)


def map_classes(obj, parent):
    for name, obj in inspect.getmembers(obj, inspect.isclass):
        node = GRAPH.get_or_create_vertex("class", name=name)
        GRAPH.get_or_create_edge(parent, "has-class", node)

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

            logging.debug(
                "(%s)-[:subclasses]->(%s)",
                parent.properties["name"],
                name
            )

            last = node
            map_method(obj, node)


def map_modules(obj, parent):
    # get all the functions in the module
    for name, obj in inspect.getmembers(obj, inspect.ismodule):
        _id = id(obj) + id(parent)
        if _id in SEEN:
            continue
        SEEN.add(_id)
        node = GRAPH.get_or_create_vertex("module", name=name)
        GRAPH.get_or_create_edge(parent, "imports", node)

        logging.debug(
            "(%s)-[:imports]->(%s)",
            parent.properties["name"],
            name
        )

        map_classes(obj, node)
        map_functions(obj, node)
        map_modules(obj, node)


def scrape(obj):
    logging.info("Scrapping %r", obj)
    parent = GRAPH.get_or_create_vertex("module", name=obj.__name__)
    map_modules(obj, parent)
    map_functions(obj, parent)


def main():
    from ruruki_eye.server import run

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "module",
        type=importlib.import_module,
        help="Importable module to inspect.",
    )

    parser.add_argument(
        "--address",
        default="0.0.0.0",
        help="Address to bind to."
    )

    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Port for ruruki-eye to listen on."
    )

    parser.add_argument(
        "--level",
        default="info",
        choices=["info", "warn", "error", "debug"],
        help="Logging level."
    )

    parser.add_argument(
        "--logfile",
        help="Send logs to a file. Default is to log to stdout."
    )

    ns = parser.parse_args()

    levels = {
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR,
        "debug": logging.DEBUG,
    }

    logging.basicConfig(
        filename=ns.logfile,
        level=levels.get(ns.level, logging.INFO)
    )

    scrape(ns.module)

    logging.info("Vertices: %d", len(GRAPH.vertices))
    logging.info("Edges: %d", len(GRAPH.edges))
    logging.info("Modules: %d", len(GRAPH.get_vertices("module")))
    logging.info("Classes: %d", len(GRAPH.get_vertices("class")))
    logging.info("Methods: %d", len(GRAPH.get_vertices("method")))
    logging.info("Function: %d", len(GRAPH.get_vertices("function")))
    logging.info("Files: %d", len(GRAPH.get_vertices("file")))
    run(ns.address, ns.port, False, GRAPH)


if __name__ == "__main__":
    main()
