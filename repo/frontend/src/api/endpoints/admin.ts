import client from '../client'

export interface UserRecord {
  id: string
  username: string
  role: string
  email: string | null
  phone: string | null
  is_active: boolean
  last_login: string | null
  created_at: string
}

export interface Location {
  id: string
  name: string
  address: string
  timezone: string
  is_active: boolean
}

export interface Room {
  id: string
  location_id: string
  name: string
  capacity: number
  is_active: boolean
}

export interface Course {
  id: string
  title: string
  description: string
  duration_minutes: number
  price: number
  category: string
  is_active: boolean
}

export interface Instructor {
  id: string
  user_id: string
  username: string
  bio: string
  is_active: boolean
}

export interface Promotion {
  id: string
  name: string
  type: 'pct_off' | 'fixed_off' | 'bogo'
  value: number
  min_order_amount: number | null
  applies_to: string[] | 'all'
  stack_group: string | null
  is_exclusive: boolean
  is_active: boolean
  valid_from: string
  valid_until: string
}

export interface AuditLog {
  id: string
  actor_id: string
  actor_username: string
  entity_type: string
  entity_id: string
  action: string
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  ip_address: string
  created_at: string
}

export const adminApi = {
  // Users
  getUsers: async (params?: Record<string, unknown>) => {
    const res = await client.get('/api/users', { params })
    return { items: res.data.items as UserRecord[], total: res.data.meta.total_count as number }
  },
  getUser: async (id: string) => {
    const res = await client.get(`/api/users/${id}`)
    return res.data as UserRecord
  },
  createUser: async (payload: Partial<UserRecord> & { password: string }) => {
    const res = await client.post('/api/users', payload)
    return res.data as UserRecord
  },
  updateUser: async (id: string, payload: Partial<UserRecord>) => {
    const res = await client.patch(`/api/users/${id}`, payload)
    return res.data as UserRecord
  },
  deleteUser: async (id: string) => {
    await client.delete(`/api/users/${id}`)
  },

  // Locations
  getLocations: async () => {
    const res = await client.get('/api/locations')
    return res.data as Location[]
  },
  createLocation: async (payload: Partial<Location>) => {
    const res = await client.post('/api/locations', payload)
    return res.data as Location
  },
  updateLocation: async (id: string, payload: Partial<Location>) => {
    const res = await client.patch(`/api/locations/${id}`, payload)
    return res.data as Location
  },

  // Rooms
  getRooms: async (locationId: string) => {
    const res = await client.get(`/api/locations/${locationId}/rooms`)
    return res.data as Room[]
  },
  createRoom: async (locationId: string, payload: { name: string; capacity: number }) => {
    const res = await client.post(`/api/locations/${locationId}/rooms`, payload)
    return res.data as Room
  },

  // Courses
  getCourses: async () => {
    const res = await client.get('/api/courses')
    return res.data as Course[]
  },
  createCourse: async (payload: Partial<Course>) => {
    const res = await client.post('/api/courses', payload)
    return res.data as Course
  },
  updateCourse: async (id: string, payload: Partial<Course>) => {
    const res = await client.patch(`/api/courses/${id}`, payload)
    return res.data as Course
  },

  // Instructors
  getInstructors: async () => {
    const res = await client.get('/api/instructors')
    return res.data as Instructor[]
  },
  createInstructor: async (payload: Partial<Instructor>) => {
    const res = await client.post('/api/instructors', payload)
    return res.data as Instructor
  },

  // Promotions
  getPromotions: async () => {
    const res = await client.get('/api/promotions')
    return res.data as Promotion[]
  },
  createPromotion: async (payload: Partial<Promotion>) => {
    const res = await client.post('/api/promotions', payload)
    return res.data as Promotion
  },
  updatePromotion: async (id: string, payload: Partial<Promotion>) => {
    const res = await client.patch(`/api/promotions/${id}`, payload)
    return res.data as Promotion
  },
  deletePromotion: async (id: string) => {
    await client.delete(`/api/promotions/${id}`)
  },
  previewPromotion: async (payload: object) => {
    const res = await client.post('/api/promotions/preview', payload)
    return res.data
  },

  // Audit logs
  getAuditLogs: async (params?: Record<string, unknown>) => {
    const clean = Object.fromEntries(Object.entries(params ?? {}).filter(([, v]) => v !== '' && v != null))
    const res = await client.get('/api/audit-logs', { params: clean })
    return { items: res.data.items as AuditLog[], total: res.data.meta.total_count as number }
  },
}
