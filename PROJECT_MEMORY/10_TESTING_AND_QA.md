# Testing And QA

Manual checks that still matter:
- CRM opening on the real user screen size;
- project card opening and fitting on screen;
- estimate editor opening from a project;
- direct price list opening from CRM;
- Excel import into the price list;
- `Ctrl+V` in estimate search fields;
- immediate search refresh after paste;
- estimate bottom buttons staying visible;
- contract generation against the real Word template.

End-to-end flow to re-run:
1. office save -> home reopen
2. price update import -> estimate add/edit -> save back to price list
3. estimate -> project -> counterparty -> contract

QA logging rule:
- if a test is actually run, record outcome, machine, and result in the next session log entry.
