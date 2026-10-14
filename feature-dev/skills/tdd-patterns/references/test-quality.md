# Test quality examples

Each pair shows a test that passes RED and mutation proof but proves little, then the fix. The rules are in `SKILL.md` § Test Quality.

Adapted from the TDD guidance in [mattpocock/skills](https://github.com/mattpocock/skills) (MIT, Copyright (c) 2026 Matt Pocock).

## Expected value from a literal, not from the code

pytest:

```python
# Tautology: the expected value is computed by the function under test's own helper.
def test_invoice_total():
    invoice = make_invoice(lines=[(2, Decimal("10.00")), (1, Decimal("5.00"))])
    assert invoice.total() == sum_lines(invoice.lines) * (1 + TAX_RATE)

# Independent: the value is worked out by hand from the spec (tax 21%).
def test_invoice_total_includes_tax():
    invoice = make_invoice(lines=[(2, Decimal("10.00")), (1, Decimal("5.00"))])
    assert invoice.total() == Decimal("30.25")
```

vitest:

```ts
// Tautology
expect(formatDuration(90)).toBe(`${Math.floor(90 / 60)}m ${90 % 60}s`)

// Independent
expect(formatDuration(90)).toBe('1m 30s')
```

## Mock the boundary, not your own code

pytest:

```python
# Mocks the project's own service: proves the view calls it, not that the sync works.
def test_sync_calls_service(mocker, client):
    sync = mocker.patch("billing.services.sync_customer")
    client.post("/api/customers/1/sync")
    sync.assert_called_once()

# Mocks only the third-party HTTP API and asserts the outcome.
@responses.activate
def test_sync_stores_remote_plan(client, customer):
    responses.get(f"https://api.example-billing.com/customers/{customer.remote_id}",
                  json={"plan": "pro"})
    client.post(f"/api/customers/{customer.id}/sync")
    customer.refresh_from_db()
    assert customer.plan == "pro"
```

The last assert reads the database, which is fine here: the stored plan is the contract of the endpoint.

vitest:

```ts
// Mocks the project's own composable
vi.mock('@/composables/useCart')

// Mocks only the HTTP client module, renders the real composable
vi.mock('@/api/http', () => ({ get: vi.fn().mockResolvedValue({ items: [] }) }))
```

## Time and randomness

```python
@time_machine.travel("2026-03-01 09:00", tick=False)
def test_trial_expires_after_14_days():
    trial = start_trial()
    assert trial.expires_at == datetime(2026, 3, 15, 9, 0, tzinfo=UTC)
```

```ts
vi.useFakeTimers()
vi.setSystemTime(new Date('2026-03-01T09:00:00Z'))
```

## No good seam

If the only way to observe the behavior is calling `_parse_header()` directly, or mocking `OrderService` inside `OrderService`, the code has no seam for this test. Report it (`tdd-runner` halts with a `blocker` naming the missing seam) instead of testing the private helper.
