# Scanning Patterns

## Debt Markers

```bash
# High-priority markers
grep -rn "FIXME\|TODO.*urgent\|TODO.*security\|TODO.*bug" --include="*.py" .

# Standard markers
grep -rn "TODO\|HACK\|XXX\|NOQA\|type: ignore" --include="*.py" .
```

## Code Smells

### Broad Exception Handling
```bash
grep -rn "except:\s*$\|except Exception:" --include="*.py" .
```

### Hardcoded Values
```bash
# Potential secrets
grep -rn "password\s*=\s*[\"']\|secret\s*=\s*[\"']\|api_key\s*=\s*[\"']" --include="*.py" .

# Hardcoded URLs/IPs
grep -rn "http://\|https://.*\(localhost\|127\.0\.0\.1\)" --include="*.py" .
```

### Magic Numbers
```bash
grep -rn "range([0-9]\{2,\})\|sleep([0-9]\{2,\})\|timeout=[0-9]\{2,\}" --include="*.py" .
```

### Print Statements (Debug Leftovers)
```bash
grep -rn "^\s*print(" --include="*.py" . | grep -v "test_\|_test\.py"
```

### Mutable Default Arguments
```bash
grep -rn "def.*=\s*\[\]\|def.*=\s*{}" --include="*.py" .
```

## Complexity Indicators

### Long Files
```bash
find . -name "*.py" -not -path "*/migrations/*" -exec wc -l {} + | awk '$1 > 500 {print}'
```

### Long Functions (approximate)
```bash
# Files with potentially long functions - review manually
grep -l "def \|async def " --include="*.py" -r . | xargs -I {} sh -c 'echo "=== {} ===" && grep -n "def \|async def " {}'
```

### Deep Nesting
```bash
# Lines with deep indentation (>4 levels = 16+ spaces)
grep -rn "^                " --include="*.py" .
```

## Django-Specific

```bash
# N+1 query indicators (missing select_related/prefetch_related)
grep -rn "\.objects\.\(all\|filter\|get\)(" --include="*.py" . | grep -v "select_related\|prefetch_related"

# Raw SQL (potential injection)
grep -rn "\.raw(\|\.extra(\|cursor\.execute(" --include="*.py" .

# Deprecated patterns
grep -rn "from django.utils.encoding import smart_text\|from django.conf.urls import url" --include="*.py" .

# Missing migrations indicator
grep -rn "class Meta:" --include="models.py" -A2 | grep -v "managed = False"
```

## Flask-Specific

```bash
# Debug mode in production code
grep -rn "app\.run(.*debug=True\|DEBUG\s*=\s*True" --include="*.py" .

# Missing CSRF protection
grep -rn "@app\.route.*methods.*POST" --include="*.py" .
```

## FastAPI-Specific

```bash
# Sync functions in async context (blocking)
grep -rn "def \w\+(" --include="*.py" . | grep -v "async def\|__init__\|__"

# Missing response_model
grep -rn "@app\.\(get\|post\|put\|delete\)(" --include="*.py" . | grep -v "response_model"
```

## Python Anti-Patterns

```bash
# Star imports
grep -rn "from .* import \*" --include="*.py" .

# Global keyword
grep -rn "^\s*global " --include="*.py" .

# Assert in production code (disabled with -O)
grep -rn "^\s*assert " --include="*.py" . | grep -v "test_\|_test\.py\|conftest"

# String formatting with % (prefer f-strings)
grep -rn '"\s*%\s*(\|'\''\s*%\s*(' --include="*.py" .

# Nested functions > 2 levels
grep -rn "def .*:$" --include="*.py" -A 20 | grep -E "^\s{8,}def "
```

## Test Coverage Gaps

```bash
# Files without corresponding tests
for f in $(find . -name "*.py" -not -path "*/test*" -not -name "test_*" -not -path "*/migrations/*"); do
  base=$(basename "$f" .py)
  if ! find . -name "test_${base}.py" -o -name "${base}_test.py" | grep -q .; then
    echo "No test file for: $f"
  fi
done
```

## Radon Thresholds (if available)

```bash
# Show only complex functions (C grade or worse)
radon cc . -a -s -n C

# Maintainability index (A=best, C+=needs attention)
radon mi . -s -n B
```
