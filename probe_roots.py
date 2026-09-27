#!/usr/bin/env python3
"""BEDDED ROOTS probe (weekly): real specs for every Garden machine over SSH, and each agent's schedule/model/pay,
saved to site/data/roots.json for The Green Thumb's field guide. Read-only commands only; nothing secret is collected."""
import base64, datetime as dt, glob, json, os, re, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
H = os.path.expanduser("~/.hermes")
LINUX = ("echo host=$(hostname); . /etc/os-release 2>/dev/null; echo os=\"$PRETTY_NAME\"; echo kernel=$(uname -r); echo arch=$(uname -m); "
         "echo cpu=\"$(grep -m1 -E 'model name|^Model' /proc/cpuinfo | cut -d: -f2 | xargs)\"; echo cores=$(nproc); "
         "echo mem_mb=$(free -m | awk '/Mem:/{print $2}'); echo disk=\"$(df -h / | awk 'NR==2{print $2\" total, \"$5\" used\"}')\"; "
         "echo up=\"$(uptime -p)\"; echo root=$(awk '$2==\"/\"{print $4}' /proc/mounts | cut -d, -f1 | head -1); "
         "echo containers=\"$(docker ps --format '{{.Names}}' 2>/dev/null | tr '\\n' ' ')\"; echo temp=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2)")
WIN = ("$o=Get-CimInstance Win32_OperatingSystem; $c=Get-CimInstance Win32_Processor | Select-Object -First 1; $d=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\"; "
       "'host='+$env:COMPUTERNAME; 'os='+$o.Caption; 'arch='+$env:PROCESSOR_ARCHITECTURE; 'cpu='+$c.Name; 'cores='+$c.NumberOfLogicalProcessors; "
       "'mem_mb='+[math]::Round($o.TotalVisibleMemorySize/1024); 'disk='+[math]::Round($d.Size/1GB)+'G total, '+[math]::Round(100-$d.FreeSpace*100/$d.Size)+'% used'; "
       "'up='+[math]::Round(((Get-Date)-$o.LastBootUpTime).TotalDays,1)+' days'")
MACHINES = [("The Garden", None, "linux"), ("X VM", "cak3d", "linux"), ("theBAK3RY", "thebak3ry", "linux"), ("Hack-Safe", "hack-safe", "linux"),
            ("NukeBox", "nukebox", "windows"), ("HP laptop", "hp-laptop", "windows")]
AGENTS = {"main": "Ganja", "gardener": "The Gardiner", "chronic": "CHRONIC", "maple": "Maple", "herbie": "Herbie", "homie": "Homie", "ibby": "Ibby",
          "discostu": "Disco Stu", "bak3r": "BAK3R", "cyph3r": "CYPH3R", "clydius": "Clydius", "tinyz": "tinyZ", "big": "B.I.G"}


def probe(alias, kind):
    if kind == "windows":
        enc = base64.b64encode(WIN.encode("utf-16-le")).decode()
        cmd = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", alias, "powershell -NoProfile -EncodedCommand " + enc]
    else:
        cmd = ["bash", "-c", LINUX] if alias is None else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", alias, LINUX]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return {"reachable": False}
    info = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    info = {k.strip(): v.strip() for k, v in info.items() if v.strip()}
    info["reachable"] = bool(info.get("host"))
    return info


def agents():
    pay = {}
    files = sorted(glob.glob(os.path.join(H, "garden", "doublewide", "site", "data", "payroll-20*.json")))
    if files:
        pay = {r["agent"]: r for r in json.load(open(files[-1])).get("rows") or []}
    timers = {}
    for t in glob.glob(os.path.expanduser("~/.config/systemd/user/relay-*.timer")):
        m = re.search(r"OnCalendar=(.+)", open(t).read())
        if m:
            timers[os.path.basename(t)[6:-6]] = m.group(1).strip()
    out = {}
    for prof, name in AGENTS.items():
        jobs_f = os.path.join(H, "cron", "jobs.json") if prof == "main" else os.path.join(H, "profiles", prof, "cron", "jobs.json")
        try:
            jobs = [j for j in json.load(open(jobs_f)).get("jobs") or [] if str(j.get("name", "")).startswith("Relay:")]
        except Exception:
            jobs = []
        model = next((j.get("model_snapshot") for j in jobs if j.get("model_snapshot")), None)
        prov = next((j.get("provider_snapshot") for j in jobs if j.get("provider_snapshot")), None)
        key = "ganja" if prof == "main" else prof
        sched = [v for k, v in timers.items() if k == key or k.startswith(key)]
        gw_active = subprocess.run(["systemctl", "--user", "is-active", "hermes-gateway.service" if prof == "main" else "hermes-gateway-%s.service" % prof],
                                   capture_output=True, text=True).stdout.strip()
        out[name] = {"profile": prof, "jobs": [j["name"].replace("Relay: ", "") for j in jobs], "model": model, "provider": prov, "schedule": sched,
                     "gateway": gw_active, "pay_month": (pay.get(name) or {}).get("month"), "grade": (pay.get(name) or {}).get("grade")}
    return out


if __name__ == "__main__":
    data = {"probed": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
            "machines": {name: probe(alias, kind) for name, alias, kind in MACHINES}, "agents": agents()}
    os.makedirs(os.path.join(ROOT, "site", "data"), exist_ok=True)
    json.dump(data, open(os.path.join(ROOT, "site", "data", "roots.json"), "w"), indent=1)
    print("roots probed:", ", ".join("%s %s" % (k, "✓" if v.get("reachable") else "✗") for k, v in data["machines"].items()))
