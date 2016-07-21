"""
Scrapping from command line.
"""
import argparse
import importlib
import logging
import re
from funnel_web.scrape import scrape_pkg, run_server, dump, EXCLUDES


def regex(expression):
    """
    Return a compiled regular expression.

    :param expression: Expression to compile.
    :type expression: :class:`str`
    :returns: Compiled regular expression.
    :rtype: :class:`re.SRE_Pattern`
    """
    return re.compile(r"%s" % expression)


def main():
    """
    Command line main run.
    """
    global EXCLUDES

    parser = argparse.ArgumentParser(
        description=(
            "Generate an indepth directed dependency graph for a "
            "given module."
        )
    )

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

    parser.add_argument(
        "--dump",
        help="Dump the graph to a file."
    )

    parser.add_argument(
        "--exclude",
        action="append",
        metavar="REGEX",
        type=regex,
        help=(
            "Exclude/skip over modules or packages who name "
            "match the exclude regex"
        )
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

    if ns.exclude:
        EXCLUDES.extend(ns.exclude)

    scrape_pkg(ns.module)

    if ns.dump:
        dump(ns.dump)

    run_server(ns.address, ns.port)
