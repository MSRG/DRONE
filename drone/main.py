#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time

from drone import DroneOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Drone: Dynamic Resource Orchestration for Containerized Clouds'
    )

    parser.add_argument(
        '--app-name',
        required=True,
        help='Name of the application to orchestrate'
    )

    parser.add_argument(
        '--namespace',
        default='default',
        help='Kubernetes namespace (default: default)'
    )

    parser.add_argument(
        '--mode',
        choices=['public', 'private'],
        default='public',
        help='Orchestration mode: public or private cloud (default: public)'
    )

    parser.add_argument(
        '--prometheus-url',
        help='Prometheus server URL'
    )

    parser.add_argument(
        '--in-cluster',
        action='store_true',
        help='Use in-cluster Kubernetes configuration'
    )

    parser.add_argument(
        '--config-file',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--iterations',
        type=int,
        help='Number of orchestration iterations to run'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval between iterations in seconds (default: 60)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main entry point for the Drone framework."""
    args = parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    try:
        logger.info(
            f"Starting Drone orchestrator for application: {args.app_name}")
        logger.info(f"Mode: {args.mode}, Namespace: {args.namespace}")

        # Create orchestrator instance
        orchestrator = DroneOrchestrator(
            app_name=args.app_name,
            namespace=args.namespace,
            mode=args.mode,
            prometheus_url=args.prometheus_url,
            in_cluster=args.in_cluster,
            config_file=args.config_file
        )

        # Run orchestrator
        if args.iterations:
            logger.info(
                f"Running for {args.iterations} iterations with {args.interval}s interval")
            orchestrator.start(iterations=args.iterations,
                               interval=args.interval)
        else:
            logger.info("Running indefinitely with %ds interval",
                        args.interval)
            orchestrator.start(interval=args.interval)

    except KeyboardInterrupt:
        logger.info("Orchestration interrupted by user")
    except Exception as e:
        logger.error(f"Error during orchestration: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
