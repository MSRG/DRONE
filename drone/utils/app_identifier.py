import logging
from kubernetes import client

logger = logging.getLogger(__name__)


class ApplicationIdentifier:

    def __init__(self, k8s_client):

        self.k8s_client = k8s_client

    def identify_app_type(self, app_name, namespace="default"):

        try:
            if hasattr(self.k8s_client, 'batch_v1'):
                jobs = self.k8s_client.batch_v1.list_namespaced_job(namespace=namespace,
                                                                     field_selector=f"metadata.name={app_name}")
                if jobs.items:
                    return "batch"
                if hasattr(self.k8s_client, 'batch_v1beta1'):
                    cron_jobs = self.k8s_client.batch_v1beta1.list_namespaced_cron_job(
                        namespace=namespace, field_selector=f"metadata.name={app_name}")
                    if cron_jobs.items:
                        return "batch"
        except (AttributeError, Exception) as e:
            logger.debug(f"Error checking batch jobs: {e}")
        try:
            custom_objects_api = client.CustomObjectsApi()
            spark_apps = custom_objects_api.list_namespaced_custom_object(
                group="sparkoperator.k8s.io", version="v1beta2", namespace=namespace,
                plural="sparkapplications", field_selector=f"metadata.name={app_name}")
            if spark_apps.get('items', []):
                return "batch"
        except Exception as e:
            logger.debug(f"Error checking Spark applications: {e}")
        try:
            if hasattr(self.k8s_client, 'core_v1'):
                services = self.k8s_client.core_v1.list_namespaced_service(
                    namespace=namespace, field_selector=f"metadata.name={app_name}")
                if services.items:
                    return "microservice"
            if hasattr(self.k8s_client, 'networking_v1'):
                ingresses = self.k8s_client.networking_v1.list_namespaced_ingress(
                    namespace=namespace, field_selector=f"metadata.name={app_name}")
                if ingresses.items:
                    return "microservice"
        except (AttributeError, Exception) as e:
            logger.debug(f"Error checking services and ingresses: {e}")
        try:
            if hasattr(self.k8s_client, 'apps_v1'):
                deployments = self.k8s_client.apps_v1.list_namespaced_deployment(
                    namespace=namespace, field_selector=f"metadata.name={app_name}")
                if deployments.items:
                    labels = deployments.items[0].metadata.labels
                    if labels:
                        if any(k in labels for k in ['app.kubernetes.io/component', 'service', 'microservice']):
                            return "microservice"
        except (AttributeError, Exception) as e:
            logger.debug(f"Error checking deployment labels: {e}")
        logger.info(f"Could not definitively identify app type for {app_name}, defaulting to microservice")
        return "microservice"

    def get_app_characteristics(self, app_name, namespace="default"):

        app_type = self.identify_app_type(app_name, namespace)
        characteristics = {
            "app_type": app_type,
            "recurring": False,
            "stateful": False,
            "network_intensive": False,
            "memory_intensive": False,
            "cpu_intensive": False
        }

        # Check if the application is stateful
        try:
            if hasattr(self.k8s_client, 'apps_v1'):
                statefulsets = self.k8s_client.apps_v1.list_namespaced_stateful_set(
                    namespace=namespace,
                    field_selector=f"metadata.name={app_name}"
                )

                if statefulsets.items:
                    characteristics["stateful"] = True
        except (AttributeError, Exception) as e:
            logger.debug(f"Error checking if app is stateful: {e}")

        # Check if it's recurring (for batch jobs)
        if app_type == "batch":
            try:
                if hasattr(self.k8s_client, 'batch_v1beta1'):
                    cron_jobs = self.k8s_client.batch_v1beta1.list_namespaced_cron_job(
                        namespace=namespace,
                        field_selector=f"metadata.name={app_name}"
                    )

                    if cron_jobs.items:
                        characteristics["recurring"] = True
            except (AttributeError, Exception) as e:
                logger.debug(f"Error checking if batch job is recurring: {e}")

        # Try to infer resource intensiveness from labels or annotations
        try:
            if hasattr(self.k8s_client, 'apps_v1'):
                deployments = self.k8s_client.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    field_selector=f"metadata.name={app_name}"
                )

                if deployments.items:
                    labels = deployments.items[0].metadata.labels or {}
                    annotations = deployments.items[0].metadata.annotations or {
                    }

                    # Check for resource usage indicators in labels or annotations
                    if labels.get('resource-profile') == 'network-intensive' or annotations.get('resource-profile') == 'network-intensive':
                        characteristics["network_intensive"] = True

                    if labels.get('resource-profile') == 'memory-intensive' or annotations.get('resource-profile') == 'memory-intensive':
                        characteristics["memory_intensive"] = True

                    if labels.get('resource-profile') == 'cpu-intensive' or annotations.get('resource-profile') == 'cpu-intensive':
                        characteristics["cpu_intensive"] = True
        except (AttributeError, Exception) as e:
            logger.debug(f"Error checking resource intensiveness: {e}")

        return characteristics
