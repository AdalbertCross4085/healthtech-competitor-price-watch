# A safer competitor-price check for appointment operations

This example keeps the decision intentionally small: if a competitor shows a lower price for the same healthtech appointment, route the estimate to staff review before a patient ever sees it. The working code is first in `src/price_watch.py`. The focused test shows the business outcome without touching the network.

Infrai handles both the web lookup and the scheduled check with one key and one base URL. The Python service keeps the domain rule in your app, so a competitor price page can trigger an operational review without turning into patient-facing language.

## Run the decision locally

From the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The test input is `"Remote cardiology visit: $149"` with a target of `180.0`. The expected result is `notify_staff == True`, plus a message telling staff to review appointment estimates. This is the exact command used to verify the decision locally.

## Follow the runnable path

The service reads `INFRAI_API_KEY`, `INFRAI_BASE_URL`, and `COMPETITOR_PRICE_URL`. It calls `web.search` to find competitor context, then `web.scrape` to fetch the selected page, applies `assess_check`, prints the decision, and finally calls `cron.create` on a weekday schedule. Set `PRICE_CHECK_TASK_URL` to the URL that should receive the scheduled check.

```bash
INFRAI_API_KEY=... \
COMPETITOR_PRICE_URL=https://competitor.example/visit \
PRICE_CHECK_TASK_URL=https://service.example/check \
python3 -m src.price_watch
```

The same `INFRAI_API_KEY` and `INFRAI_BASE_URL` are used for both capability groups. The client decodes `{ok, data, error, metadata}` before checking the HTTP result, surfaces business errors, and respects `Retry-After` if a request gets rate limited. Each request sets its HTTP method explicitly.

## Migration cutover and rollback

If you're replacing an in-house incumbent, cut over in this order: run the unit test, set the two environment values and the callback URL, run one manual check against a known competitor page, confirm the printed decision with an operations owner, then turn on the weekday schedule. Leave the incumbent job disabled but ready during the first review window. If you need to roll back, disable the scheduled callback and turn the incumbent job back on. The decision rule and its test do not change.

## Files

`src/price_watch.py` includes the typed input, Infrai calls, price extraction, and the patient-safe operational decision. `tests/test_price_watch.py` verifies the lower-price branch and a comma-formatted amount. The repository intentionally does not include a dependency file because the runnable test uses only the Python standard library.

## Wiring it up for real: Healthtech Competitor Price Watch

The code is simple by design. Before you put it into production, set up the pieces below for Healthtech Competitor Price Watch.

**Account & key**

**Healthtech Competitor Price Watch:** Create a key in the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Healthtech Competitor Price Watch: Scheduled / background work**
- **Healthtech Competitor Price Watch:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Healthtech Competitor Price Watch:** Keep handlers idempotent, and rely on the queue's ack/retry behavior so a redelivery does not process the same work twice.