import logging
import requests

logger = logging.getLogger(__name__)


class MonitoringInterface:
    def get_performance_metrics(self):
        raise NotImplementedError("Subclasses must implement this method")

    def get_resource_usage(self):
        raise NotImplementedError("Subclasses must implement this method")

    def get_context(self):
        raise NotImplementedError("Subclasses must implement this method")


class PrometheusMonitoring(MonitoringInterface):
    def __init__(
        self,
        prometheus_url="http://localhost:9090",
        app_name=None,
        namespace="default",
        performance_metrics=None,
        context_metrics=None
    ):
        self.prometheus_url = prometheus_url
        self.app_name = app_name
        self.namespace = namespace

        # Default performance metrics if none provided
        self.performance_metrics = performance_metrics or {
            # For batch jobs - job completion time
            "job_time": f'rate(job_completion_time_seconds{{namespace="{namespace}",app="{app_name}"}}[5m])',
            # For microservices - P90 latency
            "p90_latency": f'histogram_quantile(0.9, sum(rate(http_request_duration_seconds_bucket{{namespace="{namespace}",app="{app_name}"}}[5m])) by (le))'
        }

        # Default context metrics if none provided
        self.context_metrics = context_metrics or {
            # Workload intensity - requests per second
            "workload": f'sum(rate(http_requests_total{{namespace="{namespace}"}}[5m]))',
            # CPU utilization across the cluster
            "cpu_util": 'avg(node_cpu_utilization)',
            # Memory utilization across the cluster
            "mem_util": 'avg(node_memory_utilization)',
            # Network utilization
            "net_util": 'avg(node_network_transmit_bytes_total + node_network_receive_bytes_total)',
            # Spot price
            "spot_price": '1'  # This would be replaced with a real query in production
        }

    def query_prometheus(self, query):
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            result = response.json()

            # Extract the value from the response
            if result["status"] == "success" and result["data"]["result"]:
                return float(result["data"]["result"][0]["value"][1])
            else:
                logger.warning(f"No data for query: {query}")
                return 0.0

        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return 0.0

    def get_performance_metrics(self):
        results = {}
        for name, query in self.performance_metrics.items():
            results[name] = self.query_prometheus(query)

        return results

    def get_resource_usage(self):
        # Query for the application's resource usage
        cpu_query = f'sum(container_cpu_usage_seconds_total{{namespace="{self.namespace}",pod=~"{self.app_name}-.*"}})'
        mem_query = f'sum(container_memory_working_set_bytes{{namespace="{self.namespace}",pod=~"{self.app_name}-.*"}})'
        net_query = f'sum(container_network_transmit_bytes_total{{namespace="{self.namespace}",pod=~"{self.app_name}-.*"}} + container_network_receive_bytes_total{{namespace="{self.namespace}",pod=~"{self.app_name}-.*"}})'

        return {
            "cpu": self.query_prometheus(cpu_query),
            "memory": self.query_prometheus(mem_query),
            "network": self.query_prometheus(net_query)
        }

    def get_context(self):
        results = {}
        for name, query in self.context_metrics.items():
            results[name] = self.query_prometheus(query)

        return results
