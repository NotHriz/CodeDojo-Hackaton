import test from 'node:test'
import assert from 'node:assert/strict'
import { retrySubmission, chatHistory, formatTime, localDateTime } from '../src/services/community-ui.js'

test('retries keep UUID and full payload until content changes or success resets it', () => {
  let next = 0
  const retry = retrySubmission(() => `key-${++next}`)
  const body = { description: 'Cleared', observed_at: '2026-10-17T02:00:00Z', evidence_urls: [] }
  const first = retry.prepare(body)
  body.description = 'Edited'
  assert.equal(first.body.description, 'Cleared')
  const same = retry.prepare({ ...body, description: 'Cleared' })
  assert.deepEqual(same, first)
  assert.equal(retry.prepare(body).key, 'key-2')
  retry.reset()
  assert.equal(retry.prepare(body).key, 'key-3')
})

test('history keeps newest six valid messages including full assistant response', () => {
  const longAnswer = 'A'.repeat(3000) + '\nFictional demo'
  const turns = Array.from({ length: 5 }, (_, i) => ({ question: `Q${i}`, reply: { answer: i === 4 ? longAnswer : `A${i}`, sources: [{ id: 'private-ui-only' }] } }))
  const history = chatHistory(turns)
  assert.equal(history.length, 6)
  assert.equal(history[0].content, 'Q2')
  assert.equal(history.at(-1).content, longAnswer)
  assert.deepEqual(Object.keys(history[0]), ['role', 'content'])
})

test('missing and invalid dates remain unknown', () => {
  assert.equal(formatTime(null), 'Date unknown')
  assert.equal(formatTime('bad'), 'Date unknown')
  assert.notEqual(formatTime('2026-10-17T02:00:00Z'), 'Date unknown')
})

test('clearing input preserves seconds so a recent report is not rounded before its event', () => {
  const value = new Date('2026-10-17T02:23:45.678Z')
  assert.equal(new Date(localDateTime(value)).getTime(), value.getTime())
})
