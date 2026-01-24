# Run Full Test Suite

**Primary Agent**: oh-my-claudecode:qa-tester
**Supporting Agents**: oh-my-claudecode:build-fixer, oh-my-claudecode:code-reviewer, oh-my-claudecode:architect
**Situation**: Execute comprehensive testing across all FHIR4DS components

Execute the complete FHIR4DS test suite and compliance validation:

**Specification Compliance Testing:**
1. **FHIRPath R4 Tests:**
   - Execute: `python tests/official/fhirpath/fhirpath_r4_test_runner.py`
   - Target: Progress toward 100% compliance from current 0.9%
   - Report pass rates and specific failures

2. **SQL-on-FHIR Tests:**
   - Execute: `python tests/run_tests.py --dialect all`
   - Target: Maintain 100% compliance
   - Verify ViewDefinition processing integrity

3. **CQL Framework Tests:**
   - Execute available CQL test suites
   - Target: Progress toward 100% compliance from current 59.2%
   - Focus on translation layer accuracy

4. **Quality Measure Tests:**
   - Run eCQI framework compliance tests
   - Validate measure calculation accuracy
   - Test population-scale performance

**Multi-Database Validation:**
1. **DuckDB Environment:**
   - Run full test suite with DuckDB backend
   - Measure performance characteristics
   - Validate JSON operation efficiency

2. **PostgreSQL Environment:**
   - Run identical tests with PostgreSQL backend
   - Compare performance metrics with DuckDB
   - Ensure feature parity and identical results

**Architecture Compliance Testing:**
1. **Thin Dialect Validation:**
   - Verify no business logic in dialect implementations
   - Confirm only syntax differences between databases
   - Test dialect method overriding patterns

2. **Population-First Design:**
   - Validate population-scale query generation
   - Test CTE-first SQL generation approach
   - Measure performance vs row-by-row alternatives

3. **Unified FHIRPath Execution:**
   - Confirm single execution path for all specifications
   - Test SQL-on-FHIR → FHIRPath translation
   - Validate CQL → FHIRPath translation accuracy

**Performance Benchmarking:**
1. **Population Scale Tests:**
   - 1M patient FHIRPath expression evaluation
   - Complex CQL measure calculation performance
   - Monolithic vs individual query comparison

2. **Memory and Resource Usage:**
   - Monitor memory consumption patterns
   - Validate resource cleanup
   - Test concurrent execution capabilities

**Reporting:**
1. **Compliance Metrics:**
   - Current vs target compliance percentages
   - Regression analysis from previous runs
   - Specific test failures requiring attention

2. **Performance Results:**
   - Query execution times and memory usage
   - Database optimization effectiveness
   - Population vs row-by-row performance gains

3. **Architecture Validation:**
   - Confirm adherence to all architectural principles
   - Identify any violations requiring remediation
   - Document architectural integrity status

**Recommendations:**
Provide specific action items to address any failures, performance issues, or architectural violations discovered during testing.

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Comprehensive QA testing | `oh-my-claudecode:qa-tester` | sonnet |
| Production-ready QA | `oh-my-claudecode:qa-tester-high` | opus |
| Build error investigation | `oh-my-claudecode:build-fixer` | sonnet |
| Simple build fixes | `oh-my-claudecode:build-fixer-low` | haiku |
| Code quality review | `oh-my-claudecode:code-reviewer` | opus |
| Quick code checks | `oh-my-claudecode:code-reviewer-low` | haiku |
| Architecture verification | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
