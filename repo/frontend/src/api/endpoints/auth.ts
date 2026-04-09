import client from '../client'

export const authApi = {
  login: async (username: string, password: string) => {
    const res = await client.post('/api/auth/login', { username, password })
    return res.data as { access_token: string; refresh_token: string }
  },
  refresh: async (refreshToken: string) => {
    const res = await client.post('/api/auth/refresh', { refresh_token: refreshToken })
    return res.data as { access_token: string; refresh_token: string }
  },
  logout: async () => {
    await client.post('/api/auth/logout')
  },
  changePassword: async (currentPassword: string, newPassword: string) => {
    await client.post('/api/auth/change-password', { current_password: currentPassword, new_password: newPassword })
  },
}
