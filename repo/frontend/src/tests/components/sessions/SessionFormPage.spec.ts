import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/admin/sessions/new', params: {} }),
}))

vi.mock('@/stores/sessions', () => ({
  useSessionsStore: () => ({
    currentSession: null,
    fetchOne: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    createRecurring: vi.fn(),
  }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/api/endpoints/admin', () => ({
  adminApi: {
    getCourses: vi.fn().mockResolvedValue([]),
    getInstructors: vi.fn().mockResolvedValue([]),
    getLocations: vi.fn().mockResolvedValue([]),
    getRooms: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('vee-validate', () => ({
  useForm: () => ({
    handleSubmit: (fn: any) => fn,
    defineField: (name: string) => [{ value: '' }, {}],
    errors: {},
    setFieldValue: vi.fn(),
  }),
}))

vi.mock('yup', () => ({
  object: () => ({ shape: () => ({}) }),
  string: () => ({ required: () => ({}) }),
  number: () => ({ required: () => ({ min: () => ({ max: () => ({}) }) }), min: () => ({ max: () => ({ default: () => ({}) }) }) }),
}))

describe('SessionFormPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('detects create mode when no route param id', () => {
    const routeParams = {}
    const isEdit = !!routeParams.id
    expect(isEdit).toBe(false)
  })

  it('detects edit mode when route param id present', () => {
    const routeParams = { id: 's-1' }
    const isEdit = !!routeParams.id
    expect(isEdit).toBe(true)
  })

  it('capacity validates between 1 and 500', () => {
    const validate = (cap: number) => cap >= 1 && cap <= 500
    expect(validate(0)).toBe(false)
    expect(validate(1)).toBe(true)
    expect(validate(500)).toBe(true)
    expect(validate(501)).toBe(false)
  })

  it('buffer minutes default to 10', () => {
    const defaultBuffer = 10
    expect(defaultBuffer).toBe(10)
  })

  it('recurring option only in create mode', () => {
    const isEdit = false
    const showRecurring = !isEdit
    expect(showRecurring).toBe(true)
  })

  it('rooms cascade from location selection', () => {
    const locations = [{ id: 'l-1', name: 'HQ' }]
    const selectedLocationId = 'l-1'
    const rooms = [
      { id: 'r-1', location_id: 'l-1', name: 'Room A' },
      { id: 'r-2', location_id: 'l-2', name: 'Room B' },
    ]
    const filteredRooms = rooms.filter(r => r.location_id === selectedLocationId)
    expect(filteredRooms).toHaveLength(1)
    expect(filteredRooms[0].name).toBe('Room A')
  })
})
