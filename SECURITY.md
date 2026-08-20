# Security Policy

## Supported Versions

Only the latest release is supported. Older releases receive no fixes.

## Reporting a Vulnerability

Please report vulnerabilities privately — do not open a public issue.

- Preferred: [Report a vulnerability](https://github.com/russellyvr/Ai-Tools/security/advisories/new) via GitHub private vulnerability reporting.
- Fallback: email russellyvr@gmail.com with "SECURITY Ai-Tools" in the subject.

You can expect an acknowledgement within 7 days. Please include steps to reproduce and the commit or release version affected.

## Verifying Releases

Install from tagged releases rather than the mutable `main` branch. Release assets carry GitHub build-provenance attestations. Verify a download with:

```
gh attestation verify <asset.zip> --repo russellyvr/Ai-Tools
```
