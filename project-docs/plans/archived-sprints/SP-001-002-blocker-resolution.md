# SP-001-002 Blocker Resolution

**Date**: 27-09-2025
**Issue**: Missing Source Code for Unit Test Development
**Reporter**: Junior Developer
**Status**: **CRITICAL BLOCKER** - Requires Immediate Senior Solution Architect/Engineer Decision

---

## Issue Description

The junior developer has identified a critical blocker for SP-001-002 (Unit Test Framework Implementation):

**Problem**: The main `fhir4ds/` directory is empty, but there is a complete codebase located in `archive/fhir4ds/`

**Impact**: Cannot proceed with unit test development without access to the FHIRPath parser source code

---

## Current Directory Structure Analysis

### Main fhir4ds Directory
```
fhir4ds/
└── (empty)
```

### Archive fhir4ds Directory
```
archive/fhir4ds/
├── __init__.py
├── config.py
├── cql/
├── cte_pipeline/
├── datastore/
├── dialects/
├── fhir/
├── fhirpath/          ← FHIRPath parser components here
├── helpers/
├── pipeline/
├── server/
├── terminology/
├── utils/
└── view_runner.py
```

**Analysis**: The archive contains a complete, mature FHIR4DS implementation with extensive FHIRPath functionality.

---

## Architectural Decision Required

### Option 1: Use Archive Code as Current Codebase
**Approach**: Move archive code to main fhir4ds directory
**Pros**:
- Complete, functional codebase available immediately
- Extensive FHIRPath implementation for testing
- Mature architecture and features

**Cons**:
- May conflict with PEP-001's goal of building testing infrastructure from scratch
- Large, complex codebase may not align with current sprint scope

### Option 2: Create Minimal FHIRPath Components for Testing
**Approach**: Create basic FHIRPath parser stubs in main fhir4ds directory
**Pros**:
- Aligns with incremental development approach
- Simpler scope for initial testing framework

**Cons**:
- Significant development effort to create parser components
- May delay sprint objectives

### Option 3: Test Framework with Mock Components
**Approach**: Use mocks/stubs for FHIRPath components while building test framework
**Pros**:
- Can proceed with testing infrastructure development
- Framework ready when actual components available

**Cons**:
- Limited value for specification compliance testing
- May not provide realistic testing patterns

---

## Recommendation

Based on the sprint goals and PEP-001 objectives, I recommend **Option 1: Use Archive Code as Current Codebase**.

### Rationale
1. **Sprint Efficiency**: Enables immediate progress on testing infrastructure
2. **Realistic Testing**: Provides actual FHIRPath implementation for meaningful unit tests
3. **Specification Compliance**: Archive code likely has existing FHIRPath functionality to test against official specifications
4. **Architecture Alignment**: Testing infrastructure can validate real implementation

### Implementation Plan
1. **Move Archive Code**: Copy `archive/fhir4ds/*` to `fhir4ds/`
2. **Update Task Scope**: Modify SP-001-002 to test existing FHIRPath components
3. **Validate Functionality**: Ensure copied code is functional and testable
4. **Continue Sprint**: Proceed with unit test development against real codebase

---

## Required Senior Solution Architect/Engineer Decision

**Question**: Should we move the archive code to the main fhir4ds directory to enable unit testing development?

**Urgency**: **CRITICAL** - Sprint 001 progress blocked until resolved

**Dependencies**:
- SP-001-002 cannot proceed without source code access
- SP-001-003 (Official test integration) depends on SP-001-002
- Overall sprint success at risk

---

## Alternative Sprint Adjustment

If archive code should not be used, we need to adjust Sprint 001 scope:

### Modified Sprint Goals
1. **Test Infrastructure Only**: Focus on framework without actual component testing
2. **Mock-Based Testing**: Create test framework using mocks
3. **Documentation Focus**: Enhance testing documentation and patterns
4. **Defer Unit Testing**: Move actual unit test implementation to future sprint

---

**Awaiting Senior Solution Architect/Engineer decision on how to proceed.**

---

**Created**: 27-09-2025 by Junior Developer issue escalation
**Priority**: **CRITICAL BLOCKER**
**Next Action Required**: Senior Solution Architect/Engineer decision