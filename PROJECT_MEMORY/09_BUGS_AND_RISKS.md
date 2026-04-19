# Bugs And Risks

Known risks:
- path portability remains a critical risk because stale absolute paths can silently break live workflow;
- UI behavior must be validated on real user screens, not only assumed from code changes;
- contract generation depends on the real Word template and should not be considered safe without live checks;
- finance design can become messy if project-specific entries are duplicated instead of filtered from a shared source.

Known rough areas from previous work:
- estimate search field clipboard behavior is historically sensitive;
- quick search refresh after paste needs real verification;
- bottom action buttons in the estimate window need manual screen-fit checks;
- Excel price import window ownership and z-order need live validation.

Meta risk:
- environment path drift exists already: the environment-reported project folder does not match the repo path currently found on disk.
