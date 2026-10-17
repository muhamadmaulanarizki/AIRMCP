(function (root) {
  'use strict';

  const FINAL = new Set(['done', 'error', 'cancelled']);

  class OrchestrationRun {
    constructor(team, agents, task) {
      this.task = String(task || '');
      this.startedAt = Date.now();
      this.finishedAt = null;
      this.order = [...new Set(team || [])];
      this.records = new Map();
      const lookup = new Map((agents || []).map(agent => [agent.name, agent]));
      this.order.forEach((name, index) => {
        const agent = lookup.get(name) || {};
        this.records.set(name, {
          name,
          title: agent.title || name,
          provider: agent.provider || 'auto',
          index,
          status: 'queued',
          detail: 'menunggu giliran',
          startedAt: null,
          finishedAt: null,
          elapsedMs: 0,
          output: '',
        });
      });
    }

    set(name, status, detail, extra) {
      let record = this.records.get(name);
      if (!record) {
        record = {name, title: name, provider: 'auto', index: this.records.size, status: 'queued', detail: '', startedAt: null, finishedAt: null, elapsedMs: 0, output: ''};
        this.records.set(name, record);
        this.order.push(name);
      }
      const now = Date.now();
      if (status === 'running' && !record.startedAt) record.startedAt = now;
      if (FINAL.has(status)) {
        record.finishedAt = now;
        record.elapsedMs = record.startedAt ? now - record.startedAt : 0;
      }
      Object.assign(record, extra || {}, {status, detail: detail || record.detail});
      return record;
    }

    startFirst() {
      const record = this.list().find(item => item.status === 'queued');
      return record ? this.set(record.name, 'running', 'menganalisis tugas') : null;
    }

    complete(name, output, provider) {
      const record = this.set(name, 'done', 'hasil diterima', {output: String(output || ''), provider: provider || this.records.get(name)?.provider || 'auto'});
      this.startFirst();
      return record;
    }

    fail(message) {
      const active = this.list().find(item => item.status === 'running');
      if (active) this.set(active.name, 'error', message || 'proses gagal');
      this.list().filter(item => item.status === 'queued').forEach(item => this.set(item.name, 'cancelled', 'tidak dijalankan'));
      this.finishedAt = Date.now();
    }

    cancel() {
      this.list().filter(item => !FINAL.has(item.status)).forEach(item => this.set(item.name, 'cancelled', 'dihentikan pengguna'));
      this.finishedAt = Date.now();
    }

    finish() {
      this.list().filter(item => item.status === 'running').forEach(item => this.set(item.name, 'done', item.detail));
      this.list().filter(item => item.status === 'queued').forEach(item => this.set(item.name, 'cancelled', 'tidak mendapat turn'));
      this.finishedAt = Date.now();
    }

    list() {
      return this.order.map(name => this.records.get(name)).filter(Boolean);
    }

    summary() {
      const records = this.list();
      return records.reduce((counts, item) => {
        counts[item.status] = (counts[item.status] || 0) + 1;
        return counts;
      }, {total: records.length, queued: 0, running: 0, done: 0, error: 0, cancelled: 0});
    }

    static signals(content) {
      const text = String(content || '');
      const paths = [...new Set(text.match(/(?:[A-Za-z]:\\[^\s`"'<>]+|(?:[\w.-]+[\\/])+[\w.-]+\.(?:js|ts|tsx|jsx|py|json|md|css|html|sql|yml|yaml))/g) || [])];
      const tests = /\b(?:tests?|pytest|unittest|vitest|jest)\b/i.test(text);
      const passed = /\b(?:pass(?:ed)?|lulus|berhasil|success)\b/i.test(text);
      const failed = /\b(?:fail(?:ed|ure)?|gagal|error)\b/i.test(text);
      const diff = /```diff|^\+\+\+\s|^---\s/m.test(text);
      return {paths: paths.slice(0, 4), tests, testState: failed ? 'fail' : passed ? 'pass' : 'mentioned', diff};
    }
  }

  root.OrchestrationRun = OrchestrationRun;
  if (typeof module !== 'undefined' && module.exports) module.exports = {OrchestrationRun};
})(typeof globalThis !== 'undefined' ? globalThis : window);
