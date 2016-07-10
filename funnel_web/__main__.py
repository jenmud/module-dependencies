"""
Scrapping from command line.
"""
import argparse
import importlib
import logging
from funnel_web.scrape import scrape, run_server


def main():
    """
    Command line main run.
    """
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
    run_server(ns.address, ns.port)
