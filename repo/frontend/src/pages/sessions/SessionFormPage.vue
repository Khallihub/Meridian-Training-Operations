<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm } from 'vee-validate'
import * as yup from 'yup'
import { useSessionsStore } from '@/stores/sessions'
import { useUiStore } from '@/stores/ui'
import { adminApi } from '@/api/endpoints/admin'
import AppLayout from '@/layouts/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const sessions = useSessionsStore()
const ui = useUiStore()

const editId = route.params.id as string | undefined
const isEdit = !!editId
const isRecurring = ref(false)
const courses = ref<any[]>([])
const instructors = ref<any[]>([])
const locations = ref<any[]>([])
const rooms = ref<any[]>([])

const schema = yup.object({
  title: yup.string().required('Required'),
  course_id: yup.string().uuid().required('Required'),
  instructor_id: yup.string().uuid().required('Required'),
  room_id: yup.string().uuid().required('Required'),
  start_time: yup.string().required('Required'),
  end_time: yup.string().required('Required'),
  capacity: yup.number().min(1).max(500).required('Required'),
  buffer_minutes: yup.number().min(0).max(60).default(10),
  rrule: yup.string().when('$recurring', { is: true, then: s => s.required('RRULE required for recurring') }),
})

const { defineField, handleSubmit, errors, setValues } = useForm({ validationSchema: schema })
const [title, titleAttrs] = defineField('title')
const [courseId, courseAttrs] = defineField('course_id')
const [instructorId, instrAttrs] = defineField('instructor_id')
const [roomId, roomAttrs] = defineField('room_id')
const [startTime, startAttrs] = defineField('start_time')
const [endTime, endAttrs] = defineField('end_time')
const [capacity, capAttrs] = defineField('capacity')
const [bufferMinutes, bufferAttrs] = defineField('buffer_minutes')
const [rrule, rruleAttrs] = defineField('rrule')
const recurrenceEndDate = ref('')

const isSubmitting = ref(false)

onMounted(async () => {
  const [c, i, l] = await Promise.all([
    adminApi.getCourses(), adminApi.getInstructors(), adminApi.getLocations()
  ])
  courses.value = c
  instructors.value = i
  locations.value = l

  if (isEdit) {
    await sessions.fetchOne(editId)
    const s = sessions.currentSession!
    setValues({
      title: s.title,
      course_id: s.course_id, instructor_id: s.instructor_id, room_id: s.room_id,
      start_time: s.start_time.slice(0, 16), end_time: s.end_time.slice(0, 16),
      capacity: s.capacity, buffer_minutes: s.buffer_minutes,
    })
    if (s.room_id && s.location_id) handleLocationChange(s.location_id)
  }
})

async function handleLocationChange(locId: string) {
  rooms.value = await adminApi.getRooms(locId)
}

const onSubmit = handleSubmit(async (values) => {
  isSubmitting.value = true
  try {
    if (isEdit) {
      await sessions.update(editId, values)
      ui.addToast('Session updated', 'success')
    } else if (isRecurring.value) {
      await sessions.createRecurring({
        title: values.title,
        course_id: values.course_id,
        instructor_id: values.instructor_id,
        room_id: values.room_id,
        capacity: values.capacity,
        buffer_minutes: values.buffer_minutes,
        recurrence: {
          rrule_string: rrule.value,
          start_date: values.start_time,
          end_date: recurrenceEndDate.value || undefined,
        },
      })
      ui.addToast('Recurring sessions created', 'success')
    } else {
      await sessions.create(values)
      ui.addToast('Session created', 'success')
    }
    router.back()
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <AppLayout>
    <div class="max-w-2xl">
      <h1 class="text-xl font-semibold text-foreground mb-6">{{ isEdit ? 'Edit Session' : 'New Session' }}</h1>
      <div class="bg-card border border-border rounded-lg p-6">
        <form @submit.prevent="onSubmit" class="flex flex-col gap-5">
          <!-- Title -->
          <div>
            <label class="block text-sm font-medium mb-1">Session Title</label>
            <input v-model="title" v-bind="titleAttrs" type="text" placeholder="e.g. Introduction to Python — Week 1" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            <p v-if="errors.title" class="text-xs text-destructive mt-1">{{ errors.title }}</p>
          </div>

          <!-- Course -->
          <div>
            <label class="block text-sm font-medium mb-1">Course</label>
            <select v-model="courseId" v-bind="courseAttrs" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
              <option value="">Select course…</option>
              <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.title }}</option>
            </select>
            <p v-if="errors.course_id" class="text-xs text-destructive mt-1">{{ errors.course_id }}</p>
          </div>

          <!-- Instructor -->
          <div>
            <label class="block text-sm font-medium mb-1">Instructor</label>
            <select v-model="instructorId" v-bind="instrAttrs" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
              <option value="">Select instructor…</option>
              <option v-for="i in instructors" :key="i.id" :value="i.id">{{ i.username }}</option>
            </select>
          </div>

          <!-- Location → Room cascade -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Location</label>
              <select @change="handleLocationChange(($event.target as HTMLSelectElement).value)" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
                <option value="">Select location…</option>
                <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Room</label>
              <select v-model="roomId" v-bind="roomAttrs" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
                <option value="">Select room…</option>
                <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }} (cap {{ r.capacity }})</option>
              </select>
            </div>
          </div>

          <!-- Times -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Start</label>
              <input v-model="startTime" v-bind="startAttrs" type="datetime-local" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
              <p v-if="errors.start_time" class="text-xs text-destructive mt-1">{{ errors.start_time }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">End</label>
              <input v-model="endTime" v-bind="endAttrs" type="datetime-local" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Capacity</label>
              <input v-model="capacity" v-bind="capAttrs" type="number" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Buffer (min)</label>
              <input v-model="bufferMinutes" v-bind="bufferAttrs" type="number" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
          </div>

          <!-- Recurring toggle -->
          <div v-if="!isEdit" class="flex items-center gap-2">
            <input id="recurring" type="checkbox" v-model="isRecurring" class="rounded" />
            <label for="recurring" class="text-sm">Recurring session</label>
          </div>
          <div v-if="isRecurring" class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">RRULE string</label>
              <input v-model="rrule" v-bind="rruleAttrs" type="text" placeholder="FREQ=WEEKLY;BYDAY=TU,TH;BYHOUR=18" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm font-mono" />
              <p v-if="errors.rrule" class="text-xs text-destructive mt-1">{{ errors.rrule }}</p>
              <p class="text-xs text-muted-foreground mt-1">e.g. FREQ=WEEKLY;BYDAY=TU,TH;BYHOUR=18;BYMINUTE=30</p>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Series end date (optional)</label>
              <input v-model="recurrenceEndDate" type="datetime-local" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
              <p class="text-xs text-muted-foreground mt-1">Leave blank to use RRULE UNTIL/COUNT clause.</p>
            </div>
          </div>

          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="isSubmitting" class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50 flex items-center gap-2">
              <div v-if="isSubmitting" class="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              {{ isEdit ? 'Save Changes' : (isRecurring ? 'Create Series' : 'Create Session') }}
            </button>
            <button type="button" @click="router.back()" class="px-4 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
