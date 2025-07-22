import logging

logger = logging.getLogger(__name__)


class ObjectiveEnforcer:
    def __init__(
        self,
        alpha=0.5,
        beta=0.5,
        performance_target=None,
        cost_target=None
    ):
        self.set_weights(alpha, beta)
        self.performance_target = performance_target
        self.cost_target = cost_target

    def set_weights(self, alpha, beta):
        # Validate and normalize weights
        if alpha < 0 or beta < 0:
            raise ValueError("Weights must be non-negative")

        # Normalize to sum to 1
        total = alpha + beta
        self.alpha = alpha / total if total > 0 else 0.5
        self.beta = beta / total if total > 0 else 0.5

        logger.info(
            f"Set objective weights: alpha={self.alpha}, beta={self.beta}")

    def get_weights(self):
        return self.alpha, self.beta

    def set_performance_target(self, target):
        self.performance_target = target
        logger.info(f"Set performance target: {target}")

    def set_cost_target(self, target):
        self.cost_target = target
        logger.info(f"Set cost target: {target}")

    def validate_performance(self, value):
        if self.performance_target is None:
            return True

        return value <= self.performance_target

    def validate_cost(self, value):
        if self.cost_target is None:
            return True

        return value <= self.cost_target


class ResourceEnforcer:
    def __init__(
        self,
        resource_limits=None,
        k8s_client=None
    ):
        self.k8s_client = k8s_client

        # Default resource limits (as fraction of total)
        self.resource_limits = resource_limits or {
            "cpu": 0.8,  # 80% of total CPU
            "memory": 0.7,  # 70% of total memory
            "network": 0.5  # 50% of network capacity
        }

        # Store absolute resource limits if available
        self.absolute_limits = {}

        if k8s_client:
            self._calculate_absolute_limits()

    def _calculate_absolute_limits(self):
        if not self.k8s_client:
            logger.warning(
                "No Kubernetes client provided, using fractional limits only")
            return

        try:
            nodes = self.k8s_client.get_nodes()

            if not nodes:
                logger.warning("No nodes found in the cluster")
                return

            # Calculate total cluster resources
            total_cpu = 0
            total_memory = 0

            for node in nodes:
                if "allocatable" in node and "cpu" in node["allocatable"]:
                    # Convert CPU string (e.g., "8") to float
                    cpu_str = node["allocatable"]["cpu"]
                    try:
                        cpu = float(cpu_str)
                        total_cpu += cpu
                    except (ValueError, TypeError):
                        # Handle case where CPU is specified with unit (e.g., "800m")
                        if cpu_str.endswith('m'):
                            try:
                                total_cpu += float(cpu_str[:-1]) / 1000
                            except (ValueError, TypeError):
                                pass

                if "allocatable" in node and "memory" in node["allocatable"]:
                    # Convert memory string (e.g., "16Gi") to bytes
                    mem_str = node["allocatable"]["memory"]
                    try:
                        if mem_str.endswith('Ki'):
                            total_memory += float(mem_str[:-2]) * 1024
                        elif mem_str.endswith('Mi'):
                            total_memory += float(mem_str[:-2]) * 1024 * 1024
                        elif mem_str.endswith('Gi'):
                            total_memory += float(mem_str[:-2]) * \
                                1024 * 1024 * 1024
                        else:
                            total_memory += float(mem_str)
                    except (ValueError, TypeError, AttributeError):
                        pass

            # Set absolute limits based on fractional limits
            self.absolute_limits = {
                "cpu": total_cpu * self.resource_limits["cpu"],
                "memory": total_memory * self.resource_limits["memory"]
            }

            logger.info(
                f"Calculated absolute resource limits: {self.absolute_limits}")

        except Exception as e:
            logger.error(f"Error calculating absolute resource limits: {e}")

    def set_resource_limits(self, limits):
        # Validate limits
        for key, value in limits.items():
            if value < 0 or value > 1:
                raise ValueError(
                    f"Resource limit for {key} must be between 0 and 1")

        self.resource_limits.update(limits)
        logger.info(f"Set resource limits: {self.resource_limits}")

        if self.k8s_client:
            self._calculate_absolute_limits()

    def set_absolute_limits(self, limits):
        self.absolute_limits.update(limits)
        logger.info(f"Set absolute resource limits: {self.absolute_limits}")

    def get_resource_limits(self):
        return self.resource_limits.copy()

    def get_absolute_limits(self):
        return self.absolute_limits.copy()

    def validate_resource_usage(self, usage):
        # If absolute limits are available, use them
        if self.absolute_limits:
            for key, limit in self.absolute_limits.items():
                if key in usage and usage[key] > limit:
                    logger.warning(
                        f"Resource usage {key}={usage[key]} exceeds limit {limit}")
                    return False

        return True

    def get_resource_safety_margin(self, usage):
        safety_margins = {}

        if self.absolute_limits:
            for key, limit in self.absolute_limits.items():
                if key in usage:
                    safety_margins[key] = max(0, (limit - usage[key]) / limit)

        return safety_margins
