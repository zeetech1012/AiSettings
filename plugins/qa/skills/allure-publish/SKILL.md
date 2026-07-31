---
name: allure-publish
description: Выгрузка allure-results на центральный allure-docker-service (login → CSRF → send-results → generate-report) с разбивкой по project_id. Локально и в GitLab CI. Triggers on "выгрузи прогон в allure", "залей результаты в allure", "publish allure", "send results to allure server", "отправь отчёт в allure", "allure-publish".
---

# SKILL: ALLURE_PUBLISH

## Цель
Отправить сырые `allure-results/` на центральный `allure-docker-service` и сгенерировать отчёт —
из локального прогона или из GitLab CI. Мультипроект через `project_id`. Без хардкода секретов.

## Предусловия (всё из ENV / CI-variables / .env — НИКОГДА не хардкодить)
- `ALLURE_BASE`   — API сервиса, по умолчанию `https://allure.example.com/allure-docker-service`.
- `ALLURE_USER`   — пишущий пользователь (обычно `ci`).
- `ALLURE_CI_PASS` — пароль (masked+protected в CI; локально — из `/opt/allure/.env` или `/tmp/allure_pass`).
- `ALLURE_PROJECT` — `project_id` под продукт (energy-app-native, qa-monorepo, auth_http, …).
- `RESULTS_DIR`   — каталог результатов, по умолчанию `allure-results`.

Сервис `frankescobar/allure-docker-service` использует **JWT-cookie + CSRF**: сначала `login`
(кладёт cookie `csrf_access_token`), затем запросы с заголовком `X-CSRF-TOKEN` и этим cookie.

## Шаги
1. Проверить, что `RESULTS_DIR` существует и непуст — иначе выйти без ошибки (нечего слать).
2. `login` → получить cookie-jar и вытащить `csrf_access_token`.
3. `send-results` — отправить **ВСЕ** файлы прогона (результаты + вложения), не один файл.
4. `generate-report` — с `execution_name`/`execution_type` для осмысленных трендов.
5. Вернуть ссылку на отчёт: `<ALLURE_BASE>/projects/<project>/reports/latest/index.html`.

## Готовый сценарий (bash; работает локально и в CI)
```bash
set -euo pipefail
ALLURE_BASE="${ALLURE_BASE:-https://allure.example.com/allure-docker-service}"
ALLURE_USER="${ALLURE_USER:-ci}"
RESULTS_DIR="${RESULTS_DIR:-allure-results}"
: "${ALLURE_PROJECT:?set ALLURE_PROJECT (project_id продукта)}"
: "${ALLURE_CI_PASS:?set ALLURE_CI_PASS (из ENV/CI-variables/.env, не хардкодить)}"

[ -d "$RESULTS_DIR" ] && ls -A "$RESULTS_DIR" >/dev/null 2>&1 || { echo "no $RESULTS_DIR"; exit 0; }

ck=$(mktemp)
# 1) login → cookie + CSRF
curl -sf -X POST -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ALLURE_USER\",\"password\":\"$ALLURE_CI_PASS\"}" \
  -c "$ck" "$ALLURE_BASE/login" >/dev/null
CSRF=$(awk '/csrf_access_token/{print $7}' "$ck")

# 2) ВСЕ файлы прогона
files=(); for f in "$RESULTS_DIR"/*; do files+=(-F "files[]=@$f"); done
curl -sf -X POST -H "X-CSRF-TOKEN: $CSRF" -b "$ck" "${files[@]}" \
  "$ALLURE_BASE/send-results?project_id=$ALLURE_PROJECT&force_project_creation=true" >/dev/null

# 3) генерация с метаданными прогона
curl -sf -X GET -H "X-CSRF-TOKEN: $CSRF" -b "$ck" \
  "$ALLURE_BASE/generate-report?project_id=$ALLURE_PROJECT&execution_name=${CI_PIPELINE_ID:-local-$(whoami)}&execution_type=${CI_PIPELINE_ID:+gitlabci}" >/dev/null
rm -f "$ck"
echo "OK → $ALLURE_BASE/projects/$ALLURE_PROJECT/reports/latest/index.html"
```

## GitLab CI (фрагмент джобы)
```yaml
publish-allure:
  stage: report
  when: always
  allow_failure: true            # отчётность не валит пайплайн
  variables:
    ALLURE_BASE: "https://allure.example.com/allure-docker-service"
    ALLURE_PROJECT: "energy-app-native"   # свой на каждый продукт
  script:
    - bash scripts/allure-publish.sh      # тело — из «Готового сценария» выше
  # ALLURE_CI_PASS — masked+protected CI-variable; allure-results в .gitignore
```

## Правила
- **Секреты только из ENV/CI-variables/.env**, не в git, не в логи (`set +x` вокруг login).
- Слать **сырые** `allure-results` (не готовый HTML) — иначе не будет истории/трендов.
- **`project_id` на продукт** — отдельная история/тренды, проекты не перетирают друг друга.
- TLS на сервере валидный (Let's Encrypt) → `-k` не нужен. `-k` только для самоподписанных сертов.
- Если упало на login → проверь пароль/ротацию; на send/generate → CSRF-заголовок и cookie.
- `allure-results/` — в `.gitignore`.

## Связано
- Доки: `Company/_wiki/qa-infra/allure2-docker-service-setup-prompt` (развёртывание сервиса),
  задача `allure-central-reporting` / Huly СЕРВЕ-6.
