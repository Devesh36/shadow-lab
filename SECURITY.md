# Security policy

Test only explicitly authorized applications with disposable data and synthetic identities. Destructive testing, credential attacks, broad discovery, arbitrary model-generated exploits, and untrusted repository execution are unsupported. Do not expose the demo or local dashboard publicly.

If reporting a defect in ShadowLab itself, use GitHub private vulnerability reporting when available; avoid including target secrets, raw tokens, or user data. Normal issues should contain sanitized reproduction information only. No guaranteed response SLA is established for this initial project.

Security-sensitive contributions must preserve TLS/checksum verification, policy authority, denial-by-default execution, private-destination restrictions, response sanitization, and developer approval of patches. See the threat model for boundaries and remaining risks.
