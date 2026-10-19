import { JupyterFrontEnd } from '@jupyterlab/application';
import { Dialog, showDialog } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { INotebookTracker } from '@jupyterlab/notebook';
import { ServerConnection } from '@jupyterlab/services';
import { IStatusBar } from '@jupyterlab/statusbar';
import { Widget } from '@lumino/widgets';
import '../style/index.css';

const PLUGIN_ID = '@keio/classroom-status:plugin';
const statusLabels = {
  recording: 'Recording',
  synced: 'Synced',
  offline: 'Offline / queued',
  attention: 'Attention needed'
};

function sha256(text) {
  const bytes = new TextEncoder().encode(text);
  return crypto.subtle.digest('SHA-256', bytes).then(buffer =>
    [...new Uint8Array(buffer)].map(byte => byte.toString(16).padStart(2, '0')).join('')
  );
}

const plugin = {
  id: PLUGIN_ID,
  autoStart: true,
  requires: [IStatusBar, INotebookTracker],
  activate: (app, statusBar, tracker) => {
    const settings = ServerConnection.makeSettings();
    const node = document.createElement('button');
    node.className = 'keio-course-evidence-status';
    node.type = 'button';
    node.textContent = 'Recording';
    node.title = 'Course recording and synchronization status';
    node.setAttribute('aria-label', 'Course recording and synchronization status');
    const widget = new Widget({ node });
    statusBar.registerStatusItem(PLUGIN_ID, { item: widget, align: 'right', rank: 0 });

    async function api(endpoint, method = 'GET', payload = undefined) {
      const url = URLExt.join(settings.baseUrl, `api/course-evidence/${endpoint}`);
      const init = { method, cache: 'no-store' };
      if (payload !== undefined) {
        init.body = JSON.stringify(payload);
        init.headers = { 'Content-Type': 'application/json' };
      }
      const response = await ServerConnection.makeRequest(url, init, settings);
      if (!response.ok) {
        let detail = `request failed (${response.status})`;
        try {
          const error = await response.json();
          detail = error.message || error.error || detail;
        } catch {}
        throw new Error(detail);
      }
      const contentType = response.headers.get('content-type') || '';
      return contentType.includes('application/json') ? response.json() : response.text();
    }

    let lastStatus = null;
    async function refreshStatus() {
      try {
        lastStatus = await api('status');
        const label = statusLabels[lastStatus.status] || 'Recording';
        node.textContent = label;
        node.classList.toggle('keio-course-evidence-offline', lastStatus.status === 'offline');
        node.classList.toggle('keio-course-evidence-attention', lastStatus.status === 'attention');
        const last = lastStatus.last_successful_sync ? `Last sync: ${lastStatus.last_successful_sync}` : 'Not synchronized yet';
        node.title = `${label} · ${lastStatus.pending_events} pending events · ${last}`;
      } catch {
        node.textContent = 'Attention needed';
        node.classList.add('keio-course-evidence-attention');
        node.title = 'Course recording status is unavailable. Notebook work remains available.';
      }
    }

    async function showStatusDialog() {
      const body = document.createElement('div');
      body.className = 'keio-course-evidence-dialog';
      const status = document.createElement('p');
      const snapshot = lastStatus || {};
      status.textContent = `${statusLabels[snapshot.status] || 'Recording'} · ${snapshot.pending_events || 0} pending event(s). ${snapshot.last_successful_sync ? `Last successful sync: ${snapshot.last_successful_sync}.` : 'No successful sync has been recorded yet.'}`;
      const disclosure = document.createElement('p');
      disclosure.textContent = 'The course workspace records visible OpenCode messages, allowlisted tool outcomes, selected notebook cell change/execution metadata, notebook save checkpoints, and bounded SysML model checkpoints. It is used for student feedback and instructor review. Hidden reasoning, credentials, unrelated files, and general computer activity are excluded. Local evidence is retained while offline; submitted records cannot prove activity outside this workspace.';
      const link = document.createElement('a');
      link.href = URLExt.join(settings.baseUrl, 'api/course-evidence/disclosure');
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'Read the full recording and privacy disclosure';
      body.append(status, disclosure, link);
      const result = await showDialog({
        title: 'Course activity recording',
        body: new Widget({ node: body }),
        buttons: [Dialog.cancelButton({ label: 'Close' }), Dialog.createButton({ label: 'Sync now', accept: true }), Dialog.createButton({ label: 'Enroll', accept: true }), Dialog.createButton({ label: 'Export local evidence', accept: true }), Dialog.createButton({ label: 'Export performance log', accept: true })]
      });
      if (!result.button.accept) return;
      const action = result.button.label;
      if (action === 'Sync now') {
        try {
          const response = await api('sync', 'POST', {});
          await refreshStatus();
          await showDialog({ title: 'Synchronization complete', body: `Accepted ${response.accepted || 0} event(s). ${response.pending_events || 0} remain queued.`, buttons: [Dialog.okButton()] });
        } catch (error) {
          await refreshStatus();
          await showDialog({ title: 'Synchronization queued', body: `${error.message}. Local evidence remains saved for retry.`, buttons: [Dialog.okButton()] });
        }
      } else if (action === 'Enroll') {
        const form = document.createElement('div');
        const label = document.createElement('label');
        label.textContent = 'One-time enrollment code from your instructor';
        const input = document.createElement('input');
        input.type = 'password';
        input.autocomplete = 'off';
        input.className = 'keio-course-enrollment-code';
        label.appendChild(input);
        form.appendChild(label);
        const enrollResult = await showDialog({ title: 'Enroll this course workspace', body: new Widget({ node: form }), buttons: [Dialog.cancelButton(), Dialog.createButton({ label: 'Enroll', accept: true })] });
        if (!enrollResult.button.accept || !input.value) return;
        try {
          await api('enroll', 'POST', { enrollment_code: input.value });
          input.value = '';
          await refreshStatus();
          await showDialog({ title: 'Enrollment complete', body: 'This workspace can submit course evidence when the instructor endpoint is reachable.', buttons: [Dialog.okButton()] });
        } catch (error) {
          input.value = '';
          await showDialog({ title: 'Enrollment failed', body: `${error.message}. Ask the instructor to verify the code and collector setup.`, buttons: [Dialog.okButton()] });
        }
      } else if (action === 'Export local evidence') {
        window.open(URLExt.join(settings.baseUrl, 'api/course-evidence/export'), '_blank', 'noopener');
      } else if (action === 'Export performance log') {
        window.open(URLExt.join(settings.baseUrl, 'api/course-evidence/performance-export'), '_blank', 'noopener');
      }
    }
    node.addEventListener('click', () => { void showStatusDialog(); });
    void refreshStatus();
    window.setInterval(() => { void refreshStatus(); }, 15000);

    const pending = new Map();
    const sentRuns = new Map();
    const settingsPromise = ServerConnection.makeSettings();
    const currentSessionId = () => tracker.currentWidget?.sessionContext?.session?.kernel?.id || 'jupyter-local';
    async function recordActivity(kind, path, payload, sourceRef, sessionId = currentSessionId()) {
      if (!path || !(path.endsWith('.ipynb') || path.endsWith('.sysml'))) return;
      try {
        await api('activity', 'POST', { kind, session_id: sessionId, source_ref: sourceRef, payload: { relative_path: path, ...payload } });
      } catch { /* Collection failure never blocks editing or execution. */ }
    }
    function relativeNotebookPath(panel) {
      return panel?.context?.path || null;
    }
    function readCell(panel, index) {
      const model = panel?.model?.cells?.get(index);
      const source = model?.sharedModel?.getSource?.() ?? model?.value?.text ?? '';
      return { model, source: String(source), id: model?.id || model?.sharedModel?.getId?.() || `cell-${index}` };
    }
    function attachNotebook(panel) {
      if (!panel || panel.__keioEvidenceAttached) return;
      panel.__keioEvidenceAttached = true;
      let strictSysmlMode = false;
      const attachCells = () => {
        for (let index = 0; index < panel.model.cells.length; index += 1) {
          const { model, id } = readCell(panel, index);
          if (!model || model.__keioEvidenceAttached) continue;
          model.__keioEvidenceAttached = true;
          model.contentChanged?.connect(async () => {
            clearTimeout(pending.get(id));
            const timer = window.setTimeout(async () => {
              const current = readCell(panel, index);
              const sourceHash = await sha256(current.source);
              await recordActivity('notebook.cell.changed', relativeNotebookPath(panel), { cell_id: id, source_sha256: sourceHash, source_chars: current.source.length }, `cell-change:${relativeNotebookPath(panel)}:${id}:${sourceHash}`, panel.sessionContext?.session?.kernel?.id || 'jupyter-local');
            }, 1500);
            pending.set(id, timer);
          });
        }
      };
      attachCells();
      panel.model.cells.changed.connect(attachCells);
      const onKernelMessage = async (_sender, message) => {
        const msgType = message?.header?.msg_type;
        const content = message?.content || {};
        if (msgType === 'execute_input') {
          const code = String(content.code || '');
          const strictCommand = code.trim().match(/^%strict(?:\s+(on|off))?$/i);
          if (strictCommand?.[1]) strictSysmlMode = strictCommand[1].toLowerCase() === 'on';
          let index = panel.content.activeCellIndex;
          if (!readCell(panel, index).source || readCell(panel, index).source !== code) {
            index = Array.from({ length: panel.model.cells.length }, (_, i) => i).find(i => readCell(panel, i).source === code) ?? index;
          }
          const cell = readCell(panel, index);
          const key = message.parent_header?.msg_id || `${Date.now()}-${cell.id}`;
          sentRuns.set(key, { cell_id: cell.id, code, path: relativeNotebookPath(panel), session_id: panel.sessionContext?.session?.kernel?.id || 'jupyter-local' });
        } else if (msgType === 'error') {
          const key = message.parent_header?.msg_id;
          const run = sentRuns.get(key);
          if (run) run.error = String(content.evalue || content.ename || 'execution error');
        } else if (msgType === 'status' && content.execution_state === 'idle') {
          const key = message.parent_header?.msg_id;
          const run = sentRuns.get(key);
          if (!run) return;
          sentRuns.delete(key);
          const sourceHash = await sha256(run.code);
          await recordActivity('notebook.cell.executed', run.path, {
            cell_id: run.cell_id, source_sha256: sourceHash, source_chars: run.code.length,
            outcome: run.error ? 'error' : 'completed', ...(run.error ? { diagnostic: run.error.slice(0, 500) } : {})
          }, `cell-run:${run.path}:${run.cell_id}:${key}`, run.session_id);
          if (run.path && strictSysmlMode && !run.code.trimStart().startsWith('%')) {
            await recordActivity('sysml.validation', run.path, {
              cell_id: run.cell_id, source_sha256: sourceHash,
              parser: 'OpenSysML', parser_version: 'jupyter-opensysml-kernel==0.9.3.dev20261008',
              strict_conformance: true, outcome: run.error ? 'error' : 'completed',
              ...(run.error ? { diagnostic: run.error.slice(0, 500) } : {})
            }, `sysml-validation:${run.path}:${run.cell_id}:${key}`, run.session_id);
          }
        }
      };
      let attachedKernel = null;
      const attachKernel = () => {
        const kernel = panel.sessionContext?.session?.kernel || null;
        if (kernel === attachedKernel) return;
        if (attachedKernel) {
          attachedKernel.iopubMessage?.disconnect(onKernelMessage);
          for (const [key, run] of sentRuns) {
            if (run.path === relativeNotebookPath(panel)) sentRuns.delete(key);
          }
        }
        attachedKernel = kernel;
        strictSysmlMode = false;
        attachedKernel?.iopubMessage?.connect(onKernelMessage);
      };
      panel.sessionContext?.sessionChanged?.connect(attachKernel);
      attachKernel();
    }
    tracker.widgetAdded.connect((_sender, panel) => attachNotebook(panel));
    for (const panel of tracker) attachNotebook(panel);
    void settingsPromise;
  }
};

export default plugin;
