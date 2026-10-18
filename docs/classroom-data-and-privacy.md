<table width="100%">
  <tr>
    <td align="left" valign="middle">
      <strong>Agentic Product Concept Modeling 2026</strong><br>
      Laurent Balmelli, Hidekazu Nishimura<br>
      vers 2, 18/10/26
    </td>
    <td align="right" valign="middle">
      <img src="./keio-logo.png" alt="Keio University" width="140">
    </td>
  </tr>
</table>

---

# Classroom Data and Privacy

## Purpose and notice

The course workspace records selected course interactions to support personalized feedback and instructor review of learning progression. The JupyterLab status bar reports the recording and synchronization state and links to this disclosure. Ask the instructor before entering private or unrelated personal information in a course chat or notebook.

The collection is not a final-grade generator. The instructor reviews evidence and makes assessment decisions. A laptop-controlled local log cannot prove that all course work or conversations passed through this workspace.

## What the recorder captures

- Student-visible messages sent in the course OpenCode chat and finalized, student-visible assistant text. Hidden reasoning is excluded.
- Pseudonymous local device/student identifiers, OpenCode session/message/part references, timestamps, and selected agent/skill transitions.
- Allowlisted tool names and completion/error summaries. Arbitrary tool arguments, full shell history, and unrestricted raw tool output are excluded.
- Links between coach questions and the next student reply when the relationship can be inferred; inferred links are marked as such. Original student text is retained without an AI paraphrase.
- Selected Jupyter notebook cell-change and execution metadata, notebook saves, and checkpoints for `.sysml` files under the course model folder. Notebook sources are represented by hashes/IDs; bounded text snapshots may be recorded for small course SysML models.
- Local synchronization receipts and failure details. Credentials and provider secrets are filtered best-effort and are never intentionally included.

The recorder does not monitor unrelated files, applications, browser history, global shell history, or activity outside the course workspace. It does not record hidden model reasoning or claim tamper-proof completeness. Credential filtering is best-effort; students should still avoid putting secrets in chat, notebooks, or models.

## Local storage and submission

Local JSONL logs, a SQLite delivery outbox, identity, and an enrollment token live in `workspace/private-course-data/`, which is host-backed and excluded from Git. They persist across container recreation. The original local event journal is retained after synchronization; only acknowledged outbox entries are marked complete. If the collector is unavailable, work continues and evidence remains queued. Use the status indicator's **Sync now** or **Export local evidence** action when needed.

No instructor endpoint is configured in a fresh checkout. Enrollment and synchronization begin only after an instructor configures the collector URL and provides a one-time enrollment code. Student submission credentials allow upload and status access for that student; they do not permit reading another student's records. Instructor retrieval requires a separate instructor credential.

## Decisions required before real classroom collection

The pilot software does not select Keio's production hosting, identity provider, data controller, legal basis, retention period, deletion process, backup policy, or access roster. The instructor and university must review the collection disclosure, approve the educational purpose and data handling, choose retention/deletion rules, secure a TLS endpoint and backups, and communicate the policy before issuing real student enrollments. Do not use the local staging collector for actual student evidence.

If you have questions about enrollment, synchronization, or your recorded course work, contact your instructor.
