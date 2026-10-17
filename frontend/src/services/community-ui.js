// Shared presentation and retry rules. No network or persisted chat/draft storage.
export const REPORT_STATUS = {
  unverified: 'Unverified', community_corroborated: 'Community corroborated',
  disputed: 'Disputed', resolved: 'Resolved',
}
export const HISTORY_ACTION = {
  report_created: 'Barrier reported', vote_updated: 'Report vote updated',
  clearance_submitted: 'Clearing observation submitted', clearance_vote_updated: 'Clearing vote updated',
}
export function formatTime(value) {
  if (!value || !Number.isFinite(new Date(value).getTime())) return 'Date unknown'
  return new Date(value).toLocaleString('en-GB')
}
export function localDateTime(value = new Date()) {
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 23)
}
export function chatHistory(turns) {
  return turns.flatMap(turn => [
    { role: 'user', content: turn.question }, { role: 'assistant', content: turn.reply.answer },
  ]).slice(-6)
}
export function retrySubmission(makeId = () => crypto.randomUUID()) {
  let previous = null
  return {
    prepare(body) {
      const encoded = JSON.stringify(body)
      if (!previous || previous.encoded !== encoded) {
        previous = { encoded, key: makeId(), body: JSON.parse(encoded) }
      }
      return { key: previous.key, body: JSON.parse(JSON.stringify(previous.body)) }
    },
    reset() { previous = null },
  }
}
