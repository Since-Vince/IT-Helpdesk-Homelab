# INC-465316 — Linux Password Lock Investigation (Home Lab)

> **Project type:** Simulated IT help desk / Identity & Access Management (IAM) lab  
> **Date:** October 10, 2026  
> **Platform:** Ubuntu 24.04 in an isolated Docker container (`iam-lab`)  
> **Ticket system:** Self-hosted osTicket  
> **Account:** `lab_jrivera` (fictional)  
> **Status:** Administrative password lock cleared; interactive local password authentication **verified**; original simulated security investigation remains open

## Executive summary

As part of a simulated help desk ticket, I investigated password-authentication availability for a fictional Linux employee account. I created a disposable Ubuntu account, checked its password state and expiration settings, intentionally applied an administrative password lock, then reversed the lock using Linux account-management tools. The password status returned from `L` to `P`, account expiration settings did not change, and a non-root interactive `su` test succeeded using the configured lab password. This verifies **local password authentication through `su`**, but does not establish that SSH authentication succeeds.

**Scope note:** This was a controlled administrative password-lock exercise associated with ticket INC-465316. It **does not reproduce or resolve** the earlier fictional repeated-failed-login / `pam_faillock` security incident. Any conclusions about that broader incident require separate evidence.

## Objective and scope

- Investigate Linux user existence, password state, and expiration without modifying the home server's real user accounts.
- Safely reproduce an administrative password lock in an isolated, network-disabled Docker container.
- Restore the previously configured password without unnecessarily resetting it.
- Verify the fix by performing a password-authenticated local login from an unprivileged account.
- Record exactly what the evidence establishes, and identify remaining verification steps.

## Lab setup

| Component | Configuration |
|---|---|
| Host | Ubuntu home lab server with Docker and CasaOS |
| Training environment | Docker container `iam-lab`, Ubuntu 24.04 |
| Network isolation | `--network none` |
| Fictional user | `lab_jrivera` |
| Help desk | osTicket ticket `#465316` (simulation) |

A network-isolated container was created for the exercise:

```bash
docker run -d --name iam-lab --network none ubuntu:24.04 sleep infinity
docker exec iam-lab useradd -m -s /bin/bash lab_jrivera
```

## Investigation and actions

### 1. Verify that the account exists

```bash
docker exec iam-lab getent passwd lab_jrivera
```

Observed output:

```text
lab_jrivera:x:1001:1001::/home/lab_jrivera:/bin/bash
```

**Finding:** The account existed, had a home directory, and was configured with `/bin/bash` as its login shell.

### 2. Inspect password status and aging

```bash
docker exec iam-lab passwd -S lab_jrivera
docker exec iam-lab chage -l lab_jrivera
```

Initially, before configuring a password, `passwd -S` returned:

```text
lab_jrivera L 2026-10-10 0 99999 7 -1
```

`L` denotes a locked password. The aging report showed **Account expires: never** and **Password expires: never**. Account expiration and password locking are distinct controls.

### 3. Configure a lab-only password

```bash
docker exec -it iam-lab passwd lab_jrivera
```

A temporary lab password was set interactively. The password status was then reported as `P` (usable password configured). **No password is included in this report.**

### 4. Reproduce an administrative password lock

```bash
docker exec iam-lab passwd -l lab_jrivera
docker exec iam-lab passwd -S lab_jrivera
docker exec iam-lab chage -l lab_jrivera
```

**Observed:** The password status became `L`, while account expiration settings did not change. This simulated an **administrative password lock**, not a failed-login threshold or `pam_faillock` event.

### 5. Remove the administrative lock

After confirming this was an authorized training change, the password lock was reversed:

```bash
docker exec iam-lab passwd -u lab_jrivera
docker exec iam-lab passwd -S lab_jrivera
docker exec iam-lab chage -l lab_jrivera
```

**Observed:** `passwd -S` returned password status `P`. Account expiration settings remained unchanged.

### 6. Verify interactive password authentication (Phase 6)

A password-authenticated login test was performed **as an unprivileged user**, so `su` had to request the target account's password rather than bypassing verification through root privileges.

```bash
docker exec -it --user nobody iam-lab su - lab_jrivera
# Enter the temporary lab password when prompted (not recorded).
whoami
id
exit
```

Observed terminal evidence:

```text
Password:
lab_jrivera@7c6cc3a30d87:~$ whoami
lab_jrivera
lab_jrivera@7c6cc3a30d87:~$ id
uid=1001(lab_jrivera) gid=1001(lab_jrivera) groups=1001(lab_jrivera)
lab_jrivera@7c6cc3a30d87:~$ exit
logout
```

**Finding:** The container accepted the configured lab password for `lab_jrivera`, then started a shell under the target user identity (UID 1001). This verifies the **local `su`/PAM password-authentication path** in the isolated container. It does **not** verify SSH service availability or SSH password login, and it does **not** establish why the separately simulated repeated-login incident occurred.

## Evidence summary

| Evidence | Observation | Interpretation |
|---|---|---|
| `getent passwd lab_jrivera` | Account entry exists | Linux account was created |
| `passwd -S` after initial user creation | `L` | Password authentication locked or unavailable |
| `passwd -S` after setting password | `P` | Usable password configured |
| `passwd -S` after `passwd -l` | `L` | Administrative password lock applied |
| `chage -l` after lock | No expiration change | Password lock and account expiration are separate |
| `passwd -S` after `passwd -u` | `P` | Administrative password lock reversed |
| Interactive local login from `nobody` using `su - lab_jrivera` | Password accepted; `whoami` and `id` showed `lab_jrivera` (UID 1001) | Local password authentication verified |

## Root cause and resolution — controlled exercise only

**Controlled cause:** The lab password was deliberately locked using `passwd -l`, which prevents password-based authentication with that password.  
**Resolution performed:** `passwd -u lab_jrivera` removed the administrative password lock without assigning a different password.  
**Verification completed:** `passwd -S` returned `P`, and `chage -l` showed unchanged expiration settings.  
**Verification completed:** An unprivileged `nobody` session successfully authenticated as `lab_jrivera` via `su`. `whoami` and `id` confirmed the effective user was `lab_jrivera` (UID 1001). **Not verified:** SSH password login, any repeated-failure lockout policy, or resolution of the earlier suspicious-login case.

## Security considerations

- Authenticate the ticket requester using an approved identity-verification workflow before making real account changes.
- Check the reason for an account lock and seek authorization before removing it.
- Never ask a user to disclose an existing password or include passwords, API keys, or other secrets in ticket notes or a public repository.
- Treat suspicious authentication activity as a separate investigation rather than assuming that unlocking a password resolves it.
- Use sanitized screenshots and fictional identities in portfolio documentation.

## Skills demonstrated

Linux account administration (`getent`, `passwd`, `chage`), Docker-based isolation, IAM troubleshooting, change verification, technical documentation, and the distinction between an administrative password lock and a repeated-failed-login lockout.

## Next steps

- [x] Verify interactive local password authentication from an unprivileged identity.
- [x] Record the observed successful login and `whoami`/`id` results (October 10, 2026).
- [ ] Investigate failed password attempts and the container's PAM policy separately; do not assume `pam_faillock` is configured.
- [ ] Determine whether local password authentication and SSH password authentication are configured differently.
- [ ] Attach redacted terminal evidence to the GitHub project.
- [ ] Update the osTicket lab ticket with the scope, actions, and remaining verification.

## Lessons learned

A successful account-state change is not the same as a successful user login. In this exercise, the administrative lock was reversed and local authentication was independently verified from a non-root identity. The result demonstrates a specific authentication path, not blanket access to every service. Effective help desk troubleshooting requires diagnosing the failure, making the smallest authorized change, and verifying the affected access method.
