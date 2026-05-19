"""Lab 04 — your custom function tool.

Pick ONE of the two scenarios in the docstring below, uncomment the
matching function, and fill in the body. Then either:

* register it as a local function tool via the Agent Framework, or
* deploy it as a Functions HTTP trigger by wiring it into a new
  Blueprint in `src/functions/` (the README walks you through that).

Ships **fully commented**. Lab 04 step 5 uncomments this file.

Scenario A — `check_sanctions_list(name)`:
    Returns True if `name` is on a small hard-coded sanctions list.
    The agent should use this before persisting any memo that names
    a counter-party so we flag risky parties before HITL #2.

Scenario B — `lookup_engagement(engagement_id)`:
    Returns stub engagement metadata (client name, partner, status).
    The agent calls this when the user provides a case_id so the
    drafter has consistent client context.
"""

# from __future__ import annotations
#
# from typing import Annotated, Any
#
# # ---- Scenario A: sanctions check ----------------------------------------
# #
# # _SANCTIONS = {
# #     "Adriatic Holdings d.o.o.",
# #     "Mountain Trade Co.",
# # }
# #
# # def check_sanctions_list(
# #     name: Annotated[str, "Counter-party legal name to check."],
# # ) -> bool:
# #     """Return True if the name appears on the demo sanctions list."""
# #     return name.strip() in _SANCTIONS
#
#
# # ---- Scenario B: engagement lookup --------------------------------------
# #
# # _ENGAGEMENTS: dict[str, dict[str, Any]] = {
# #     "ENG-2026-001": {
# #         "client_name": "Contoso Manufacturing",
# #         "partner": "A. Berger",
# #         "status": "active",
# #     },
# # }
# #
# # def lookup_engagement(
# #     engagement_id: Annotated[str, "Engagement id, e.g. ENG-2026-001"],
# # ) -> dict[str, Any]:
# #     """Return stubbed engagement metadata, or an empty dict if unknown."""
# #     return _ENGAGEMENTS.get(engagement_id, {})
