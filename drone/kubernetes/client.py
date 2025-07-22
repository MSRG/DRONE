import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)


class KubernetesClient:
    def __init__(self, namespace="default", in_cluster=False):
        self.namespace = namespace
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.configured = True
        except Exception as e:
            logger.error(f"Error configuring Kubernetes client: {e}")
            self.configured = False

    def apply_resource_action(self, app_name, cpu, memory, replicas=None, node_affinities=None):
        if not self.configured:
            logger.error("Kubernetes client not properly configured")
            return False
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace=self.namespace,
                                                                   field_selector=f"metadata.name={app_name}")
            if deployments.items:
                return self._update_deployment(deployments.items[0],
                    cpu,
                    memory,
                    replicas,
                    node_affinities
                )

            # Try to find StatefulSet
            statefulsets = self.apps_v1.list_namespaced_stateful_set(
                namespace=self.namespace,
                field_selector=f"metadata.name={app_name}"
            )

            if statefulsets.items:
                return self._update_statefulset(
                    statefulsets.items[0],
                    cpu,
                    memory,
                    replicas,
                    node_affinities
                )

            logger.error(f"No Deployment or StatefulSet found for {app_name}")
            return False

        except Exception as e:
            logger.error(f"Error applying resource action: {e}")
            return False

    def _update_deployment(
        self,
        deployment,
        cpu,
        memory,
        replicas=None,
        node_affinities=None
    ):
        try:
            # Update resource requests and limits
            for container in deployment.spec.template.spec.containers:
                if not container.resources:
                    container.resources = client.V1ResourceRequirements()

                if not container.resources.requests:
                    container.resources.requests = {}

                if not container.resources.limits:
                    container.resources.limits = {}

                container.resources.requests["cpu"] = str(cpu)
                container.resources.limits["cpu"] = str(
                    cpu * 1.2)  # 20% buffer

                container.resources.requests["memory"] = memory
                container.resources.limits["memory"] = memory

            # Update replicas if specified
            if replicas is not None:
                deployment.spec.replicas = replicas

            # Update node affinities if specified
            if node_affinities:
                if not deployment.spec.template.spec.affinity:
                    deployment.spec.template.spec.affinity = client.V1Affinity()

                if not deployment.spec.template.spec.affinity.node_affinity:
                    deployment.spec.template.spec.affinity.node_affinity = client.V1NodeAffinity()

                # Build required node affinities
                preferred_terms = []
                for zone, nodes in node_affinities.items():
                    term = client.V1PreferredSchedulingTerm(
                        weight=10,
                        preference=client.V1NodeSelectorTerm(
                            match_expressions=[
                                client.V1NodeSelectorRequirement(
                                    key="kubernetes.io/hostname",
                                    operator="In",
                                    values=nodes
                                )
                            ]
                        )
                    )
                    preferred_terms.append(term)

                deployment.spec.template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution = preferred_terms

            # Update the Deployment
            self.apps_v1.replace_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=self.namespace,
                body=deployment
            )

            return True

        except Exception as e:
            logger.error(f"Error updating Deployment: {e}")
            return False

    def _update_statefulset(
        self,
        statefulset,
        cpu,
        memory,
        replicas=None,
        node_affinities=None
    ):
        try:
            # Update resource requests and limits
            for container in statefulset.spec.template.spec.containers:
                if not container.resources:
                    container.resources = client.V1ResourceRequirements()

                if not container.resources.requests:
                    container.resources.requests = {}

                if not container.resources.limits:
                    container.resources.limits = {}

                container.resources.requests["cpu"] = str(cpu)
                container.resources.limits["cpu"] = str(
                    cpu * 1.2)  # 20% buffer

                container.resources.requests["memory"] = memory
                container.resources.limits["memory"] = memory

            # Update replicas if specified
            if replicas is not None:
                statefulset.spec.replicas = replicas

            # Update node affinities if specified
            if node_affinities:
                if not statefulset.spec.template.spec.affinity:
                    statefulset.spec.template.spec.affinity = client.V1Affinity()

                if not statefulset.spec.template.spec.affinity.node_affinity:
                    statefulset.spec.template.spec.affinity.node_affinity = client.V1NodeAffinity()

                # Build required node affinities
                preferred_terms = []
                for zone, nodes in node_affinities.items():
                    term = client.V1PreferredSchedulingTerm(
                        weight=10,
                        preference=client.V1NodeSelectorTerm(
                            match_expressions=[
                                client.V1NodeSelectorRequirement(
                                    key="kubernetes.io/hostname",
                                    operator="In",
                                    values=nodes
                                )
                            ]
                        )
                    )
                    preferred_terms.append(term)

                statefulset.spec.template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution = preferred_terms

            # Update the StatefulSet
            self.apps_v1.replace_namespaced_stateful_set(
                name=statefulset.metadata.name,
                namespace=self.namespace,
                body=statefulset
            )

            return True

        except Exception as e:
            logger.error(f"Error updating StatefulSet: {e}")
            return False

    def get_current_resources(self, app_name):
        if not self.configured:
            logger.error("Kubernetes client not properly configured")
            return {}

        try:
            # Try to find Deployment
            deployments = self.apps_v1.list_namespaced_deployment(
                namespace=self.namespace,
                field_selector=f"metadata.name={app_name}"
            )

            if deployments.items:
                return self._extract_resources(deployments.items[0])

            # Try to find StatefulSet
            statefulsets = self.apps_v1.list_namespaced_stateful_set(
                namespace=self.namespace,
                field_selector=f"metadata.name={app_name}"
            )

            if statefulsets.items:
                return self._extract_resources(statefulsets.items[0])

            logger.error(f"No Deployment or StatefulSet found for {app_name}")
            return {}

        except Exception as e:
            logger.error(f"Error getting current resources: {e}")
            return {}

    def _extract_resources(self, resource):
        result = {
            "replicas": resource.spec.replicas
        }

        # Aggregate resources from all containers
        total_cpu = 0.0
        total_memory = 0.0
        
        for container in resource.spec.template.spec.containers:
            if container.resources and container.resources.requests:
                if "cpu" in container.resources.requests:
                    cpu_str = container.resources.requests["cpu"]
                    # Parse CPU value (e.g., "100m" -> 0.1, "1" -> 1.0)
                    try:
                        if cpu_str.endswith('m'):
                            total_cpu += float(cpu_str[:-1]) / 1000
                        else:
                            total_cpu += float(cpu_str)
                    except ValueError:
                        pass

                if "memory" in container.resources.requests:
                    mem_str = container.resources.requests["memory"]
                    # Parse memory value to Mi
                    try:
                        if mem_str.endswith('Mi'):
                            total_memory += float(mem_str[:-2])
                        elif mem_str.endswith('Gi'):
                            total_memory += float(mem_str[:-2]) * 1024
                        elif mem_str.endswith('Ki'):
                            total_memory += float(mem_str[:-2]) / 1024
                        else:
                            # Assume bytes
                            total_memory += float(mem_str) / (1024 * 1024)
                    except ValueError:
                        pass
        
        # Set aggregated values
        result["cpu"] = total_cpu if total_cpu > 0 else 0.5  # Default to 0.5 CPU
        result["memory"] = f"{int(total_memory)}Mi" if total_memory > 0 else "512Mi"  # Default to 512Mi

        # Extract node affinities if present
        if (resource.spec.template.spec.affinity and
            resource.spec.template.spec.affinity.node_affinity and
                resource.spec.template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution):

            result["node_affinities"] = {}
            for term in resource.spec.template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution:
                for expr in term.preference.match_expressions:
                    if expr.key == "kubernetes.io/hostname":
                        result["node_affinities"][f"zone_{len(result['node_affinities'])+1}"] = expr.values

        return result

    def get_nodes(self):
        if not self.configured:
            logger.error("Kubernetes client not properly configured")
            return []

        try:
            nodes = self.core_v1.list_node()
            result = []

            for node in nodes.items:
                node_info = {
                    "name": node.metadata.name,
                    "labels": node.metadata.labels,
                    "allocatable": node.status.allocatable,
                    "capacity": node.status.capacity
                }

                result.append(node_info)

            return result

        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return []
