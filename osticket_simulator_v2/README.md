# IT Help Desk Simulator v2

A local training-only ticket generator for self-hosted osTicket. Python 3 standard library, no pip packages. Keeps credentials **out of the repository**.

## Contents
- `osticket_ticket_generator_v2.py`: safe preview-by-default generator, osTicket API poster
- `employees.json`: 20 entirely fictional employees across Sales, HR, Operations, IT, Finance, Marketing and Support. Uses the reserved `example.com` domain.
- `osticket-lab-generator.service`: one-shot systemd service with `LoadCredential`, running as your existing Ubuntu user
- `osticket-lab-generator.timer`: runs daily at 09:00 **in the server's local timezone**, with catch-up after power-off

## Install on Ubuntu / CasaOS
Copy the contents of this ZIP to `/DATA/AppData/osticket/`. Do not overwrite your original working `osticket_ticket_generator.py`; the new file is named `_v2.py`.

```sh
cd /DATA/AppData/osticket
python3 osticket_ticket_generator_v2.py --list-employees
python3 osticket_ticket_generator_v2.py --count 5
```

The second command is a **preview only**; sends no requests.

## Test one actual ticket
Ensure you've rotated any previously shared admin password/API key. The osTicket API key must be **Active**, permitted to **Create Tickets**, and registered for the host's source IP (for this home lab, previously verified as `172.23.0.1`). In the same shell:

```sh
export OSTICKET_URL=http://127.0.0.1:8085
read -rsp 'API key: ' OSTICKET_API_KEY; echo
export OSTICKET_API_KEY
python3 osticket_ticket_generator_v2.py --count 1 --send
```

## Install the daily systemd timer
These example service files use the actual username `l3ince`, location `/DATA/AppData/osticket`, and port 8085 from this lab. Check your server's local time zone and change the `OnCalendar=` field if you want a different time:

```sh
timedatectl
sudo install -m 600 -o root -g root /dev/null /etc/osticket-lab-generator.key
sudo nano /etc/osticket-lab-generator.key
```

Paste ONLY your **new** key on one line, save and close, then:

```sh
sudo chmod 600 /etc/osticket-lab-generator.key
sudo chown root:root /etc/osticket-lab-generator.key
sudo cp /DATA/AppData/osticket/osticket-lab-generator.service /etc/systemd/system/
sudo cp /DATA/AppData/osticket/osticket-lab-generator.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start osticket-lab-generator.service
sudo journalctl -u osticket-lab-generator.service -n 40 --no-pager
```

Once the manual service test works, turn on automation:

```sh
sudo systemctl enable --now osticket-lab-generator.timer
systemctl list-timers --all osticket-lab-generator.timer
```

Stop scheduled submissions at any time:

```sh
sudo systemctl disable --now osticket-lab-generator.timer
```

The systemd service uses `LoadCredential` (systemd 247+, available on modern Ubuntu versions) to pass a private copy of the API key to the script at runtime without putting it in the script, service file, or process command arguments. **Do not share the contents of `/etc/osticket-lab-generator.key`.** Running `systemctl start` manually creates real lab tickets, not just a preview.

## Notes
- Each ticket subject starts with `[LAB]` and includes a unique case reference.
- Scenario priorities and departments are written into the ticket description and are **not automatically configured as osTicket priorities/departments**. Create osTicket Help Topics/Departments separately if you want routing.
- `alert=false` and `autorespond=false` request that osTicket suppress notifications. Verify behaviour before larger batches.
- Nothing here creates actual outages. Reproduce failures only with disposable test environments.
- If the service reports HTTP 401, check the source IP, API permission, and credential file.
- With `Persistent=true`, the timer can run shortly after being enabled if a previous scheduled run was missed.
