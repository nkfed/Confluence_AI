# Confluence_AI — AI Agent for Confluence Cloud

AI‑агент для інтеграції з Confluence Cloud, який автоматизує читання, аналіз, узагальнення та оновлення сторінок у робочому просторі з оптимізацією для надійної роботи з AI API.

---

## 🎯 Мета проєкту

Створити Python‑агента, який:

- 📖 читає сторінки Confluence через REST API  
- 🧠 аналізує контент за допомогою зовнішніх AI‑моделей  
- 📝 генерує summary, рекомендації, структури документації  
- ✏️ оновлює сторінки або створює нові  
- 🔐 працює з токенами через `.env`  
- 🏗️ має модульну архітектуру для подальшого розширення

---

## ⚡ Optimization Patch v2.0 — What's New

### 🚀 **Performance Boost**
- **+14% Gemini success rate** (77.8% → 92%+)
- **-90% 429 errors** (22% → 2.2%)
- **-33% latency** (1300ms → 867ms average)
- **15x better stability** (±4637ms → ±300ms)

### 🔧 **Key Features**
1. **Pre-flight Rate Control** — Checks API readiness before requests, prevents 70% of rate limit errors
2. **Adaptive Cooldown** — Dynamic escalation (500ms → 1500ms → 7000ms) for consecutive errors
3. **Micro-batching** — Processes 46 pages in optimal batches (~2 items) with intelligent pausing
4. **Detailed Metrics** — Per-call statistics: success rate, fallback rate, response time, tokens
5. **Logging Rotation** — Automatic file rotation prevents disk exhaustion (10MB/file, 10 backups)

### 📊 **Control Run Results (46 pages)**
```
Operations:      46 pages (23 batches)
Success Rate:    92%+ (12/13 tracked)
429 Errors:      1 in 46 (2.2%)
Avg Response:    867ms ✅
Max Response:    1566ms ✅
Fallback Used:   1 (OpenAI seamless)
Status:          ✅ PRODUCTION READY
```

**📚 Full Documentation:** See [CHANGELOG.md](CHANGELOG.md) and [docs/PATCH_v2_INTEGRATION_COMPLETE_2026-01-04.md](docs/PATCH_v2_INTEGRATION_COMPLETE_2026-01-04.md)

---

## 🧩 Architecture

```
Confluence_AI/
│
├── src/
│   ├── agents/           # AI agents (tagging, summary, etc.)
│   ├── api/              # FastAPI endpoints
│   ├── clients/          # External API clients (Confluence, OpenAI, Gemini)
│   ├── core/
│   │   ├── ai/           # AI routing, optimization patch v2.0
│   │   ├── logging/      # Centralized logging with rotation
│   │   ├── whitelist/    # Page access control
│   │   └── agent_mode_resolver/
│   ├── services/         # Business logic (tagging, summary, context)
│   ├── models/           # Data models (Pydantic)
│   └── utils/            # Helpers, HTML cleaning, etc.
│
├── tests/                # Unit and integration tests
├── docs/                 # Documentation and architecture decisions
├── logs/                 # Application logs (auto-rotated)
│
├── run_server.py         # FastAPI server entry point
├── settings.py           # Environment configuration
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Confluence, OpenAI, and Gemini tokens
```

### 3. Run Server
```bash
python run_server.py
# API available at http://localhost:8000
```

### 4. Use API Endpoints
```bash
# Tag single page
curl -X POST http://localhost:8000/tagging/tag-page \
  -H "Content-Type: application/json" \
  -d '{"page_id": "123456", "mode": "DRY-RUN"}'

# Tag entire space
curl -X POST http://localhost:8000/tagging/tag-space/SPACE-KEY \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [CHANGELOG.md](CHANGELOG.md) | Version history and features |
| [docs/architecture/](docs/architecture/) | System design and flows |
| [docs/PATCH_v2_INTEGRATION_COMPLETE_2026-01-04.md](docs/PATCH_v2_INTEGRATION_COMPLETE_2026-01-04.md) | v2.0 integration details |
| [docs/LOGGING_ROTATION_SETUP_2026-01-04.md](docs/LOGGING_ROTATION_SETUP_2026-01-04.md) | Log rotation configuration |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

---

## 🔌 API Endpoints

### **Tagging**
- `POST /tagging/tag-page/{page_id}` — Tag single page
- `POST /tagging/tag-space/{space_key}` — Tag entire space
- `POST /tagging/tag-tree/{root_id}` — Tag page tree
- `POST /bulk/reset-tags/{space_key}` — Reset tags with tree scope

### **Utilities**
- `GET /health` — Health check
- `GET /metrics` — Performance metrics

See [docs/bulk-operations/](docs/bulk-operations/) for detailed endpoint documentation.

---

## 🔐 Security

- 🔒 Environment variables for all tokens (.env)
- 🔐 Whitelist-based page access control
- 📝 Audit logging for all operations
- 🛡️ Security warnings for policy violations

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tagging_service.py

# Run with coverage
pytest --cov=src

# Run integration tests
pytest tests/bulk/
```

---

## 📊 Monitoring

### **Logs**
- `logs/app.log` — Application logs
- `logs/ai_calls.log` — AI API calls (auto-rotated)
- `logs/audit.log` — Operation audit trail
- `logs/security.log` — Security events

### **Metrics**
- Success rate per AI provider
- Fallback rate and reasons
- Response time statistics
- Token usage tracking

---

## 🛠️ Performance Optimization

### **v2.0 Optimization Patch**

The system now includes intelligent rate limit handling:

```python
# Automatic pre-flight checks
patch = get_optimization_patch_v2()
await patch.preflight_cooldown()  # Checks if API is ready

# Adaptive cooldown on rate limits
reason, wait_ms = await patch.adaptive_cooldown()
print(f"Waiting {wait_ms}ms due to: {reason}")

# Micro-batching for bulk operations
batches = patch.micro_batch(page_ids)
for batch in batches:
    # Process each batch with pause between
    process_batch(batch)
```

For implementation details, see [src/core/ai/optimization_patch_v2.py](src/core/ai/optimization_patch_v2.py)

---

## 📈 Roadmap

- [x] ✅ Core Confluence tagging with AI
- [x] ✅ Fallback to OpenAI when Gemini fails
- [x] ✅ Optimization Patch v2.0 (pre-flight, adaptive cooldown, micro-batching)
- [x] ✅ Centralized logging with rotation
- [ ] ⏳ Jira integration
- [ ] ⏳ Telegram notifications
- [ ] ⏳ CI/CD integration
- [ ] ⏳ Advanced caching layer

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -m "Add your feature"`
3. Push to branch: `git push origin feature/your-feature`
4. Open Pull Request

---

## 📝 License

MIT License — See LICENSE file for details

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/nkfed/Confluence_AI/issues)
- **Discussions:** [GitHub Discussions](https://github.com/nkfed/Confluence_AI/discussions)
- **Documentation:** See [docs/](docs/) folder

---

**Last Updated:** 2026-01-04  
**Version:** v2.0 (Optimization Patch)  
**Status:** ✅ Production Ready


