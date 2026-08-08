import { FetchError, type FetchOptions } from 'ofetch'

export interface ApiError {
  statusCode: number
  message: string
  code?: string
  email?: string
}

type RequestOptions = Omit<FetchOptions, 'method' | 'baseURL' | 'body'>
type RequestMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
type RequestBody = FetchOptions['body']

interface ValidationErrorItem {
  msg: string
}

interface StructuredErrorDetail {
  message: string
  code?: string
  email?: string
}

function isStructuredErrorDetail(detail: unknown): detail is StructuredErrorDetail {
  return typeof detail === 'object' && detail !== null && 'message' in detail
}

function normalizeApiError(error: unknown): ApiError {
  if (error instanceof FetchError) {
    const statusCode = error.statusCode ?? 500
    const detail = (error.data as { detail?: unknown } | undefined)?.detail

    if (isStructuredErrorDetail(detail)) {
      return { statusCode, message: detail.message, code: detail.code, email: detail.email }
    }

    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? (detail as ValidationErrorItem[]).map((validationError) => validationError.msg).join(', ')
        : error.message

    return { statusCode, message }
  }

  return { statusCode: 500, message: 'Unexpected error, please try again' }
}

export function useApi() {
  const runtimeConfig = useRuntimeConfig()
  const authStore = useAuthStore()
  const router = useRouter()

  async function request<T>(path: string, method: RequestMethod, options: RequestOptions = {}, body?: RequestBody): Promise<T> {
    try {
      return await $fetch<T>(path, {
        ...options,
        method,
        body,
        baseURL: import.meta.server ? runtimeConfig.apiBaseUrlInternal : runtimeConfig.public.apiBaseUrl,
        headers: {
          ...options.headers,
          ...(authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {})
        }
      })
    } catch (error) {
      const apiError = normalizeApiError(error)

      // The backend rejects an expired/invalid token the same way
      // ("Could not validate credentials") on every protected endpoint —
      // including lazy-loaded, out-of-the-way requests like an employee's
      // stats card, which may well be the first request fired long after
      // the token actually expired. `authStore.token` truthy is what tells
      // this apart from a genuine failed /auth/login attempt (no token yet
      // there, so this never fires on the login page itself). Without this,
      // every such call would just render the raw backend error text as if
      // it were data instead of prompting a re-login.
      if (apiError.statusCode === 401 && authStore.token && import.meta.client) {
        authStore.logout()
        router.push('/login')
      }

      throw apiError
    }
  }

  const apiGet = <T>(path: string, options?: RequestOptions): Promise<T> =>
    request<T>(path, 'GET', options)

  const apiPost = <T>(path: string, body?: RequestBody, options?: RequestOptions): Promise<T> =>
    request<T>(path, 'POST', options, body)

  const apiPut = <T>(path: string, body?: RequestBody, options?: RequestOptions): Promise<T> =>
    request<T>(path, 'PUT', options, body)

  const apiPatch = <T>(path: string, body?: RequestBody, options?: RequestOptions): Promise<T> =>
    request<T>(path, 'PATCH', options, body)

  const apiDelete = <T>(path: string, body?: RequestBody, options?: RequestOptions): Promise<T> =>
    request<T>(path, 'DELETE', options, body)

  const apiGetBlob = (path: string, options?: RequestOptions): Promise<Blob> =>
    request<Blob>(path, 'GET', { ...options, responseType: 'blob' })

  return { apiGet, apiPost, apiPut, apiPatch, apiDelete, apiGetBlob }
}
