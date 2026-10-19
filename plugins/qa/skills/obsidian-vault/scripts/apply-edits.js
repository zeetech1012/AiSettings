// apply-edits.js — пакетные точечные правки заметок vault через Obsidian API (obsidian eval).
// Вход: JSON [{file: <abs или vault-relative путь>, edits: [{old, new, all?}]}]. Каждый old обязан
// встречаться ровно один раз (иначе all: true); frontmatter `updated:` ставится сам, если были правки.
// Запуск: sed -e 's/__DRY__/true/' -e 's#__EDITS__#/abs/path/edits.json#' apply-edits.js > run.js
//         obsidian eval code="$(cat run.js)"      # сначала DRY=true, затем false
(async () => {
  const fs = require('fs');
  const DRY = __DRY__;
  const TODAY = '2026-09-04';
  const EDITS_PATH = '__EDITS__';
  const vaultRoot = app.vault.adapter.basePath;
  const list = JSON.parse(fs.readFileSync(EDITS_PATH, 'utf8'));
  const report = [];
  let totalApplied = 0, totalProblems = 0;
  for (const entry of list) {
    let rel = entry.file;
    if (rel.startsWith(vaultRoot)) rel = rel.slice(vaultRoot.length + 1);
    const file = app.vault.getAbstractFileByPath(rel);
    if (!file) { report.push('MISSING FILE ' + rel); totalProblems++; continue; }
    const before = await app.vault.read(file);
    let text = before;
    let applied = 0;
    const problems = [];
    for (const e of entry.edits) {
      if (!e.old || e.old === e.new) { problems.push('EMPTY/NOOP edit'); continue; }
      const count = text.split(e.old).length - 1;
      if (count === 0) { problems.push('NOT FOUND: ' + JSON.stringify(e.old.slice(0, 90))); continue; }
      if (count > 1 && !e.all) { problems.push('AMBIGUOUS(' + count + '): ' + JSON.stringify(e.old.slice(0, 90))); continue; }
      text = text.split(e.old).join(e.new);
      applied += count;
    }
    if (applied > 0 && text.startsWith('---\n')) {
      const end = text.indexOf('\n---', 4);
      if (end > 0) {
        let fm = text.slice(0, end);
        const rest = text.slice(end);
        if (/\nupdated: [^\n]*/.test(fm)) fm = fm.replace(/\nupdated: [^\n]*/, '\nupdated: ' + TODAY);
        else fm = fm + '\nupdated: ' + TODAY;
        text = fm + rest;
      }
    }
    if (!DRY && text !== before) {
      await app.vault.process(file, () => text);
    }
    totalApplied += applied; totalProblems += problems.length;
    report.push((DRY ? '[dry] ' : '[ok]  ') + rel + '  applied=' + applied + (problems.length ? '  PROBLEMS=' + problems.length + '\n      ' + problems.join('\n      ') : ''));
  }
  report.push('TOTAL applied=' + totalApplied + ' problems=' + totalProblems + (DRY ? ' (dry run, nothing written)' : ''));
  return report.join('\n');
})()
