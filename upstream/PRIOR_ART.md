# Prior art in huggingface/smolagents (issues and PRs, open and closed)

Searched 2026-10-20 on github.com/huggingface/smolagents/issues (this search covers issues and PRs, all states).
Method note: the GitHub REST/search API was not reachable from the working environment (403, repository-bound
access); the results pages were read through a web fetch that returns a text rendering of the page. Where the
rendering did not show a state it is written "not shown" (the item list only showed an "opened" date, which on
GitHub usually means open). Titles truncated on the page end in "…".

Result counts: `retry` 90, `"rate limit"` 37, `Retry-After` 40, `max_retries` 5, `RETRY_WAIT` 4,
plus two narrower checks: `is_rate_limit_error` 2, `retries openai client` 4.

## Directly relevant (read in full)
| # | type | title | state | covers the stacking (inner OpenAI `max_retries` x outer `Retrying`)? |
|---|---|---|---|---|
| 1801 | PR | Proposition: retry on rate limit errors | merged 2025-10-15 | No. Introduces the outer retry ("3 times in total with 120 seconds delay"); no review comment mentions the client's own retries. |
| 1829 | PR | Proposition: Add exponential backoff with jitter for retries | merged | Not read in full; title only adds backoff. |
| 2107 | PR | feat(retry): honour Retry-After header when retrying rate-limit errors | closed by author, unmerged, no reviews | No. Honors Retry-After in the outer loop; does not mention the client's `max_retries`. |
| 2165 | issue | No built-in retry/backoff for transient model API errors in MultiStepAgent | not shown | No (asks for MORE retry types). |
| 2186 | PR | fix: extend retry predicate to cover transient server errors and connection failures | open (closes #2165) | No stacking. Overlaps with the *classification* half: matches 429/5xx/connection by code. |
| 2382 | PR | feat(models): retry on transient server/network errors, not just rate limits | open | No stacking. Overlaps with the *classification* half: "classifies retryable failures by HTTP status code and exception type first, using message matching only as a fallback". |
| 2435 | PR | Fix InferenceClientModel hangs and add retries on overload and loadin… | not shown | No (InferenceClientModel). |
| 2586 | issue | Retrying's default wait_seconds=0.0 disables backoff entirely, and reraise has no effect | not shown | No (Retrying defaults). |
| 2589, 2596, 2617, 2646, 2662 | PR | Fix Retrying default backoff / reraise (five competing PRs for #2586) | 2646 closed, others not shown | No. |
| 2967 | issue | ApiModel RateLimiter is not thread-safe: concurrent calls can bypass requests_per_minute | not shown | No (client-side throttle). |
| 2964, 3003 | PR | Use a monotonic clock for rate limiting / Make RateLimiter thread-safe | not shown | No. |
| 388 | PR | Support passing additional parameters for openai client initialization | merged 2025-02-21 | No (this is what lets users pass `max_retries` in `client_kwargs`). |
| 736 | issue | [BUG] Completions.create() got an unexpected keyword argument 'max_retries' | closed | No. |

Conclusion: **no issue or PR found that reports or fixes the stacking** of the OpenAI client's default
`max_retries=2` under `ApiModel.retryer`. Not a stop condition. But #2186 and #2382 (both open) already propose
status-code-based classification, so a status_code change would compete with them ("first reviewable PR wins").

## All other hits (title only; none concerns model-request retry stacking)
retry: 3015, 2977, 2975, 2862, 2861, 2818, 2750, 2704 (closed), 2692, 2689, 2688, 2675, 2674, 2664 (closed),
2587 (closed), 2566, 2564, 2559, 2558 (merged), 2556, 2555, 2554 (closed), 2553, 2552, 2475, 2457, 2400 (closed,
"fix: retry empty LiteLLM choices responses"), 2210 (closed), 2189, 2172 (closed), 2166, 2129, 2123, 2117, 2112,
2059, 2052, 2045, 2037 (closed), 1990, 1976, 1941, 1912 (closed), 1908, 1883, 1872, 1852 (closed), 1834 (closed),
1832, 1790, 1775, 1725 (closed), 1694, 1684 (merged), 1501 (closed), 1232, 1169 (closed), 1139 (closed),
1131 (merged), 1115 (merged), 1096 (merged), 1092 (closed), 1052 (closed), 1039 (closed), 972 (merged), 948 (merged),
901, 797 (merged), 760 (closed), 522 (closed), 430, 361 (closed), 201, 153, 143 (closed), 102 (closed).
"rate limit" (beyond the above): 2671, 2522, 2480, 2387, 2380 (merged), 2167, 1972, 1896, 1767 (closed), 1732,
1519 (merged), 1516 (merged, "Implement rate limiting in all API models"), 1515 (merged), 1508 (merged), 1134,
1101 (closed), 967 (closed), 962 (closed), 833 (closed), 808 (closed), 738 (closed), 652 (closed), 596, 124, 39 (closed).
Retry-After: all 40 hits appear in the lists above.
max_retries: 1725, 1501, 901, 736, 388. RETRY_WAIT: 2646, 2596, 2586, 2107. retries openai client: 1725, 1158 (closed), 808, 388.
