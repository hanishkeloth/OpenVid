# Security

Do not report credentials or exploitable private-server details in a public issue. Use GitHub private vulnerability reporting when enabled, or open a minimal issue requesting private contact without disclosing the vulnerability.

OpenVid is for trusted self-hosted use. Use HTTPS and an instance access token outside localhost, with request/storage limits at your reverse proxy. Keep private backups of the data volume and encryption key. The server administrator can decrypt stored provider connections.

Workspace cookies are bearer credentials. Do not share them. Leave private-network provider access disabled unless the instance and users are trusted. Run one process per volume; wait for jobs before restarting. Never commit runtime data, keys or provider logs. The release packager includes only explicitly allowed source and samples.
