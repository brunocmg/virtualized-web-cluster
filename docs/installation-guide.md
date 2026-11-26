# Installation and configuration guide

Step-by-step guide to build the lab: three Debian 13 VMs on VirtualBox (an nginx web server, a Locust load generator and a Prometheus + Grafana monitoring VM).

All commands run as root (`su -`). Configuration files referenced here are in [`../configs/`](../configs/) and the dashboard is in [`../grafana/`](../grafana/).

## 0. Environment

- Host: Ubuntu 26.04, VirtualBox 7.2.22, Intel Celeron, 20 GB RAM.
- Three Debian 13 (netinst) VMs with a 10 GB disk each. Install with DHCP on the NAT adapter and the SSH server selected. No desktop on `http` and `monitor`; `client` gets Xfce so Firefox can open the Locust web UI.

| VM | RAM / vCPU | Adapter 1 | Adapter 2 | Adapter 3 | IP |
|---|---|---|---|---|---|
| `http` | 1 GB / 1 | NAT | Internal network `intnet` | - | 192.168.10.10 |
| `client` | 2 GB / 2 | NAT | Internal network `intnet` | - | 192.168.10.20 |
| `monitor` | 2 GB / 1 | NAT | Internal network `intnet` | Host-only | 192.168.10.30 and 192.168.56.30 |

The recorded tests used 1 GB on `http`. You can give it more RAM; it does not change the setup.

## 1. Network (on every VM)

Edit `/etc/network/interfaces` and add the internal-network interface. Example for `http`:

```
auto enp0s8
iface enp0s8 inet static
    address 192.168.10.10
    netmask 255.255.255.0
```

Use `192.168.10.20` on `client`. On `monitor`, use `192.168.10.30` on `enp0s8` and `192.168.56.30` on `enp0s9` (host-only). Apply and test:

```
systemctl restart networking
ip a
ping -c 2 8.8.8.8
ping -c 2 192.168.10.10
```

## 2. VM `http` (web server)

```
apt update
apt install -y nginx prometheus-node-exporter prometheus-nginx-exporter
systemctl enable --now nginx prometheus-node-exporter
systemctl status nginx --no-pager
curl http://192.168.10.10
curl -s http://192.168.10.10:9100/metrics | grep -E "^node_(cpu|memory|network)" | head -5
```

Enable nginx `stub_status` on localhost only (`/etc/nginx/conf.d/status.conf`, see [`configs/http/status.conf`](../configs/http/status.conf)):

```
server {
    listen 127.0.0.1:8080;
    location /stub_status {
        stub_status;
    }
}
```

Point the exporter to it (`/etc/default/prometheus-nginx-exporter`):

```
ARGS="-nginx.scrape-uri=http://127.0.0.1:8080/stub_status"
```

Reload and check:

```
nginx -t && systemctl reload nginx
systemctl restart prometheus-nginx-exporter
curl -s http://127.0.0.1:9113/metrics | grep nginx_up
```

Expected result: `nginx_up 1`.

## 3. VM `client` (load generator)

```
apt update
apt install -y python3-venv prometheus-node-exporter
systemctl enable --now prometheus-node-exporter
python3 -m venv ~/locust-env
source ~/locust-env/bin/activate
pip install locust
```

Create `~/locustfile.py` (see [`configs/client/locustfile.py`](../configs/client/locustfile.py)):

```python
from locust import HttpUser, task, between

class ServidorUser(HttpUser):
    wait_time = between(0, 0.1)
    host = "http://192.168.10.10"

    @task
    def pagina_inicial(self):
        self.client.get("/")
```

`between(0, 0.1)` makes each virtual user wait 0 to 0.1 s between requests, which produces heavy load with few users. A slower pace such as `between(0.5, 1.5)` also works but needs many more users to reach the same request rate.

Start Locust manually (there is no systemd service):

```
source ~/locust-env/bin/activate
locust -f ~/locustfile.py --host http://192.168.10.10
ss -tlnp | grep 8089
```

Open Firefox inside the VM at `http://127.0.0.1:8089`, set the number of users and spawn rate and click *Start swarming*. If the port is busy: `pkill -f locust`.

## 4. VM `monitor` (Prometheus, Blackbox Exporter, Grafana)

```
apt update
apt install -y prometheus prometheus-node-exporter prometheus-blackbox-exporter
systemctl enable --now prometheus prometheus-node-exporter prometheus-blackbox-exporter
```

Grafana from the official repository:

```
apt install -y apt-transport-https wget gpg
mkdir -p /etc/apt/keyrings
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
apt update
apt install -y grafana
systemctl daemon-reload
systemctl enable --now grafana-server
```

Use [`configs/monitor/prometheus.yml`](../configs/monitor/prometheus.yml) as `/etc/prometheus/prometheus.yml`. It sets a 15 s global scrape interval, 5 s for the `prometheus` and `blackbox-http` jobs, and these jobs: `prometheus`, `node`, `servidor-http`, `cliente`, `nginx` and `blackbox-http`. Validate and restart:

```
promtool check config /etc/prometheus/prometheus.yml
systemctl restart prometheus
curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[a-z]*"'
```

Every target must be `up`.

## 5. Grafana and dashboard

On the host PC (not inside a VM), open `http://192.168.56.30:3000` (login `admin`; change the password). Under *Connections → Data sources*, add Prometheus with URL `http://localhost:9090`. Then either import [`grafana/cluster-web-desempenho.json`](../grafana/cluster-web-desempenho.json) or build the dashboard *Cluster web - desempenho* with a 5 s refresh and these panels:

| Panel | Query |
|---|---|
| Requests per second | `rate(nginx_http_requests_total[1m])` |
| Active connections | `nginx_connections_active` |
| CPU (%) | `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)` |
| Memory (%) | `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100` |
| Network received | `rate(node_network_receive_bytes_total{device="enp0s8"}[1m])` |
| Latency | `probe_duration_seconds{job="blackbox-http"}` |

Set the unit of the latency panel to *seconds*; Grafana then shows milliseconds.

## 6. Running the test

In the Locust UI, keeping the same `locustfile.py`:

| Phase | Users | Spawn rate |
|---|---|---|
| Idle | 0 | - |
| Load 1 | 10 | 2 |
| Load 2 | 50 | 5 |
| Load 3 | 200 | 50 |
| Load 4 | 500 | 50 |
| Recovery | Stop | - |
| Stress | 1000 | 100 |

In each phase, wait for the curves to settle and take a screenshot of the dashboard.

## 7. Troubleshooting

- **`apt` on the host returns 403 for an `http` repository:** switch the repository to `https`.
- **A VM starts with a black screen (saved state):** `VBoxManage discardstate <vm-name>`.
- **Debian installer cannot reach a mirror:** choose another mirror.
- **Grafana does not install:** check the URL in `/etc/apt/sources.list.d/grafana.list` (a typo here is easy to miss).
- **Locust shows `No connection adapters were found for 'htpp://...'`:** the host has a typo (`htpp` instead of `http`) in the command, in `locustfile.py` or in the Host field of the UI. Fix it and restart.
- **VirtualBox says adapter 3 is invalid ("Name: Not selected"):** the host-only network no longer exists. Create one in *Tools → Network → Host-only Networks* with IPv4 `192.168.56.1/24` (or `VBoxManage hostonlyif create`), then select it in the adapter settings. On Linux you may also need `* 192.168.56.0/21` in `/etc/vbox/networks.conf`.
- **Connections stall below the number of users in the 1000-user test:** the client VM's open-file limit (`ulimit -n`, default 1024) is a likely cause. Raising it before starting Locust (for example `ulimit -n 65535`) is the first thing to try; this was not tested in the project.