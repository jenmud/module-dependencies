import argparse
import inspect
import importlib
import logging
import ruruki

from ruruki.graphs import Graph


GRAPH = Graph()
GRAPH.add_vertex_constraint("class", "name")
GRAPH.add_vertex_constraint("method", "name")
GRAPH.add_vertex_constraint("file", "name")
GRAPH.add_vertex_constraint("function", "name")
GRAPH.add_vertex_constraint("module", "name")


SEEN = set()


def map_filename_from_module(module, parent):
    try:
        filename = inspect.getfile(module)
        if filename:
            parent_file = GRAPH.get_or_create_vertex("file", name=filename)
            GRAPH.get_or_create_edge(parent, "found-in", parent_file)
            logging.debug("(%s)-[:found-in]->(%s)", filename, module)
    except TypeError:
        logging.warn("Failed to get the file for %s", module)


def map_functions_from_module(module, parent):
    # get all the functions in the module
    for fname, func in inspect.getmembers(module, inspect.isfunction):
        fnode = GRAPH.get_or_create_vertex("function", name=fname)
        GRAPH.get_or_create_edge(parent, "has-function", fnode)


def map_classes_from_module(module, parent):
    # get all the classes in the module
    for cname, cls in inspect.getmembers(module, inspect.isclass):
        cnode = GRAPH.get_or_create_vertex("class", name=cname)
        GRAPH.get_or_create_edge(parent, "has-class", cnode)
        last = cnode
        for name in inspect.getmro(cls):
            node = GRAPH.get_or_create_vertex("class", name=name.__name__)
            GRAPH.get_or_create_edge(last, "subclasses", node)
            last = node

        try:
            # get all the class methods in the class
            for mname, meth in inspect.getmembers(cls, inspect.ismethod):
                mnode = GRAPH.get_or_create_vertex("method", name=mname)
                GRAPH.get_or_create_edge(cnode, "has-method", mnode)
        except ImportError:
            logging.exception("Skipping due to an import error")


def build_dep(module, parent):
    previous = parent

    for name, module in inspect.getmembers(module, inspect.ismodule):

        # avoid loops
        if module in SEEN:
            continue
        SEEN.add(module)

        parent = GRAPH.get_or_create_vertex("module", name=name)

        # link to the previous parent
        GRAPH.get_or_create_edge(parent, "comes-from", previous)
        logging.debug(
            "(%s)-[:comes-from]->(%s)", name, previous.properties["name"]
        )


        map_filename_from_module(module, parent)
        map_functions_from_module(module, parent)
        map_classes_from_module(module, parent)
        build_dep(module, parent)


def scrape(module):
    logging.info("Scrapping %r", module)
    try:
        build_dep(
            module,
            GRAPH.get_or_create_vertex("module", name=module.__name__)
        )
    except Exception:
        logging.exception("Hmmm, seems like something went wrong !")


def main():
    from ruruki_eye.server import run

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "module",
        type=importlib.import_module,
        help="Importable module to inspect.",
    )

    parser.add_argument(
        "-p",
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

    run("0.0.0.0", ns.port, False, GRAPH)


if __name__ == "__main__":
    main()
