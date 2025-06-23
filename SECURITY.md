# Security Information for ZTalon

## False Positive Warnings

ZTalon may trigger false positive warnings from antivirus software and Windows SmartScreen because:

1. **It's a new application** without established reputation
2. **It modifies system settings** (registry, services, etc.)
3. **It downloads and executes scripts** for optimization
4. **It requires administrator privileges** to function properly

## Verification Steps

### 1. Check File Integrity

```bash
# Verify SHA256 checksum (provided with each release)
certutil -hashfile ZTalon.exe SHA256
```

### 2. Scan with Multiple Engines

- Upload to [VirusTotal](https://www.virustotal.com) before running
- Check our official VirusTotal submissions in releases

### 3. Source Code Verification

- ZTalon is **100% open source**
- Review the code at: https://github.com/sogik/ZTalon
- Build from source if you prefer: `build.bat`

## What ZTalon Does

✅ **Safe Operations:**

- Registry modifications for performance
- Disables telemetry and bloatware
- Installs legitimate software (DirectX, C++, etc.)
- Downloads scripts from trusted sources (FR33THY, ChrisTitusTech)

❌ **Does NOT:**

- Collect personal data
- Connect to unauthorized servers
- Install malware or adware
- Damage your system (when used properly)

## Running ZTalon Safely

1. **Download only from GitHub releases**
2. **Verify checksums** before running
3. **Run on a fresh Windows installation** (recommended)
4. **Create a system restore point** before use
5. **Review what will be changed** in the interactive menus

## Reporting Issues

If you believe ZTalon contains actual malware or security issues:

- Open an issue on GitHub
- Contact: [your-email]
- Provide VirusTotal scan results

---

_ZTalon is licensed under BSD-3-Clause and is maintained by sogik_
