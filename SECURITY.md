# Security Policy

## Scope

> **Early-stage research framework** — Not for production use

Security issues addressed on a best-effort basis with no formal SLA.

---

## Security Considerations

### Framework Scope

✅ **Designed for:**
- Investment research and backtesting
- Historical data analysis
- Reproducible research workflows

❌ **NOT designed for:**
- Production trading systems
- Real-time order execution
- Direct market connectivity

### Known Limitations

1. **No Built-in Authentication**
   - Library assumes authenticated data access (Bloomberg Terminal, local files)
   - Does not handle credentials, API keys, or authentication logic
   - Users responsible for securing data connections

2. **File-Based Persistence Only**
   - Uses Parquet/JSON files for data storage
   - No database encryption or access control
   - Files stored in project directory (protect via filesystem permissions)

3. **No Production Risk Controls**
   - Binary position sizing (no position limits)
   - No real-time risk monitoring
   - No circuit breakers or safety mechanisms
   - Designed for research simulation only

4. **External Data Dependencies**
   - Bloomberg Terminal integration requires active session
   - File-based data loading trusts input file integrity
   - No validation of data authenticity or tampering

---

## Reporting a Vulnerability

### How to Report

If you discover a security vulnerability in aponyx, please **do NOT** open a public issue. Instead:

1. **Email security report to:**
   - **Email:** 26568863+stabilefrisur@users.noreply.github.com
   - **Subject:** `[SECURITY] aponyx vulnerability report`

2. **Include in your report:**
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact and severity assessment
   - Suggested fix (if available)
   - Your contact information for follow-up

### What to Expect

- **Response:** Best effort, no guaranteed timeline
- **Fix Timeline:** Depends on severity and available time
  - No SLA or guaranteed response time
  - Addressed as time and resources permit

### Disclosure Policy

- No formal disclosure process
- Fixes published when available
- Reporter may be credited if desired

---

## Security Best Practices for Users

### Data Security

1. **Protect Data Files**
   ```bash
   # Set appropriate file permissions
   chmod 600 data/raw/*.parquet
   chmod 700 data/
   ```

2. **Secure Bloomberg Credentials**
   - Bloomberg Terminal authentication handled externally
   - Do not commit Bloomberg credentials to version control
   - Use Bloomberg's built-in security features

3. **Validate Input Data**
   ```python
   from aponyx.data import validate_cdx_schema
   
   # Always validate external data
   cdx_df = load_external_data("untrusted_source.parquet")
   validate_cdx_schema(cdx_df)  # Raises on invalid schema
   ```

### Code Security

1. **Keep Dependencies Updated**
   ```bash
   # Regularly update dependencies
   uv sync --upgrade
   ```

2. **Use Virtual Environments**
   ```bash
   # Always work in isolated environment
   uv sync
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```

3. **Review Third-Party Code**
   - Inspect data provider implementations before use
   - Validate external signal libraries
   - Audit custom extensions

### Environment Security

1. **Protect Project Directory**
   - Restrict filesystem access to project folder
   - Do not run with elevated privileges
   - Use separate user accounts for research vs production systems

2. **Secure Configuration**
   ```python
   # Do NOT hardcode sensitive paths or credentials
   # ❌ BAD:
   # DATA_DIR = "//shared-server/sensitive-data"
   
   # ✅ GOOD: Use environment variables
   import os
   DATA_DIR = os.getenv("APONYX_DATA_DIR", "data/")
   ```

3. **Audit Logging**
   - Review logs for unexpected behavior
   - Monitor file access patterns
   - Track data provider connections

---

## Dependency Security

### Vulnerability Scanning

We use automated tools to monitor dependencies:
- **Dependabot** - Automated dependency updates
- **GitHub Security Advisories** - CVE notifications

### Core Dependencies

Critical dependencies with security implications:

| Package | Purpose | Security Notes |
|---------|---------|----------------|
| `pandas` | Data manipulation | Trusted scientific computing library |
| `numpy` | Numerical operations | Trusted scientific computing library |
| `pyarrow` | Parquet I/O | Apache foundation, actively maintained |
| `xbbg` | Bloomberg integration | Community library, use with caution |

### Optional Dependencies

- `plotly` - Visualization (client-side rendering, no server risks)
- `streamlit` - Dashboards (development only, not production)

### Updating Dependencies

```bash
# Check for security updates
uv sync --upgrade

# Review changes
git diff uv.lock

# Test after updates
pytest --cov=aponyx
```

---

## Data Privacy

### Personal Data

aponyx does **not** collect, store, or transmit personal data:
- No user tracking or analytics
- No telemetry or error reporting
- No external API calls (except Bloomberg Terminal if configured)

### Market Data

- Market data sourced from Bloomberg Terminal or local files
- Users responsible for compliance with data licensing terms
- No data redistribution functionality

### Research Outputs

- Backtest results stored locally as Parquet/JSON
- No automatic upload or sharing
- Users control all output persistence

---

## Incident Response

### If You Suspect a Security Issue

1. **Stop using affected functionality**
2. **Report to maintainers** (see Reporting section above)
3. **Check for updates** on GitHub Security Advisories
4. **Apply patches** when available

### Security Advisories

Security fixes documented in:
- **Changelog:** https://github.com/stabilefrisur/aponyx/blob/master/CHANGELOG.md

---

## Compliance

### License

aponyx is released under **MIT License**:
- Open source, no warranty
- Use at your own risk
- See [LICENSE](LICENSE) for full terms

### Financial Regulations

**Important:** aponyx is a research tool, not financial advice.

Users must:
- Comply with applicable financial regulations
- Ensure proper licensing for market data usage
- Follow institutional policies for research software
- Maintain audit trails as required

### Export Controls

Research software generally exempt from export controls, but users should:
- Verify compliance with local laws
- Check export restrictions for derived work
- Review institutional policies

---

## Contact

**Security Issues:** 26568863+stabilefrisur@users.noreply.github.com  
**General Issues:** https://github.com/stabilefrisur/aponyx/issues  
**Project Repository:** https://github.com/stabilefrisur/aponyx

---

**Maintained by stabilefrisur**  
**Last Updated:** November 14, 2025
