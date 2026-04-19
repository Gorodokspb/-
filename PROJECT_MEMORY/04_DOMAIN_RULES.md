# Domain Rules

Business flow:
- estimate -> project -> counterparty -> contract

Estimate-first rule:
- an estimate is the first-class starting point of the deal;
- it later feeds project, counterparty, and contract steps.

Counterparty rule:
- counterparty creation can happen after estimate work;
- contract generation depends on valid project, estimate, and counterparty data.

Price list rules:
- Excel import must not create duplicate rows for the same work name;
- if a work exists and price or unit changed, update the existing row;
- if the existing row is already current, skip it;
- an estimate row created from the price list should keep a reference to the source price row;
- when that estimate row is edited, the user should be able to push the change back to the price list.

Finance direction:
- one shared cash desk should become the source of truth;
- every income or expense can optionally link to a project;
- project finance views should filter shared operations;
- project tabs should not create duplicate finance entries.
