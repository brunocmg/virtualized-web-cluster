# AI assistance

## LLM used

Claude, by Anthropic (Claude Sonnet 5.5 and Opus 5.5).

## Prompt

> I need to build Topic 6 of my university course: "Virtualization: web cluster with performance monitoring". It is three Debian 13 VMs on VirtualBox (an HTTP server with nginx, a client with Locust, and monitoring with Prometheus and Grafana), with an internal network `intnet` 192.168.10.0/24 and a host-only adapter only on the monitoring VM. Guide me step by step through the installation and configuration, explaining every command. I need Grafana dashboards for CPU, memory, network and latency/requests, and screenshots of the behavior under load. Afterwards, help me review the group's report and slides so that they match what I actually built.

The prompt above is an English translation of the original (written in Portuguese).

## How the LLM was used

- Step-by-step guidance while building the environment.
- Explaining and fixing errors (network, `apt`, Grafana, a VM with a black screen).
- Writing the PromQL queries for the dashboard.
- Interpreting the load-test results.
- Reviewing the report and the slides so they reflect what was built.
- Help structuring the report text.

All commands were executed, and all screenshots and measurements were obtained, by me in my own environment.