import { createHash, randomUUID } from 'node:crypto';
import { appendFile, link, mkdir, readFile, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';

const COURSE_ID = 'keio-2026';
const MAX_TEXT = 20000;
const MAX_SNAPSHOT = 50000;
const toolAllowlist = new Set([
  'skill', 'read', 'glob', 'grep', 'bash', 'edit', 'write', 'apply_patch',
  'get_active_notebook', 'get_active_cell_id', 'read_notebook', 'read_cell',
  'add_cell', 'edit_cell', 'run_cell', 'run_all_cells', 'open_file',
]);
const secretPatterns = [
  /\bBearer\s+[A-Za-z0-9._~+/=-]{12,}/gi,
  /\bsk-[A-Za-z0-9_-]{16,}\b/g,
  /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/g,
  /\bAIza[0-9A-Za-z_-]{30,}\b/g,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g,
];

const cleanText = (value, limit = MAX_TEXT) => {
  let text = String(value ?? '').slice(0, limit);
  for (const pattern of secretPatterns) text = text.replace(pattern, '[REDACTED]');
  return text;
};
const safeId = value => String(value ?? 'session').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 96) || 'session';
const hash = value => createHash('sha256').update(value).digest('hex');
const canonical = value => JSON.stringify(value, Object.keys(value).sort());

async function ensureIdentity(dataDir) {
  await mkdir(dataDir, { recursive: true, mode: 0o700 });
  const identityPath = path.join(dataDir, 'identity.json');
  try {
    return JSON.parse(await readFile(identityPath, 'utf8'));
  } catch {
    const identity = { student_id: `student-${randomUUID()}`, device_id: randomUUID() };
    const temp = `${identityPath}.${process.pid}.tmp`;
    await writeFile(temp, `${JSON.stringify(identity)}\n`, { mode: 0o600, flag: 'wx' }).catch(async error => {
      if (error.code !== 'EEXIST') throw error;
    });
    await link(temp, identityPath).catch(error => {
      if (error.code !== 'EEXIST') throw error;
    });
    await unlink(temp).catch(() => {});
    try { return JSON.parse(await readFile(identityPath, 'utf8')); } catch { return identity; }
  }
}

export async function ClassroomRecorder({ directory }) {
  const dataDir = process.env.COURSE_DATA_DIR || '/home/keio/work/private-course-data';
  const identity = await ensureIdentity(dataDir);
  let questionBank = [];
  try {
    const bank = JSON.parse(await readFile(process.env.COURSE_QUESTION_BANK_PATH || '/opt/course/opencode/question-bank.json', 'utf8'));
    questionBank = Array.isArray(bank.questions) ? bank.questions : [];
  } catch {}
  const spoolDir = path.join(dataDir, 'spool');
  await mkdir(spoolDir, { recursive: true, mode: 0o700 });
  const agentByMessage = new Map();
  const activeSkillBySession = new Map();
  const pendingQuestionBySession = new Map();
  const sessionStarted = new Set();
  const queued = new Set();
  let writeChain = Promise.resolve();

  async function spool(event) {
    const file = path.join(spoolDir, `${safeId(event.session_id)}.jsonl`);
    await appendFile(file, `${JSON.stringify(event)}\n`, { mode: 0o600 });
  }

  async function emit(event) {
    const eventId = hash(`${COURSE_ID}\0${identity.device_id}\0${event.source}\0${event.source_ref}`);
    if (queued.has(eventId)) return;
    queued.add(eventId);
    const envelope = {
      schema_version: '1.0', event_id: eventId, course_id: COURSE_ID,
      student_id: identity.student_id, device_id: identity.device_id,
      session_id: String(event.session_id || 'local'), timestamp_utc: new Date().toISOString(),
      kind: event.kind, source: event.source, payload: event.payload || {},
    };
    for (const key of ['agent', 'skill', 'message_id', 'related_question_id']) {
      if (event[key]) envelope[key] = event[key];
    }
    writeChain = writeChain.then(async () => {
      const tokenPath = path.join(dataDir, '.ingest-token');
      let token = '';
      try { token = (await readFile(tokenPath, 'utf8')).trim(); } catch {}
      if (token) {
        try {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), 1200);
          const response = await fetch('http://127.0.0.1:8888/api/course-evidence/ingest', {
            method: 'POST', signal: controller.signal,
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify(envelope),
          });
          clearTimeout(timer);
          if (response.ok) return;
        } catch {}
      }
      await spool(envelope);
    }).catch(async () => spool(envelope));
    await writeChain;
  }

  function base(kind, source, sourceRef, sessionId, payload = {}, extra = {}) {
    return { kind, source, source_ref: sourceRef, session_id: sessionId, payload, ...extra };
  }

  function linkQuestion(sessionId, text, messageId) {
    if (!text.includes('?')) return null;
    const lower = text.toLowerCase();
    const match = questionBank.find(question => Array.isArray(question.match_keywords)
      && question.match_keywords.some(keyword => typeof keyword === 'string' && lower.includes(keyword.toLowerCase())));
    const questionId = match?.id || `coach-${hash(`${sessionId}\0${messageId}\0${text}`).slice(0, 12)}`;
    pendingQuestionBySession.set(sessionId, questionId);
    emit(base('coach.question', 'opencode', `question:${messageId}`, sessionId, {
      question_id: questionId, question: cleanText(text, 2000), message_id: messageId,
      association: match ? 'question-bank-topic-heuristic' : 'assistant-question-heuristic',
    }, { message_id: messageId, agent: 'sysml-design-coach' }));
    return questionId;
  }

  return {
    'chat.message': async (input, output) => {
      const message = output?.message;
      const sessionId = input?.sessionID || message?.sessionID;
      if (!sessionId || !message?.id) return;
      const text = (output?.parts || []).filter(part => part?.type === 'text').map(part => part.text || '').join('\n');
      const questionId = pendingQuestionBySession.get(sessionId) || null;
      await emit(base(questionId ? 'student.answer' : 'student.message', 'opencode', `message:${message.id}`, sessionId, {
        text: cleanText(text),
        ...(questionId ? { question_id: questionId, association: 'next-student-message-in-session' } : {}),
      }, { message_id: message.id, related_question_id: questionId || undefined }));
      if (questionId) pendingQuestionBySession.delete(sessionId);
    },
    event: async ({ event }) => {
      const type = event?.type;
      const properties = event?.properties || {};
      const sessionId = properties.sessionID;
      if (!sessionId) return;
      if (type === 'session.created' && !sessionStarted.has(sessionId)) {
        sessionStarted.add(sessionId);
        await emit(base('class.session.started', 'opencode', `session:${sessionId}:created`, sessionId, { started_at_ms: properties.info?.time?.created || Date.now() }));
        return;
      }
      if (type === 'session.deleted') {
        await emit(base('class.session.ended', 'opencode', `session:${sessionId}:deleted`, sessionId, {}));
        return;
      }
      if (type === 'session.next.agent.switched') {
        await emit(base('agent.switched', 'opencode', `agent:${properties.messageID || event.id}`, sessionId, { agent: cleanText(properties.agent, 120) }, { agent: properties.agent }));
        return;
      }
      if (type === 'permission.replied') {
        await emit(base('permission.decided', 'opencode', `permission:${properties.requestID || event.id}`, sessionId, { decision: properties.reply }));
        return;
      }
      if (type === 'message.updated') {
        const info = properties.info;
        if (info?.role === 'assistant' && info.id && info.agent) agentByMessage.set(info.id, info.agent);
        return;
      }
      if (type !== 'message.part.updated') return;
      const part = properties.part;
      if (!part || !part.id) return;
      const currentAgent = agentByMessage.get(part.messageID) || 'unknown';
      if (part.type === 'text' && currentAgent !== 'unknown' && part.time?.end && !part.synthetic && !part.ignored) {
        const text = cleanText(part.text);
        await emit(base('agent.message', 'opencode', `part:${part.id}`, sessionId, { text }, {
          message_id: part.messageID, agent: currentAgent, skill: activeSkillBySession.get(sessionId),
        }));
        if (currentAgent === 'sysml-design-coach') linkQuestion(sessionId, text, part.messageID);
        return;
      }
      if (part.type !== 'tool' || !toolAllowlist.has(part.tool)) return;
      const status = part.state?.status;
      if (status !== 'completed' && status !== 'error') return;
      const completed = part.state || {};
      if (part.tool === 'skill' && status === 'completed') {
        const name = completed.input?.name;
        if (typeof name === 'string' && /^[a-z][a-z0-9-]{1,50}$/.test(name)) {
          activeSkillBySession.set(sessionId, name);
          await emit(base('skill.loaded', 'opencode', `skill:${part.callID}`, sessionId, { name, trigger: 'skill-tool' }, { skill: name, agent: currentAgent, message_id: part.messageID }));
        }
      }
      const filePath = completed.input?.path || completed.input?.filename;
      const relativePath = typeof filePath === 'string' && /^\/home\/keio\/work\/models\/[A-Za-z0-9_.-]+\.sysml$/.test(filePath)
        ? filePath.replace('/home/keio/work/models/', '') : undefined;
      const summary = status === 'error' ? cleanText(completed.error || 'Tool reported an error', 500) : cleanText(completed.title || 'Completed', 250);
      await emit(base('tool.completed', 'opencode', `tool:${part.callID}`, sessionId, {
        tool: part.tool, outcome: status === 'completed' ? 'success' : 'error', summary,
        ...(relativePath ? { relative_path: relativePath } : {}),
      }, { agent: currentAgent, skill: activeSkillBySession.get(sessionId), message_id: part.messageID }));
    },
    dispose: async () => { await writeChain; },
  };
}

export default ClassroomRecorder;
