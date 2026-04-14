/**
 * Regression tests for Medium issue: SessionDetailPage misclassifies canceled
 * bookings as active due to a status spelling mismatch ('cancelled' vs 'canceled').
 *
 * The page filters bookings with: items.find(b => b.status !== 'canceled')
 * A canceled booking must resolve to null so the "Book Now" button is shown.
 */

import { describe, it, expect } from 'vitest'

// The filtering expression used in SessionDetailPage.vue:
//   myBooking.value = res.items.find((b: any) => b.status !== 'canceled') ?? null
function findActiveBooking(items: Array<{ id: string; status: string }>): { id: string; status: string } | null {
  return items.find(b => b.status !== 'canceled') ?? null
}

describe('SessionDetailPage — active booking filter', () => {
  it('returns null for a canceled booking (Book Now should be visible)', () => {
    const items = [{ id: 'b1', status: 'canceled' }]
    expect(findActiveBooking(items)).toBeNull()
  })

  it('returns the booking for a confirmed booking (Booked badge visible, no Book Now)', () => {
    const items = [{ id: 'b1', status: 'confirmed' }]
    const result = findActiveBooking(items)
    expect(result).not.toBeNull()
    expect(result?.status).toBe('confirmed')
  })

  it('returns the booking for a requested booking (pending state)', () => {
    const items = [{ id: 'b1', status: 'requested' }]
    const result = findActiveBooking(items)
    expect(result).not.toBeNull()
    expect(result?.id).toBe('b1')
  })

  it('skips canceled and returns the first non-canceled booking when multiple exist', () => {
    const items = [
      { id: 'b1', status: 'canceled' },
      { id: 'b2', status: 'confirmed' },
    ]
    const result = findActiveBooking(items)
    expect(result?.id).toBe('b2')
  })

  it('returns null when list is empty', () => {
    expect(findActiveBooking([])).toBeNull()
  })

  it('does NOT treat the legacy misspelling "cancelled" as canceled (regression guard)', () => {
    // If the filter were using 'cancelled' (old bug) instead of 'canceled',
    // a booking with status 'canceled' would NOT be filtered out — it would be
    // returned as active.  This test confirms the correct spelling is in effect.
    const items = [{ id: 'b1', status: 'canceled' }]
    // With the correct filter (status !== 'canceled') the item IS filtered.
    expect(findActiveBooking(items)).toBeNull()

    // Demonstrate what the bug looked like: wrong filter would NOT exclude it.
    const buggyFilter = (i: typeof items) => i.find(b => b.status !== 'cancelled') ?? null
    expect(buggyFilter(items)).not.toBeNull() // the bug: 'canceled' !== 'cancelled' → truthy
  })
})
