# Drone

This repo contains implementation of paper [Lifting the Fog of Uncertainties: Dynamic Resource Orchestration for the Containerized Cloud](https://dl.acm.org/doi/10.1145/3620678.3624646).

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

1. Create a configuration file (`config.yaml`):

```yaml
# See config.yaml for an example configuration
```

2. Run the orchestrator:

```bash
python main.py --app-name my-application --mode public --config-file config.yaml
```

## Usage

### Command Line Options

```
--app-name       Application name to orchestrate (required)
--namespace      Kubernetes namespace (default: "default")
--mode           Orchestration mode: "public" or "private" (default: "public")
--prometheus-url URL for Prometheus server (default: http://prometheus-server.monitoring:9090)
--in-cluster     Use in-cluster Kubernetes configuration
--mock           Use mock components for testing
--config-file    Path to configuration file
--iterations     Number of orchestration iterations to run
--interval       Interval between iterations in seconds (default: 60)
--verbose        Enable verbose logging
```
