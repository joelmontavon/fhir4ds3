# FHIRPath Performance Monitoring System

## Overview

The FHIRPath Performance Monitoring System provides comprehensive performance monitoring, profiling, and optimization capabilities for the FHIRPath evaluation pipeline. This system is designed to support population-scale healthcare analytics with minimal overhead while providing actionable insights for system optimization.

## Components

### 1. Performance Monitor (`monitor.py`)

The core performance monitoring system that captures metrics with minimal overhead.

**Key Features:**
- Configurable monitoring levels (disabled, basic, detailed, profiling)
- Real-time metrics collection with <2% overhead
- Memory usage tracking (optional with psutil)
- Component-level performance tracking
- Alert system with configurable thresholds
- Thread-safe operation for concurrent evaluation

**Basic Usage:**
```python
from fhir4ds.fhirpath.performance import PerformanceMonitor, MonitoringConfig

# Create monitor with custom configuration
config = MonitoringConfig(
    level=MonitoringLevel.BASIC,
    sample_rate=1.0,  # Monitor 100% of operations
    enable_memory_tracking=True
)
monitor = PerformanceMonitor(config)

# Monitor an operation
with monitor.monitor_operation("fhirpath_evaluation") as op_id:
    # Your code here
    result = evaluate_expression(expression, data)

    # Optionally record component metrics
    monitor.record_component_metric(op_id, "parser", 15.5)

# Get current metrics
metrics = monitor.get_current_metrics()
print(f"Average duration: {metrics['avg_duration_ms']}ms")
```

**Global Monitor:**
```python
from fhir4ds.fhirpath.performance import monitor

# Use global monitor with context manager
with monitor("my_operation") as op_id:
    # Your code here
    pass
```

### 2. FHIRPath Profiler (`profiler.py`)

Detailed profiling system for evaluation pipeline components.

**Key Features:**
- Component-level profiling (parsing, evaluation, type operations, database operations)
- Call stack tracking for nested operations
- Optimization suggestions based on profiling data
- Bottleneck identification
- Optional cProfile integration for detailed call graphs

**Basic Usage:**
```python
from fhir4ds.fhirpath.performance import FHIRPathProfiler, ProfilerConfig

# Create profiler
config = ProfilerConfig(
    profile_sample_rate=0.1,  # Profile 10% of operations
    save_detailed_profiles=True
)
profiler = FHIRPathProfiler(config)

# Profile an operation
with profiler.profile_operation("expression_evaluation") as session_id:
    # Profile individual components
    with profiler.profile_component(session_id, "parser"):
        parse_result = parse_expression(expression)

    with profiler.profile_component(session_id, "evaluator"):
        result = evaluate_parsed(parse_result, data)

# Get profiling summary
summary = profiler.get_profile_summary()
print(f"Top bottlenecks: {summary['top_bottlenecks']}")
print(f"Optimization opportunities: {summary['optimization_opportunities']}")
```

### 3. Metrics Collector (`metrics.py`)

Comprehensive metrics collection and analysis system.

**Key Features:**
- Unified metrics from monitor and profiler
- Statistical analysis (mean, median, percentiles)
- Trend analysis over time
- Performance regression detection
- Automated bottleneck detection
- Severity classification and impact scoring

**Basic Usage:**
```python
from fhir4ds.fhirpath.performance import (
    MetricsCollector, BottleneckDetector, MetricsAnalyzer
)

# Create metrics collector
collector = MetricsCollector(monitor, profiler)

# Collect current metrics
collector.collect_metrics()

# Generate summary
summary = collector.generate_summary(hours=24)
print(f"Operations in last 24h: {summary.total_operations}")
print(f"P95 duration: {summary.p95_duration_ms}ms")

# Analyze trends
trends = collector.get_trend_analysis(hours=24)
print(f"Performance trend: {trends['trend_direction']}")

# Detect bottlenecks
detector = BottleneckDetector(collector)
bottlenecks = detector.detect_bottlenecks()
for bottleneck in bottlenecks:
    print(f"Bottleneck: {bottleneck.component} ({bottleneck.severity})")
    print(f"  Recommendations: {bottleneck.recommendations}")

# Generate comprehensive report
analyzer = MetricsAnalyzer(collector, detector)
report = analyzer.generate_performance_report(hours=24)
print(f"Compliance status: {report.compliance_status}")
```

### 4. Performance Dashboard (`dashboard.py`)

Unified dashboard interface for monitoring system health.

**Key Features:**
- Real-time system health monitoring
- Comprehensive performance reports
- Component breakdown analysis
- Health scoring (0-100)
- Status classification (excellent, good, fair, poor, critical)
- Export capabilities (JSON)

**Basic Usage:**
```python
from fhir4ds.fhirpath.performance import PerformanceDashboard, get_global_dashboard

# Get global dashboard
dashboard = get_global_dashboard()

# Check current status
status = dashboard.get_current_status()
print(f"Health score: {status['health_score']}/100")
print(f"Status: {status['status']}")
print(f"Active bottlenecks: {status['active_bottlenecks']}")

# Generate performance report
report = dashboard.generate_performance_report(hours=24)
print(f"Total operations: {report['summary']['total_operations']}")
print(f"Average duration: {report['summary']['avg_duration_ms']}ms")

# Get health check
health = dashboard.get_health_check()
print(f"Overall status: {health['overall_status']}")
for check_name, check_result in health['checks'].items():
    print(f"  {check_name}: {check_result['status']}")

# Export dashboard data
exported = dashboard.export_dashboard_data(format='json')
with open('performance_report.json', 'w') as f:
    f.write(exported)
```

## Integration with FHIRPath Evaluator

The performance monitoring system is automatically integrated with the FHIRPath evaluation engine:

```python
from fhir4ds.fhirpath.evaluator import FHIRPathEvaluationEngine
from fhir4ds.fhirpath.performance import (
    PerformanceMonitor, MonitoringConfig,
    FHIRPathProfiler, ProfilerConfig
)

# Create custom monitor and profiler
monitor = PerformanceMonitor(MonitoringConfig(level=MonitoringLevel.DETAILED))
profiler = FHIRPathProfiler(ProfilerConfig(profile_sample_rate=1.0))

# Create engine with performance monitoring
engine = FHIRPathEvaluationEngine(
    performance_monitor=monitor,
    profiler=profiler
)

# Evaluation automatically includes performance monitoring
result = engine.evaluate(ast_node, context)

# Access performance metrics
metrics = monitor.get_current_metrics()
profile_summary = profiler.get_profile_summary()
```

## Configuration

### Monitoring Levels

- **DISABLED**: No monitoring
- **BASIC**: Basic timing and memory tracking (~0.1ms overhead)
- **DETAILED**: Component-level metrics (~0.5ms overhead)
- **PROFILING**: Full profiling with call traces (~1.0ms overhead)

### Alert Thresholds

Default thresholds can be customized:

```python
config = MonitoringConfig(
    alert_thresholds={
        'evaluation_time_ms': 100.0,      # Alert if evaluation > 100ms
        'memory_usage_mb': 100.0,         # Alert if memory delta > 100MB
        'collection_operation_time_ms': 50.0
    }
)
```

### Sampling Rate

Control how many operations are monitored/profiled:

```python
# Monitor 100% of operations
monitor_config = MonitoringConfig(sample_rate=1.0)

# Profile 10% of operations (reduces overhead)
profiler_config = ProfilerConfig(profile_sample_rate=0.1)
```

## Performance Considerations

### Overhead

The monitoring system is designed for minimal overhead:

- **Basic monitoring**: <2% overhead (typically 0.1ms per operation)
- **Detailed profiling**: ~1-2% overhead with sampling
- **Memory tracking**: Requires psutil, adds ~0.5ms per operation

### Memory Usage

- Metrics history: Limited to configurable size (default 1000 entries)
- Profile results: Limited to 100 recent profiles
- Thread-safe with locks for concurrent access

### Scaling

The system is designed for population-scale analytics:

- Efficient data structures (deques with maxlen)
- Sampling capabilities to reduce overhead
- Configurable detail levels
- Thread-safe for concurrent evaluation

## Best Practices

### 1. Use Appropriate Monitoring Level

```python
# Development: Detailed profiling
config = MonitoringConfig(level=MonitoringLevel.DETAILED)

# Production: Basic monitoring with sampling
config = MonitoringConfig(
    level=MonitoringLevel.BASIC,
    sample_rate=0.1  # Monitor 10% of operations
)
```

### 2. Leverage Sampling

```python
# Profile expensive operations less frequently
profiler_config = ProfilerConfig(
    profile_sample_rate=0.05,  # Profile 5% of operations
    save_detailed_profiles=False  # Disable cProfile for overhead
)
```

### 3. Regular Metrics Collection

```python
import schedule

def collect_and_report():
    collector.collect_metrics()
    report = analyzer.generate_performance_report(hours=1)
    # Send report or alert if needed

# Collect metrics every hour
schedule.every(1).hour.do(collect_and_report)
```

### 4. Monitor Health Status

```python
dashboard = get_global_dashboard()
health = dashboard.get_health_check()

if health['overall_status'] == 'unhealthy':
    # Alert or take action
    logger.warning(f"System health degraded: {health['health_score']}/100")
    for check_name, check_result in health['checks'].items():
        if check_result['status'] == 'unhealthy':
            logger.error(f"Failed check: {check_name} - {check_result['details']}")
```

### 5. Act on Bottlenecks

```python
detector = BottleneckDetector(collector)
bottlenecks = detector.detect_bottlenecks()

critical_bottlenecks = [b for b in bottlenecks if b.severity == 'critical']
if critical_bottlenecks:
    logger.critical(f"Critical bottlenecks detected: {len(critical_bottlenecks)}")
    for bottleneck in critical_bottlenecks:
        logger.critical(f"  {bottleneck.component}: {bottleneck.description}")
        for rec in bottleneck.recommendations:
            logger.info(f"    Recommendation: {rec}")
```

## Testing

Comprehensive test suite with 93%+ test coverage:

```bash
# Run all performance monitoring tests
pytest tests/unit/fhirpath/performance/ -v

# Run specific test module
pytest tests/unit/fhirpath/performance/test_monitor.py -v
pytest tests/unit/fhirpath/performance/test_profiler.py -v
pytest tests/unit/fhirpath/performance/test_metrics.py -v

# Check coverage
pytest tests/unit/fhirpath/performance/ --cov=fhir4ds.fhirpath.performance
```

## Database Compatibility

The performance monitoring system is database-agnostic and works with:

- **DuckDB**: Embedded analytics and development
- **PostgreSQL**: Production deployments
- Any database dialect supported by FHIR4DS

## Future Enhancements

Potential future improvements:

1. **Real-time Dashboard**: Web-based real-time monitoring interface
2. **Predictive Analytics**: ML-based performance prediction
3. **Auto-optimization**: Automatic query optimization based on profiling
4. **Distributed Monitoring**: Support for multi-node deployments
5. **Historical Analysis**: Long-term performance trends and regression detection
6. **Integration with APM Tools**: Support for DataDog, New Relic, etc.

## Troubleshooting

### High Overhead

If monitoring overhead is too high:

```python
# Reduce monitoring level
config = MonitoringConfig(level=MonitoringLevel.BASIC)

# Increase sampling rate
config.sample_rate = 0.1  # Monitor only 10%

# Disable memory tracking
config.enable_memory_tracking = False
```

### Missing Metrics

If no metrics are collected:

```python
# Check if monitoring is enabled
assert monitor.config.enabled == True

# Check sampling rate
assert monitor.config.sample_rate > 0

# Manually collect metrics
collector.collect_metrics()
```

### Memory Issues

If memory usage is high:

```python
# Reduce history size
config = MonitoringConfig(max_history_size=100)

# Regular metrics reset
monitor.reset_metrics()
```

## Architecture Alignment

This performance monitoring system aligns with FHIR4DS unified architecture:

- **No Business Logic in Dialects**: All monitoring logic is in the core engine
- **Population-First**: Designed for population-scale analytics monitoring
- **CTE-First Compatible**: Monitors CTE generation and execution
- **Database-Agnostic**: Works with all supported database dialects
- **Specification Compliant**: Maintains FHIRPath specification compliance

## Support

For issues or questions:

1. Check test suite for usage examples
2. Review inline code documentation
3. Consult FHIR4DS architecture documentation
4. File issues in project repository

---

**Version**: 1.0.0
**Last Updated**: September 29, 2025
**Status**: Production Ready