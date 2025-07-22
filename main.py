import argparse
import logging
import sys
from drone import DroneOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("drone")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Drone Resource Orchestration Framework"
    )
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--mode", choices=["public", "private"], default="public")
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--in-cluster", action="store_true")
    parser.add_argument("--config-file")
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    try:
        orchestrator = DroneOrchestrator(
            app_name=args.app_name,
            namespace=args.namespace,
            mode=args.mode,
            prometheus_url=args.prometheus_url,
            in_cluster=args.in_cluster,
            config_file=args.config_file
        )
        orchestrator.start(
            iterations=args.iterations,
            interval=args.interval
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
