import os
import sys

from automation_service import build_automation_plan, resolve_automation_plan, inspect_application
from test_patient_registration_flow import PATIENT_REGISTRATION_TEST_CASE

ctx = inspect_application('http://localhost:3000')
plan = build_automation_plan(PATIENT_REGISTRATION_TEST_CASE, framework='selenium', language='java', base_url='http://localhost:3000')

print('--- PLANNED ACTIONS ---')
for a in plan.actions:
    print(f'step={a.step_number} act={a.action} target="{a.business_target}" val={a.value_reference}')

resolved = resolve_automation_plan(plan, ctx)
print('--- RESOLVED ACTIONS ---')
for a in resolved.actions:
    loc = a.locator_resolution.locator if a.locator_resolution else None
    strat = loc.strategy.value if loc else None
    val = loc.value if loc else None
    print(f'step={a.step_number} act={a.action} target="{a.business_target}" strat={strat} val="{val}"')
