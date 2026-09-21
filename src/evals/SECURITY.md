# Security Policy

## Scope

This directory contains a **demonstration** environment. It is not intended for
production use and deliberately omits controls that a production deployment
requires — notably private networking. See `docs/day-2.md` for the production
posture and `docs/threat-model.md` for the analysed threats.

## Reporting a vulnerability

Do not open a public issue for a security problem.

Use GitHub private vulnerability reporting on this repository, or contact the
repository owner directly. Please include reproduction steps and the affected
paths.

## What is enforced here

| Control | Mechanism |
|---------|-----------|
| No API keys on Search | `disableLocalAuth: true` in `infra/modules/search.bicep` |
| No local auth on Search | `disableLocalAuth: true` in `infra/modules/search.bicep` |
| No local auth on Foundry | `disableLocalAuth: true` in `infra/modules/foundry.bicep` |
| No secrets in outputs | Contract rule — `specs/001-foundry-evals-demo/contracts.md §1` prohibits key, SAS and connection-string outputs |
| Least-privilege RBAC | 9 resource-scoped assignments in `infra/modules/rbac.bicep`, each with a documented justification |
| No secrets in git | `gitleaks` in the quality gate; `results/` and `.azure/` are gitignored |
| Synthetic data only | `tests/test_corpus.py` asserts reserved-for-fiction formats for every identifier |

## Synthetic data

All personal data in `corpus/` is fabricated and uses formats reserved for
fiction and documentation:

- SSN area `000` — never issued by the SSA
- Phone `(212) 555-01xx` — reserved for fictional use
- Email `@example.com` — RFC 2606

If you extend the corpus, keep to these formats. The test suite will fail if you
do not, which is the point.

## Reporting a problem with the demo's own claims

If a guard described in this repository does not actually hold — a threshold that
does not block, a test that silently skips, a control that is asserted but not
enforced — that is a security issue in the sense that matters most here. Please
report it the same way.
