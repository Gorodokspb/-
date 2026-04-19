# Environment And Paths

Currently detected live repo:
- `C:\Users\Aleks\YandexDisk-Gorodok198\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`

Git status at memory bootstrap:
- branch `master`
- tracking `origin/master`
- working tree was clean when this memory system was created

Observed inconsistency:
- the chat environment reported a project path ending with `Декорартстрой_CRM`;
- that literal path was not found on disk during inspection;
- the repository that does exist and contains the active code is `CRM_OLD_BAD`.

Operational implication:
- future sessions should verify the actual repo folder before assuming the environment path is correct.

Path-handling reminder for the application:
- prefer root-relative project paths;
- include repair logic for older stored absolute paths.
