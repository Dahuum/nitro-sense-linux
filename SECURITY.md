# Security and privileged access

Run the desktop app as your normal user. Only driver setup needs administrator
access. The optional installer grants the nitrosense group access to fixed Acer
control files, never an unrestricted root shell. The app does not execute
profile contents or arbitrary commands from imported JSON.

Manual fan mode is firmware state. Normal app exit, handled termination, and
failed profile application request Auto. SIGKILL, a crashed kernel, a vanished
driver, and power failure cannot be recovered by a dead Python process. Close the
app normally when possible. A known-good driver interface can request recovery:

```sh
printf '0,0\n' | sudo tee /sys/devices/platform/acer-wmi/nitro_sense/fan_speed
```

Do not expose sysfs controls to all users. Do not post secrets in issue reports.
Report a suspected access-control vulnerability privately using GitHub's private
vulnerability reporting when enabled; otherwise open an issue requesting a
private contact without publishing exploit details.
