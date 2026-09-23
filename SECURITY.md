Security Policy

Supported Versions

Security fixes are currently provided for the latest released version of the project.

Version| Supported
0.1.x| Yes
< 0.1.0| No

Reporting a Security Vulnerability

If you discover a security vulnerability, please do not disclose it publicly in a GitHub issue.

Instead, report it privately through GitHub's security reporting mechanism:

Security Advisories:
https://github.com/janreimen/Python-Analyze-SolarEdge-Registers/security/advisories

Please include:

- A clear description of the vulnerability.
- The affected version.
- Steps to reproduce the issue.
- Any relevant logs, configuration, or proof-of-concept information.
- The potential impact, if known.

Please allow reasonable time for investigation and remediation before publicly disclosing the vulnerability.

Sensitive Information

When reporting issues, take care not to publish sensitive information such as:

- SolarEdge inverter serial numbers.
- Internal IP addresses.
- Network credentials.
- API keys or tokens.
- Passwords.
- Private SSH keys.
- Private infrastructure configuration.

Raw SolarEdge register dumps may contain device-specific information. Review them before attaching them to public GitHub issues.

Scope

This project is a diagnostic tool that communicates with SolarEdge inverters using Modbus TCP.

It does not provide authentication, authorization, network isolation, or security controls for the inverter or the surrounding network.

Users are responsible for securing their Modbus TCP network and restricting access to the inverter appropriately.

Dependency Security

The project uses third-party Python dependencies listed in "requirements.txt".

Dependencies should be kept up to date within their supported version ranges.

The project intentionally does not depend on the "solaredge_modbus" package.

Public Issues

For normal bugs and non-sensitive problems, please use the project's GitHub issue tracker:

https://github.com/janreimen/Python-Analyze-SolarEdge-Registers/issues

Do not use public issues for undisclosed security vulnerabilities.
