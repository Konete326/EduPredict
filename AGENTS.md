# AGENTS.md

Mandatory workspace instructions for all AI agents working on **EduPredict**.

## Mandatory Pre-Flight & Per-Task Execution Protocol

On **every task**, you MUST read and strictly enforce the specifications and rules inside `.agents/` before writing or editing any code:

1. `.agents/prd.md` — Product scope, 4 role panels (`Admin`, `Teacher`, `Student`, `Analyst`), and anti-bloat lock.
2. `.agents/srd.md` — Pure Django MVT + MongoDB Atlas architecture, RBAC, data cleaning pipeline, and ML engine specs.
3. `.agents/trd.md` — Strict modular directory structure, MongoDB schemas, named URL routing map, and global component contracts.
4. `.agents/design.md` — Light/Dark CSS variable tokens (`static/css/global.css`), `@efferd/app-shell-3` layout, `z-10`..`z-60` stack, 5-row pagination, and mobile card-list standards.
5. `.agents/project-rules.md` & `.agents/rules/edupredict-rules.md` — All 20 mandatory engineering, UI/UX, role isolation, zero-comment, file-size cap (`<= 350-400` lines, views `<= 250` lines), TTL caching, `.env` git tracking, and Roman Urdu communication rules.
6. `.agents/git-sync.md` — Mandatory pre-task `git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main`, post-task Section 4 Active Handover State rewrite, and automatic GitHub push (`feature/<module>` and `main`).
7. `.agents/skills/edupredict-workflow/SKILL.md` — End-to-end execution and verification checklist (`python manage.py check`, `python manage.py test`, `node --check`, zero comments).
