# Security Review Findings - Commit 04315b1

## Review Date
October 18, 2025

## Scope
Review of security hardening implementation in commit `04315b1`, which includes:
- SECURITY_HARDENING.md documentation
- security-harden.sh script
- remove-security-harden.s (renamed to .sh)
- setup-ttslo.sh script
- systemd service files (ttslo.service, ttslo-dashboard.service)
- Environment file template (ttslo.env.example)

## Issues Found and Fixed

### 1. CRITICAL: Incorrect File Extension
**File**: `remove-security-harden.s`
**Issue**: File had wrong extension `.s` instead of `.sh`, causing confusion and potential execution issues
**Fix**: Renamed file to `remove-security-harden.sh` and updated all references
**Severity**: Medium
**Status**: ✅ FIXED

### 2. nginx Configuration Indentation Error
**File**: `security-harden.sh` (line 275)
**Issue**: Incorrect indentation in nginx proxy configuration could cause nginx config validation to fail
**Fix**: Corrected indentation for `proxy_pass` directive
**Severity**: Medium
**Status**: ✅ FIXED

### 3. Missing nginx Variable Escaping
**File**: `security-harden.sh` (lines 276-279)
**Issue**: nginx variables like `$host` were not escaped in bash heredoc, potentially causing interpolation issues
**Fix**: Escaped all nginx variables with backslash (e.g., `\$host`)
**Severity**: Low
**Status**: ✅ FIXED

### 4. Insufficient SSH Key Validation
**File**: `security-harden.sh` (configure_sshd function)
**Issue**: Script only checked if authorized_keys file exists, not if it contains valid SSH keys
**Fix**: Added validation to check for valid SSH public key formats (ssh-rsa, ssh-ed25519, ecdsa-*, sk-*)
**Severity**: High (could lead to lockout)
**Status**: ✅ FIXED

### 5. Dashboard Password Logging
**File**: `security-harden.sh` (configure_nginx_dashboard function)
**Issue**: Generated password is printed to console which could be captured in logs
**Fix**: Added security warning to save the password immediately
**Severity**: Medium (information disclosure)
**Status**: ✅ FIXED (warning added)

### 6. Duplicate ReadOnlyPaths in systemd Units
**File**: `deploy/systemd/ttslo.service` and `deploy/systemd/ttslo-dashboard.service`
**Issue**: Multiple paths on single ReadOnlyPaths line could cause parsing issues
**Fix**: Split into separate ReadOnlyPaths directives (one per path) following systemd best practices
**Severity**: Low
**Status**: ✅ FIXED

### 7. Missing Executable Permissions
**File**: `security-harden.sh`, `setup-ttslo.sh`, `remove-security-harden.sh`
**Issue**: Scripts had 644 permissions instead of 755, preventing direct execution
**Fix**: Added executable permissions (chmod +x)
**Severity**: Low
**Status**: ✅ FIXED

### 8. Unclear Configuration Section
**File**: `security-harden.sh`
**Issue**: Hardcoded username "tc3" without prominent notice to customize
**Fix**: Added prominent comment emphasizing need to change ADMIN_USER
**Severity**: Low
**Status**: ✅ FIXED

### 9. ShellCheck Warnings
**Files**: Multiple scripts
**Issue**: Minor shellcheck warnings for quoting and code patterns
**Fix**: 
- Added proper quoting in remove-security-harden.sh
- Fixed nginx reload logic to avoid && || pattern
- Added shellcheck disable directives where appropriate
**Severity**: Low
**Status**: ✅ FIXED

## Security Best Practices Validated

### ✅ Correctly Implemented
1. **SSH Hardening**
   - Password authentication disabled for SSH
   - Console login remains functional (good for recovery)
   - Root login disabled
   - MaxAuthTries limited to 3
   - Proper backup of sshd_config before modification

2. **PAM Faillock Configuration**
   - Targeted to sshd and sudo only (not common-auth)
   - Reasonable lockout parameters (5 attempts, 900s unlock)
   - Recovery instructions provided
   - Backups created before modification

3. **UFW Firewall**
   - Default deny incoming policy
   - SSH rate-limited
   - Dashboard restricted to private subnets (192.168.0.0/24)
   - Proper error handling with `|| true`

4. **systemd Service Isolation**
   - Comprehensive sandboxing (PrivateTmp, PrivateDevices, ProtectSystem=strict)
   - Process runs as unprivileged user 'ttslo'
   - Read-only code directory, read-write state directory
   - NoNewPrivileges and capability dropping
   - Memory protections (MemoryDenyWriteExecute)
   - Namespace and syscall restrictions
   - Protection of kernel interfaces

5. **Secrets Management**
   - Environment file with proper permissions (0640, root:ttslo)
   - Secrets read from secure location (/etc/ttslo/)
   - Not committed to git
   - Proper ownership and group access

6. **nginx Reverse Proxy**
   - Dashboard bound to localhost only
   - Basic authentication in front of dashboard
   - Strong random password generation
   - Proper proxy headers set

7. **Backup Strategy**
   - Timestamped backups of all modified config files
   - Backup verification before restoration
   - Non-destructive by default

## Potential Concerns (Not Fixed - Design Decisions)

### 1. Dashboard Password in Console Output
**Issue**: Generated password is printed to stdout
**Rationale**: This is intentional for first-time setup. Admin must save it manually.
**Recommendation**: Consider writing to a separate file with restricted permissions
**Severity**: Low

### 2. Hardcoded Admin Username
**Issue**: Username "tc3" is hardcoded in configuration section
**Rationale**: Documented as configuration variable that should be changed
**Status**: Acceptable (clearly marked as configuration)

### 3. Network Access Not Restricted by IP
**Issue**: systemd units don't use IPAddressDeny/IPAddressAllow
**Rationale**: Kraken endpoints use CDNs with dynamic IPs, making IP restrictions brittle
**Status**: Acceptable (documented in comments)

### 4. No Automatic Unattended Upgrades
**Issue**: Script doesn't configure unattended-upgrades
**Rationale**: Mentioned in SECURITY_HARDENING.md as manual step
**Status**: Acceptable (documented)

## Testing Performed

1. ✅ Bash syntax validation (bash -n) - All scripts pass
2. ✅ ShellCheck static analysis - All critical issues resolved
3. ✅ systemd-analyze verify - Unit files validated (uv path warning expected)
4. ✅ File permission verification - All scripts executable

## Recommendations for Future Enhancements

1. **Add idempotency checks**: Script could detect if hardening is already applied
2. **Add rollback verification**: Verify services restart successfully after hardening
3. **Add fail2ban jail.local**: Instead of jail.d override
4. **Add audit logging**: Enable auditd rules for security events
5. **Add AIDE/Tripwire**: File integrity monitoring
6. **Add key rotation documentation**: Process for rotating Kraken API keys
7. **Consider systemd-creds**: For sealed credential storage (mentioned in docs)
8. **Add health checks**: Verify services are running after hardening
9. **Add connectivity tests**: Verify Kraken API is reachable after UFW setup

## Overall Assessment

**Security Posture**: ✅ STRONG

The security implementation is comprehensive and follows industry best practices for:
- Defense in depth (SSH, PAM, UFW, systemd sandboxing)
- Principle of least privilege (unprivileged user, capability dropping)
- Fail-safe defaults (deny incoming, read-only code)
- Recovery options (console login, backup restoration)

**Code Quality**: ✅ GOOD

Scripts are well-structured with:
- Proper error handling (set -euo pipefail)
- Backup creation before modifications
- Idempotent operations where possible
- Clear documentation and comments

**Documentation**: ✅ EXCELLENT

SECURITY_HARDENING.md provides:
- Step-by-step hardening checklist
- Recovery procedures
- Rationale for each security control
- Links to additional resources

## Conclusion

All critical and high-severity issues have been identified and fixed. The security hardening implementation is production-ready with minor improvements applied. The codebase demonstrates a strong understanding of Linux security principles and follows best practices for secure application deployment.

## Signed Off By
GitHub Copilot Security Review
Date: October 18, 2025
