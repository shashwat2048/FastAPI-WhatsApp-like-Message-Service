"""
Prometheus-style metrics helpers.
"""
from typing import Dict, Optional, Tuple
from collections import defaultdict
import time


class MetricsCollector:
    """Simple metrics collector for Prometheus-style metrics."""
    
    def __init__(self):
        # Counters: metric_name -> {(label_key, label_value): count}
        self.counters: Dict[str, Dict[Tuple[str, ...], float]] = defaultdict(lambda: defaultdict(float))
        # Histogram: metric_name -> {(label_key, label_value): [values]}
        self.histograms: Dict[str, Dict[Tuple[str, ...], list]] = defaultdict(lambda: defaultdict(list))
        self.start_time = time.time()
    
    def _build_label_key(self, labels: Optional[Dict[str, str]] = None) -> Tuple[str, ...]:
        """Build a tuple key from labels dict for hashing."""
        if not labels:
            return tuple()
        return tuple(sorted(labels.items()))
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment a counter metric."""
        label_key = self._build_label_key(labels)
        self.counters[name][label_key] += value
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation."""
        label_key = self._build_label_key(labels)
        self.histograms[name][label_key].append(value)
    
    def get_metrics(self) -> str:
        """
        Generate Prometheus-style metrics output in text/plain format.
        
        Returns:
            String in Prometheus exposition format (text/plain)
        """
        lines = []
        
        # Format counters
        for metric_name in sorted(self.counters.keys()):
            for label_key, value in sorted(self.counters[metric_name].items()):
                if label_key:
                    # Build label string from tuple
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                    lines.append(f"{metric_name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{metric_name} {value}")
        
        # Format histograms (as summary with count and sum)
        for metric_name in sorted(self.histograms.keys()):
            for label_key, values in sorted(self.histograms[metric_name].items()):
                count = len(values)
                sum_value = sum(values)
                
                if label_key:
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                    lines.append(f"{metric_name}_count{{{label_str}}} {count}")
                    lines.append(f"{metric_name}_sum{{{label_str}}} {sum_value}")
                else:
                    lines.append(f"{metric_name}_count {count}")
                    lines.append(f"{metric_name}_sum {sum_value}")
        
        return "\n".join(lines) + "\n"


# Global metrics instance
metrics = MetricsCollector()


def record_http_request(path: str, status: int):
    """
    Record an HTTP request metric.
    
    Args:
        path: Request path
        status: HTTP status code
    """
    metrics.increment_counter(
        "http_requests_total",
        labels={"path": path, "status": str(status)}
    )


def record_webhook_request(result: str):
    """
    Record a webhook request metric.
    
    Args:
        result: One of "created", "duplicate", "invalid_signature", "validation_error"
    """
    metrics.increment_counter(
        "webhook_requests_total",
        labels={"result": result}
    )


def record_latency(latency_ms: float, labels: Optional[Dict[str, str]] = None):
    """
    Record a latency observation.
    
    Args:
        latency_ms: Latency in milliseconds
        labels: Optional labels for the metric
    """
    metrics.observe_histogram(
        "http_request_latency_ms",
        latency_ms,
        labels=labels
    )


def get_metrics() -> str:
    """
    Get Prometheus-style metrics output.
    
    Returns:
        String in Prometheus exposition format (text/plain)
    """
    return metrics.get_metrics()

