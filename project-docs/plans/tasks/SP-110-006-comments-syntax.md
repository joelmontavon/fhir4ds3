# Task SP-110-006: Comments Syntax - Parser Support

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Feature Implementation
**Complexity:** LOW
**Priority:** P1
**Estimated Effort:** 4-8 hours

---

## Task Description

Implement full comment syntax support in parser to achieve 100% pass rate in comments_syntax category.

## Current State

**Category:** comments_syntax
**Current Pass Rate:** 34.4% (11/32 tests passing)
**Gap:** 21 failing tests
**Impact:** +2.2% overall compliance

## Key Issues

### 1. Multi-line Comments `/* */`
- Not supported in lexer
- Comment content not ignored
- Nested comments not handled

### 2. Single-line Comments `//`
- Not supported in lexer
- Comment extends to end of line
- Not recognized in all contexts

### 3. Comment Preservation in AST
- Comments not preserved in AST
- No comment nodes in parse tree
- Comments lost during parsing

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. Comments must be handled in the lexer/parser layer.

**Exception:** Comment support requires grammar changes since comments are a lexical feature. This is one of the few cases where grammar modification is acceptable.

### Step 1: Add Comment Token Handling to Grammar
**Location:** `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4`

Add comment token definitions:
- Add `COMMENT` token for `//` single-line comments
- Add `COMMENT` token for `/* */` multi-line comments
- Configure parser to skip/ignore comments

### Step 2: Update ASTPathListener
**Location:** `fhir4ds/main/fhirpath/parser_core/fhirpath_py/ASTPathListener.py`

Ensure comments are properly ignored during AST construction:
- Skip comment tokens during parsing
- Don't create AST nodes for comments

### Step 3: Test Comment Syntax
Run compliance tests to verify:
- Test single-line comments are ignored
- Test multi-line comments are ignored
- Test comments in various positions
- Verify comments don't affect expression evaluation

## Testing Strategy

1. **Unit Tests:** Test lexer comment recognition
2. **Parser Tests:** Test parser comment handling
3. **Compliance Tests:** Run full comments_syntax suite
4. **Edge Cases:** Test comment edge cases

## Success Criteria

- [ ] All 21 comments_syntax tests passing
- [ ] Single-line comments supported
- [ ] Multi-line comments supported
- [ ] Comments properly ignored
- [ ] Comments optionally preserved
- [ ] No regressions
- [ ] Code reviewed and approved

## Dependencies

- None (can start immediately)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar (COMMENT SUPPORT IS OK HERE)
**Supporting:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/ASTPathListener.py` - AST construction
- `tests/compliance/fhirpath/` - Compliance tests

**Note:** Comment support is a lexical feature and requires grammar changes. This is an acceptable exception to the "no grammar changes" rule.

## Notes

- This is a LOW complexity task
- **EXCEPTION:** Comment support requires grammar changes (acceptable exception)
- Comments should be ignored during parsing, not preserved in AST
- Most use cases just need to ignore comments
- Test with various comment placements

## Expected Compliance Impact

**Before:** 95.6% (892/934)
**After:** 97.8% (913/934)
**Improvement:** +2.2%
