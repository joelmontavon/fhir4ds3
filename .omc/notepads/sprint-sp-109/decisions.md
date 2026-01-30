# Sprint SP-109 Decisions

## Strategic Decisions

### 1. Sprint Scope
**Decision**: Focus on the 4 high-impact categories (P0) to achieve 90%+ compliance
**Rationale**:
- P0 categories represent 28% potential gain (263 tests)
- Quick wins (P2) add 2% more (20 tests)
- Total achievable: ~93% compliance
- Defer lowest-priority items to SP-110

### 2. Implementation Order
**Decision**: Tackle categories in order of architectural dependencies
**Rationale**:
1. Type Functions (foundation for comparisons)
2. Arithmetic Operators (precedence fixes)
3. Function Calls (registry improvements)
4. Collection Functions (most complex, depends on others)

### 3. Parallel Execution Strategy
**Decision**: Use Ultrapilot with 5 workers for parallel implementation
**Rationale**:
- Independent categories can be worked in parallel
- Estimated 14-19 hours vs 72-94 hours sequential
- Proven effective in SP-108

### 4. Testing Strategy
**Decision**: Continuous testing after each task
**Rationale**:
- Catch regressions early
- Verify fixes work as expected
- Maintain sprint velocity

## Technical Decisions

### 1. CTE Column Preservation
**Decision**: Implement comprehensive column tracking in CTE builder
**Approach**:
- Track all intermediate columns through CTE chain
- Preserve columns needed by subsequent operations
- Implement column dependency analysis

### 2. Type System Enhancements
**Decision**: Extend type system for negative numbers and temporal types
**Approach**:
- Fix unary polarity operator precedence in parser
- Implement temporal type compatibility matrix
- Add Quantity unit conversion support

### 3. Function Registry
**Decision**: Implement proper function signature resolution
**Approach**:
- Create function signature registry
- Implement parameter type coercion
- Add validation for single-value constraints

### 4. Lambda Variables
**Decision**: Improve lambda variable scope handling
**Approach**:
- Track lambda variable context through CTE chain
- Implement proper scope nesting
- Handle edge cases in nested expressions

## Risk Mitigation Decisions

### 1. High-Risk Categories
**Decision**: Start with lower-risk categories to build momentum
**Rationale**:
- Type functions and arithmetic are lower risk
- Build confidence before tackling complex collection functions
- Learn from earlier tasks for later ones

### 2. Regression Prevention
**Decision**: Implement comprehensive testing after each fix
**Approach**:
- Run full compliance suite after each task
- Check for regressions in passing categories
- Document any side effects

### 3. Architecture Alignment
**Decision**: Maintain unified FHIRPath architecture principles
**Approach**:
- Business logic in translator, not dialects
- CTE-first design for all operations
- Population-scale optimization maintained

## Success Criteria

### Minimum Viable Sprint
- [ ] Achieve 90%+ compliance (840+ tests passing)
- [ ] All P0 categories at 85%+ or complete
- [ ] No regressions in currently passing tests
- [ ] Code passes architect review

### Stretch Goals
- [ ] Achieve 95%+ compliance (887+ tests passing)
- [ ] All P0 categories at 95%+
- [ ] Quick wins (P2) completed
- [ ] Ready for final push to 100% in SP-110

## Definition of Done

For each task:
- [ ] All tests in category passing (or target percentage reached)
- [ ] Code reviewed and approved
- [ ] No regressions in other categories
- [ ] Compliance report shows improvement
- [ ] Both DuckDB and PostgreSQL tests passing

For sprint:
- [ ] All planned tasks complete
- [ ] Full compliance suite passing at expected level
- [ ] Code reviewed and approved
- [ ] Ready to merge to main
- [ ] Sprint documentation complete
