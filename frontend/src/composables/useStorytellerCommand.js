import { ref, unref } from 'vue'

export function useStorytellerCommand({ connected }) {
  const pending = ref([])
  const error = ref(null)

  function clearError(key = null) {
    if (!key || error.value?.key === key) error.value = null
  }

  async function run(key, operation) {
    clearError()
    if (!unref(connected)) {
      error.value = { key, message: '连接中，暂时不能操作' }
      return null
    }
    if (pending.value.includes(key)) return null

    pending.value = [...pending.value, key]
    try {
      return await operation()
    } catch (cause) {
      const nextError = {
        key,
        message: cause?.message || '操作失败，请稍后重试',
      }
      if (cause?.code) nextError.code = cause.code
      if (cause?.details) nextError.details = cause.details
      if (cause?.status) nextError.status = cause.status
      error.value = nextError
      return null
    } finally {
      pending.value = pending.value.filter((item) => item !== key)
    }
  }

  return { pending, error, run, clearError }
}
