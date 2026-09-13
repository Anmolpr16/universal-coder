# Security model

The runtime enforces a workspace boundary for file operations and blocks a small set of obviously destructive shell patterns. This is **not a complete sandbox**. For untrusted repositories, run the service inside an OS/container/VM sandbox with least-privilege filesystem and network permissions. Never expose the HTTP server directly to the public internet without authentication and transport security.
